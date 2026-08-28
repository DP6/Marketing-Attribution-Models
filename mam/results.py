import polars as pl
import pandas as pd
from typing import Any, Dict


class AttributionResult:
    """
    Padronização dos resultados de atribuição.
    Contém resultados granulares por jornada e resultados agregados por canal.
    """

    def __init__(
        self,
        raw_df: pl.DataFrame,
        aggregated_df: pl.DataFrame,
        model_metadata: Dict[str, Any],
    ):
        self._raw_df = raw_df
        self._aggregated_df = aggregated_df
        self.metadata = model_metadata

    def to_polars(self) -> pl.DataFrame:
        """Retorna o resultado agregado em formato Polars DataFrame."""
        return self._aggregated_df

    def to_pandas(self) -> pd.DataFrame:
        """Retorna o resultado agregado em formato Pandas DataFrame."""
        return self._aggregated_df.to_pandas()

    def to_dict(self) -> dict:
        """Estrutura os dados agregados para formato de dicionário Python."""
        return self._aggregated_df.to_dict(as_series=False)

    def to_raw_polars(self) -> pl.DataFrame:
        """Retorna o resultado granular por jornada em formato Polars."""
        return self._raw_df

    def plot(self) -> None:
        """Gera visualização do resultado deste modelo específico usando Plotly (a implementar)."""
        pass
