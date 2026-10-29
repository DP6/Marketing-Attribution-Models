"""Persistence of a MAM session to the `.mam` file (ZIP of Parquet + manifest.json)."""

import io
import json
import math
import os
import zipfile
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Dict, List, Optional, Union

import numpy as np
import pandas as pd
import polars as pl

if TYPE_CHECKING:
    from .core import MAM

FORMAT_VERSION = 1

JOURNEYS = "input/journeys.parquet"
ATTRIBUTION = "results/attribution.parquet"
TRANSITION_MATRIX = "markov/transition_matrix.parquet"
REMOVAL_EFFECT = "markov/removal_effect.parquet"
CONV_TABLE = "shapley/conv_table.parquet"
MANIFEST = "manifest.json"

MODEL_NAMES = (
    "last_click",
    "first_click",
    "linear",
    "position_based",
    "time_decay",
    "markov",
    "shapley",
)


def _mam_version() -> str:
    from . import __version__

    return __version__


def _to_parquet_bytes(df: pl.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.write_parquet(buf, compression="snappy")
    return buf.getvalue()


def _transition_matrix_long(tm: pd.DataFrame) -> pl.DataFrame:
    long = tm.stack()
    return pl.DataFrame(
        {
            "from_state": [str(i) for i, _ in long.index],
            "to_state": [str(j) for _, j in long.index],
            "probability": long.to_numpy(dtype="float64"),
        }
    )


def _removal_effect(re: pd.DataFrame) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "channel": [str(c) for c in re.index],
            "removal_effect": re["removal_effect"].to_numpy(dtype="float64"),
        }
    )


def _conv_table(ct: pl.DataFrame, params: dict) -> pl.DataFrame:
    col = f"attribution_shapley_size{params['max_size']}_{params['value_column']}_algorithmic"
    return ct.rename({col: "attribution"})


def _check_finite(obj) -> None:
    if isinstance(obj, float) and not math.isfinite(obj):
        raise ValueError("manifest must not contain NaN/inf")
    if isinstance(obj, dict):
        for v in obj.values():
            _check_finite(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _check_finite(v)


def save_mam(
    mam: "MAM",
    path: Union[str, "os.PathLike[str]"],
    models: List[str],
    model_kwargs: Optional[Dict[str, dict]] = None,
) -> dict:
    """Runs the requested models, stores successful results in `mam.results`,
    writes the `.mam` file atomically and returns the manifest."""
    path = os.fspath(path)
    model_kwargs = model_kwargs or {}
    unknown = [m for m in models if m not in MODEL_NAMES]
    if unknown:
        raise ValueError(f"Unknown model(s): {unknown}. Valid: {list(MODEL_NAMES)}")
    if len(set(models)) != len(models):
        raise ValueError(f"Duplicate model(s) in `models`: {models}")

    members: Dict[str, pl.DataFrame] = {
        JOURNEYS: mam.unified_df.with_columns(
            pl.col("channels").cast(pl.List(pl.String))
        )
    }
    model_entries = []
    attribution_frames = []

    for name in models:
        kwargs = dict(model_kwargs.get(name, {}))
        try:
            result = getattr(mam, f"run_{name}")(**kwargs)
        except Exception as e:  # recorded in the manifest, never aborts the save
            mam.results.pop(
                name, None
            )  # never keep a stale result from an earlier save
            model_entries.append(
                {"name": name, "status": "error", "params": kwargs, "error": str(e)}
            )
            continue
        mam.results[name] = result
        params = dict(result.metadata.get("kwargs", kwargs))
        agg = result.to_polars()
        channels_dtype = (
            "categorical"
            if agg.schema["channels"] in (pl.Categorical, pl.Enum)
            else "string"
        )
        model_entries.append(
            {
                "name": name,
                "status": "ok",
                "params": params,
                "channels_dtype": channels_dtype,
            }
        )
        attribution_frames.append(
            agg.select(
                pl.lit(name).alias("model"),
                pl.col("channels").cast(pl.String).alias("channel"),
                pl.col("attribution").cast(pl.Float64),
            )
        )
        if name == "markov":
            members[TRANSITION_MATRIX] = _transition_matrix_long(
                result.metadata["transition_matrix"]
            )
            members[REMOVAL_EFFECT] = _removal_effect(result.metadata["removal_effect"])
        elif name == "shapley":
            members[CONV_TABLE] = _conv_table(result.metadata["conv_table"], params)

    if attribution_frames:
        members[ATTRIBUTION] = pl.concat(attribution_frames)
    else:
        members[ATTRIBUTION] = pl.DataFrame(
            schema={"model": pl.String, "channel": pl.String, "attribution": pl.Float64}
        )

    manifest = {
        "format": "mam",
        "format_version": FORMAT_VERSION,
        "mam_version": _mam_version(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input": {
            "format_type": mam.format_type,
            "path_separator": mam.sep,
            "conversion_value_column": mam.conversion_value_colname,
            "create_journey_id_based_on_conversion": bool(
                mam.create_journey_id_based_on_conversion
            ),
        },
        "models": model_entries,
        "files": {name: {"rows": df.height} for name, df in members.items()},
    }
    _check_finite(manifest)

    tmp = path + ".tmp"
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(
                MANIFEST,
                json.dumps(manifest, indent=2, allow_nan=False),
                compress_type=zipfile.ZIP_STORED,
            )
            for name, df in members.items():
                zf.writestr(
                    name, _to_parquet_bytes(df), compress_type=zipfile.ZIP_STORED
                )
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    return manifest


def _read_member(zf: zipfile.ZipFile, name: str) -> pl.DataFrame:
    return pl.read_parquet(io.BytesIO(zf.read(name)))


def _transition_matrix_from_long(long: pl.DataFrame):
    """Returns (square pandas DataFrame, state names) in the original state order:
    `(inicio)`, channels sorted, `(null)`, `(conversion)`."""
    absorbing = {"(inicio)", "(null)", "(conversion)"}
    states = set(long["from_state"].unique().to_list())
    channels = sorted(states - absorbing)
    names = ["(inicio)"] + channels + ["(null)", "(conversion)"]
    idx = {s: i for i, s in enumerate(names)}
    matrix = np.zeros((len(names), len(names)), dtype=float)
    for frm, to, p in long.iter_rows():
        matrix[idx[frm], idx[to]] = p
    return pd.DataFrame(matrix, columns=names, index=names), names


def load_mam(path: str) -> "MAM":
    """Reads a `.mam` file written by `save_mam` back into a MAM."""
    from .core import MAM
    from .results import AttributionResult

    with zipfile.ZipFile(path) as zf:
        manifest = json.loads(zf.read(MANIFEST))
        if manifest.get("format") != "mam":
            raise ValueError(f"Not a .mam file: format={manifest.get('format')!r}")
        if manifest.get("format_version") != FORMAT_VERSION:
            raise ValueError(
                f"Unsupported .mam format_version {manifest.get('format_version')!r}; "
                f"this library reads version {FORMAT_VERSION}"
            )

        inp = manifest["input"]
        journeys = _read_member(zf, JOURNEYS).with_columns(
            pl.col("channels").cast(pl.List(pl.Categorical))
        )
        mam = MAM._from_unified(
            journeys,
            inp["format_type"],
            inp["path_separator"],
            inp["conversion_value_column"],
            inp["create_journey_id_based_on_conversion"],
        )

        attribution = _read_member(zf, ATTRIBUTION)
        for entry in manifest["models"]:
            if entry["status"] != "ok":
                continue
            name, params = entry["name"], entry["params"]
            agg = attribution.filter(pl.col("model") == name).select(
                pl.col("channel").alias("channels"), "attribution"
            )
            if entry.get("channels_dtype") == "categorical":
                agg = agg.with_columns(pl.col("channels").cast(pl.Categorical))
            metadata = {"model_name": name, "kwargs": params}
            if name == "markov":
                tm, names = _transition_matrix_from_long(
                    _read_member(zf, TRANSITION_MATRIX)
                )
                re = _read_member(zf, REMOVAL_EFFECT)
                metadata["transition_matrix"] = tm
                metadata["removal_effect"] = pd.DataFrame(
                    {"removal_effect": re["removal_effect"].to_numpy()},
                    index=re["channel"].to_list(),
                )
                metadata["channels_names"] = names
            elif name == "shapley":
                col = f"attribution_shapley_size{params['max_size']}_{params['value_column']}_algorithmic"
                metadata["conv_table"] = _read_member(zf, CONV_TABLE).rename(
                    {"attribution": col}
                )
            mam.results[name] = AttributionResult(None, agg, metadata)
    return mam
