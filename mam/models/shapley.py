import math
from functools import lru_cache
from typing import Optional

import numpy as np
import polars as pl

from .base import BaseModel

VALUE_COLUMNS = ("conv_rate", "conversions", "conversion_value", "total_sequences")

# A set of n channels has 2**n subsets. Above this size the weight matrix alone
# takes gigabytes, so the model stops instead of running out of memory.
MAX_CHANNELS = 20

# Internal key for a combination: each channel as "<length in bytes>:<name>",
# concatenated. Grouping and joins use it instead of the display string, and
# the length prefix keeps it unambiguous whatever characters a name contains.
_KEY_PART = pl.concat_str(
    pl.element().str.len_bytes().cast(pl.String), pl.lit(":"), pl.element()
)


@lru_cache(maxsize=8)
def _coalitions(n: int):
    """Every non-empty subset of n channels and its Shapley weight per channel."""
    # Returns (subsets, W): subsets[k] holds the channel indices of coalition k,
    # and W[k, i] is (s-1)!(n-s)!/n! when channel i is in it and -s!(n-s-1)!/n!
    # when it isn't, s being the coalition size. The Shapley values are V @ W.
    masks = np.arange(1, 1 << n)
    members = ((masks[:, None] >> np.arange(n)) & 1).astype(bool)
    sizes = members.sum(axis=1)
    f = [math.factorial(k) for k in range(n + 1)]
    inside = np.array([f[s - 1] * f[n - s] / f[n] for s in sizes])
    outside = np.array([-f[s] * f[n - s - 1] / f[n] if s < n else 0.0 for s in sizes])
    weights = np.where(members, inside[:, None], outside[:, None])
    subsets = [tuple(int(i) for i in np.flatnonzero(row)) for row in members]
    return subsets, weights


class ShapleyModel(BaseModel):
    """Shapley attribution over the set of channels of each journey."""

    # Each journey is reduced to its distinct channels; with max_size, only the
    # max_size most recent ones (by last appearance) are kept. The value of a set
    # of channels is value_column over the journeys with exactly that set. Within
    # each converting set, the Shapley shares split the converted value of its
    # journeys, and each journey's part for a channel is divided equally among
    # that channel's touches, so the raw output adds up to the aggregate.
    #
    # A channel can get a negative Shapley value when the sets it joins convert
    # less than the sets without it. It is kept, as in the textbook Shapley value.

    def __init__(
        self,
        max_size: Optional[int] = 4,
        value_column: str = "conv_rate",
        separator: str = " > ",
    ):
        if max_size is not None and (
            isinstance(max_size, bool)
            or not isinstance(max_size, (int, np.integer))
            or max_size < 1
        ):
            raise ValueError(
                f"max_size must be an integer of 1 or more, or None; got {max_size!r}."
            )
        if value_column not in VALUE_COLUMNS:
            raise ValueError(
                f"value_column must be one of {', '.join(VALUE_COLUMNS)}; "
                f"got {value_column!r}."
            )
        self.max_size = None if max_size is None else int(max_size)
        self.value_column = value_column
        self.separator = separator
        self.conv_table = None
        self._shares = None
        self._channels = None

    def _with_combination(self, df: pl.DataFrame) -> pl.DataFrame:
        """Adds _combo, the journey's set of channels, and _key, its internal key."""
        # _combo is sorted, but holds only the max_size most recent channels.
        # Reversed, the first occurrence of each channel is its last appearance,
        # so unique keeps the most recent first and head keeps the max_size most
        # recent. One list.eval is much faster than chaining list.* calls.
        recent = pl.element().reverse().unique(maintain_order=True)
        if self.max_size is not None:
            recent = recent.head(self.max_size)
        combo = pl.col("channels").cast(pl.List(pl.String)).list.eval(recent.sort())
        return df.with_columns(combo.alias("_combo")).with_columns(
            pl.col("_combo").list.eval(_KEY_PART).list.join("").alias("_key")
        )

    def _compute_shapley(self, df: pl.DataFrame) -> pl.DataFrame:
        self._channels = (
            df.select(pl.col("channels").cast(pl.List(pl.String)).explode())
            .to_series()
            .drop_nulls()
            .unique()
            .sort()
            .to_list()
        )
        converted = pl.col("has_conversion").fill_null(False)
        every_set = (
            self._with_combination(df)
            .group_by("_key")
            .agg(
                pl.col("_combo").first(),
                (converted.cast(pl.Int64) * pl.col("weight"))
                .sum()
                .alias("conversions"),
                pl.col("weight").sum().alias("total_sequences"),
                pl.when(converted)
                .then(pl.col("conversion_value") * pl.col("weight"))
                .otherwise(0.0)
                .sum()
                .alias("conversion_value"),
            )
            .with_columns(
                (pl.col("conversions") / pl.col("total_sequences")).alias("conv_rate")
            )
            .sort("_key")
        )
        # Every observed set gives a value (with total_sequences, a set that
        # never converted is still worth its journeys); only sets that
        # converted have value to split.
        value = dict(
            zip(
                map(tuple, every_set["_combo"].to_list()),
                every_set[self.value_column].cast(pl.Float64).to_list(),
            )
        )
        table = every_set.filter(pl.col("conversions") > 0)

        combos = table["_combo"].to_list()
        largest = max((len(c) for c in combos), default=0)
        if largest > MAX_CHANNELS:
            raise ValueError(
                f"A journey has {largest} distinct channels after max_size, and "
                f"Shapley needs 2**{largest} subsets of them, more than this "
                f"machine can hold. Set max_size to {MAX_CHANNELS} or less "
                "(15 or less keeps it fast)."
            )
        shares = []
        for combo in combos:
            subsets, weights = _coalitions(len(combo))
            v = np.array([value.get(tuple(combo[i] for i in s), 0.0) for s in subsets])
            phi = v @ weights
            # phi adds up to the value of the combination itself, which is
            # positive unless value_column is 0 there (revenue 0).
            total = phi.sum()
            if total != 0:
                shares.append((phi / total).tolist())
            else:
                shares.append([1.0 / len(combo)] * len(combo))

        allocated = [
            [s * cv for s in share]
            for share, cv in zip(shares, table["conversion_value"].to_list())
        ]
        self._shares = pl.DataFrame(
            {"_key": table["_key"], "channels": table["_combo"], "_share": shares},
            schema={
                "_key": pl.String,
                "channels": pl.List(pl.String),
                "_share": pl.List(pl.Float64),
            },
        ).explode(["channels", "_share"])
        self.conv_table = table.select(
            pl.col("_combo").list.join(self.separator).alias("combinations"),
            "conversions",
            "total_sequences",
            "conv_rate",
            "conversion_value",
            pl.Series("attribution", allocated, dtype=pl.List(pl.Float64)),
        )
        return self.conv_table

    def _ensure(self, df: pl.DataFrame) -> None:
        if self.conv_table is None:
            self._compute_shapley(df)

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        self._ensure(df)
        touches = (
            self._with_combination(df)
            .select(
                "journey_id",
                pl.col("_combo").list.join(self.separator).alias("combinations"),
                "_key",
                "channels",
                "has_conversion",
                "weight",
                "conversion_value",
            )
            .explode("channels")
            .with_columns(pl.col("channels").cast(pl.String))
        )
        return (
            touches.join(self._shares, on=["_key", "channels"], how="left")
            .with_columns(
                pl.when(pl.col("has_conversion").fill_null(False))
                .then(
                    pl.col("_share").fill_null(0.0)
                    * pl.col("conversion_value")
                    * pl.col("weight").cast(pl.Float64)
                    / pl.len().over("journey_id", "channels").cast(pl.Float64)
                )
                .otherwise(0.0)
                .alias("attribution_value")
            )
            .drop("_key", "_share")
        )

    def get_aggregated_results(self, df: pl.DataFrame) -> pl.DataFrame:
        self._ensure(df)
        credit = (
            self.conv_table.select(
                pl.col("combinations"),
                "attribution",
            )
            .with_columns(self._combo_lists())
            .explode(["channels", "attribution"])
            .group_by("channels")
            .agg(pl.col("attribution").sum())
        )
        everyone = pl.DataFrame(
            {"channels": self._channels}, schema={"channels": pl.String}
        )
        return (
            everyone.join(credit, on="channels", how="left")
            .with_columns(pl.col("attribution").fill_null(0.0))
            .sort(["attribution", "channels"], descending=[True, False])
        )

    def _combo_lists(self) -> pl.Series:
        """The channel list of each conv_table row, in the same order."""
        return (
            self._shares.group_by("_key", maintain_order=True)
            .agg("channels")
            .get_column("channels")
        )
