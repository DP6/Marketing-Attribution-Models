from marketing_attribution_models.data import random_data


def test_random_df():
    df = random_data.data_frame(user_id=300, k=50000, conv_rate=0.4)
    assert df.shape == (50000, 4)
