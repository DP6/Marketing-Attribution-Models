import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import polars as pl

from .validation import (
    InputSpec,
    ParsedColumns,
    Problem,
    build_spec,
    flatten,
    parse_columns,
    revenue_row_masks,
    split_path,
)

OUTLIER_IQR_FACTOR = 3.0
OUTLIER_MIN_ROWS = 20
OUTLIER_METHODS = ("iqr", "zscore")
OUTLIER_VARIABLES = ("n_steps", "duration", "conversion_value")
OUTLIER_EXAMPLES = 5
OUTLIER_JOURNEYS_SCHEMA = {
    "journey_id": pl.String,
    "outlier_on": pl.String,
    "weight": pl.Float64,
}


@dataclass
class OutlierCut:
    """
    Cut-offs for one measure of the journeys and the journeys past them.

    variable is n_steps (touches), duration (hours from first to last touch) or
    conversion_value (revenue of a converting journey). Journeys below lower or above
    upper are outliers; journeys counts them, weighted by occurrences in format 3, and
    the shares are of all journeys, conversions and revenue. examples are the ids of
    the farthest ones.
    """

    variable: str
    method: str
    threshold: float
    lower: float
    upper: float
    journeys: int
    share_journeys: Optional[float]
    share_conversions: Optional[float]
    share_revenue: Optional[float]
    examples: List[str] = field(default_factory=list)


@dataclass
class DataQualityReport:
    """
    Result of check_data_quality. Nothing here changes the input data.

    outliers has one OutlierCut per measure the data allows, and outlier_journeys one
    row per outlier journey: its id (as in MAM), the measures it is an outlier on and
    its weight. remove_outliers returns the data without those journeys.
    """

    summary: Dict[str, Any] = field(default_factory=dict)
    errors: List[Problem] = field(default_factory=list)
    warnings: List[Problem] = field(default_factory=list)
    quality: List[Problem] = field(default_factory=list)
    expected_types: Dict[str, str] = field(default_factory=dict)
    outliers: List[OutlierCut] = field(default_factory=list)
    outlier_journeys: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame(schema=OUTLIER_JOURNEYS_SCHEMA),
        compare=False,
    )
    _outlier_rows: Optional[pl.Series] = field(default=None, repr=False, compare=False)
    _checked: Optional[Tuple[int, Tuple[str, ...]]] = field(
        default=None, repr=False, compare=False
    )

    @property
    def ok(self) -> bool:
        """True when MAM runs on this data. Warnings and quality findings don't stop it."""
        return not self.errors

    def remove_outliers(
        self, df: Union[pl.DataFrame, pd.DataFrame]
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """
        Returns the checked data without the outlier journeys: every row of each one
        goes, and every other row stays as it was. Values are never capped.
        """
        frame = pl.from_pandas(df) if isinstance(df, pd.DataFrame) else df
        if self._checked != (frame.height, tuple(frame.columns)):
            raise ValueError(
                "remove_outliers needs the same data that was passed to "
                "check_data_quality."
            )
        if self._outlier_rows is None:
            return df
        if isinstance(df, pd.DataFrame):
            return df[~self._outlier_rows.to_numpy()]
        return df.filter(~self._outlier_rows)

    def __str__(self) -> str:
        lines = ["Summary"]
        lines += [f"  {name}: {value}" for name, value in self.summary.items()]
        lines.append("Expected types")
        lines += [f"  {col}: {kind}" for col, kind in self.expected_types.items()]
        for title, problems in (
            ("Errors (MAM stops)", self.errors),
            ("Warnings (MAM runs)", self.warnings),
            ("Data quality", self.quality),
        ):
            lines.append(f"{title}: {len(problems)}")
            lines += [f"  [{p.check}] {p.message}" for p in problems]
        if self.outliers:
            lines.append("Outliers")
            lines += [
                f"  {cut.variable}: {cut.journeys} journey(s) outside "
                f"[{cut.lower:.4g}, {cut.upper:.4g}] ({cut.method}, {cut.threshold:g})"
                for cut in self.outliers
            ]
        return "\n".join(lines)


def _expected_types(spec: InputSpec) -> Dict[str, str]:
    separator = f"joined by '{spec.path_separator}'"
    expected = {spec.has_conv_col: "boolean or 0/1, with no nulls"}
    if spec.conversion_value_col:
        expected[spec.conversion_value_col] = (
            "number, not negative, with a value on every conversion"
        )
    if spec.is_session:
        expected[spec.channels_col] = "text, one channel per row"
        expected[spec.datetime_col] = "datetime, or text as ISO 2026-01-05 10:00:00"
        expected[spec.user_id_col] = "any type, with no nulls"
    elif spec.format_type == "journey":
        expected[spec.channels_col] = f"text, channels {separator}"
        expected[spec.user_id_col] = "any type, unique, with no nulls"
        expected[spec.time_col] = (
            f"text, hours to the end of the journey {separator}, falling"
        )
    else:
        expected[spec.channels_col] = f"text, channels {separator}"
        expected[spec.occurrences_col] = "whole numbers above zero"
    # Optional columns not in use (format 2 times) and session columns not given
    return {col: kind for col, kind in expected.items() if col is not None}


def _channel_names(parsed: ParsedColumns) -> Optional[pl.Series]:
    if parsed.tokens is None:
        return None
    return flatten(parsed.tokens).drop_nulls().unique(maintain_order=True)


def _summary(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"rows": df.height}
    weight = (
        df.get_column(spec.occurrences_col).cast(pl.Float64, strict=False)
        if spec.occurrences_col in df.columns
        else None
    )

    if spec.is_session and spec.user_id_col in df.columns:
        users = df.get_column(spec.user_id_col).drop_nulls().n_unique()
        summary["unique_users"] = users
        summary["journeys"] = users
        if spec.split_on_conversion and parsed.flag is not None:
            summary["journeys"] = _split_journey_count(df, spec, parsed)
    elif spec.format_type == "journey":
        summary["journeys"] = df.height
    elif weight is not None:
        summary["journeys"] = int(weight.fill_nan(None).sum())

    names = _channel_names(parsed)
    summary["channels"] = None if names is None else names.len()

    if parsed.flag is None:
        summary["conversions"] = None
    elif weight is not None:
        summary["conversions"] = int(
            (parsed.flag.fill_null(False).cast(pl.Float64) * weight)
            .fill_nan(None)
            .sum()
        )
    else:
        summary["conversions"] = int(parsed.flag.fill_null(False).sum())

    if spec.conversion_value_col:
        summary["revenue"] = (
            None
            if parsed.revenue is None
            else float(parsed.revenue.fill_nan(None).sum())
        )
    if spec.is_session:
        summary["first_date"] = None if parsed.dates is None else parsed.dates.min()
        summary["last_date"] = None if parsed.dates is None else parsed.dates.max()
    return summary


def _split_journey_count(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> Optional[int]:
    if parsed.dates is None:
        return None
    return (
        pl.DataFrame(
            {
                "user": df.get_column(spec.user_id_col),
                "date": parsed.dates,
                "flag": parsed.flag.fill_null(False),
            }
        )
        # Tied rows keep the input order, as in MAM
        .sort("user", "date", maintain_order=True)
        .with_columns(
            pl.col("flag")
            .cast(pl.Int64)
            .shift(1)
            .fill_null(0)
            .cum_sum()
            .over("user")
            .alias("journey")
        )
        .select("user", "journey")
        .drop_nulls("user")
        .n_unique()
    )


def _similar_channel_names(parsed: ParsedColumns) -> List[Problem]:
    names = _channel_names(parsed)
    if names is None:
        return []
    groups = (
        pl.DataFrame({"name": names})
        .with_columns(
            pl.col("name")
            .str.to_lowercase()
            .str.replace_all(r"[\s_\-]+", "")
            .alias("key")
        )
        .group_by("key", maintain_order=True)
        .agg(pl.col("name"))
        .filter(pl.col("name").list.len() > 1)
    )
    if groups.is_empty():
        return []
    shown = "; ".join(
        ", ".join(repr(name) for name in group)
        for group in groups.get_column("name").to_list()
    )
    return [
        Problem(
            "similar_channel_names",
            f"Channel names that look like the same channel: {shown}. "
            "MAM counts each spelling as its own channel.",
            groups.height,
        )
    ]


def _revenue_findings(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> List[Problem]:
    if parsed.flag is None or parsed.revenue is None:
        return []
    findings = []
    zero = int(
        (parsed.flag.fill_null(False) & (parsed.revenue == 0)).fill_null(False).sum()
    )
    if zero:
        findings.append(
            Problem(
                "zero_revenue_conversion",
                f"{zero} converting row(s) have revenue 0.",
                zero,
            )
        )
    _, on_touch = revenue_row_masks(df, spec, parsed.flag, parsed.revenue, parsed.dates)
    touches = 0 if on_touch is None else int(on_touch.sum())
    if touches:
        findings.append(
            Problem(
                "revenue_on_touch_in_converting_journey",
                f"{touches} non-converting row(s) have revenue inside a journey that converts. "
                "MAM adds it to the revenue of that journey.",
                touches,
            )
        )
    return findings


def _date_findings(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> List[Problem]:
    dates = parsed.dates
    if dates is None or dates.null_count() == dates.len():
        return []
    findings = []
    naive = dates.dt.replace_time_zone(None)
    future = naive > datetime.datetime.now()
    count = int(future.fill_null(False).sum())
    if count:
        findings.append(
            Problem(
                "future_dates",
                f"{count} row(s) have dates in the future, up to {naive.max()}.",
                count,
            )
        )

    days = naive.drop_nulls().dt.epoch("d").cast(pl.Float64)
    q1, q3 = days.quantile(0.25), days.quantile(0.75)
    margin = OUTLIER_IQR_FACTOR * max(q3 - q1, 1.0)
    far = naive.filter(
        (naive.dt.epoch("d") < q1 - margin) | (naive.dt.epoch("d") > q3 + margin)
    )
    if not far.is_empty() and df.height >= OUTLIER_MIN_ROWS:
        findings.append(
            Problem(
                "far_dates",
                f"{far.len()} row(s) have dates far from the rest of the data, from "
                f"{far.min()} to {far.max()}.",
                far.len(),
            )
        )

    if spec.user_id_col in df.columns:
        tied = pl.DataFrame(
            {"user": df.get_column(spec.user_id_col), "date": naive}
        ).is_duplicated()
        count = int(tied.sum())
        if count:
            findings.append(
                Problem(
                    "tied_timestamps",
                    f"{count} row(s) share the same date with another touch of the same user, so "
                    "their real order is unknown: MAM keeps them in the order of the rows. "
                    "Send full timestamps when you can.",
                    count,
                )
            )
    return findings


def _journeys(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> Optional[Tuple[pl.DataFrame, pl.Series]]:
    """
    One row per journey, with the ids MAM gives them: journey_id, weight, converted,
    the measures (n_steps, duration, revenue) when the data has them. Also returns
    the journey of each input row, so outliers can be removed whole.
    """
    if parsed.tokens is None or parsed.flag is None:
        return None
    flag = parsed.flag.fill_null(False)
    if spec.is_session:
        if spec.user_id_col not in df.columns or parsed.dates is None:
            return None
        rows = pl.DataFrame(
            {
                "user": df.get_column(spec.user_id_col).cast(pl.String),
                "date": parsed.dates,
                "converted": flag,
                "revenue": (
                    parsed.revenue
                    if parsed.revenue is not None
                    else pl.Series([0.0] * df.height)
                ),
            }
        ).with_row_index("row")
        if spec.split_on_conversion:
            rows = (
                rows.sort("user", "date", maintain_order=True)
                .with_columns(
                    pl.concat_str(
                        [
                            pl.col("user"),
                            pl.lit("_J"),
                            pl.col("converted")
                            .cast(pl.Int64)
                            .shift(1)
                            .fill_null(0)
                            .cum_sum()
                            .over("user")
                            .cast(pl.String),
                        ]
                    ).alias("journey_id")
                )
                .sort("row")
            )
        else:
            rows = rows.with_columns(pl.col("user").alias("journey_id"))
        table = (
            rows.drop_nulls("journey_id")
            .group_by("journey_id")
            .agg(
                pl.lit(1.0).alias("weight"),
                pl.col("converted").any(),
                pl.len().cast(pl.Float64).alias("n_steps"),
                (
                    (
                        pl.col("date").max() - pl.col("date").min()
                    ).dt.total_microseconds()
                    / 3.6e9
                ).alias("duration"),
                pl.col("revenue").sum(),
            )
            .sort("journey_id")
        )
        if parsed.revenue is None:
            table = table.drop("revenue")
        return table, rows.get_column("journey_id")

    if spec.format_type == "journey":
        if spec.user_id_col not in df.columns:
            return None
        ids = df.get_column(spec.user_id_col).cast(pl.String)
        weight = pl.Series([1.0] * df.height)
        columns = {"n_steps": parsed.tokens.list.len().cast(pl.Float64)}
        if spec.time_col and spec.time_col in df.columns:
            columns["duration"] = df.select(
                split_path(pl.col(spec.time_col), spec.path_separator)
                .list.eval(pl.element().cast(pl.Float64, strict=False))
                .list.max()
            ).to_series()
        revenue = parsed.revenue
    else:
        if spec.occurrences_col not in df.columns:
            return None
        ids = pl.Series([f"path_{i}" for i in range(df.height)])
        weight = df.get_column(spec.occurrences_col).cast(pl.Float64, strict=False)
        columns = {"n_steps": parsed.tokens.list.len().cast(pl.Float64)}
        # Format 3 revenue is the row total, so one journey has its average
        revenue = None if parsed.revenue is None else parsed.revenue / weight
    table = pl.DataFrame(
        {"journey_id": ids, "weight": weight, "converted": flag, **columns}
    )
    if revenue is not None:
        table = table.with_columns(revenue.alias("revenue"))
    return table, ids


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    """First value whose cumulative weight reaches q of the total."""
    order = np.argsort(values, kind="stable")
    cumulative = np.cumsum(weights[order])
    index = np.searchsorted(cumulative, q * cumulative[-1], side="left")
    return float(values[order][min(index, len(values) - 1)])


def _cut_offs(
    values: np.ndarray, weights: np.ndarray, method: str, threshold: float
) -> Optional[Tuple[float, float]]:
    """None when the IQR is 0 (half or more of the journeys share one value): the rule
    would make every other journey an outlier, so it can't separate them."""
    if method == "iqr":
        q1 = _weighted_quantile(values, weights, 0.25)
        q3 = _weighted_quantile(values, weights, 0.75)
        if q3 == q1:
            return None
        margin = threshold * (q3 - q1)
        return q1 - margin, q3 + margin
    mean = float(np.average(values, weights=weights))
    std = float(np.sqrt(np.average((values - mean) ** 2, weights=weights)))
    return mean - threshold * std, mean + threshold * std


def _share(part: float, total: float) -> Optional[float]:
    return part / total if total else None


def _outliers(
    df: pl.DataFrame,
    spec: InputSpec,
    parsed: ParsedColumns,
    method: str,
    threshold: float,
) -> Tuple[List[OutlierCut], pl.DataFrame, Optional[pl.Series], List[str]]:
    """
    Cut-offs for each measure of the journeys, the journeys past them, a mask of their
    rows in the input, and the measures with no IQR spread (no cut). Journeys are
    weighted by their occurrences in format 3.
    """
    empty = pl.DataFrame(schema=OUTLIER_JOURNEYS_SCHEMA)
    found = _journeys(df, spec, parsed)
    if found is None:
        return [], empty, None, []
    table, row_ids = found
    weight = table.get_column("weight").fill_nan(None)
    valid = weight.is_not_null() & (weight > 0)
    weight = weight.fill_null(0.0)
    converted = table.get_column("converted")
    has_revenue = "revenue" in table.columns
    revenue = (
        table.get_column("revenue").fill_nan(None).fill_null(0.0) * weight
        if has_revenue
        else None
    )
    totals = {
        "journeys": float(weight.filter(valid).sum()),
        "conversions": float(weight.filter(valid & converted).sum()),
        "revenue": float(revenue.filter(valid).sum()) if has_revenue else 0.0,
    }

    cuts = []
    flags = {}
    no_spread = []
    for variable, column in zip(OUTLIER_VARIABLES, ("n_steps", "duration", "revenue")):
        if column not in table.columns:
            continue
        values = table.get_column(column).fill_nan(None)
        measured = (valid & values.is_not_null()).fill_null(False)
        if variable == "conversion_value":
            measured = measured & converted & (values > 0).fill_null(False)
        if float(weight.filter(measured).sum()) < OUTLIER_MIN_ROWS:
            continue
        bounds = _cut_offs(
            values.filter(measured).to_numpy(),
            weight.filter(measured).to_numpy(),
            method,
            threshold,
        )
        if bounds is None:
            no_spread.append(variable)
            continue
        lower, upper = bounds
        out = measured & ((values < lower) | (values > upper)).fill_null(False)
        flags[variable] = out
        distance = pl.max_horizontal(
            pl.lit(lower) - pl.col("v"), pl.col("v") - pl.lit(upper)
        )
        examples = (
            pl.DataFrame({"journey_id": table.get_column("journey_id"), "v": values})
            .filter(out)
            .with_columns(distance.alias("distance"))
            .sort(["distance", "journey_id"], descending=[True, False])
            .head(OUTLIER_EXAMPLES)
            .get_column("journey_id")
            .to_list()
        )
        cuts.append(
            OutlierCut(
                variable=variable,
                method=method,
                threshold=threshold,
                lower=lower,
                upper=upper,
                journeys=int(round(weight.filter(out).sum())),
                share_journeys=_share(
                    float(weight.filter(out).sum()), totals["journeys"]
                ),
                share_conversions=_share(
                    float(weight.filter(out & converted).sum()), totals["conversions"]
                ),
                share_revenue=(
                    _share(float(revenue.filter(out).sum()), totals["revenue"])
                    if has_revenue
                    else None
                ),
                examples=examples,
            )
        )
    if not flags:
        return cuts, empty, None, no_spread

    marks = pl.DataFrame(
        {"journey_id": table.get_column("journey_id"), "weight": weight, **flags}
    )
    reasons = pl.concat_list(
        [pl.when(pl.col(name)).then(pl.lit(name)) for name in flags]
    ).list.drop_nulls()
    journeys = (
        marks.with_columns(reasons.alias("on"))
        .filter(pl.col("on").list.len() > 0)
        .select(
            "journey_id",
            pl.col("on").list.join(", ").alias("outlier_on"),
            "weight",
        )
    )
    rows = row_ids.is_in(journeys.get_column("journey_id").to_list()).fill_null(False)
    return cuts, journeys, rows, no_spread


def _no_spread_finding(variables: List[str]) -> List[Problem]:
    if not variables:
        return []
    return [
        Problem(
            "outliers_without_spread",
            f"No interquartile range on {', '.join(variables)}: half or more of the journeys "
            "have the same value, so the rule would flag every other journey and these "
            "measures get no cut. Use outlier_method='zscore' to check them.",
            len(variables),
        )
    ]


def _outlier_finding(
    cuts: List[OutlierCut], journeys: pl.DataFrame, method: str
) -> List[Problem]:
    counts = [cut for cut in cuts if cut.journeys]
    if not counts:
        return []
    shown = ", ".join(f"{cut.variable}: {cut.journeys}" for cut in counts)
    how = "interquartile range" if method == "iqr" else "z-score"
    return [
        Problem(
            "outliers",
            f"Journeys far from the rest by {how}: {shown}. "
            "report.remove_outliers(df) returns the data without them.",
            int(round(journeys.get_column("weight").sum())),
        )
    ]


def check_data_quality(
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
    conversion_value_colname: Optional[str] = None,
    outlier_method: str = "iqr",
    outlier_threshold: float = 3.0,
) -> DataQualityReport:
    """
    Reviews a dataset without running MAM and without changing the data.

    Takes the same arguments as MAM. Returns a report with a summary of the dataset,
    the errors that stop MAM, the warnings it runs with, the data quality findings that
    only this function reports, the type expected for each column, and the outlier
    journeys on touches, duration and revenue.

    Outliers are found by interquartile range (outlier_method="iqr": below
    Q1 - t * IQR or above Q3 + t * IQR; a measure with IQR 0 gets no cut, and the
    report says so) or by z-score ("zscore": more than t standard
    deviations from the mean), with t = outlier_threshold. report.remove_outliers(df)
    returns the data without them.
    """
    if outlier_method not in OUTLIER_METHODS:
        raise ValueError(
            f"outlier_method must be one of {OUTLIER_METHODS}, not {outlier_method!r}."
        )
    if isinstance(outlier_threshold, bool) or not (
        isinstance(outlier_threshold, (int, float)) and outlier_threshold > 0
    ):
        raise ValueError(
            f"outlier_threshold must be a number above 0, not {outlier_threshold!r}."
        )
    if isinstance(df, pd.DataFrame):
        df = pl.from_pandas(df)
    elif not isinstance(df, pl.DataFrame):
        raise TypeError("df must be either a Polars or Pandas DataFrame.")

    spec = build_spec(
        format_type,
        channels_colname,
        journey_with_conv_colname,
        datetime_colname=datetime_colname,
        user_id_colname=user_id_colname,
        time_till_conv_colname=time_till_conv_colname,
        occurrences_colname=occurrences_colname,
        create_journey_id_based_on_conversion=create_journey_id_based_on_conversion,
        path_separator=path_separator,
        conversion_value_colname=conversion_value_colname,
        columns=df.columns,
    )
    parsed = parse_columns(df, spec)
    report = DataQualityReport(
        errors=parsed.errors,
        warnings=parsed.warnings,
        expected_types=_expected_types(spec),
        summary=_summary(df, spec, parsed),
        _checked=(df.height, tuple(df.columns)),
    )
    if df.is_empty():
        return report
    cuts, journeys, rows, no_spread = _outliers(
        df, spec, parsed, outlier_method, float(outlier_threshold)
    )
    report.outliers = cuts
    report.outlier_journeys = journeys
    report._outlier_rows = rows
    report.quality = (
        _similar_channel_names(parsed)
        + _revenue_findings(df, spec, parsed)
        + _date_findings(df, spec, parsed)
        + _outlier_finding(cuts, journeys, outlier_method)
        + _no_spread_finding(no_spread)
    )
    return report
