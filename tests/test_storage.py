import io
import json
import zipfile
from pathlib import Path

import pandas as pd
import polars as pl
import pyarrow.parquet as pq
import pytest

from mam import MAM
from mam.storage import MODEL_NAMES


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
ALL = list(MODEL_NAMES)


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


@pytest.mark.parametrize("fixture", ["mam_f1", "mam_f2", "mam_f3", "mam_f2_revenue"])
def test_on_disk_schemas(fixture, request, tmp_path):
    m = request.getfixturevalue(fixture)
    p = tmp_path / "a.mam"
    m.save(str(p), models=["markov", "shapley"])
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
        n_states = tm["from_state"].n_unique()
        assert tm.height == n_states**2
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
    assert mf["input"]["conversion_value_column"] == m.conversion_value_colname
    assert mf["files"]["markov/transition_matrix.parquet"]["rows"] == n_states**2
    assert all(m["status"] == "ok" for m in mf["models"])


def test_manifest_records_channels_dtype(mam_f2, tmp_path):
    manifest = mam_f2.save(
        str(tmp_path / "a.mam"), models=["last_click", "markov", "shapley"]
    )
    by = {m["name"]: m["channels_dtype"] for m in manifest["models"]}
    assert by == {
        "last_click": "categorical",
        "markov": "string",
        "shapley": "string",
    }


# ---- load ----


def _rewrite_manifest(path, patch):
    with zipfile.ZipFile(path) as z:
        members = {n: z.read(n) for n in z.namelist()}
    manifest = json.loads(members["manifest.json"])
    manifest.update(patch)
    members["manifest.json"] = json.dumps(manifest).encode()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as z:
        for n, b in members.items():
            z.writestr(n, b)


@pytest.mark.parametrize("builder", ["f1", "f2", "f3", "f2_revenue"])
def test_round_trip(builder, request, tmp_path):
    m = request.getfixturevalue(f"mam_{builder}")
    models = ["last_click", "linear", "markov", "shapley"] + (
        [] if builder == "f3" else ["time_decay"]
    )
    m.save(str(tmp_path / "x.mam"), models=models)
    loaded = MAM.load(str(tmp_path / "x.mam"))
    assert loaded.unified_df.sort("journey_id").equals(m.unified_df.sort("journey_id"))
    assert loaded.format_type == m.format_type and loaded.sep == m.sep
    assert loaded.conversion_value_colname == m.conversion_value_colname
    for name in models:
        assert (
            loaded.results[name]
            .to_polars()
            .sort("channels")
            .equals(m.results[name].to_polars().sort("channels"))
        )
        assert loaded.results[name].metadata["model_name"] == name
    pd.testing.assert_frame_equal(
        loaded.results["markov"].metadata["transition_matrix"],
        m.results["markov"].metadata["transition_matrix"],
    )
    pd.testing.assert_frame_equal(
        loaded.results["markov"].metadata["removal_effect"],
        m.results["markov"].metadata["removal_effect"],
    )
    assert (
        loaded.results["markov"].metadata["channels_names"]
        == m.results["markov"].metadata["channels_names"]
    )
    assert (
        loaded.results["shapley"]
        .metadata["conv_table"]
        .equals(m.results["shapley"].metadata["conv_table"])
    )


def test_grouped_journey_null_times_survive(mam_f3, tmp_path):
    mam_f3.save(str(tmp_path / "g.mam"), models=["last_click"])
    loaded = MAM.load(str(tmp_path / "g.mam"))
    assert loaded.unified_df["time_till_conv"].explode().is_null().all()


def test_non_ascii_channels_round_trip(tmp_path):
    df = pl.DataFrame(
        {
            "journey_id": ["a"],
            "journey": ["Ação_Email > Mídia_Paga"],
            "conversion": [True],
            "time_till_end": ["1 > 0"],
        }
    )
    m = MAM(
        df, "journey", "journey", "conversion", time_till_conv_colname="time_till_end"
    )
    m.save(str(tmp_path / "u.mam"), models=["linear"])
    loaded = MAM.load(str(tmp_path / "u.mam"))
    assert loaded.unified_df["channels"].to_list() == [["Ação_Email", "Mídia_Paga"]]


def test_readable_without_mam(mam_f2, tmp_path):
    mam_f2.save(str(tmp_path / "a.mam"), models=["linear"])
    with zipfile.ZipFile(tmp_path / "a.mam") as z:
        raw = z.read("input/journeys.parquet")
    pdf = pd.read_parquet(io.BytesIO(raw))
    assert all(isinstance(c, str) for c in pdf["channels"].iloc[0])
    channels = pq.read_table(io.BytesIO(raw)).column("channels").to_pylist()
    assert all(isinstance(ch, list) for ch in channels)
    assert all(isinstance(c, str) for ch in channels for c in ch)


def test_duplicate_models_rejected(mam_f2, tmp_path):
    p = tmp_path / "a.mam"
    with pytest.raises(ValueError, match="Duplicate"):
        mam_f2.save(str(p), models=["linear", "linear"])
    assert not p.exists()


def test_save_accepts_pathlib_path(mam_f2, tmp_path):
    p = tmp_path / "a.mam"
    mam_f2.save(p, models=["linear"])
    assert zipfile.is_zipfile(p) and not (tmp_path / "a.mam.tmp").exists()
    assert isinstance(p, Path)


def test_failed_rerun_clears_stale_result(mam_f2, tmp_path, monkeypatch):
    mam_f2.save(str(tmp_path / "a.mam"), models=["linear"])
    assert "linear" in mam_f2.results

    def boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(mam_f2, "run_linear", boom)
    manifest = mam_f2.save(str(tmp_path / "b.mam"), models=["linear"])
    assert manifest["models"][0]["status"] == "error"
    assert "linear" not in mam_f2.results


def test_load_can_run_another_model(mam_f2, tmp_path):
    mam_f2.save(str(tmp_path / "a.mam"), models=["linear"])
    loaded = MAM.load(str(tmp_path / "a.mam"))
    assert loaded.run_first_click().to_polars().height > 0


def test_load_skips_failed_models(mam_f3, tmp_path):
    mam_f3.save(str(tmp_path / "g.mam"), models=["last_click", "time_decay"])
    loaded = MAM.load(str(tmp_path / "g.mam"))
    assert set(loaded.results) == {"last_click"}


@pytest.mark.parametrize("patch", [{"format": "other"}, {"format_version": 2}])
def test_rejects_unknown_format(mam_f2, tmp_path, patch):
    p = tmp_path / "a.mam"
    mam_f2.save(str(p), models=["linear"])
    _rewrite_manifest(p, patch)
    with pytest.raises(ValueError):
        MAM.load(str(p))
