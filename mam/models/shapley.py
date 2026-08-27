import polars as pl
import numpy as np
import math
from .base import BaseModel


class ShapleyModel(BaseModel):
    def __init__(
        self, max_size: int = 4, value_column: str = "conv_rate", separator: str = " > "
    ):
        self.max_size = max_size
        self.value_column = value_column
        self.separator = separator
        self.conv_table = None
        self.model_name = None

    def _calculate_shapley_for_journey(self, journey_channels, conv_dict, order):
        n = len(journey_channels)
        if n == 0:
            return []

        # Precompute weight matrix W of shape (2^n - 1, n)
        num_coalitions = (1 << n) - 1
        W = np.zeros((num_coalitions, n))
        V = np.zeros(num_coalitions)

        # Para cada coalizão representada por máscara de bits de 1 a 2^n - 1
        for mask in range(1, 1 << n):
            idx = mask - 1
            active_indices = [i for i in range(n) if (mask & (1 << i)) != 0]
            s = len(active_indices)

            coalition_channels = [journey_channels[i] for i in active_indices]
            if not order:
                coalition_channels = sorted(coalition_channels)

            key = self.separator.join(coalition_channels)
            V[idx] = conv_dict.get(key, 0.0)

            for i in range(n):
                if (mask & (1 << i)) != 0:
                    W[idx, i] = (
                        math.factorial(s - 1)
                        * math.factorial(n - s)
                        / math.factorial(n)
                    )
                else:
                    W[idx, i] = (
                        -math.factorial(s)
                        * math.factorial(n - s - 1)
                        / math.factorial(n)
                    )

        shapley_vals = V @ W
        return list(shapley_vals)

    def _compute_shapley(self, df: pl.DataFrame, order: bool = False):
        # 1. Gerar tabela de conversão de jornadas
        channels_utf8 = pl.col("channels").cast(pl.List(pl.Utf8))
        if order:
            unique_expr = channels_utf8.list.unique(maintain_order=True)
        else:
            unique_expr = channels_utf8.list.unique().list.sort()

        if self.max_size is not None:
            unique_expr = unique_expr.list.slice(-self.max_size)

        df_temp = df.with_columns(
            unique_expr.list.join(self.separator).alias("combinations")
        )

        conv_table = (
            df_temp.group_by("combinations")
            .agg(
                [
                    (pl.col("has_conversion").cast(pl.Int64) * pl.col("weight"))
                    .sum()
                    .alias("conversions"),
                    pl.col("weight").sum().alias("total_sequences"),
                ]
            )
            .with_columns(
                (pl.col("conversions") / pl.col("total_sequences")).alias("conv_rate"),
                pl.col("conversions").cast(pl.Float64).alias("conversion_value"),
            )
        )

        # Filtro de conversões > 0
        conv_table_filtered = conv_table.filter(pl.col("conversions") > 0)

        # Mapeamento rápido para busca
        conv_dict = dict(
            zip(
                conv_table_filtered["combinations"],
                conv_table_filtered[self.value_column],
            )
        )

        results = []
        for comb in conv_table_filtered["combinations"]:
            journey_channels = comb.split(self.separator)
            shapley_vals = self._calculate_shapley_for_journey(
                journey_channels, conv_dict, order
            )
            results.append(shapley_vals)

        # Nome do modelo consistente com legado
        model_name = f"attribution_shapley_size{self.max_size}_{self.value_column}"
        if order:
            model_name = model_name + "_order_algorithmic"
        else:
            model_name = model_name + "_algorithmic"
        self.model_name = model_name

        # Pós-processamento dos pesos conforme regras do legado
        processed_results = []
        if self.value_column in ("conv_rate", "custom_value"):
            for res, total_seq, conv_val in zip(
                results,
                conv_table_filtered["total_sequences"],
                conv_table_filtered["conversion_value"],
            ):
                res_arr = np.array(res) * total_seq
                sum_res = res_arr.sum()
                if sum_res != 0:
                    res_arr = (res_arr / sum_res) * conv_val
                processed_results.append(list(res_arr))
        else:
            processed_results = results

        conv_table_filtered = conv_table_filtered.with_columns(
            pl.Series(name=model_name, values=processed_results)
        )

        self.conv_table = conv_table_filtered
        return conv_table_filtered

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.conv_table is None:
            self._compute_shapley(df)

        # Construir flat_weights_df para junção eficiente
        flat_combs = []
        flat_channels = []
        flat_weights = []
        for row in self.conv_table.iter_rows(named=True):
            comb = row["combinations"]
            comb_channels = comb.split(self.separator)
            weights = row[self.model_name]
            for chan, w in zip(comb_channels, weights):
                flat_combs.append(comb)
                flat_channels.append(chan)
                flat_weights.append(w)

        flat_weights_df = pl.DataFrame(
            {
                "combinations": flat_combs,
                "channels": flat_channels,
                "attribution_val": flat_weights,
            }
        )

        # Gerar a coluna "combinations" no df original
        channels_utf8 = pl.col("channels").cast(pl.List(pl.Utf8))
        unique_expr = channels_utf8.list.unique().list.sort()
        if self.max_size is not None:
            unique_expr = unique_expr.list.slice(-self.max_size)

        df_with_comb = df.with_columns(
            unique_expr.list.join(self.separator).alias("combinations")
        )

        # Calcular a soma dos pesos de conversão por combinação
        df_conv_weights = (
            df_with_comb.filter(pl.col("has_conversion"))
            .group_by("combinations")
            .agg(pl.col("weight").sum().alias("sum_conv_weight"))
        )

        df_with_comb = df_with_comb.join(df_conv_weights, on="combinations", how="left")

        exploded = df_with_comb.select(
            [
                "journey_id",
                "combinations",
                "channels",
                "has_conversion",
                "weight",
                "sum_conv_weight",
            ]
        ).explode("channels")
        exploded = exploded.with_columns(pl.col("channels").cast(pl.Utf8))

        exploded = (
            exploded.join(flat_weights_df, on=["combinations", "channels"], how="left")
            .with_columns(
                [pl.col("attribution_val").fill_null(0.0).alias("attribution_val")]
            )
            .with_columns(
                pl.col("attribution_val")
                .sum()
                .over("journey_id")
                .alias("journey_sum_val")
            )
            .with_columns(
                pl.when(pl.col("has_conversion") & (pl.col("journey_sum_val") > 0))
                .then(
                    pl.col("attribution_val")
                    * pl.col("weight").cast(pl.Float64)
                    * (
                        pl.col("has_conversion").cast(pl.Float64)
                        / pl.col("journey_sum_val")
                    )
                )
                .otherwise(0.0)
                .alias("attribution_value")
            )
        )

        return exploded

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        if self.conv_table is None:
            self._compute_shapley(df)

        exploded = self.conv_table.select(
            [
                pl.col("combinations").str.split(self.separator).alias("channels"),
                pl.col(self.model_name).alias("weight"),
            ]
        ).explode(["channels", "weight"])

        return (
            exploded.group_by("channels")
            .agg(pl.col("weight").sum().alias("attribution"))
            .sort("attribution", descending=True)
        )
