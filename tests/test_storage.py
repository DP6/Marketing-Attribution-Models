from mam import MAM


def test_mam_keeps_normalized_input_config(small_format_1_df):
    m = MAM(
        small_format_1_df,
        format_type="format_1",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
        create_journey_id_based_on_conversion=True,
    )
    assert m.format_type == "session"
    assert m.create_journey_id_based_on_conversion is True
    assert m.results == {}


def test_from_unified_skips_preprocessing(small_format_1_df):
    src = MAM(
        small_format_1_df,
        format_type="session",
        channels_colname="channel",
        journey_with_conv_colname="has_conversion",
        datetime_colname="datetime",
        user_id_colname="user_id",
    )
    m = MAM._from_unified(src.unified_df, "session", " > ", None, False)
    assert m.unified_df.equals(src.unified_df)
    assert (
        m.run_last_click()
        .to_polars()
        .sort("channels")
        .equals(src.run_last_click().to_polars().sort("channels"))
    )
