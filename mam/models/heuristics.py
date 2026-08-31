import polars as pl
from .base import BaseModel


class LastClickModel(BaseModel):
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        # Pega o último canal
        return df.with_columns(
            pl.col("channels").list.last().alias("attribution_channel"),
            (pl.col("conversion_value") * pl.col("weight")).alias("attribution_value"),
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.group_by("attribution_channel")
            .agg(pl.col("attribution_value").sum().alias("attribution"))
            .rename({"attribution_channel": "channels"})
            .sort("attribution", descending=True)
        )


class FirstClickModel(BaseModel):
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        # Pega o primeiro canal
        return df.with_columns(
            pl.col("channels").list.first().alias("attribution_channel"),
            (pl.col("conversion_value") * pl.col("weight")).alias("attribution_value"),
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.group_by("attribution_channel")
            .agg(pl.col("attribution_value").sum().alias("attribution"))
            .rename({"attribution_channel": "channels"})
            .sort("attribution", descending=True)
        )


class LinearModel(BaseModel):
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        # Divide o valor igualmente entre todos os canais da jornada
        return df.with_columns(
            [
                pl.col("channels").list.len().alias("journey_len"),
                (pl.col("conversion_value") * pl.col("weight")).alias("total_value"),
            ]
        ).with_columns(
            (pl.col("total_value") / pl.col("journey_len")).alias("split_value")
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.explode("channels")
            .group_by("channels")
            .agg(pl.col("split_value").sum().alias("attribution"))
            .sort("attribution", descending=True)
        )


class PositionBasedModel(BaseModel):
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        # Atribui 40% ao primeiro e último, 20% distribuídos aos intermediários

        exploded = (
            df.with_columns(pl.col("channels").list.len().alias("journey_len"))
            .explode("channels")
            .with_columns(pl.int_range(0, pl.len()).over("journey_id").alias("pos_idx"))
        )

        weighted = exploded.with_columns(
            pl.when(pl.col("journey_len") == 1)
            .then(1.0)
            .when(pl.col("journey_len") == 2)
            .then(0.5)
            .otherwise(
                pl.when(pl.col("pos_idx") == 0)
                .then(0.4)
                .when(pl.col("pos_idx") == pl.col("journey_len") - 1)
                .then(0.4)
                .otherwise(0.2 / (pl.col("journey_len") - 2))
            )
            .alias("position_weight")
        )

        return weighted.with_columns(
            (
                pl.col("conversion_value")
                * pl.col("weight")
                * pl.col("position_weight")
            ).alias("attribution_value")
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.group_by("channels")
            .agg(pl.col("attribution_value").sum().alias("attribution"))
            .sort("attribution", descending=True)
        )


class TimeDecayModel(BaseModel):
    def __init__(self, half_life_hours: float = 7 * 24):
        self.half_life_hours = half_life_hours

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        # Usar time_till_conv para calcular o declínio exponencial.
        # Verifica se time_till_conv tem valores ausentes (como no Formato 3).
        time_conv_is_null = df.select(
            pl.col("time_till_conv").explode().is_null().all()
        ).item()

        if time_conv_is_null:
            raise ValueError(
                "O cálculo do Time Decay não é possível devido à ausência absoluta de dados temporais na base de entrada."
            )

        exploded_df = df.explode(["channels", "time_till_conv"]).rename(
            {"time_till_conv": "hours"}
        )

        # Aplicação da fórmula de decaimento exponencial
        decayed_df = exploded_df.with_columns(
            (0.5 ** (pl.col("hours") / self.half_life_hours)).alias("raw_decay_weight")
        )

        # Normalização dos pesos dentro da jornada
        decayed_df = decayed_df.with_columns(
            pl.col("raw_decay_weight")
            .sum()
            .over("journey_id")
            .alias("sum_decay_weight")
        ).with_columns(
            (pl.col("raw_decay_weight") / pl.col("sum_decay_weight")).alias(
                "normalized_weight"
            )
        )

        return decayed_df.with_columns(
            (
                pl.col("conversion_value")
                * pl.col("weight")
                * pl.col("normalized_weight")
            ).alias("attribution_value")
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        calc_df = self.calculate(df)
        return (
            calc_df.group_by("channels")
            .agg(pl.col("attribution_value").sum().alias("attribution"))
            .sort("attribution", descending=True)
        )
