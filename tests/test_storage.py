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


# ---- save ----
import io
import json
import zipfile

import polars as pl
import pyarrow.parquet as pq

ALL = [
    "last_click",
    "first_click",
    "linear",
    "position_based",
    "time_decay",
    "markov",
    "shapley",
]


def test_save_writes_expected_members_stored_and_snappy(mam_f2, tmp_path):
    p = tmp_path / "a.mam"
    manifest = mam_f2.save(str(p), models=ALL)
    with zipfile.ZipFile(p) as z:
        names = set(z.namelist())
        assert names == {
            "manifest.json",
            "input/journeys.parquet",
            "results/attribution.parquet",
            "markov/transition_matrix.parquet",
            "markov/removal_effect.parquet",
            "shapley/conv_table.parquet",
        }
        assert all(i.compress_type == zipfile.ZIP_STORED for i in z.infolist())
        md = pq.ParquetFile(io.BytesIO(z.read("input/journeys.parquet"))).metadata
        assert md.row_group(0).column(0).compression == "SNAPPY"
    assert manifest["format"] == "mam" and manifest["format_version"] == 1
    assert manifest["input"] == {
        "format_type": "journey",
        "path_separator": " > ",
        "conversion_value_column": None,
        "create_journey_id_based_on_conversion": False,
    }
    assert manifest["files"]["input/journeys.parquet"]["rows"] == 4
    assert manifest["created_at"].endswith("Z")


def test_failed_model_is_recorded_and_has_no_rows(mam_f3, tmp_path):
    p = tmp_path / "g.mam"
    manifest = mam_f3.save(
        str(p),
        models=["last_click", "time_decay"],
        model_kwargs={"time_decay": {"half_life_hours": 24.0}},
    )
    td = next(m for m in manifest["models"] if m["name"] == "time_decay")
    assert td["status"] == "error" and "Time Decay" in td["error"]
    assert td["params"] == {"half_life_hours": 24.0}
    with zipfile.ZipFile(p) as z:
        att = pl.read_parquet(z.read("results/attribution.parquet"))
    assert set(att["model"].unique()) == {"last_click"}


def test_model_params_in_manifest(mam_f2, tmp_path):
    manifest = mam_f2.save(str(tmp_path / "a.mam"), models=["markov", "shapley"])
    by = {m["name"]: m for m in manifest["models"]}
    assert by["markov"]["params"] == {"transition_to_same_state": False}
    assert by["shapley"]["params"] == {"max_size": 4, "value_column": "conv_rate"}


def test_attribution_is_unrounded_and_matches_results(mam_f2, tmp_path):
    p = tmp_path / "a.mam"
    mam_f2.save(str(p), models=["linear"])
    with zipfile.ZipFile(p) as z:
        att = pl.read_parquet(z.read("results/attribution.parquet"))
    exp = mam_f2.results["linear"].to_polars()
    assert (
        att.select("channel", "attribution").sort("channel").rows()
        == exp.select(
            pl.col("channels").cast(pl.String).alias("channel"), "attribution"
        )
        .sort("channel")
        .rows()
    )


def test_save_overwrites_via_tmp_and_leaves_no_tmp(mam_f2, tmp_path):
    p = tmp_path / "a.mam"
    p.write_bytes(b"old")
    mam_f2.save(str(p), models=["last_click"])
    assert zipfile.is_zipfile(p) and not (tmp_path / "a.mam.tmp").exists()


def test_on_disk_schemas(mam_f2_revenue, tmp_path):
    p = tmp_path / "a.mam"
    mam_f2_revenue.save(str(p), models=["markov", "shapley"])
    with zipfile.ZipFile(p) as z:
        rd = lambda n: pl.read_parquet(z.read(n))
        j = rd("input/journeys.parquet")
        assert j.schema == pl.Schema(
            {
                "journey_id": pl.String,
                "channels": pl.List(pl.String),
                "time_till_conv": pl.List(pl.Float64),
                "has_conversion": pl.Boolean,
                "weight": pl.Int64,
                "conversion_value": pl.Float64,
            }
        )
        tm = rd("markov/transition_matrix.parquet")
        assert tm.columns == ["from_state", "to_state", "probability"]
        assert tm.height == 36
        assert {"(inicio)", "(null)", "(conversion)"} <= set(tm["from_state"])
        assert (tm["probability"] == 0).any()
        assert rd("markov/removal_effect.parquet").columns == [
            "channel",
            "removal_effect",
        ]
        ct = rd("shapley/conv_table.parquet")
        assert ct.columns[-1] == "attribution"
        assert ct.schema["attribution"] == pl.List(pl.Float64)
        mf = json.loads(z.read("manifest.json"))
    assert mf["input"]["conversion_value_column"] == "revenue"
    assert mf["files"]["markov/transition_matrix.parquet"]["rows"] == 36
    assert all(m["status"] == "ok" for m in mf["models"])
