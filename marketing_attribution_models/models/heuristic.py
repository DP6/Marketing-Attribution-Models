import math

import numpy as np
import pandas as pd


def last_click(channels_list, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    return np.asarray(([0] * (len(channels_list) - 1)) + [value])


def last_click_non(channels_list, non_value, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    if len(channels_list) > 1:
        return np.asarray(
            [
                value
                if i
                == max(
                    [
                        i if canal != non_value else 0
                        for i, canal in enumerate(channels_list)
                    ]
                )
                else 0
                for i, canal in enumerate(channels_list)
            ]
        )
    else:
        return np.asarray([value])


def first_click(channels_list, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    return np.asarray([value] + ([0] * (len(channels_list) - 1)))


def linear(channels_list, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    value = value / len(channels_list)

    return np.asarray([value] * len(channels_list))


def position_based(channels_list, distribution_list=None, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    if distribution_list is None:
        distribution_list = [0.4, 0.2, 0.4]

    if len(distribution_list) > 3:
        raise ValueError("distribution_list length cannot be greater than 3")

    if len(channels_list) <= 2:
        return linear(channels_list, value=value)
    else:
        return np.asarray(
            [distribution_list[0]]
            + [distribution_list[1] / (len(channels_list) - 2)]
            * (len(channels_list) - 2)
            + [distribution_list[0]]
        )


def position_decay(channels_list, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    if len(channels_list) == 1:
        return np.asarray([value])
    else:
        return np.asarray(list(range(1, len(channels_list) + 1))) / np.sum(
            np.asarray(list(range(1, len(channels_list) + 1)))
        )


def time_decay(decay_list, decay_over_time=0.5, frequency=168, value=1):
    """

    Parameters
    ----------
    channels_list : list
        List of channels.
    Returns
    -------
    list : list
        List with values distributed
    """
    if len(decay_list) == 1:
        return np.asarray([value])
    else:
        v1 = math.log(decay_over_time)
        v2 = np.floor(np.asarray(decay_list) / frequency)
        return np.exp(v1 * v2) / sum(np.exp(v1 * v2))


if __name__ == "__main__":
    channels = pd.Series([["x", "y", "z"], ["x", "y", "z", "y", "z"], ["z"]])
    print(channels.apply(last_click))
    print(channels.apply(lambda x: last_click_non(x, "z")))
    print(channels.apply(first_click))
    print(channels.apply(linear))
    print(channels.apply(position_based))
    print(channels.apply(position_decay))
    dacay = pd.Series([[1680, 168, 0], [168, 0]])
    print(dacay.apply(time_decay))
