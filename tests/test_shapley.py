import polars as pl
from mam.core import MAM
from mam.results import AttributionResult


def test_shapley_format_2(small_format_2_df):
    mam_instance = MAM(
        df=small_format_2_df,
        format_type="journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        time_till_conv_colname="time_till_end",
    )
    result = mam_instance.run_shapley(max_size=4, value_column="conv_rate")

    assert isinstance(result, AttributionResult)
    agg_df = result.to_polars()
    assert isinstance(agg_df, pl.DataFrame)
    assert "channels" in agg_df.columns
    assert "attribution" in agg_df.columns

    # Soma de atribuições deve ser igual ao total de conversões (2.0)
    total_attributions = agg_df["attribution"].sum()
    assert abs(total_attributions - 2.0) < 1e-5

    metadata = result.metadata
    assert metadata["model_type"] == "algorithmic"
    assert metadata["model_name"].startswith("shapley_size4")


def test_shapley_format_3(small_format_3_df):
    mam_instance = MAM(
        df=small_format_3_df,
        format_type="grouped_journey",
        channels_colname="journey",
        journey_with_conv_colname="has_conversion",
        occurrences_colname="occurrences",
    )
    result = mam_instance.run_shapley(max_size=3, value_column="conversions")
    agg_df = result.to_polars()

    # Soma das conversões deve ser 200
    total_attributions = agg_df["attribution"].sum()
    assert abs(total_attributions - 200.0) < 1e-5
