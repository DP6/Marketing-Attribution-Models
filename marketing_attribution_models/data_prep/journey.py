import pandas as pd


def journey_id_based_on_conversion(
    df, group_id, transaction_colname, timestamp_colname=None, break_window=None
):
    """
    Internal function that creates a journey_id column into a DF containing a User ID and Boolean column
    that indicates if there has been a conversion on that instance
    group_id = List of columns to be used as a ID
    """

    def list_dif(list_dates):
        max_value = len(list_dates)

        last_value = None
        results = []
        for i in list_dates:
            if last_value is None:
                results.append(0)
            else:
                value_dif = i - last_value
                results.append(value_dif.days)
                last_value = i
        return results

    df_temp = df.copy()

    for i in group_id:
        df[i] = df[i].apply(str)

    df_temp = (
        df.copy()
        # Converting bool column to int
        .assign(
            journey_id=df[transaction_colname].map(lambda x: 0 if x == False else 1)
        )
    )

    # Cumsum for each transaction to expand the value for the rows that did not have a transaction
    df_temp["journey_id"] = df_temp.groupby(group_id)["journey_id"].cumsum()

    # Timestamp break window
    if timestamp_colname is not None:
        df_time = df.groupby(group_id)[timestamp_colname].apply(list).reset_index()
        df_time.columns = group_id + ["date_id"]
        df_time["date_id"] = df_time["date_id"].apply(list_dif)
        df_time["date_id"] = df_time["date_id"].apply(
            lambda x: [0 if value_d <= break_window else 1 for value_d in x]
        )

        df_time = df_time.explode("date_id", ignore_index=True)
        df_time["date_id"] = df_time["date_id"].apply(int)
        df_time["date_id"] = df_time.groupby(group_id)["date_id"].cumsum()
        df_temp["journey_id"] = df_temp["journey_id"] + df_time["date_id"]
        # print(df_temp['journey_id'])

    # Subtracting 1 only for the row that had a transaction
    t = df_temp["journey_id"] - 1
    df_temp["journey_id"] = (
        df_temp["journey_id"]
        .where((df_temp[transaction_colname] == False), t)
        .apply(str)
    )
    df_temp["journey_id"] = "id:" + df_temp[group_id[0]] + "_J:" + df_temp["journey_id"]

    del t
    return df_temp


if __name__ == "__main__":
    df = pd.DataFrame(
        {
            "id": ["1A", "1A", "1A", "1B", "1B", "1B", "1B", "1B", "1C", "1C", "1C"],
            "date": [
                "2020-10-01",
                "2020-10-02",
                "2020-11-01",
                "2020-10-01",
                "2020-10-02",
                "2020-10-15",
                "2020-10-26",
                "2020-12-26",
                "2020-12-26",
                "2020-12-27",
                "2020-12-28",
            ],
            "converted": [
                False,
                False,
                True,
                False,
                False,
                True,
                False,
                True,
                False,
                True,
                True,
            ],
        }
    )
    df.date = pd.to_datetime(df.date)
    print(df)
    print(journey_id_based_on_conversion(df, ["id"], "converted", "date", 7))
