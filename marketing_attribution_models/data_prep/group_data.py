import pandas as pd


def group_channels(
    df,
    channels_colname,
    group_timestamp_colname,
    group_channels_by_id_list,
    print_log=True,
):

    # Grouping channels based on group_channels_by_id_list
    ######################################################
    if print_log:
        print("group_channels == True")
        print("Grouping channels...")
    temp_channels = (
        df.groupby(group_channels_by_id_list)[channels_colname]
        .apply(list)
        .reset_index()
    )
    if print_log:
        print("Status: Done")

    # Grouping timestamp based on group_channels_by_id_list
    ####################################################
    if print_log:
        print("Grouping timestamp...")
    df_temp = df[group_channels_by_id_list + [group_timestamp_colname]]
    df_temp = df_temp.merge(
        df.groupby(group_channels_by_id_list)[group_timestamp_colname].max(),
        on=group_channels_by_id_list,
    )

    # calculating the time till conversion
    ######################################
    df_temp["time_till_conv"] = (
        df_temp[group_timestamp_colname + "_y"]
        - df_temp[group_timestamp_colname + "_x"]
    ).astype("timedelta64[h]")

    df_temp = (
        df_temp.groupby(group_channels_by_id_list)["time_till_conv"]
        .apply(list)
        .reset_index()
        .assign(channel=temp_channels[channels_colname])
    )
    if print_log:
        print("Status: Done")

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
            "channelsss": [
                "Google",
                "Google",
                "Face",
                "Face",
                "Face",
                "Organic",
                "Organic",
                "Organic",
                "Google",
                "Face",
                "Google",
            ],
        }
    )
    df.date = pd.to_datetime(df.date)
    print(df)
    results = group_channels(
        df,
        channels_colname="channelsss",
        group_timestamp_colname="date",
        group_channels_by_id_list=["id"],
        print_log=True,
    )
    print(results)
