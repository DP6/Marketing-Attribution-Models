import os
import sys
import warnings
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import polars as pl

MAX_EXAMPLES = 5
RESERVED_CHANNELS = ("(inicio)", "(null)", "(conversion)")
ISO_DATE_PATTERN = r"^\s*\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2}(\.\d+)?)?)?\s*$"


class InputValidationError(ValueError):
    """Raised when the input data would make MAM fail or return wrong results."""

    def __init__(self, problems: List["Problem"]):
        self.problems = problems
        super().__init__(
            "The input data has problems that must be fixed before running MAM:\n"
            + "\n".join(f"- {problem.message}" for problem in problems)
        )


@dataclass(frozen=True)
class Problem:
    check: str
    message: str
    rows: int = 0


@dataclass(frozen=True)
class InputSpec:
    """Column names of the input data, already resolved for its format."""

    format_type: str
    channels_col: str
    has_conv_col: str
    datetime_col: Optional[str] = None
    user_id_col: Optional[str] = None
    time_col: Optional[str] = None
    occurrences_col: Optional[str] = None
    conversion_value_col: Optional[str] = None
    split_on_conversion: bool = False
    path_separator: str = " > "

    @property
    def is_session(self) -> bool:
        return self.format_type == "session"

    @property
    def required_cols(self) -> List[str]:
        cols = [
            self.channels_col,
            self.has_conv_col,
            self.datetime_col,
            self.user_id_col,
            self.time_col,
            self.occurrences_col,
            self.conversion_value_col,
        ]
        return [col for col in cols if col is not None]


@dataclass
class ParsedColumns:
    """Columns read into their working type, or None when they can't be read."""

    flag: Optional[pl.Series] = None
    revenue: Optional[pl.Series] = None
    dates: Optional[pl.Series] = None
    tokens: Optional[pl.Series] = None
    errors: List[Problem] = field(default_factory=list)
    warnings: List[Problem] = field(default_factory=list)


FORMAT_ALIASES = {
    "session": "session",
    "format_1": "session",
    "journey": "journey",
    "format_2": "journey",
    "grouped_journey": "grouped_journey",
    "format_3": "grouped_journey",
}


def resolve_format(format_type: str) -> str:
    """The format's name ('session', 'journey' or 'grouped_journey') from any alias."""
    normalized = FORMAT_ALIASES.get(format_type.lower().strip())
    if normalized is None:
        raise ValueError(
            f"Unknown format_type '{format_type}'. "
            "Supported formats: 'session', 'journey', 'grouped_journey'."
        )
    return normalized


def build_spec(
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
    columns: Optional[Sequence[str]] = None,
) -> InputSpec:
    """
    Resolves the column names of a format. In format 2 the time column is optional:
    without time_till_conv_colname MAM uses 'time_till_end' when the data has it, and
    no times otherwise (every model runs except Time Decay).
    """
    resolved = resolve_format(format_type)
    common = dict(
        format_type=resolved,
        channels_col=channels_colname,
        has_conv_col=journey_with_conv_colname,
        conversion_value_col=conversion_value_colname,
        path_separator=path_separator,
    )
    if resolved == "session":
        return InputSpec(
            datetime_col=datetime_colname,
            user_id_col=user_id_colname,
            split_on_conversion=create_journey_id_based_on_conversion,
            **common,
        )
    if resolved == "journey":
        time_col = time_till_conv_colname
        if not time_col and (columns is None or DEFAULT_TIME_COL in columns):
            time_col = DEFAULT_TIME_COL
        return InputSpec(
            user_id_col=user_id_colname if user_id_colname else "journey_id",
            time_col=time_col,
            **common,
        )
    return InputSpec(
        occurrences_col=occurrences_colname if occurrences_colname else "occurrences",
        **common,
    )


def parse_iso_dates(series: pl.Series) -> pl.Series:
    """Reads ISO dates with or without time and fractions of a second; others become null."""
    text = series.str.strip_chars().str.replace("T", " ")
    formats = ("%Y-%m-%d %H:%M:%S%.f", "%Y-%m-%d %H:%M", "%Y-%m-%d")
    return (
        pl.select(
            pl.coalesce(
                [
                    text.str.strptime(pl.Datetime("us"), fmt, strict=False)
                    for fmt in formats
                ]
            )
        )
        .to_series()
        .alias(series.name)
    )


DEFAULT_TIME_COL = "time_till_end"


def split_path(path: pl.Expr, separator: str) -> pl.Expr:
    """
    Splits a path (or its times) into a list on the separator exactly as given, then
    removes the spaces around each item: with " > ", "A > B" and " A  >  B " give
    ["A", "B"], while "A>B" is one channel. A channel name with the separator inside
    needs another path_separator.
    """
    return (
        path.cast(pl.String)
        .str.split(separator)
        .list.eval(pl.element().str.strip_chars())
    )


def flatten(lists: pl.Series) -> pl.Series:
    """Every value of a list column, skipping empty lists, on any polars version."""
    lists = lists.filter(lists.list.len() > 0)
    try:
        return lists.explode(empty_as_null=False)
    except TypeError:
        return lists.explode()


def _examples(values: pl.Series) -> str:
    shown = values.unique(maintain_order=True).head(MAX_EXAMPLES).to_list()
    return ", ".join(repr(value) for value in shown)


def _row_examples(mask: pl.Series) -> str:
    rows = mask.arg_true().head(MAX_EXAMPLES).to_list()
    return ", ".join(str(row) for row in rows)


def _rows_problem(check: str, mask: pl.Series, text: str) -> List[Problem]:
    """Builds a problem from a boolean mask of the offending rows."""
    count = int(mask.fill_null(False).sum())
    if count == 0:
        return []
    return [
        Problem(
            check,
            f"{text} {count} row(s), for example rows {_row_examples(mask.fill_null(False))}.",
            count,
        )
    ]


def _read_flag(df: pl.DataFrame, col: str) -> Tuple[Optional[pl.Series], List[Problem]]:
    series = df.get_column(col)
    expected = f"Conversion flag '{col}' must be boolean or 0/1."
    if series.dtype != pl.Boolean and not series.dtype.is_numeric():
        return None, [
            Problem(
                "invalid_conversion_flag",
                f"{expected} It is {series.dtype}: convert it, for example yes/no to true/false.",
                df.height,
            )
        ]
    problems = _rows_problem(
        "null_conversion_flag",
        series.is_null(),
        f"Conversion flag '{col}' has no value on",
    )
    if series.dtype == pl.Boolean:
        return series, problems

    values = series.cast(pl.Float64)
    invalid = ~(values.is_in([0.0, 1.0]).fill_null(False)) & values.is_not_null()
    if invalid.any():
        problems += _rows_problem(
            "invalid_conversion_flag",
            invalid,
            f"{expected} Other values on",
        )
        return None, problems
    return values.cast(pl.Boolean), problems


def _read_revenue(
    df: pl.DataFrame, col: str
) -> Tuple[Optional[pl.Series], List[Problem]]:
    series = df.get_column(col)
    if not series.dtype.is_numeric():
        return None, [
            Problem(
                "invalid_revenue_type",
                f"Revenue '{col}' must be numeric. It is {series.dtype}: convert it to float.",
                df.height,
            )
        ]
    values = series.cast(pl.Float64)
    problems = _rows_problem(
        "invalid_revenue",
        values.is_nan() | values.is_infinite(),
        f"Revenue '{col}' must be a finite number. NaN or infinite on",
    )
    problems += _rows_problem(
        "negative_revenue",
        values < 0,
        f"Revenue '{col}' can't be negative: remove refunds from the input. Negative on",
    )
    return values, problems


def _read_dates(
    df: pl.DataFrame, col: str
) -> Tuple[Optional[pl.Series], List[Problem]]:
    series = df.get_column(col)
    problems = _rows_problem(
        "null_date", series.is_null(), f"Date '{col}' has no value on"
    )
    if series.dtype == pl.Datetime:
        return series, problems
    if series.dtype == pl.Date:
        return series.cast(pl.Datetime), problems
    how_to_fix = (
        "Send ISO dates, such as 2026-01-05 10:00:00, or a datetime column, "
        "with times in a single time zone."
    )
    if series.dtype != pl.String:
        problems.append(
            Problem(
                "invalid_date_type",
                f"Date '{col}' must be a date or text. It is {series.dtype}. {how_to_fix}",
                df.height,
            )
        )
        return None, problems

    not_iso = ~series.str.contains(ISO_DATE_PATTERN).fill_null(True)
    if not_iso.any():
        bad = series.filter(not_iso)
        note = ""
        if bad.str.contains("/").any():
            note = " Dates with slashes are read day first, whatever the order in the file."
        elif bad.str.contains(r"(Z|[+-]\d{2}:?\d{2})\s*$").any():
            note = " Time zones in the text aren't supported: convert to one time zone first."
        problems.append(
            Problem(
                "ambiguous_dates",
                f"Date '{col}' can't be read safely: {int(not_iso.sum())} row(s) are not in "
                f"the format 2026-01-05 10:00:00, for example {_examples(bad)}.{note} "
                f"{how_to_fix}",
                int(not_iso.sum()),
            )
        )
        return None, problems

    parsed = parse_iso_dates(series)
    invalid = parsed.is_null() & series.is_not_null()
    if invalid.any():
        problems.append(
            Problem(
                "invalid_dates",
                f"Date '{col}' has values that aren't real dates on {int(invalid.sum())} row(s), "
                f"for example {_examples(series.filter(invalid))}. {how_to_fix}",
                int(invalid.sum()),
            )
        )
        return None, problems
    return parsed, problems


def _read_session_channels(
    df: pl.DataFrame, col: str
) -> Tuple[Optional[pl.Series], List[Problem]]:
    series = df.get_column(col)
    if series.dtype not in (pl.String, pl.Categorical, pl.Enum):
        return None, [
            Problem(
                "invalid_channel_type",
                f"Channel '{col}' must be text. It is {series.dtype}: convert the ids to text.",
                df.height,
            )
        ]
    names = series.cast(pl.String).str.strip_chars()
    problems = _rows_problem(
        "null_channel", names.is_null(), f"Channel '{col}' has no value on"
    )
    problems += _rows_problem(
        "empty_channel",
        names.str.len_chars() == 0,
        f"Channel '{col}' is empty on",
    )
    tokens = df.select(pl.concat_list(names.alias("token"))).to_series()
    return tokens, problems


def _read_paths(
    df: pl.DataFrame, col: str, separator: str
) -> Tuple[Optional[pl.Series], List[Problem]]:
    series = df.get_column(col)
    if series.dtype in (pl.Categorical, pl.Enum):  # e.g. pandas 'category'
        series = series.cast(pl.String)
    if series.dtype != pl.String:
        return None, [
            Problem(
                "invalid_path_type",
                f"Path '{col}' must be text with channels joined by '{separator}'. "
                f"It is {series.dtype}: convert it to text.",
                df.height,
            )
        ]
    problems = _rows_problem(
        "null_path", series.is_null(), f"Path '{col}' has no value on"
    )

    # Same split as the preprocessing, so "A >" shows an empty channel
    tokens = df.select(split_path(pl.col(col), separator)).to_series()
    problems += _rows_problem(
        "empty_channel_in_path",
        tokens.list.eval(pl.element().str.len_chars() == 0).list.any(),
        f"Path '{col}' is empty or has an empty channel between separators on",
    )
    return tokens, problems


def _read_times(
    df: pl.DataFrame, col: str, separator: str, tokens: Optional[pl.Series]
) -> List[Problem]:
    series = df.get_column(col)
    if series.dtype != pl.String:
        return [
            Problem(
                "invalid_time_type",
                f"Times '{col}' must be text with one value per channel joined by "
                f"'{separator}'. It is {series.dtype}.",
                df.height,
            )
        ]
    problems = _rows_problem(
        "null_time", series.is_null(), f"Times '{col}' have no value on"
    )

    parts = df.select(split_path(pl.col(col), separator)).to_series()
    if tokens is not None:
        # A path with an empty channel is already reported, don't count it twice
        has_empty = tokens.list.eval(pl.element().str.len_chars() == 0).list.any()
        problems += _rows_problem(
            "time_length_mismatch",
            series.is_not_null()
            & tokens.is_not_null()
            & ~has_empty.fill_null(False)
            & (parts.list.len() != tokens.list.len()),
            f"Times '{col}' must have one value per channel. Different counts on",
        )

    frame = df.select(parts.alias("value")).with_row_index("row")
    try:
        frame = frame.explode("value", empty_as_null=True)
    except TypeError:
        frame = frame.explode("value")
    values = (
        frame.with_columns(
            pl.col("value").cast(pl.Float64, strict=False).alias("number")
        )
        .with_columns(
            (pl.col("value").is_not_null() & pl.col("number").is_null()).alias("text"),
            (pl.col("number").is_nan() | pl.col("number").is_infinite()).alias(
                "infinite"
            ),
            (pl.col("number") < 0).alias("negative"),
            pl.when(pl.col("number").is_finite())
            .then(pl.col("number"))
            .alias("finite"),
        )
        .with_columns((pl.col("finite").diff().over("row") > 0).alias("increasing"))
        .group_by("row", maintain_order=True)
        .agg(
            pl.col("text", "infinite", "negative", "increasing").fill_null(False).any()
        )
    )
    for check, column, text in (
        ("invalid_time_value", "text", "values that aren't numbers on"),
        ("invalid_time_value", "infinite", "NaN or infinite values on"),
        ("negative_time", "negative", "negative values on"),
        (
            "increasing_times",
            "increasing",
            "values that go up: they must fall to the end of the journey, on",
        ),
    ):
        problems += _rows_problem(
            check, values.get_column(column), f"Times '{col}' have {text}"
        )
    return problems


def _read_occurrences(df: pl.DataFrame, col: str) -> List[Problem]:
    series = df.get_column(col)
    if not series.dtype.is_numeric():
        return [
            Problem(
                "invalid_occurrences_type",
                f"Occurrences '{col}' must be whole numbers. It is {series.dtype}.",
                df.height,
            )
        ]
    values = series.cast(pl.Float64)
    invalid = values.is_nan() | values.is_infinite() | (values != values.floor())
    problems = _rows_problem(
        "null_occurrences", series.is_null(), f"Occurrences '{col}' have no value on"
    )
    problems += _rows_problem(
        "fractional_occurrences",
        invalid,
        f"Occurrences '{col}' must be whole numbers. Other values on",
    )
    problems += _rows_problem(
        "non_positive_occurrences",
        values <= 0,
        f"Occurrences '{col}' must be above zero. Other values on",
    )
    return problems


def revenue_row_masks(
    df: pl.DataFrame,
    spec: InputSpec,
    flag: Optional[pl.Series],
    revenue: Optional[pl.Series],
    dates: Optional[pl.Series],
) -> Tuple[Optional[pl.Series], Optional[pl.Series]]:
    """
    Marks rows with revenue and no conversion, as two masks: rows in a journey with
    no conversion at all, and rows in a journey that converts on another row.
    """
    if flag is None or revenue is None:
        return None, None
    flag = flag.fill_null(False)
    # NaN and infinite values are already errors of their own (NaN counts as above zero)
    with_revenue = ~flag & (revenue.is_finite() & (revenue > 0)).fill_null(False)
    if not spec.is_session:
        return with_revenue, pl.Series([False] * df.height)
    if spec.user_id_col not in df.columns:
        return None, None

    frame = pl.DataFrame(
        {
            "user": df.get_column(spec.user_id_col),
            "flag": flag,
            "date": (
                dates
                if dates is not None
                else pl.Series([None] * df.height, dtype=pl.Datetime)
            ),
        }
    )
    if spec.split_on_conversion and dates is not None:
        # A touch belongs to a converting journey when a conversion follows it
        covered = frame.select(
            (
                pl.col("date")
                <= pl.col("date").filter(pl.col("flag")).max().over("user")
            ).fill_null(False)
        ).to_series()
    else:
        covered = frame.select(pl.col("flag").any().over("user")).to_series()
    return with_revenue & ~covered, with_revenue & covered


def parse_columns(df: pl.DataFrame, spec: InputSpec) -> ParsedColumns:
    """Reads every column of the input, collecting what stops MAM or changes its results."""
    parsed = ParsedColumns()
    errors = parsed.errors

    if spec.is_session and (spec.datetime_col is None or spec.user_id_col is None):
        errors.append(
            Problem(
                "missing_arguments",
                "datetime_colname and user_id_colname are required for 'session' format.",
            )
        )
    missing = [col for col in spec.required_cols if col not in df.columns]
    if missing:
        errors.append(
            Problem(
                "missing_columns",
                f"Missing columns: {', '.join(repr(col) for col in missing)}. "
                f"Available columns: {', '.join(repr(col) for col in df.columns)}.",
            )
        )
    if df.is_empty():
        errors.append(Problem("no_rows", "The input data has no rows."))
        return parsed

    if spec.has_conv_col in df.columns:
        parsed.flag, problems = _read_flag(df, spec.has_conv_col)
        errors += problems
    if spec.conversion_value_col in df.columns:
        parsed.revenue, problems = _read_revenue(df, spec.conversion_value_col)
        errors += problems
    if spec.channels_col in df.columns:
        if spec.is_session:
            parsed.tokens, problems = _read_session_channels(df, spec.channels_col)
        else:
            parsed.tokens, problems = _read_paths(
                df, spec.channels_col, spec.path_separator
            )
        errors += problems

    if spec.is_session:
        if spec.user_id_col in df.columns:
            errors += _rows_problem(
                "null_user",
                df.get_column(spec.user_id_col).is_null(),
                f"User '{spec.user_id_col}' has no value on",
            )
        if spec.datetime_col in df.columns:
            parsed.dates, problems = _read_dates(df, spec.datetime_col)
            errors += problems
    elif spec.format_type == "journey":
        if spec.user_id_col in df.columns:
            errors += _journey_id_problems(df, spec.user_id_col)
        if spec.time_col in df.columns:
            errors += _read_times(df, spec.time_col, spec.path_separator, parsed.tokens)
    elif spec.occurrences_col in df.columns:
        errors += _read_occurrences(df, spec.occurrences_col)

    if spec.format_type != "journey":
        errors += _duplicate_row_problems(df)
    if spec.split_on_conversion:
        errors += _tied_conversion_problems(df, spec, parsed)
    errors += _revenue_problems(df, spec, parsed)
    parsed.warnings += _reserved_channel_problems(parsed.tokens)
    return parsed


def _journey_id_problems(df: pl.DataFrame, col: str) -> List[Problem]:
    ids = df.get_column(col).cast(pl.String)
    problems = _rows_problem(
        "null_journey_id", ids.is_null(), f"Journey id '{col}' has no value on"
    )
    known = ids.drop_nulls()
    duplicated = known.filter(known.is_duplicated())
    if not duplicated.is_empty():
        problems.append(
            Problem(
                "duplicate_journey_id",
                f"Journey id '{col}' must be unique: {duplicated.n_unique()} id(s) repeat over "
                f"{duplicated.len()} row(s), for example {_examples(duplicated)}.",
                duplicated.len(),
            )
        )
    return problems


def _duplicate_row_problems(df: pl.DataFrame) -> List[Problem]:
    return _rows_problem(
        "duplicate_rows",
        df.is_duplicated(),
        "Rows with every column equal count as duplicates. Remove them, or send full "
        "timestamps if they are different touches. Repeated on",
    )


def _tied_conversion_problems(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> List[Problem]:
    """
    A conversion at the same timestamp as another touch of the user: when journeys are
    split at conversions, their order decides which journey that touch (and its
    revenue) belongs to, and the data doesn't have it.
    """
    if (
        parsed.flag is None
        or parsed.dates is None
        or spec.user_id_col not in df.columns
    ):
        return []
    same_moment = ["user", "date"]
    tied = (
        pl.DataFrame(
            {
                "user": df.get_column(spec.user_id_col),
                "date": parsed.dates,
                "flag": parsed.flag.fill_null(False),
            }
        )
        .select(
            (
                pl.col("user").is_not_null()
                & pl.col("date").is_not_null()
                & (pl.len().over(same_moment) > 1)
                & pl.col("flag").any().over(same_moment)
            ).alias("tied")
        )
        .to_series()
    )
    return _rows_problem(
        "tied_conversion",
        tied,
        "A conversion has the same timestamp as another touch of the same user, so MAM "
        "can't tell which journey that touch belongs to when it splits journeys at "
        "conversions. Send full timestamps. Tied on",
    )


def _revenue_problems(
    df: pl.DataFrame, spec: InputSpec, parsed: ParsedColumns
) -> List[Problem]:
    if parsed.flag is None or parsed.revenue is None:
        return []
    problems = _rows_problem(
        "null_revenue_on_conversion",
        parsed.flag.fill_null(False) & parsed.revenue.is_null(),
        f"Revenue '{spec.conversion_value_col}' has no value on converting",
    )
    no_conversion, _ = revenue_row_masks(
        df, spec, parsed.flag, parsed.revenue, parsed.dates
    )
    if no_conversion is not None:
        problems += _rows_problem(
            "revenue_without_conversion",
            no_conversion,
            f"Revenue '{spec.conversion_value_col}' must sit in a journey that converts. "
            "Revenue with no conversion on",
        )
    return problems


def _reserved_channel_problems(tokens: Optional[pl.Series]) -> List[Problem]:
    if tokens is None:
        return []
    reserved = flatten(tokens).drop_nulls()
    reserved = reserved.filter(reserved.is_in(list(RESERVED_CHANNELS)))
    if reserved.is_empty():
        return []
    return [
        Problem(
            "reserved_channel_name",
            f"Invalid channel names {_examples(reserved)}: the Markov model uses these names "
            "internally and gives them no credit. Rename them.",
            reserved.len(),
        )
    ]


_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def _user_stacklevel() -> int:
    """stacklevel for warnings.warn called here that points at the first frame outside
    the mam package: the user's MAM(...) or JAToolbox(...) call."""
    level, frame = 1, sys._getframe(1)
    while frame is not None and os.path.abspath(frame.f_code.co_filename).startswith(
        _PACKAGE_DIR
    ):
        level, frame = level + 1, frame.f_back
    return level


def validate_input(df: pl.DataFrame, spec: InputSpec) -> None:
    """Stops on what makes MAM fail or return wrong results; warns on what it can run with."""
    parsed = parse_columns(df, spec)
    if parsed.errors:
        raise InputValidationError(parsed.errors)
    for problem in parsed.warnings:
        warnings.warn(problem.message, UserWarning, stacklevel=_user_stacklevel())
