from abc import ABC, abstractmethod
import polars as pl


class BaseModel(ABC):
    """
    Interface base para todos os modelos de atribuição da Nova MAM.
    """

    @abstractmethod
    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Executa os cálculos matemáticos sobre o DataFrame interno unificado.
        Retorna o DataFrame enriquecido com os pesos de atribuição por linha.
        """
        pass

    @abstractmethod
    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        """
        Agrupa os resultados agregando o valor total convertido ponderado por canal.
        """
        pass
