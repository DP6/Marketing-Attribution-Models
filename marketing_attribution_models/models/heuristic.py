import numpy as np
import pandas as pd


def last_click(list, value=1):
    """

    Parameters
    ----------
    list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    return np.asarray(([0] * (len(list) - 1)) + [value])


def first_click(list, value=1):
    """

    Parameters
    ----------
    list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    return np.asarray([value] + ([0] * (len(list) - 1)))


if __name__ == "__main__":
    channels = pd.Series([["x", "y", "z"]])
    print(channels.apply(last_click))
