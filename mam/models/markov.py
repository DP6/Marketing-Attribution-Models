import polars as pl
import numpy as np
import pandas as pd
from .base import BaseModel


class MarkovModel(BaseModel):
    def __init__(self, transition_to_same_state: bool = False):
        self.transition_to_same_state = transition_to_same_state
        self.transition_matrix_df = None
        self.removal_effect_df = None
        self.channels_names = None
        self._calculated_weights = None

    def _build_transition_matrix(self, df: pl.DataFrame):
        # 1. Construção de Caminhos Estendidos
        extended_df = df.with_columns(
            pl.concat_list(
                [
                    pl.lit(["(inicio)"]),
                    pl.col("channels").cast(pl.List(pl.Utf8)),
                    pl.when(pl.col("has_conversion"))
                    .then(pl.lit(["(conversion)"]))
                    .otherwise(pl.lit(["(null)"])),
                ]
            ).alias("extended_channels")
        )

        # 2. Criação de Pares de Transição
        transitions_df = (
            extended_df.with_columns(
                [
                    pl.col("extended_channels")
                    .list.slice(0, pl.col("extended_channels").list.len() - 1)
                    .alias("orig_list"),
                    pl.col("extended_channels")
                    .list.slice(1, pl.col("extended_channels").list.len() - 1)
                    .alias("dest_list"),
                ]
            )
            .explode(["orig_list", "dest_list"])
            .group_by(["orig_list", "dest_list"])
            .agg(pl.col("weight").sum().alias("transition_count"))
        )

        if not self.transition_to_same_state:
            transitions_df = transitions_df.filter(
                pl.col("orig_list") != pl.col("dest_list")
            )

        # 3. Mapeamento de Estados para Índices
        all_states = set(transitions_df["orig_list"].unique().to_list()) | set(
            transitions_df["dest_list"].unique().to_list()
        )
        channels = sorted(list(all_states - {"(inicio)", "(null)", "(conversion)"}))
        channels_names = ["(inicio)"] + channels + ["(null)", "(conversion)"]
        self.channels_names = channels_names

        state_to_idx = {name: idx for idx, name in enumerate(channels_names)}

        transitions_with_idx = transitions_df.with_columns(
            [
                pl.col("orig_list")
                .replace_strict(state_to_idx, return_dtype=pl.Int64)
                .alias("orig_idx"),
                pl.col("dest_list")
                .replace_strict(state_to_idx, return_dtype=pl.Int64)
                .alias("dest_idx"),
            ]
        )

        # 4. Construção da Matriz NumPy
        size = len(channels_names)
        matrix = np.zeros((size, size), dtype=float)

        for row in transitions_with_idx.iter_rows(named=True):
            matrix[row["orig_idx"], row["dest_idx"]] = row["transition_count"]

        # Adicionar transições para estados absorventes
        matrix[-2, -2] = 1.0  # (null) -> (null)
        matrix[-1, -1] = 1.0  # (conversion) -> (conversion)

        return matrix, channels, channels_names

    def _normalize_rows(self, matrix):
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums = np.where(row_sums == 0, 1.0, row_sums)
        return matrix / row_sums

    def _calc_total_conversion(self, matrix):
        m_norm = self._normalize_rows(matrix)
        Q = m_norm[:-2, :-2]
        R = m_norm[:-2, -2:]

        # Fundamental matrix N = (I - Q)^-1
        N = np.linalg.inv(np.identity(len(Q)) - Q)
        return (N @ R)[0, 1]

    def _compute_markov(self, df: pl.DataFrame):
        matrix, channels, channels_names = self._build_transition_matrix(df)
        size = len(channels_names)

        # Probabilidade de conversão original
        conversion_orig = self._calc_total_conversion(matrix)

        # Se a probabilidade original for 0, tratar para evitar divisões por zero
        if conversion_orig == 0:
            removal_effect_val = np.zeros(len(channels))
            results = np.zeros(len(channels))
        else:
            # Efeito de remoção para cada canal de marketing
            conversions = np.zeros(size)
            for column in range(1, size - 2):
                temp = matrix.copy()
                temp[:, -2] = temp[:, -2] + temp[:, column]
                temp[:, column] = 0.0
                conversions[column] = self._calc_total_conversion(temp)

            removal_effect_val = 1.0 - (conversions[1:-2] / conversion_orig)

            # Normalização dos efeitos de remoção
            sum_re = removal_effect_val.sum()
            if sum_re == 0:
                results = np.zeros(len(channels))
            else:
                results = removal_effect_val / sum_re

        # Armazenar matriz de transições normatizada
        matrix_norm = self._normalize_rows(matrix)
        self.transition_matrix_df = pd.DataFrame(
            matrix_norm, columns=channels_names, index=channels_names
        )
        self.removal_effect_df = pd.DataFrame(
            {"removal_effect": removal_effect_val}, index=channels
        )

        self._calculated_weights = dict(zip(channels, results))
        return self._calculated_weights

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        if self._calculated_weights is None:
            self._compute_markov(df)

        channels = list(self._calculated_weights.keys())
        results = list(self._calculated_weights.values())

        weights_df = pl.DataFrame({"channel": channels, "weight_val": results})

        # Explodir canais e calcular a atribuição proporcional por jornada
        exploded = df.select(
            ["journey_id", "channels", "has_conversion", "weight"]
        ).explode("channels")
        exploded = exploded.with_columns(pl.col("channels").cast(pl.Utf8))

        exploded = exploded.join(
            weights_df, left_on="channels", right_on="channel", how="left"
        ).with_columns(pl.col("weight_val").fill_null(0.0))

        exploded = exploded.with_columns(
            pl.col("weight_val").sum().over("journey_id").alias("sum_weight")
        )

        exploded = exploded.with_columns(
            pl.when(pl.col("sum_weight") > 0)
            .then(pl.col("weight_val") / pl.col("sum_weight"))
            .otherwise(0.0)
            .alias("norm_weight")
        ).with_columns(
            (
                pl.col("has_conversion").cast(pl.Float64)
                * pl.col("weight")
                * pl.col("norm_weight")
            ).alias("attribution_value")
        )

        return exploded

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.group_by("channels")
            .agg(pl.col("attribution_value").sum().alias("attribution"))
            .sort("attribution", descending=True)
        )
