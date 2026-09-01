import polars as pl
import pandas as pd
from typing import Union, Optional
from .preprocessing import MAMPipeline
from .results import AttributionResult
from .models.heuristics import (
    LastClickModel,
    FirstClickModel,
    LinearModel,
    PositionBasedModel,
    TimeDecayModel,
)
from .models.markov import MarkovModel
from .models.shapley import ShapleyModel


class MAM:
    """
    Orquestrador central de atribuições. Automatiza a conversão de formatos de
    entrada baseados em Polars para o Esquema Unificado Interno do core.
    """

    def __init__(
        self,
        df: Union[pl.DataFrame, pd.DataFrame],
        format_type: str,
        channels_colname: str,
        journey_with_conv_colname: str,
        datetime_colname: Optional[str] = None,
        user_id_colname: Optional[str] = None,
        time_till_conv_colname: Optional[str] = None,
        occurrences_colname: Optional[str] = None,
        create_journey_id_based_on_conversion: bool = False,
        path_separator: str = " > ",
        verbose: bool = False,
        conversion_value_colname: Optional[str] = None,
    ):
        self.verbose = verbose
        self.sep = path_separator
        self.conversion_value_colname = conversion_value_colname

        # Conversão de Pandas para Polars sob o capô
        if isinstance(df, pd.DataFrame):
            df_polars = pl.from_pandas(df)
        else:
            df_polars = df

        self.unified_df = MAMPipeline.preprocess(
            df=df_polars,
            format_type=format_type,
            channels_colname=channels_colname,
            journey_with_conv_colname=journey_with_conv_colname,
            datetime_colname=datetime_colname,
            user_id_colname=user_id_colname,
            time_till_conv_colname=time_till_conv_colname,
            occurrences_colname=occurrences_colname,
            create_journey_id_based_on_conversion=create_journey_id_based_on_conversion,
            path_separator=path_separator,
            conversion_value_colname=conversion_value_colname,
        )

    def run_last_click(self) -> AttributionResult:
        """Executa o modelo heurístico Last Click."""
        model_instance = LastClickModel()
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {"model_type": "heuristic", "model_name": "last_click", "kwargs": {}}

        return AttributionResult(raw_results, agg_results, metadata)

    def run_first_click(self) -> AttributionResult:
        """Executa o modelo heurístico First Click."""
        model_instance = FirstClickModel()
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {
            "model_type": "heuristic",
            "model_name": "first_click",
            "kwargs": {},
        }

        return AttributionResult(raw_results, agg_results, metadata)

    def run_linear(self) -> AttributionResult:
        """Executa o modelo heurístico Linear."""
        model_instance = LinearModel()
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {"model_type": "heuristic", "model_name": "linear", "kwargs": {}}

        return AttributionResult(raw_results, agg_results, metadata)

    def run_position_based(self) -> AttributionResult:
        """Executa o modelo heurístico Position Based."""
        model_instance = PositionBasedModel()
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {
            "model_type": "heuristic",
            "model_name": "position_based",
            "kwargs": {},
        }

        return AttributionResult(raw_results, agg_results, metadata)

    def run_time_decay(self, half_life_hours: float = 168.0) -> AttributionResult:
        """Executa o modelo heurístico Time Decay."""
        model_instance = TimeDecayModel(half_life_hours=half_life_hours)
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {
            "model_type": "heuristic",
            "model_name": "time_decay",
            "kwargs": {"half_life_hours": half_life_hours},
        }

        return AttributionResult(raw_results, agg_results, metadata)

    def run_markov(self, transition_to_same_state: bool = False) -> AttributionResult:
        model_instance = MarkovModel(transition_to_same_state=transition_to_same_state)
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {
            "model_type": "algorithmic",
            "model_name": "markov",
            "transition_matrix": model_instance.transition_matrix_df,
            "removal_effect": model_instance.removal_effect_df,
            "channels_names": model_instance.channels_names,
            "kwargs": {"transition_to_same_state": transition_to_same_state},
        }

        return AttributionResult(raw_results, agg_results, metadata)

    def run_shapley(
        self, max_size: int = 4, value_column: str = "conv_rate"
    ) -> AttributionResult:
        model_instance = ShapleyModel(
            max_size=max_size, value_column=value_column, separator=self.sep
        )
        raw_results = model_instance.calculate(self.unified_df)
        agg_results = model_instance.get_aggregated_results(self.unified_df)

        metadata = {
            "model_type": "algorithmic",
            "model_name": f"shapley_size{max_size}_{value_column}",
            "conv_table": model_instance.conv_table,
            "kwargs": {"max_size": max_size, "value_column": value_column},
        }

        return AttributionResult(raw_results, agg_results, metadata)

    def generate_report(
        self,
        models: list[str],
        output_html_path: str = "report.html",
        output_json_path: str = "report_raw_data.json",
        model_kwargs: dict = None,
    ) -> dict:
        """
        Gera o One Page Report interativo e exporta os dados brutos para JSON.
        """
        from .reporting import generate_report as gen_report

        return gen_report(
            mam_instance=self,
            models=models,
            output_html_path=output_html_path,
            output_json_path=output_json_path,
            model_kwargs=model_kwargs,
        )

    @property
    def jatoolbox(self):
        """
        Acessa a JAToolbox inicializada com o dataframe unificado da MAM.

        Retorna
        -------
        JAToolbox
            Uma instância da Journey Analysis Toolbox configurada para o DataFrame unificado.
        """
        from .analysis import JAToolbox

        return JAToolbox(
            df=self.unified_df,
            channels_col="channels",
            time_col="time_till_conv",
            weight_col="weight",
        )
