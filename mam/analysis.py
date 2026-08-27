import polars as pl
import pandas as pd
from typing import Optional, Union


class JAToolbox:
    """
    A modern, high-performance refactored version of the DP6 JAToolbox
    (Journey Analysis Toolbox) integrated natively with Polars.
    """

    def __init__(
        self,
        df: Optional[Union[pl.DataFrame, pd.DataFrame]] = None,
        channels_col: str = "channels",
        time_col: str = "time_till_conv",
        weight_col: str = "weight",
        format_type: Optional[str] = None,
        journey_with_conv_colname: Optional[str] = None,
        datetime_colname: Optional[str] = None,
        user_id_colname: Optional[str] = None,
        time_till_conv_colname: Optional[str] = None,
        occurrences_colname: Optional[str] = None,
        create_journey_id_based_on_conversion: bool = False,
        path_separator: str = " > ",
    ):
        """
        Inicializa a Journey Analysis Toolbox (JAToolbox).

        Esta ferramenta suporta dois modos principais de inicialização:

        1. Inicialização Direta (Dados já Unificados):
           Útil quando você já possui um DataFrame pré-processado no formato unificado interno
           da Nova MAM (coluna de canais como lista de strings/categorias, coluna de tempo e coluna de pesos).
           Neste modo, basta passar o DataFrame (Polars ou Pandas).

        2. Pré-processamento Automático (Dados Brutos):
           Útil quando você deseja analisar um DataFrame bruto diretamente de uma fonte externa (formatos
           'session', 'journey' ou 'grouped_journey'). Ao fornecer o parâmetro `format_type` e as colunas de origem,
           a JAToolbox executa internamente o pipeline de pré-processamento da biblioteca antes de iniciar as análises.

        Parâmetros
        ----------
        df : pl.DataFrame ou pd.DataFrame, opcional
            O conjunto de dados contendo as jornadas de marketing. Pode ser fornecido em formato Polars ou Pandas
            (que será convertido automaticamente para Polars sob o capô).
        channels_col : str, padrão "channels"
            Nome da coluna que contém os canais de marketing. No Modo 1, deve ser uma lista. No Modo 2,
            deve apontar para a coluna original com o caminho (ex: "google > facebook").
        time_col : str, padrão "time_till_conv"
            Nome da coluna que contém o tempo até a conversão. Relevante no Modo 1.
        weight_col : str, padrão "weight"
            Nome da coluna com o peso/frequência de ocorrência de cada jornada. Relevante no Modo 1.
        format_type : str, opcional
            O tipo de formato de entrada para o pré-processamento automático. Deve ser um de:
            - 'session' ou 'format_1': Dados de sessão individuais de usuários.
            - 'journey' ou 'format_2': Jornadas lineares agregadas por linha de usuário.
            - 'grouped_journey' ou 'format_3': Jornadas unificadas agrupadas por frequência.
        journey_with_conv_colname : str, opcional
            Nome da coluna de conversão original (obrigatória para todos os formatos se format_type for fornecido).
        datetime_colname : str, opcional
            Nome da coluna contendo a data/hora do touchpoint (obrigatória apenas para formato 'session').
        user_id_colname : str, opcional
            Nome da coluna de ID do usuário ou jornada.
        time_till_conv_colname : str, opcional
            Nome da coluna de tempo até o evento final/conversão (formato 'journey').
        occurrences_colname : str, opcional
            Nome da coluna contendo a frequência de aparição de cada jornada (formato 'grouped_journey').
        create_journey_id_based_on_conversion : bool, padrão False
            Se True, divide as jornadas de usuários em sessões com base em conversões intermediárias.
        path_separator : str, padrão " > "
            O delimitador de texto que separa as mídias nos caminhos originais de texto.

        Exemplos de Uso
        ---------------
        >>> # Modo 1: Inicialização direta com dados já unificados (Pandas ou Polars)
        >>> from mam import JAToolbox
        >>> tb = JAToolbox(df_unificado)

        >>> # Modo 2: Inicialização com pré-processamento interno direto
        >>> tb_raw = JAToolbox(
        ...     df=df_bruto,
        ...     format_type="journey",
        ...     channels_col="jornada",
        ...     journey_with_conv_colname="conversao",
        ...     time_till_conv_colname="tempo_para_conversao"
        ... )
        """
        if df is not None and format_type is not None:
            from .preprocessing import MAMPipeline

            self.df = MAMPipeline.preprocess(
                df=df,
                format_type=format_type,
                channels_colname=channels_col,
                journey_with_conv_colname=journey_with_conv_colname,
                datetime_colname=datetime_colname,
                user_id_colname=user_id_colname,
                time_till_conv_colname=time_till_conv_colname,
                occurrences_colname=occurrences_colname,
                create_journey_id_based_on_conversion=create_journey_id_based_on_conversion,
                path_separator=path_separator,
            )
            # Reconfigura as colunas padrão do formato unificado interno resultante do pipeline
            self.channels_col = "channels"
            self.time_col = "time_till_conv"
            self.weight_col = "weight"
        else:
            if isinstance(df, pd.DataFrame):
                self.df = pl.from_pandas(df)
            else:
                self.df = df
            self.channels_col = channels_col
            self.time_col = time_col
            self.weight_col = weight_col

    def _get_df(self, df: Optional[pl.DataFrame]) -> pl.DataFrame:
        target_df = df if df is not None else self.df
        if target_df is None:
            raise ValueError("Nenhum DataFrame foi fornecido.")
        return target_df

    def get_size(
        self, df: Optional[pl.DataFrame] = None, channels_col: Optional[str] = None
    ) -> pl.Series:
        """Calcula o número de touchpoints em cada jornada."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        return target_df[col].list.len()

    def get_first_tp(
        self, df: Optional[pl.DataFrame] = None, channels_col: Optional[str] = None
    ) -> pl.Series:
        """Retorna o primeiro touchpoint de cada jornada."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        return target_df[col].list.first()

    def get_last_tp(
        self, df: Optional[pl.DataFrame] = None, channels_col: Optional[str] = None
    ) -> pl.Series:
        """Retorna o último touchpoint de cada jornada."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        return target_df[col].list.last()

    def get_nth_tp(
        self,
        n: int,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
        last_if_out: bool = False,
    ) -> pl.Series:
        """Retorna o n-ésimo touchpoint de cada jornada."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col

        if not last_if_out:
            # Se algum item estiver fora do range, levanta erro para paridade com legado
            any_out = (target_df[col].list.len() <= n).any()
            if any_out:
                raise ValueError(
                    f"Index {n} out of range. Considere usar last_if_out=True"
                )

        expr = pl.col(col).list.slice(n, 1).list.first()
        if last_if_out:
            expr = (
                pl.when(pl.col(col).list.len() > n)
                .then(expr)
                .otherwise(pl.col(col).list.last())
            )

        return target_df.select(expr).to_series()

    def get_intermediate_tp(
        self,
        range_tuple: tuple,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.Series:
        """Retorna uma sub-jornada formada pelos touchpoints no intervalo especificado."""
        col = channels_col or self.channels_col
        target_df = self._get_df(df)
        start, end = min(range_tuple), max(range_tuple)
        length = end - start
        return target_df.select(pl.col(col).list.slice(start, length)).to_series()

    def get_tps_counts(
        self,
        norm: bool = False,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
        weight_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Retorna a contagem de ocorrências de cada touchpoint distinto no DataFrame."""
        target_df = self._get_df(df)
        c_col = channels_col or self.channels_col
        w_col = weight_col or self.weight_col

        tps_counts = (
            target_df.select([c_col, w_col])
            .explode(c_col)
            .group_by(c_col)
            .agg(pl.col(w_col).sum().alias("count"))
            .rename({c_col: "channels"})
        )
        if norm:
            total = tps_counts["count"].sum()
            tps_counts = tps_counts.with_columns(
                (pl.col("count") / total).alias("count")
            )
        return tps_counts.sort("count", descending=True)

    def skip_tp(
        self,
        tp_to_skip: str,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Retorna as jornadas sem as ocorrências de um canal específico."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        expr = pl.col(col).list.eval(pl.element().filter(pl.element() != tp_to_skip))
        return target_df.with_columns(expr)

    def skip_tp_group(
        self,
        tps_to_skip: list,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Retorna as jornadas sem nenhum dos canais presentes no grupo especificado."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        expr = pl.col(col).list.eval(
            pl.element().filter(~pl.element().is_in(tps_to_skip))
        )
        return target_df.with_columns(expr)

    def check_tp(
        self,
        tp_to_check: str,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.Series:
        """Verifica a presença de um touchpoint nas jornadas."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        return target_df[col].list.contains(tp_to_check)

    def check_tp_group(
        self,
        tp_group_to_check: list,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Verifica a presença de cada um dos canais em um grupo especificado."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        exprs = [pl.col(col).list.contains(tp).alias(tp) for tp in tp_group_to_check]
        return target_df.select(exprs)

    def get_tp_counts(
        self,
        tp: str,
        norm: bool = False,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.Series:
        """Calcula quantas vezes um touchpoint aparece em cada jornada."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        count_expr = (
            pl.col(col)
            .list.eval(pl.element().filter(pl.element() == tp).len())
            .list.first()
            .fill_null(0)
        )
        if norm:
            count_expr = count_expr / pl.col(col).list.len()
        return target_df.select(count_expr).to_series()

    def get_duration(
        self,
        range_tuple: tuple = (0, -1),
        df: Optional[pl.DataFrame] = None,
        time_col: Optional[str] = None,
    ) -> pl.Series:
        """Retorna o intervalo de tempo decorrido entre dois touchpoints na jornada."""
        target_df = self._get_df(df)
        t_col = time_col or self.time_col

        start_val = pl.col(t_col).list.get(range_tuple[0])
        end_idx = range_tuple[1]
        if end_idx == -1:
            end_val = pl.col(t_col).list.last()
        else:
            end_val = pl.col(t_col).list.get(end_idx)

        return target_df.select((start_val - end_val).alias("duration")).to_series()

    def translate_tp(
        self,
        translation_dict: dict,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Traduz/substitui nomes de canais em cada jornada usando um dicionário."""
        target_df = self._get_df(df)
        col = channels_col or self.channels_col
        expr = pl.col(col).list.eval(
            pl.element().replace_strict(translation_dict, default=pl.element())
        )
        return target_df.with_columns(expr)

    def get_transitions(
        self,
        count: bool = True,
        norm: bool = False,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
        weight_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Retorna as transições orig-dest ocorridas nas jornadas, opcionalmente com frequências."""
        target_df = self._get_df(df)
        c_col = channels_col or self.channels_col
        w_col = weight_col or self.weight_col

        channels_utf8 = pl.col(c_col).cast(pl.List(pl.Utf8))
        transitions_df = (
            target_df.select([channels_utf8.alias("ch"), w_col])
            .filter(pl.col("ch").list.len() >= 2)
            .with_columns(
                [
                    pl.col("ch")
                    .list.slice(0, pl.col("ch").list.len() - 1)
                    .alias("orig_list"),
                    pl.col("ch")
                    .list.slice(1, pl.col("ch").list.len() - 1)
                    .alias("dest_list"),
                ]
            )
            .explode(["orig_list", "dest_list"])
        )
        if count:
            grouped = transitions_df.group_by(["orig_list", "dest_list"]).agg(
                pl.col(w_col).sum().alias("count")
            )
            if norm:
                total_transitions = grouped["count"].sum()
                grouped = grouped.with_columns(
                    (pl.col("count") / total_transitions).alias("count")
                )
            return grouped.sort("count", descending=True)
        else:
            return transitions_df.select(["orig_list", "dest_list"]).unique()

    def channels_by_tp(
        self,
        max_journey_size: int,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
        weight_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Determina quantas vezes cada canal apareceu em cada etapa/estágio da jornada."""
        target_df = self._get_df(df)
        c_col = channels_col or self.channels_col
        w_col = weight_col or self.weight_col

        unique_channels = (
            target_df.select(pl.col(c_col).explode())
            .unique()
            .filter(pl.col(c_col).is_not_null())[c_col]
            .to_list()
        )
        result_df = pl.DataFrame({"channels": unique_channels})

        for i in range(max_journey_size):
            col_name = f"tp_{i+1}"
            step_df = (
                target_df.select(
                    [
                        pl.col(c_col)
                        .list.slice(i, 1)
                        .list.first()
                        .cast(pl.Utf8)
                        .alias("channel"),
                        pl.col(w_col),
                    ]
                )
                .filter(pl.col("channel").is_not_null())
                .group_by("channel")
                .agg(pl.col(w_col).sum().alias(col_name))
            )
            result_df = result_df.join(
                step_df, left_on="channels", right_on="channel", how="left"
            ).fill_null(0)

        for i in range(max_journey_size):
            col_name = f"tp_{i+1}"
            result_df = result_df.with_columns(pl.col(col_name).cast(pl.Int64))

        return result_df

    def tps_by_channel(
        self,
        df: Optional[pl.DataFrame] = None,
        channels_col: Optional[str] = None,
        weight_col: Optional[str] = None,
    ) -> pl.DataFrame:
        """Determina a contagem total de aparições de cada canal em todo o conjunto de dados."""
        target_df = df if df is not None else self.df
        tps_counts = self.get_tps_counts(
            norm=False, df=target_df, channels_col=channels_col, weight_col=weight_col
        )
        return tps_counts.rename({"channels": "Channel", "count": "Count"})
