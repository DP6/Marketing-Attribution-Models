from typing import Union, Optional
import polars as pl
import pandas as pd


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
        lf = lf.with_columns(pl.col(datetime_col).str.to_datetime())

    # Cast channel to categorical before aggregation so list is typed correctly
    lf = lf.with_columns(pl.col(channel_col).cast(pl.Categorical).alias(channel_col))

    # Sort chronologically by user and datetime
    lf = lf.sort([user_id_col, datetime_col])

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
            .alias("journey_idx")
        ).with_columns(
            pl.concat_str(
                [pl.col(user_id_col), pl.lit("_J"), pl.col("journey_idx")]
            ).alias("journey_id")
        )
    else:
        lf = lf.with_columns(pl.col(user_id_col).cast(pl.String).alias("journey_id"))

    # Aggregate into lists
    agg_exprs = [
        pl.col(channel_col).alias("channels"),
        # Difference in hours up to the last interaction in the journey
        (
            (pl.col(datetime_col).max() - pl.col(datetime_col)).dt.total_seconds()
            / 3600.0
        ).alias("time_till_conv"),
        pl.col(has_conv_col).any().alias("has_conversion"),
        pl.lit(1, dtype=pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        agg_exprs.append(
            pl.col(conversion_value_col).fill_null(0.0).sum().cast(pl.Float64).alias("conversion_value")
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
    time_col: str,
    has_conv_col: str,
    path_separator: str = " > ",
    conversion_value_col: Optional[str] = None,
) -> pl.DataFrame:
    """
    Converts Format 2 (Journeys) to the Unified Internal Representation.
    """
    col_exprs = [
        pl.col(journey_id_col).cast(pl.String).alias("journey_id"),
        pl.col(journey_col)
        .str.split(path_separator)
        .cast(pl.List(pl.Categorical))
        .alias("channels"),
        pl.col(time_col)
        .str.split(path_separator)
        .cast(pl.List(pl.Float64))
        .alias("time_till_conv"),
        pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
        pl.lit(1, dtype=pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        col_exprs.append(
            pl.col(conversion_value_col).cast(pl.Float64).fill_null(0.0).alias("conversion_value")
        )
    else:
        col_exprs.append(
            pl.col(has_conv_col).cast(pl.Float64).alias("conversion_value")
        )

    unified_df = (
        df.lazy()
        .with_columns(col_exprs)
        .select(
            ["journey_id", "channels", "time_till_conv", "has_conversion", "weight", "conversion_value"]
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
        pl.concat_str([pl.lit("path_"), pl.col("journey_idx")]).alias(
            "journey_id"
        ),
        pl.col(journey_col)
        .str.split(path_separator)
        .cast(pl.List(pl.Categorical))
        .alias("channels"),
        # Initialize time_till_conv as a list of nulls of the same length (absence of time data)
        pl.col(journey_col)
        .str.split(path_separator)
        .list.eval(
            pl.repeat(pl.lit(None, dtype=pl.Float64), pl.element().len())
        )
        .alias("time_till_conv"),
        pl.col(has_conv_col).cast(pl.Boolean).alias("has_conversion"),
        pl.col(occurrences_col).cast(pl.Int64).alias("weight"),
    ]

    if conversion_value_col:
        col_exprs.append(
            pl.col(conversion_value_col).cast(pl.Float64).fill_null(0.0).alias("conversion_value")
        )
    else:
        col_exprs.append(
            pl.col(has_conv_col).cast(pl.Float64).alias("conversion_value")
        )

    unified_df = (
        df.lazy()
        .with_row_index("journey_idx")
        .with_columns(col_exprs)
        .select(
            ["journey_id", "channels", "time_till_conv", "has_conversion", "weight", "conversion_value"]
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

        normalized_format = format_type.lower().strip()

        if normalized_format in ("session", "format_1"):
            if not datetime_colname or not user_id_colname:
                raise ValueError(
                    "datetime_colname and user_id_colname are required for 'session' format."
                )
            return pipeline_format_1_to_unified(
                df=df,
                datetime_col=datetime_colname,
                user_id_col=user_id_colname,
                channel_col=channels_colname,
                has_conv_col=journey_with_conv_colname,
                create_journey_id_based_on_conversion=create_journey_id_based_on_conversion,
                conversion_value_col=conversion_value_colname,
            )

        elif normalized_format in ("journey", "format_2"):
            journey_id_col = user_id_colname if user_id_colname else "journey_id"
            time_col = (
                time_till_conv_colname if time_till_conv_colname else "time_till_end"
            )

            # Ensure these columns exist or raise a helpful error
            if journey_id_col not in df.columns:
                raise ValueError(
                    f"Journey ID column '{journey_id_col}' not found in DataFrame."
                )
            if time_col not in df.columns:
                raise ValueError(f"Time column '{time_col}' not found in DataFrame.")

            return pipeline_format_2_to_unified(
                df=df,
                journey_id_col=journey_id_col,
                journey_col=channels_colname,
                time_col=time_col,
                has_conv_col=journey_with_conv_colname,
                path_separator=path_separator,
                conversion_value_col=conversion_value_colname,
            )

        elif normalized_format in ("grouped_journey", "format_3"):
            occurrences_col = (
                occurrences_colname if occurrences_colname else "occurrences"
            )
            if occurrences_col not in df.columns:
                raise ValueError(
                    f"Occurrences column '{occurrences_col}' not found in DataFrame."
                )

            return pipeline_format_3_to_unified(
                df=df,
                journey_col=channels_colname,
                occurrences_col=occurrences_col,
                has_conv_col=journey_with_conv_colname,
                path_separator=path_separator,
                conversion_value_col=conversion_value_colname,
            )

        else:
            raise ValueError(
                f"Unknown format_type '{format_type}'. "
                "Supported formats: 'session', 'journey', 'grouped_journey'."
            )
