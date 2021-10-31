import pandas as pd
import random


def data_frame(user_id=300, k=50000, conv_rate=0.4):
    """ """
    channels = [
        "Direct",
        "Direct",
        "Facebook",
        "Facebook",
        "Facebook",
        "Google Search",
        "Google Search",
        "Google Search",
        "Google Search",
        "Google Display",
        "Organic",
        "Organic",
        "Organic",
        "Organic",
        "Organic",
        "Organic",
        "Email Marketing",
        "Youtube",
        "Instagram",
    ]
    has_transaction = ([True] * int(conv_rate * 100)) + (
        [False] * int((1 - conv_rate) * 100)
    )
    user_id = list(range(0, 700))
    day = [str(i) if len(str(i)) != 1 else "0" + str(i) for i in range(1, 30)]
    month = [str(i) if len(str(i)) != 1 else "0" + str(i) for i in range(1, 12)]
    visitStartTime = ["2020-" + month + "-" + day for month, day in zip(month, day)]

    res = {}
    colnames = ["channels", "has_transaction", "user_id", "visitStartTime"]
    for i, name in zip([channels, has_transaction, user_id, visitStartTime], colnames):
        res[name] = random.choices(population=i, k=k)

    return pd.DataFrame(res)


if __name__ == "__main__":
    print(data_frame(user_id=300, k=50000, conv_rate=0.4))

    def test_random_df():
        df = data_frame(user_id=300, k=50000, conv_rate=0.4)
        assert df.shape == (50000, 4)

    test_random_df()
