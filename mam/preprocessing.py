from typing import Union, Optional
import polars as pl
import pandas as pd

from .validation import build_spec, parse_iso_dates, split_path, validate_input

# Name of MAM's own row counter, so it can't clash with a column of the input
ROW_INDEX = "__mam_row_index"


def _no_times(journey_col: str, path_separator: str) -> pl.Expr:
    """One null time per channel, for inputs without times (format 3, format 2 without)."""
    return split_path(pl.col(journey_col), path_separator).list.eval(
        pl.repeat(pl.lit(None, dtype=pl.Float64), pl.element().len())
    )


def pipeline_format_1_to_unified(
    df: pl.DataFrame,
    datetime_col: str,
    user_id_col: str,
    channel_col: str,
    has_conv_col: str,
    create_journey_id_based_on_conversion: bool = False,
    conversion_value_col: Optional[str] = None,
) -> pl.DataFrame:
    """
    Converts Format 1 (Sessions / Touchpoints) to the Unified Internal Representation.

    Columns in output:
    - journey_id: pl.String
    - channels: pl.List(pl.Categorical)
    - time_till_conv: pl.List(pl.Float64)
    - has_conversion: pl.Boolean
    - weight: pl.Int64
    - conversion_value: pl.Float64
    """
    # Create lazyframe from df
    lf = df.lazy()

    # Check if datetime needs parsing
    datetime_dtype = df.schema[datetime_col]
    if datetime_dtype in (pl.String, pl.Utf8):
        lf = lf.with_columns(parse_iso_dates(df.get_column(datetime_col)))

    # Cast channel to categorical before aggregation so list is typed correctly
    # A 0/1 conversion flag becomes boolean, which any() needs on older polars
    lf = lf.with_columns(
        pl.col(channel_col)
        .cast(pl.String)
        .str.strip_chars()
        .cast(pl.Categorical)
        .alias(channel_col),
        pl.col(has_conv_col).cast(pl.Boolean).alias(has_conv_col),
    )

    # Sort chronologically by user and datetime. Touches at the same timestamp keep the
    # order of the input rows, so the same data always gives the same journeys
    lf = lf.sort([user_id_col, datetime_col], maintain_order=True)

    # Segment journeys if requested
    if create_journey_id_based_on_conversion:
        # Shift conversion flag to group elements AFTER a conversion into a new journey
        # True is treated as 1, False as 0 for cum_sum
        lf = lf.with_columns(
            pl.col(has_conv_col)
            .cast(pl.Int64)
            .shift(1)
            .fill_null(0)
            .cum_sum()
            .over(user_id_col)
            .alias(ROW_INDEX)
        ).with_columns(
            pl.concat_str([pl.col(user_id_col), pl.lit("_J"), pl.col(ROW_INDEX)]).alias(
                "journey_id"
            )
        )
    else:
        lf = lf.with_columns(pl.col(user_id_col).cast(pl.String).alias("journey_id"))

    # Aggregate into lists
    agg_exprs = [
        pl.col(channel_col).alias("channels"),
        # Difference in hours up to the last interaction in the journey
        (
            (pl.col(datetime_col).max() - pl.col(datetime_col)).dt.total_microseconds()
            / 3.6e9
        ).alias("time_till_conv"),
        pl.col(has_conv_col).any().alias("has_conversion"),
        pl.lit(1, dtype=pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        agg_exprs.append(
            pl.col(conversion_value_col)
            .cast(pl.Float64)
            .fill_null(0.0)
            .sum()
            .alias("conversion_value")
        )
    else:
        agg_exprs.append(
            pl.col(has_conv_col).any().cast(pl.Float64).alias("conversion_value")
        )

    unified_df = lf.group_by("journey_id").agg(agg_exprs)

    return unified_df.collect()


def pipeline_format_2_to_unified(
    df: pl.DataFrame,
    journey_id_col: str,
    journey_col: str,
    time_col: Optional[str],
    has_conv_col: str,
    path_separator: str = " > ",
    conversion_value_col: Optional[str] = None,
) -> pl.DataFrame:
    """
    Converts Format 2 (Journeys) to the Unified Internal Representation.

    Without a time column the times are null, as in format 3: every model runs
    except Time Decay.
    """
    times = (
        split_path(pl.col(time_col), path_separator).cast(pl.List(pl.Float64))
        if time_col
        else _no_times(journey_col, path_separator)
    )
    col_exprs = [
        pl.col(journey_id_col).cast(pl.String).alias("journey_id"),
        split_path(pl.col(journey_col), path_separator)
        .cast(pl.List(pl.Categorical))
        .alias("channels"),
        times.alias("time_till_conv"),
        pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
        pl.lit(1, dtype=pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        col_exprs.append(
            pl.col(conversion_value_col)
            .cast(pl.Float64)
            .fill_null(0.0)
            .alias("conversion_value")
        )
    else:
        col_exprs.append(
            pl.col(has_conv_col).cast(pl.Float64).alias("conversion_value")
        )

    unified_df = (
        df.lazy()
        .with_columns(col_exprs)
        .select(
            [
                "journey_id",
                "channels",
                "time_till_conv",
                "has_conversion",
                "weight",
                "conversion_value",
            ]
        )
    )
    return unified_df.collect()


def pipeline_format_3_to_unified(
    df: pl.DataFrame,
    journey_col: str,
    occurrences_col: str,
    has_conv_col: str,
    path_separator: str = " > ",
    conversion_value_col: Optional[str] = None,
) -> pl.DataFrame:
    """
    Converts Format 3 (Grouped Journeys / Frequencies) to the Unified Internal Representation.
    """
    col_exprs = [
        pl.concat_str([pl.lit("path_"), pl.col(ROW_INDEX)]).alias("journey_id"),
        split_path(pl.col(journey_col), path_separator)
        .cast(pl.List(pl.Categorical))
        .alias("channels"),
        _no_times(journey_col, path_separator).alias("time_till_conv"),
        pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
        pl.col(occurrences_col).cast(pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        col_exprs.append(
            (
                pl.col(conversion_value_col).cast(pl.Float64).fill_null(0.0)
                / pl.col(occurrences_col).cast(pl.Float64)
            ).alias("conversion_value")
        )
    else:
        col_exprs.append(
            pl.col(has_conv_col).cast(pl.Float64).alias("conversion_value")
        )

    unified_df = (
        df.lazy()
        .with_row_index(ROW_INDEX)
        .with_columns(col_exprs)
        .select(
            [
                "journey_id",
                "channels",
                "time_till_conv",
                "has_conversion",
                "weight",
                "conversion_value",
            ]
        )
    )
    return unified_df.collect()


class MAMPipeline:
    @staticmethod
    def preprocess(
        df: Union[pl.DataFrame, pd.DataFrame],
        format_type: str,  # "session", "journey", "grouped_journey"
        channels_colname: str,
        journey_with_conv_colname: str,
        datetime_colname: Optional[str] = None,
        user_id_colname: Optional[str] = None,
        time_till_conv_colname: Optional[str] = None,
        occurrences_colname: Optional[str] = None,
        create_journey_id_based_on_conversion: bool = False,
        path_separator: str = " > ",
        conversion_value_colname: Optional[str] = None,
    ) -> pl.DataFrame:
        """
        Main entrypoint for preprocessing marketing touchpoint data into
        the Unified Internal Representation.

        Raises InputValidationError when the data would make MAM fail or return
        wrong results, and warns when it can run with it. check_data_quality
        reports the same problems, and more, without running MAM.
        """
        # Convert pandas DataFrame to Polars DataFrame if necessary
        if isinstance(df, pd.DataFrame):
            df = pl.from_pandas(df)
        elif not isinstance(df, pl.DataFrame):
            raise TypeError("df must be either a Polars or Pandas DataFrame.")

        if conversion_value_colname and conversion_value_colname not in df.columns:
            raise ValueError(
                f"Conversion value column '{conversion_value_colname}' not found in DataFrame."
            )

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

        if spec.is_session:
            validate_input(df, spec)
            return pipeline_format_1_to_unified(
                df=df,
                datetime_col=datetime_colname,
                user_id_col=user_id_colname,
                channel_col=channels_colname,
                has_conv_col=journey_with_conv_colname,
                create_journey_id_based_on_conversion=create_journey_id_based_on_conversion,
                conversion_value_col=conversion_value_colname,
            )

        if spec.format_type == "journey":
            journey_id_col = spec.user_id_col

            # Ensure these columns exist or raise a helpful error
            if journey_id_col not in df.columns:
                raise ValueError(
                    f"Journey ID column '{journey_id_col}' not found in DataFrame."
                )
            validate_input(df, spec)

            return pipeline_format_2_to_unified(
                df=df,
                journey_id_col=journey_id_col,
                journey_col=channels_colname,
                time_col=spec.time_col,
                has_conv_col=journey_with_conv_colname,
                path_separator=path_separator,
                conversion_value_col=conversion_value_colname,
            )

        occurrences_col = spec.occurrences_col
        if occurrences_col not in df.columns:
            raise ValueError(
                f"Occurrences column '{occurrences_col}' not found in DataFrame."
            )
        validate_input(df, spec)

        return pipeline_format_3_to_unified(
            df=df,
            journey_col=channels_colname,
            occurrences_col=occurrences_col,
            has_conv_col=journey_with_conv_colname,
            path_separator=path_separator,
            conversion_value_col=conversion_value_colname,
        )
