import json
import polars as pl
import numpy as np
import plotly.graph_objects as go
import plotly.offline as opy
from jinja2 import Template
from typing import List, Dict, Any, Optional


def generate_report(
    mam_instance,
    models: List[str],
    output_html_path: str = "report.html",
    output_json_path: str = "report_raw_data.json",
    model_kwargs: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Gera o One Page Report interativo e exporta os dados brutos para JSON.

    Args:
        mam_instance: Uma instância da classe MAM.
        models: Lista de nomes de modelos a serem executados e exibidos no relatório.
               Ex: ["last_click", "first_click", "linear", "position_based", "time_decay", "markov", "shapley"]
        output_html_path: Caminho de saída para o arquivo HTML do relatório.
        output_json_path: Caminho de saída para o arquivo JSON dos dados brutos.
        model_kwargs: Dicionário opcional com argumentos específicos para cada modelo.
                      Ex: {"time_decay": {"half_life_hours": 7 * 24}}
    """
    if model_kwargs is None:
        model_kwargs = {}

    unified_df = mam_instance.unified_df
    total_journeys = int(unified_df.select(pl.col("weight").sum()).item())
    total_revenue = float(unified_df.select((pl.col("conversion_value") * pl.col("weight")).sum()).item())
    is_revenue = hasattr(mam_instance, "conversion_value_colname") and mam_instance.conversion_value_colname is not None

    # -------------------------------------------------------------------------
    # 1. PROCESSAMENTO DE INFORMAÇÕES DE JORNADAS (SEÇÃO 1)
    # -------------------------------------------------------------------------
    df_conv = unified_df.filter(pl.col("has_conversion"))
    df_non_conv = unified_df.filter(~pl.col("has_conversion"))

    total_conversions = (
        int(df_conv.select(pl.col("weight").sum()).item()) if len(df_conv) > 0 else 0
    )
    total_non_conversions = (
        int(df_non_conv.select(pl.col("weight").sum()).item())
        if len(df_non_conv) > 0
        else 0
    )

    pct_conv = (total_conversions / total_journeys * 100) if total_journeys > 0 else 0.0
    pct_non_conv = (
        (total_non_conversions / total_journeys * 100) if total_journeys > 0 else 0.0
    )

    # Adiciona contagem de touchpoints
    df_with_tp = unified_df.with_columns(
        pl.col("channels").list.len().alias("touchpoints")
    )
    df_conv_tp = df_with_tp.filter(pl.col("has_conversion"))
    df_non_conv_tp = df_with_tp.filter(~pl.col("has_conversion"))

    # Estatísticas de Touchpoints
    def get_tp_stats(df_target):
        if len(df_target) == 0:
            return {"min": 0, "max": 0, "mean": 0.0}
        tps = df_target["touchpoints"]
        weights = df_target["weight"]
        weighted_sum = (tps * weights).sum()
        sum_weights = weights.sum()
        mean_val = float(weighted_sum / sum_weights) if sum_weights > 0 else 0.0
        return {
            "min": int(tps.min()),
            "max": int(tps.max()),
            "mean": round(mean_val, 2),
        }

    tp_stats_all = get_tp_stats(df_with_tp)
    tp_stats_conv = get_tp_stats(df_conv_tp)
    tp_stats_non_conv = get_tp_stats(df_non_conv_tp)

    # Histogramas de Touchpoints (agrupados por contagem para performance e leveza)
    def get_tp_histogram_data(df_target):
        if len(df_target) == 0:
            return {"bins": [], "counts": []}
        counts_df = (
            df_target.group_by("touchpoints")
            .agg(pl.col("weight").sum().alias("count"))
            .sort("touchpoints")
        )
        return {
            "bins": counts_df["touchpoints"].to_list(),
            "counts": counts_df["count"].to_list(),
        }

    tp_hist_all = get_tp_histogram_data(df_with_tp)
    tp_hist_conv = get_tp_histogram_data(df_conv_tp)
    tp_hist_non_conv = get_tp_histogram_data(df_non_conv_tp)

    # Estatísticas de Duração
    df_with_duration = unified_df.with_columns(
        pl.col("time_till_conv").list.max().alias("duration")
    )
    # Verifica se os dados de tempo estão disponíveis (se todos forem nulos, não estão)
    duration_not_null = df_with_duration.filter(pl.col("duration").is_not_null())
    time_available = len(duration_not_null) > 0

    duration_stats = {"available": time_available}
    duration_hist_all = {"bins": [], "counts": []}
    duration_hist_conv = {"bins": [], "counts": []}
    duration_hist_non_conv = {"bins": [], "counts": []}

    if time_available:
        df_conv_dur = df_with_duration.filter(
            pl.col("has_conversion") & pl.col("duration").is_not_null()
        )
        df_non_conv_dur = df_with_duration.filter(
            (~pl.col("has_conversion")) & pl.col("duration").is_not_null()
        )

        def get_dur_stats(df_target):
            if len(df_target) == 0:
                return {"min": 0.0, "max": 0.0, "mean": 0.0}
            dur = df_target["duration"]
            weights = df_target["weight"]
            weighted_sum = (dur * weights).sum()
            sum_weights = weights.sum()
            mean_val = float(weighted_sum / sum_weights) if sum_weights > 0 else 0.0
            return {
                "min": round(float(dur.min()), 2),
                "max": round(float(dur.max()), 2),
                "mean": round(mean_val, 2),
            }

        duration_stats["all"] = get_dur_stats(
            df_with_duration.filter(pl.col("duration").is_not_null())
        )
        duration_stats["converting"] = get_dur_stats(df_conv_dur)
        duration_stats["non_converting"] = get_dur_stats(df_non_conv_dur)

        # Histograma de Duração (binned no numpy para performance)
        def get_duration_histogram_data(df_target):
            if len(df_target) == 0:
                return {"bins": [], "counts": []}
            durations = df_target["duration"].to_numpy()
            weights = df_target["weight"].to_numpy()

            # Escolhe uma quantidade de bins razoável para reduzir embolamento de labels (de 15 para 8)
            counts, bin_edges = np.histogram(durations, bins=8, weights=weights)
            bin_labels = [
                f"{bin_edges[i]:.1f}h-{bin_edges[i + 1]:.1f}h"
                for i in range(len(counts))
            ]
            return {"bins": bin_labels, "counts": [int(c) for c in counts]}

        duration_hist_all = get_duration_histogram_data(
            df_with_duration.filter(pl.col("duration").is_not_null())
        )
        duration_hist_conv = get_duration_histogram_data(df_conv_dur)
        duration_hist_non_conv = get_duration_histogram_data(df_non_conv_dur)

    # Top 10 caminhos mais frequentes até a conversão
    top_paths_df = (
        unified_df.filter(pl.col("has_conversion"))
        .with_columns(
            pl.col("channels")
            .cast(pl.List(pl.String))
            .list.join(mam_instance.sep)
            .alias("path")
        )
        .group_by("path")
        .agg(pl.col("weight").sum().alias("occurrences"))
        .sort("occurrences", descending=True)
        .limit(10)
    )

    top_paths = []
    for row in top_paths_df.iter_rows(named=True):
        path_pct = (
            (row["occurrences"] / total_conversions * 100)
            if total_conversions > 0
            else 0.0
        )
        top_paths.append(
            {
                "path": row["path"],
                "occurrences": row["occurrences"],
                "percentage": round(path_pct, 2),
            }
        )

    # -------------------------------------------------------------------------
    # 2. MODELOS DE ATRIBUIÇÃO (SEÇÃO 2)
    # -------------------------------------------------------------------------
    attribution_results = {}
    markov_metadata = None

    for model_name in models:
        # Tenta executar o modelo
        try:
            run_method_name = f"run_{model_name}"
            if not hasattr(mam_instance, run_method_name):
                raise ValueError(
                    f"Modelo '{model_name}' não suportado ou método '{run_method_name}' inexistente."
                )

            res = getattr(mam_instance, run_method_name)(
                **model_kwargs.get(model_name, {})
            )
            if model_name == "markov":
                markov_metadata = res.metadata

            # Guarda resultados agregados
            agg_df = res.to_polars()
            channels = agg_df["channels"].to_list()
            attributions = agg_df["attribution"].to_list()

            sum_attributions = sum(attributions)
            percentages = [
                (val / sum_attributions * 100) if sum_attributions > 0 else 0.0
                for val in attributions
            ]
            percentages = [round(p, 2) for p in percentages]
            attributions = [round(a, 2) for a in attributions]

            attribution_results[model_name] = {
                "channels": channels,
                "attributions": attributions,
                "percentages": percentages,
            }
        except Exception as e:
            # Em caso de erro (ex: Time Decay em dados sem duração), registra o erro
            attribution_results[model_name] = {"error": str(e)}

    # Processa métricas específicas do Markov se estiver presente
    markov_specific = {}
    if markov_metadata is not None:
        transition_matrix_df = markov_metadata["transition_matrix"]

        # 1. Probabilidades de transição entre canais
        transitions = []
        for orig in transition_matrix_df.index:
            if orig in ("(null)", "(conversion)"):
                continue
            for dest in transition_matrix_df.columns:
                prob = float(transition_matrix_df.loc[orig, dest])
                if prob > 0.0:
                    transitions.append(
                        {
                            "from": orig,
                            "to": dest,
                            "probability": round(prob, 4),
                            "label": f"{orig} → {dest}",
                        }
                    )
        # Ordena descendente e limita a 20 para visualização leve
        transitions_sorted = sorted(
            transitions, key=lambda x: x["probability"], reverse=True
        )
        markov_specific["transition_probabilities"] = transitions_sorted[:20]

        # 2. Canais com maior probabilidade de iniciar a jornada
        starts = []
        for col in transition_matrix_df.columns:
            if col in ("(inicio)", "(null)", "(conversion)"):
                continue
            prob = float(transition_matrix_df.loc["(inicio)", col])
            starts.append({"channel": col, "probability": round(prob, 4)})
        starts_sorted = sorted(starts, key=lambda x: x["probability"], reverse=True)[
            :10
        ]
        markov_specific["start_probabilities"] = starts_sorted

        # 3. Canais com maior probabilidade de transição para conversão
        conversions = []
        for idx in transition_matrix_df.index:
            if idx in ("(inicio)", "(null)", "(conversion)"):
                continue
            prob = float(transition_matrix_df.loc[idx, "(conversion)"])
            conversions.append({"channel": idx, "probability": round(prob, 4)})
        conversions_sorted = sorted(
            conversions, key=lambda x: x["probability"], reverse=True
        )[:10]
        markov_specific["conversion_probabilities"] = conversions_sorted

        # 4. Scatter plot: Conversão vs Engajamento
        channels_only = [
            c
            for c in transition_matrix_df.columns
            if c not in ("(inicio)", "(null)", "(conversion)")
        ]
        engagement_data = []
        for ch in channels_only:
            conv_prob = float(transition_matrix_df.loc[ch, "(conversion)"])
            eng_prob = float(
                sum(transition_matrix_df.loc[ch, other] for other in channels_only)
            )
            engagement_data.append(
                {
                    "channel": ch,
                    "conversion_probability": round(conv_prob, 4),
                    "engagement_probability": round(eng_prob, 4),
                }
            )

        markov_specific["engagement_vs_conversion"] = engagement_data

        # Medians
        conv_probs = [x["conversion_probability"] for x in engagement_data]
        eng_probs = [x["engagement_probability"] for x in engagement_data]
        markov_specific["median_conversion_probability"] = (
            round(float(np.median(conv_probs)), 4) if conv_probs else 0.0
        )
        markov_specific["median_engagement_probability"] = (
            round(float(np.median(eng_probs)), 4) if eng_probs else 0.0
        )

    # -------------------------------------------------------------------------
    # 3. GERAÇÃO DO ARQUIVO JSON COMPLETO (BI EXPORT)
    # -------------------------------------------------------------------------
    report_data = {
        "metadata": {
            "total_journeys": total_journeys,
            "total_conversions": total_conversions,
            "total_non_conversions": total_non_conversions,
            "conversion_rate": round(pct_conv, 2),
            "non_conversion_rate": round(pct_non_conv, 2),
            "total_revenue": round(total_revenue, 2),
        },
        "journey_statistics": {
            "touchpoint_statistics": {
                "all": tp_stats_all,
                "converting": tp_stats_conv,
                "non_converting": tp_stats_non_conv,
                "histograms": {
                    "all": tp_hist_all,
                    "converting": tp_hist_conv,
                    "non_converting": tp_hist_non_conv,
                },
            },
            "duration_statistics": {
                "available": time_available,
                "all": duration_stats.get("all", {}),
                "converting": duration_stats.get("converting", {}),
                "non_converting": duration_stats.get("non_converting", {}),
                "histograms": {
                    "all": duration_hist_all,
                    "converting": duration_hist_conv,
                    "non_converting": duration_hist_non_conv,
                },
            },
            "top_conversion_paths": top_paths,
        },
        "attribution_results": attribution_results,
        "markov_specific_results": markov_specific,
    }

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    # -------------------------------------------------------------------------
    # 4. CRIAÇÃO E EMBEBIMENTO DOS GRÁFICOS PLOTLY (HTML REPORT)
    # -------------------------------------------------------------------------
    plotly_divs = {}

    # 4.1 Histogramas de Touchpoints
    def build_tp_chart(hist_data, color, title):
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=hist_data["bins"],
                y=hist_data["counts"],
                marker_color=color,
                opacity=0.85,
                hovertemplate="Touchpoints: %{x}<br>Jornadas: %{y}<extra></extra>",
            )
        )
        fig.update_layout(
            title=dict(
                text=title,
                font=dict(family="Ubuntu, sans-serif", size=13, color="#ffffff"),
            ),
            xaxis=dict(
                title="Qtd. Touchpoints",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(
                title="Jornadas", color="#C4C7CB", gridcolor="rgba(255,255,255,0.05)"
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=20, t=40, b=40),
            height=250,
        )
        return opy.plot(fig, output_type="div", include_plotlyjs=False)

    plotly_divs["tp_all"] = build_tp_chart(tp_hist_all, "#63B3ED", "Todas as Jornadas")
    plotly_divs["tp_conv"] = build_tp_chart(
        tp_hist_conv, "#34D399", "Jornadas Conversoras"
    )
    plotly_divs["tp_non_conv"] = build_tp_chart(
        tp_hist_non_conv, "#E53E3E", "Jornadas Não Conversoras"
    )

    # 4.2 Histogramas de Duração (Se Disponível)
    if time_available:

        def build_dur_chart(hist_data, color, title):
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=hist_data["bins"],
                    y=hist_data["counts"],
                    marker_color=color,
                    opacity=0.85,
                    hovertemplate="Duração: %{x}<br>Jornadas: %{y}<extra></extra>",
                )
            )
            fig.update_layout(
                title=dict(
                    text=title,
                    font=dict(family="Ubuntu, sans-serif", size=13, color="#ffffff"),
                ),
                xaxis=dict(
                    title="Duração",
                    color="#C4C7CB",
                    gridcolor="rgba(255,255,255,0.05)",
                    tickangle=-45,
                    tickfont=dict(size=8, color="#C4C7CB"),
                ),
                yaxis=dict(
                    title="Jornadas",
                    color="#C4C7CB",
                    gridcolor="rgba(255,255,255,0.05)",
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=20, t=40, b=55),
                height=250,
            )
            return opy.plot(fig, output_type="div", include_plotlyjs=False)

        plotly_divs["dur_all"] = build_dur_chart(
            duration_hist_all, "#63B3ED", "Todas as Jornadas"
        )
        plotly_divs["dur_conv"] = build_dur_chart(
            duration_hist_conv, "#34D399", "Jornadas Conversoras"
        )
        plotly_divs["dur_non_conv"] = build_dur_chart(
            duration_hist_non_conv, "#E53E3E", "Jornadas Não Conversoras"
        )

    # 4.3 Gráficos de Atribuição por Modelo
    plotly_divs["attribution_charts"] = {}
    model_colors = {
        "last_click": "#63B3ED",
        "first_click": "#B794F4",
        "linear": "#D0D3D4",
        "position_based": "#FF53A1",
        "time_decay": "#FFB302",
        "markov": "#E53E3E",
        "shapley": "#34D399",
    }

    for m_name, m_res in attribution_results.items():
        if "error" in m_res:
            continue

        # Sorteia para barras horizontais ficarem organizadas (maior no topo)
        ch_list = m_res["channels"]
        att_list = m_res["attributions"]
        pct_list = m_res["percentages"]

        sorted_pairs = sorted(zip(ch_list, att_list, pct_list), key=lambda x: x[1])
        sorted_ch = [x[0] for x in sorted_pairs]
        sorted_att = [x[1] for x in sorted_pairs]
        sorted_pct = [x[2] for x in sorted_pairs]

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=sorted_att,
                y=sorted_ch,
                orientation="h",
                marker_color=model_colors.get(m_name, "#63B3ED"),
                opacity=0.9,
                text=[
                    f"R$ {val:,.2f} ({pct:.1f}%)" if is_revenue else f"{val:,.1f} ({pct:.1f}%)"
                    for val, pct in zip(sorted_att, sorted_pct)
                ],
                textposition="auto",
                hovertemplate="Canal: %{y}<br>Atribuído: " + ("R$ %{x:,.2f}" if is_revenue else "%{x:,.1f}") + "<br>Percentual: %{text}<extra></extra>",
            )
        )
        fig.update_layout(
            title=dict(
                text=f"Modelo: {m_name.replace('_', ' ').title()}",
                font=dict(family="Ubuntu, sans-serif", size=15, color="#ffffff"),
            ),
            xaxis=dict(
                title="Receita Atribuída (R$)" if is_revenue else "Conversões Atribuídas",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(color="#C4C7CB", gridcolor="rgba(255,255,255,0.05)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=100, r=40, t=50, b=40),
            height=max(220, len(ch_list) * 45),
        )
        plotly_divs["attribution_charts"][m_name] = opy.plot(
            fig, output_type="div", include_plotlyjs=False
        )

    # 4.4 Gráficos específicos de Markov
    if markov_metadata is not None and "transition_probabilities" in markov_specific:
        # Transições de Markov
        t_list = markov_specific["transition_probabilities"]
        sorted_t = sorted(t_list, key=lambda x: x["probability"])
        t_labels = [x["label"] for x in sorted_t]
        t_probs = [x["probability"] for x in sorted_t]

        fig_t = go.Figure()
        fig_t.add_trace(
            go.Bar(
                x=t_probs,
                y=t_labels,
                orientation="h",
                marker_color="#63B3ED",
                opacity=0.9,
                text=[f"{p:.2%}" for p in t_probs],
                textposition="auto",
                hovertemplate="Transição: %{y}<br>Probabilidade: %{x:.4f}<extra></extra>",
            )
        )
        fig_t.update_layout(
            title=dict(
                text="Top 20 Probabilidades de Transição entre Canais (Markov)",
                font=dict(family="Ubuntu, sans-serif", size=15, color="#ffffff"),
            ),
            xaxis=dict(
                title="Probabilidade de Transição",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
                range=[0, 1.05],
            ),
            yaxis=dict(color="#C4C7CB", gridcolor="rgba(255,255,255,0.05)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=150, r=40, t=50, b=40),
            height=550,
        )
        plotly_divs["markov_transitions"] = opy.plot(
            fig_t, output_type="div", include_plotlyjs=False
        )

        # Canais Iniciadores (Start)
        s_list = markov_specific["start_probabilities"]
        sorted_s = sorted(s_list, key=lambda x: x["probability"])
        s_ch = [x["channel"] for x in sorted_s]
        s_probs = [x["probability"] for x in sorted_s]

        fig_s = go.Figure()
        fig_s.add_trace(
            go.Bar(
                x=s_probs,
                y=s_ch,
                orientation="h",
                marker_color="#B794F4",
                opacity=0.9,
                text=[f"{p:.2%}" for p in s_probs],
                textposition="auto",
                hovertemplate="Canal: %{y}<br>Prob. de Iniciar: %{x:.4f}<extra></extra>",
            )
        )
        fig_s.update_layout(
            title=dict(
                text="Top 10 Canais com Maior Probabilidade de Iniciar a Jornada",
                font=dict(family="Ubuntu, sans-serif", size=14, color="#ffffff"),
            ),
            xaxis=dict(
                title="Probabilidade (inicio → canal)",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(color="#C4C7CB", gridcolor="rgba(255,255,255,0.05)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=100, r=40, t=50, b=40),
            height=320,
        )
        plotly_divs["markov_starts"] = opy.plot(
            fig_s, output_type="div", include_plotlyjs=False
        )

        # Canais Conversores
        c_list = markov_specific["conversion_probabilities"]
        sorted_c = sorted(c_list, key=lambda x: x["probability"])
        c_ch = [x["channel"] for x in sorted_c]
        c_probs = [x["probability"] for x in sorted_c]

        fig_c = go.Figure()
        fig_c.add_trace(
            go.Bar(
                x=c_probs,
                y=c_ch,
                orientation="h",
                marker_color="#34D399",
                opacity=0.9,
                text=[f"{p:.2%}" for p in c_probs],
                textposition="auto",
                hovertemplate="Canal: %{y}<br>Prob. de Conversão: %{x:.4f}<extra></extra>",
            )
        )
        fig_c.update_layout(
            title=dict(
                text="Top 10 Canais com Maior Probabilidade de Conversão Direta",
                font=dict(family="Ubuntu, sans-serif", size=14, color="#ffffff"),
            ),
            xaxis=dict(
                title="Probabilidade (canal → conversão)",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(color="#C4C7CB", gridcolor="rgba(255,255,255,0.05)"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=100, r=40, t=50, b=40),
            height=320,
        )
        plotly_divs["markov_conversions"] = opy.plot(
            fig_c, output_type="div", include_plotlyjs=False
        )

        # Scatter Plot: Conversão vs Engajamento
        sc_list = markov_specific["engagement_vs_conversion"]
        sc_ch = [x["channel"] for x in sc_list]
        sc_x = [x["conversion_probability"] for x in sc_list]
        sc_y = [x["engagement_probability"] for x in sc_list]
        med_x = markov_specific["median_conversion_probability"]
        med_y = markov_specific["median_engagement_probability"]

        fig_sc = go.Figure()
        fig_sc.add_trace(
            go.Scatter(
                x=sc_x,
                y=sc_y,
                mode="markers+text",
                text=sc_ch,
                textposition="top center",
                marker=dict(
                    size=14, color="#63B3ED", line=dict(width=1.5, color="#ffffff")
                ),
                hovertemplate="Canal: %{text}<br>Prob. Conversão: %{x:.4f}<br>Prob. Engajamento: %{y:.4f}<extra></extra>",
            )
        )

        # Linhas medianas pontilhadas
        fig_sc.add_vline(
            x=med_x,
            line_width=1.5,
            line_dash="dash",
            line_color="#E53E3E",
            annotation_text=f"Mediana: {med_x:.4f}",
            annotation_position="top left",
            annotation_font=dict(color="#E53E3E"),
        )
        fig_sc.add_hline(
            y=med_y,
            line_width=1.5,
            line_dash="dash",
            line_color="#E53E3E",
            annotation_text=f"Mediana: {med_y:.4f}",
            annotation_position="bottom right",
            annotation_font=dict(color="#E53E3E"),
        )

        fig_sc.update_layout(
            title=dict(
                text="Canais de Marketing: Conversão Direta vs. Engajamento na Jornada",
                font=dict(family="Ubuntu, sans-serif", size=15, color="#ffffff"),
            ),
            xaxis=dict(
                title="Probabilidade de Conversão Direta (canal → conversão)",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            yaxis=dict(
                title="Probabilidade de Engajamento (canal → outros canais)",
                color="#C4C7CB",
                gridcolor="rgba(255,255,255,0.05)",
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=60, r=40, t=50, b=50),
            height=480,
        )
        plotly_divs["markov_scatter"] = opy.plot(
            fig_sc, output_type="div", include_plotlyjs=False
        )

    # -------------------------------------------------------------------------
    # 5. RENDERIZAÇÃO DO TEMPLATE JINJA2 DO RELATÓRIO HTML
    # -------------------------------------------------------------------------
    html_template = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nova MAM - One Page Executive Report</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Ubuntu:ital,wght@0,300;0,400;0,500;0,700;1,300;1,400;1,500;1,700&family=Ubuntu+Mono:wght@400;700&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- Plotly.js CDN -->
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        primary: {
                            50: '#FFF3D6',
                            100: '#FFE1A3',
                            200: '#FFCC5C',
                            300: '#FFBD2E',
                            400: '#FFB302',
                            500: '#FFB302',
                            600: '#E39C00',
                            700: '#B87E00',
                            800: '#B87E00',
                            900: '#B87E00',
                            950: '#B87E00',
                        },
                        accent: {
                            50: '#FFEBEE',
                            100: '#FFCDD2',
                            200: '#EF9A9A',
                            300: '#E57373',
                            400: '#EF5350',
                            500: '#E53E3E',
                            600: '#D32F2F',
                            700: '#C62828',
                            800: '#B71C1C',
                            900: '#7F0000',
                            950: '#7F0000',
                        },
                        success: {
                            400: '#6EE7B7',
                            500: '#34D399',
                            600: '#059669',
                        },
                        warning: {
                            400: '#FFCC5C',
                            500: '#FFB302',
                            600: '#E39C00',
                        },
                        danger: {
                            400: '#F87171',
                            500: '#E53E3E',
                            600: '#D64500',
                        },
                        dark: {
                            50: '#FFFFFF',
                            100: '#F7F7F6',
                            200: '#EFEFEE',
                            300: '#DFE0E2',
                            400: '#C4C7CB',
                            500: '#9BA0A7',
                            600: '#5B626C',
                            700: '#33373C',
                            800: '#262728',
                            900: '#1D1D1B',
                            950: '#131312',
                        }
                    },
                    fontFamily: {
                        sans: ['Ubuntu', 'Verdana', 'sans-serif'],
                        mono: ['Ubuntu Mono', 'monospace'],
                        display: ['Ubuntu', 'Verdana', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <style>
        html {
            scroll-behavior: smooth;
        }
        body {
            background-color: #1D1D1B;
            color: #FFFFFF;
            font-family: 'Ubuntu', 'Verdana', system-ui, sans-serif;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Ubuntu', 'Verdana', system-ui, sans-serif;
        }
        .glass-card {
            background-color: #262728;
            border: 1px solid #33373C;
            border-top: 2px solid #FFB302;
            border-radius: 8px;
        }
        .gradient-text {
            color: #FFB302;
        }
    </style>
</head>
<body class="min-h-screen text-dark-100 pb-12 bg-dark-900">

    <!-- HEADER FLUIDO -->
    <header class="border-b border-dark-700/50 bg-dark-900/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div class="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
            <div class="flex items-center gap-3">
                <div class="flex items-end gap-1 px-2 py-1.5 h-10 select-none" style="transform: skewX(-15deg);">
                    <div class="w-1.5 bg-[#FFB302]" style="height: 12px;"></div>
                    <div class="w-1.5 bg-[#FFB302]" style="height: 18px;"></div>
                    <div class="w-1.5 bg-[#FFB302]" style="height: 24px;"></div>
                </div>
                <div>
                    <h1 class="text-xl font-bold font-display tracking-tight text-white flex items-center gap-2">
                        Nova MAM <span class="text-xs bg-primary-500/20 text-primary-400 px-2 py-0.5 rounded-full border border-primary-500/30">Fase 5</span>
                    </h1>
                    <p class="text-xs text-dark-400">Marketing Attribution & Customer Journey Analytics</p>
                </div>
            </div>
            <nav class="flex items-center gap-1 md:gap-4 text-sm font-medium">
                <a href="#secao1" class="px-4 py-2 rounded-lg text-dark-300 hover:text-white hover:bg-dark-800/50 transition-all">1. Jornadas</a>
                <a href="#secao2" class="px-4 py-2 rounded-lg text-dark-300 hover:text-white hover:bg-dark-800/50 transition-all">2. Atribuição</a>
                {% if markov_specific %}
                <a href="#markov-insights" class="px-4 py-2 rounded-lg text-dark-300 hover:text-white hover:bg-dark-800/50 transition-all">3. Insights Markov</a>
                {% endif %}
            </nav>
        </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 md:px-6 mt-8 flex flex-col gap-10">

        <!-- INTRODUÇÃO -->
        <section class="glass-card p-6 md:p-8 relative overflow-hidden">
            <div class="absolute -right-10 -top-10 w-40 h-40 bg-primary-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <div class="absolute -left-10 -bottom-10 w-40 h-40 bg-accent-500/10 rounded-full blur-3xl pointer-events-none"></div>
            <h2 class="text-2xl md:text-3xl font-bold text-white font-display mb-2">Relatório Executivo de Jornadas e Atribuição</h2>
            <p class="text-dark-300 max-w-4xl text-sm md:text-base leading-relaxed">
                Este relatório compila os principais indicadores de desempenho de marketing e os resultados dos modelos de atribuição configurados. Projetado para visualização em telas de computadores e notebooks, ele adota princípios de design minimalistas, mantendo alto contraste visual e legibilidade.
            </p>
        </section>

        <!-- SEÇÃO 1: JORNADAS DE CLIENTES -->
        <section id="secao1" class="flex flex-col gap-6">
            <div class="flex items-center gap-2 border-b border-dark-800 pb-3">
                <span class="text-primary-400 text-lg font-bold font-display">01 </span>
                <h3 class="text-xl font-bold font-display text-white">Análise de Jornadas do Consumidor</h3>
            </div>

            <!-- BIG NUMBERS -->
            <div class="grid grid-cols-1 sm:grid-cols-2 {% if is_revenue %}lg:grid-cols-5{% else %}lg:grid-cols-4{% endif %} gap-4">
                <div class="glass-card p-6 flex flex-col gap-1">
                    <span class="text-xs text-dark-400 uppercase tracking-wider font-semibold">Total de Jornadas</span>
                    <span class="text-3xl font-bold text-white font-display mt-1">{{ total_journeys }}</span>
                </div>
                <div class="glass-card p-6 flex flex-col gap-1">
                    <span class="text-xs text-dark-400 uppercase tracking-wider font-semibold text-success-400">Total de Conversões</span>
                    <span class="text-3xl font-bold text-success-400 font-display mt-1">{{ total_conversions }}</span>
                </div>
                {% if is_revenue %}
                <div class="glass-card p-6 flex flex-col gap-1" style="border-top: 2px solid #FFB302;">
                    <span class="text-xs text-dark-400 uppercase tracking-wider font-semibold text-primary-400">Receita Total Atribuída</span>
                    <span class="text-3xl font-bold text-primary-400 font-display mt-1">R$ {{ total_revenue|round(2) }}</span>
                </div>
                {% endif %}
                <div class="glass-card p-6 flex flex-col gap-1">
                    <span class="text-xs text-dark-400 uppercase tracking-wider font-semibold">Jornadas Conversoras (%)</span>
                    <span class="text-3xl font-bold text-white font-display mt-1">{{ total_conversions }} <span class="text-sm font-normal text-dark-400">({{ pct_conv|round(2) }}%)</span></span>
                </div>
                <div class="glass-card p-6 flex flex-col gap-1">
                    <span class="text-xs text-dark-400 uppercase tracking-wider font-semibold">Jornadas Não Conversoras (%)</span>
                    <span class="text-3xl font-bold text-white font-display mt-1">{{ total_non_conversions }} <span class="text-sm font-normal text-dark-400">({{ pct_non_conv|round(2) }}%)</span></span>
                </div>
            </div>

            <!-- TOUCHPOINT ANALYSIS -->
            <div class="glass-card p-6 flex flex-col gap-6">
                <div>
                    <h4 class="text-lg font-semibold text-white font-display">Análise de Pontos de Contato (Touchpoints)</h4>
                    <p class="text-xs text-dark-400">Distribuição e estatísticas da quantidade de canais que compõem as jornadas.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- TODAS AS JORNADAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-white">Todas as Jornadas</span>
                            <span class="text-xs px-2 py-0.5 bg-primary-500/10 text-primary-400 rounded border border-primary-500/20">Touchpoints</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_all.min }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_all.mean }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_all.max }}</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.tp_all|safe }}
                        </div>
                    </div>

                    <!-- JORNADAS CONVERSORAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-success-400">Jornadas Conversoras</span>
                            <span class="text-xs px-2 py-0.5 bg-success-500/10 text-success-400 rounded border border-success-500/20">Touchpoints</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_conv.min }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_conv.mean }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_conv.max }}</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.tp_conv|safe }}
                        </div>
                    </div>

                    <!-- JORNADAS NÃO CONVERSORAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-accent-400">Jornadas Não Conversoras</span>
                            <span class="text-xs px-2 py-0.5 bg-accent-500/10 text-accent-400 rounded border border-accent-500/20">Touchpoints</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_non_conv.min }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_non_conv.mean }}</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ tp_stats_non_conv.max }}</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.tp_non_conv|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- DURATION ANALYSIS -->
            <div class="glass-card p-6 flex flex-col gap-6">
                <div>
                    <h4 class="text-lg font-semibold text-white font-display">Análise de Tempo de Jornada (Duração)</h4>
                    <p class="text-xs text-dark-400">Distribuição estatística e histograma do tempo total (em horas) até o desfecho da jornada.</p>
                </div>

                {% if time_available %}
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <!-- TODAS AS JORNADAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-white">Todas as Jornadas</span>
                            <span class="text-xs px-2 py-0.5 bg-primary-500/10 text-primary-400 rounded border border-primary-500/20">Duração</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.all.min }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.all.mean }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.all.max }}h</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.dur_all|safe }}
                        </div>
                    </div>

                    <!-- JORNADAS CONVERSORAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-success-400">Jornadas Conversoras</span>
                            <span class="text-xs px-2 py-0.5 bg-success-500/10 text-success-400 rounded border border-success-500/20">Duração</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.converting.min }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.converting.mean }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.converting.max }}h</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.dur_conv|safe }}
                        </div>
                    </div>

                    <!-- JORNADAS NÃO CONVERSORAS -->
                    <div class="bg-dark-900/40 border border-dark-800 rounded-xl p-4 flex flex-col gap-4">
                        <div class="flex justify-between items-center">
                            <span class="text-sm font-semibold text-accent-400">Jornadas Não Conversoras</span>
                            <span class="text-xs px-2 py-0.5 bg-accent-500/10 text-accent-400 rounded border border-accent-500/20">Duração</span>
                        </div>
                        <div class="grid grid-cols-3 gap-2 text-center border-y border-dark-800/50 py-2">
                            <div>
                                <span class="text-xs text-dark-400 block">Mínimo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.non_converting.min }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Médio</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.non_converting.mean }}h</span>
                            </div>
                            <div>
                                <span class="text-xs text-dark-400 block">Máximo</span>
                                <span class="text-base font-bold text-white">{{ duration_stats.non_converting.max }}h</span>
                            </div>
                        </div>
                        <div class="mt-2">
                            {{ plotly_divs.dur_non_conv|safe }}
                        </div>
                    </div>
                </div>
                {% else %}
                <div class="bg-amber-500/10 border border-amber-500/30 rounded-xl p-6 flex flex-col gap-2">
                    <span class="text-amber-400 font-bold font-display flex items-center gap-2">
                        ⚠️ Informações de Tempo Não Disponíveis
                    </span>
                    <p class="text-sm text-dark-300">
                        O conjunto de dados de entrada fornecido (provavelmente no formato agrupado por caminhos) não contém informações de timestamp e de tempo decorrido para cada ponto de contato. Consequentemente, as estatísticas de duração e os histogramas de tempo até a conversão não puderam ser calculados e não estão presentes neste relatório.
                    </p>
                </div>
                {% endif %}
            </div>

            <!-- TOP 10 PATHS -->
            <div class="glass-card p-6 flex flex-col gap-4">
                <div>
                    <h4 class="text-lg font-semibold text-white font-display">Top 10 Caminhos Mais Frequentes de Conversão</h4>
                    <p class="text-xs text-dark-400">Lista ordenada com os caminhos que mais geraram conversões na base.</p>
                </div>

                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse text-sm">
                        <thead>
                            <tr class="border-b border-dark-700/60 text-dark-400">
                                <th class="py-3 px-4 font-semibold text-xs uppercase tracking-wider w-16">Rank</th>
                                <th class="py-3 px-4 font-semibold text-xs uppercase tracking-wider">Caminho do Consumidor (Path)</th>
                                <th class="py-3 px-4 font-semibold text-xs uppercase tracking-wider text-right w-36">Conversões (Qtd)</th>
                                <th class="py-3 px-4 font-semibold text-xs uppercase tracking-wider text-right w-36">Representação (%)</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-dark-800/40">
                            {% for p in top_conversion_paths %}
                            <tr class="hover:bg-dark-800/20 text-dark-200 transition-colors">
                                <td class="py-3 px-4 font-bold text-primary-400 text-center">#{{ loop.index }}</td>
                                <td class="py-3 px-4 font-mono text-xs">{{ p.path }}</td>
                                <td class="py-3 px-4 text-right font-semibold">{{ p.occurrences }}</td>
                                <td class="py-3 px-4 text-right text-dark-400">{{ p.percentage }}%</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <!-- SEÇÃO 2: RESULTADOS DOS MODELOS DE ATRIBUICÃO -->
        <section id="secao2" class="flex flex-col gap-6">
            <div class="flex items-center gap-2 border-b border-dark-800 pb-3">
                <span class="text-primary-400 text-lg font-bold font-display">02 </span>
                <h3 class="text-xl font-bold font-display text-white">Resultados dos Modelos de Atribuição</h3>
            </div>

            <div class="glass-card p-6 flex flex-col gap-6">
                <div>
                    <h4 class="text-lg font-semibold text-white font-display">Comparativo Visual de Atribuição por Canal</h4>
                    <p class="text-xs text-dark-400">Créditos de conversão atribuídos para cada canal de acordo com os modelos executados.</p>
                </div>

                <!-- GRÁFICOS DE MODELOS EM GRID (LARGURA TOTAL COMO CAMINHOS FREQUENTES) -->
                <div class="grid grid-cols-1 gap-8">
                    {% for m_name, chart_div in attribution_charts.items() %}
                    <div class="bg-dark-900/30 border border-dark-800 rounded-xl p-4">
                        {{ chart_div|safe }}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </section>

        <!-- SEÇÃO EXTRA: METRICS MARKOV SE INCLUÍDO -->
        {% if markov_specific %}
        <section id="markov-insights" class="flex flex-col gap-6">
            <div class="flex items-center gap-2 border-b border-dark-800 pb-3">
                <span class="text-accent-500 text-lg font-bold font-display">03 </span>
                <h3 class="text-xl font-bold font-display text-white">Insights Detalhados do Modelo de Markov</h3>
            </div>

            <!-- SCATTER PLOT DE ENGAJAMENTO VS CONVERSÃO (LARGURA TOTAL NO TOPO COMO CAMINHOS FREQUENTES) -->
            <div class="glass-card p-6">
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                    <div class="lg:col-span-2">
                        {{ markov_scatter|safe }}
                    </div>
                    <div class="bg-dark-900/40 border border-dark-800 rounded-lg p-5 text-sm text-dark-300 h-full flex flex-col justify-center">
                        <h4 class="text-lg font-semibold text-white font-display mb-2">Engajamento vs. Conversão Direta</h4>
                        <p class="text-xs text-dark-400 mb-4">Mapeamento de posicionamento estratégico de cada canal.</p>
                        <strong class="text-white block mb-2 text-base font-display">Guia de Interpretação:</strong>
                        <ul class="list-disc list-inside space-y-2">
                            <li><strong>Acima/Direita (Líderes):</strong> Alto impacto direto e alto engajamento ao longo da jornada.</li>
                            <li><strong>Direita (Fechadores):</strong> Excelente para fechar conversões diretas, porém geram menos engajamento intermediário.</li>
                            <li><strong>Acima (Auxiliares):</strong> Altamente eficazes em nutrir e conduzir leads para outros canais.</li>
                            <li><strong>Abaixo/Esquerda:</strong> Canais com menor probabilidade de engajar ou fechar diretamente.</li>
                        </ul>
                    </div>
                </div>
            </div>

            <!-- TOP INICIADORES E CONVERSORES EM LADO A LADO (MESMA LARGURA) -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="glass-card p-6 flex flex-col gap-4">
                    {{ markov_starts|safe }}
                </div>
                <div class="glass-card p-6 flex flex-col gap-4">
                    {{ markov_conversions|safe }}
                </div>
            </div>

            <!-- MATRIZ DE TRANSIÇÃO DE MARKOV (LARGURA TOTAL NA BASE) -->
            <div class="glass-card p-6">
                {{ markov_transitions|safe }}
            </div>
        </section>
        {% endif %}

    </main>

    <!-- FOOTER -->
    <footer class="max-w-7xl mx-auto px-6 mt-16 pt-6 border-t border-dark-800/60 text-center text-xs text-dark-400">
        <p>Nova MAM package © 2026 • Gerado de forma automatizada</p>
    </footer>

</body>
</html>
"""
    # Prepara o contexto de renderização
    render_context = {
        "total_journeys": total_journeys,
        "total_conversions": total_conversions,
        "total_non_conversions": total_non_conversions,
        "pct_conv": pct_conv,
        "pct_non_conv": pct_non_conv,
        "tp_stats_all": tp_stats_all,
        "tp_stats_conv": tp_stats_conv,
        "tp_stats_non_conv": tp_stats_non_conv,
        "time_available": time_available,
        "duration_stats": duration_stats,
        "top_conversion_paths": top_paths,
        "attribution_charts": plotly_divs["attribution_charts"],
        "plotly_divs": plotly_divs,
        "markov_specific": markov_specific,
        "is_revenue": is_revenue,
        "total_revenue": total_revenue,
    }

    if markov_metadata is not None:
        render_context["markov_starts"] = plotly_divs["markov_starts"]
        render_context["markov_conversions"] = plotly_divs["markov_conversions"]
        render_context["markov_scatter"] = plotly_divs["markov_scatter"]
        render_context["markov_transitions"] = plotly_divs["markov_transitions"]

    template = Template(html_template, autoescape=True)
    html_content = template.render(render_context)

    with open(output_html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return report_data
