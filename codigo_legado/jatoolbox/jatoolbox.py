import pandas as pd
from collections import Counter
import warnings


class JAToolbox:
    """
    A class to gather some methods often used in costumer journey analysis at DP6.

    Attributes
    ----------
    This class does not have any attribute.

    Methods
    -------
    get_size(j,separator = ' > ')
      Calculates the number of touch points in a given journey.

    get_last_tp(j,separator = ' > ')
      Calculates the number of touch points in a given journey.

    get_first_tp(j,separator = ' > '):
      Returns the first touch point of the journey.

    get_nth_tp(j,n, separator = ' > '):
      Returns the n_th touch point of the journey.

    get_intermediate_tp(j,range, separator=' > '):
      Returns a subjourney formed by the touch points between the points
      indicated in the range parameter.

    get_tps_counts(j,norm=False, separator = ' > '):
      Returns how many times each distinct touch point occurres in the
      journey

    skip_tp(j,tp_to_skip, separator = ' > '):
      Returns a transformed version of the journey, where all occurencies of a
      given touch point is skipped

    skip_tp_group(j,tps_to_skip, separator = ' > '):
      Returns a transformed version of the journey, where all occurencies of any
      element from a given group of touch points is skipped

    check_tp(j,tp_to_check,separator = ' > '):
      Checks if there is any occurency of a indicated touch point in the journey.

    check_tp_group(j, tp_group_to_check, separator = ' > '):
      Checks if there is any occurency of each touch indicated in a group of
      touch points.

    get_tp_counts(j,tp, norm=False, separator = ' > '):
      Returns how many occurrecies of a given touch_point there is in
      the journey

    get_duration(timestamps,range=(0,-1)):
      Returns the time interval between two indicated touch points in the journey.
      By default the interval between the first and the last touch point.

    translate_tp(j,translation_dict,separator = ' > '):
      Returns a transformed version of the journey, where indicated touch
      points are replaced by other values according to a traslation dictionary.

    get_transitions(self,j, count = True, norm=False, separator = ' > ', ):
      Returns all the transitions between two touch points that occured in the
      journey. If the optional parameter count is set to True, the occurency counts
      for each transition is also returned.

    channels_by_tp(df, j, ocurrencies, max_journey_size, separator = ' > '):
      How many times did each channel appear at each stage of the journeys.

    tps_by_channel(self,df,j,ocurrencies,separator = ' > '):
      How many times each channel appeared on the journeys.
    """

    def __init__(self):
        pass

    def get_size(self, j, separator=" > "):
        """
        Calculates the number of touch points in a given journey.

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: int. The number of touch points
        """
        result = len(j.split(separator))
        return result

    def get_first_tp(self, j, separator=" > "):
        """
        Returns the first touch point of the journey.

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: str. A string representing the first touch point of the journey
        given in j.
        """
        splitted_j = j.split(separator)
        result = splitted_j[0]
        return result

    def get_last_tp(self, j, separator=" > "):
        """
        Returns the last touch point of the journey.

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: str. A string representing the last touch point of the journey
        given in j.
        """
        splitted_j = j.split(separator)
        result = splitted_j[-1]
        return result

    def get_nth_tp(self, j, n, separator=" > ", last_if_out=False):
        """
        Returns the n_th touch point of the journey.

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        n: int. Integer indicating de desired touch point. This parameter follows
        the Phyton standart, with 0 indicating de first touch point.

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        last_if_out: bool. If False raise an exception when n bigger than the number of touch points of
        the journey. If True selected the last touch point when n bigger than the number of touch points.

        Returns: str. A string representing the n_th touch point of the journey
        given in j.
        """
        splitted_j = j.split(separator)
        len_ref = len(splitted_j)

        if len_ref > n:
            result = splitted_j[n]
        else:
            if last_if_out:
                result = splitted_j[-1]
                warnings.warn(
                    f"Index {n} out of range. The last touch point was selected."
                )
            else:
                raise ValueError(
                    f"Index {n} out of range. Consider set last_if_out as True"
                )

        return result

    def get_intermediate_tp(self, j, range, separator=" > "):
        """
        Returns a subjourney formed by the touch points between the points
        indicated in the range parameter.

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        range: tuple or list. Tuple or list of two indicating de desired range. This parameter follows
        the Phyton standart, with 0 indicating de first touch point.

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: str. A string representing the subjourney of j formed by the touch points
        in the range indicated in the range parameter. Uses the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        """
        splitted_j = j.split(separator)
        len_ref = len(splitted_j)

        len_upper_check = len_ref >= max(range)
        len_lower_check = len_ref >= min(range)
        len_check = len_upper_check and len_lower_check
        if len_check:
            asked_tps = splitted_j[min(range) : max(range)]
            result = separator.join(asked_tps)
        else:
            result = f"out of range, journey size is {len_ref}"
        return result

    def get_tps_counts(self, j, norm=False, separator=" > "):
        """
        Returns how many times each distinct touch point occurres in the
        journey

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        norm: bool. Optional parameter, if True the result is normalized according to the
        journey size. Default: False

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: pandas.Series. A pandas.Series where the indexes are strings representing
        each distinct touch point and the values are the counts of them. If norm is set to True
        those counts will be normalized according to the journey size.
        """

        splitted_j = j.split(separator)
        series_j = pd.Series(splitted_j)
        result = series_j.value_counts(normalize=norm)
        return result

    def skip_tp(self, j, tp_to_skip, separator=" > "):
        """
        Returns a transformed version of the journey, where all occurencies of a given
        touch point is skipped

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        tp_to_skip: str. A string representing the touch point to be skipped

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: str. A string representing the transformed version of the journey j,
        where all the occurecies of the touch point indicated in tp_to_skip were skipped.
        Uses the format 'tp_0 > tp_1 > tp_2 ... tp_n'.
        """

        splitted_j = j.split(separator)
        presence_check = tp_to_skip in set(splitted_j)
        if presence_check:
            keep_tps = [x for x in splitted_j if x != tp_to_skip]
            result = separator.join(keep_tps)
        else:
            result = j
        return result

    def skip_tp_group(self, j, tps_to_skip, separator=" > "):
        """
        Returns a transformed version of the journey, where all occurencies of any
        element from a given group of touch points is skipped

        Parameters:
        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        tps_to_skip: list. A list where each element should be a string representing
        a touch point to be skipped

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: str. A string representing the transformed version of the journey j,
        where all the occurecies of any touch point present in the group of
        touch points indicated in tps_to_skip were skipped.
        Uses the format 'tp_0 > tp_1 > tp_2 ... tp_n'.
        """
        splitted_j = j.split(separator)
        tps_to_remove = [x for x in set(tps_to_skip) if x in splitted_j]
        presence_check = len(tps_to_remove) > 0

        if presence_check:
            new_j = splitted_j
            for tp in tps_to_remove:
                keep_tps = [x for x in new_j if x != tp]
                new_j = keep_tps
            result = " > ".join(new_j)
        else:
            result = j
        return result

    def check_tp(self, j, tp_to_check, separator=" > "):
        """
        Checks if there is any occurency of a indicated touch point in the journey.

        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        tp_to_chek: str. A string representing the touch point whose the presence should
        checked

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: bool. A boolean indicating if there is any occurency of the touch point
        indicated in tp_to_check. True if there is, False if there is not.
        """
        splitted_j = j.split(" > ")
        result = tp_to_check in set(splitted_j)
        return result

    def check_tp_group(self, j, tp_group_to_check, separator=" > "):
        """
        Checks if there is any occurency of each touch indicated in a group of
        touch points.

        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        tps_to_chek: list. A list where each element should be a string representing
        a touch point to be checked

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey given in j. Default: ' > '

        Returns: pandas.Series. A pandas Series where the indexes are the distinct touch
        points indicated in tps_to_check and the values are booleans indicating if
        there is any occurrency of the corresponding touch point. True if there is,
        False if there is not.

        """
        distinct_tps = set(j.split(separator))
        tp_group_to_check = set(tp_group_to_check)
        checks = [x in distinct_tps for x in tp_group_to_check]
        check_dict = dict(zip(tp_group_to_check, checks))
        result = pd.Series(check_dict)

        return result

    def get_tp_counts(self, j, tp, norm=False, separator=" > "):
        """
        Returns how many occurrecies of a given touch_point there is in
        the journey

        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        tp str. A string representing the touch point which occurrencies should
        be count.

        norm: bool. Optional parameter, if True the result is normalized according to the
        journey size. Default: False

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey indicated in j. Default: ' > '

        Returns: int. A integer indicating how many occurencies of the touch point indicated
        in tp there are in the journey.
        """
        splitted_j = j.split(separator)
        tp_ocurrencies = [x for x in splitted_j if x == tp]
        if norm:
            result = len(tp_ocurrencies) / len(splitted_j)
        else:
            result = len(tp_ocurrencies)
        return result

    def get_duration(self, timestamps, range=(0, -1)):
        """
        Returns the time interval between two indicated touch points in the journey. By default
        the interval between the first and the last touch point.

        timestamps: list. An ordered list where each element is a posix integer or a timestamp,
        indicating when each touch point of the journey occurred

        range. tuple or list. A tuple or list of two elements indicating the touch points which
        the time interval between them should be calculated. This parameter follows
        the Phyton standart, with 0 indicating de first touch point. Default: (0,-1)

        Returns: int or timestamp. The time interval between the two touch points indicated in range.
        """
        first = timestamps[range[0]]
        second = timestamps[range[1]]
        result = second - first
        return result

    def translate_tp(self, j, translation_dict, separator=" > "):
        """
        Returns a transformed version of the journey, where indicated touch
        points are replaced by other values according to a traslation dictionary.

        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        translation_dict: dict. A dictionary where the keys should be strings representing
        the touch points to be replaced, and the values should be strings representing the
        replacement values

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey indicated in j. Default: ' > '

        Returns: str. A string representing the transformed version of the journey j,
        where all the occurecies of any touch point indicated in the translation_dict parameter
        were replaced by the corresponding value.
        Uses the format 'tp_0 > tp_1 > tp_2 ... tp_n'.
        """
        splitted_j = j.split(separator)
        new_tps = []
        for tp in splitted_j:
            check = tp in translation_dict.keys()
            if check:
                new_tp = translation_dict[tp]
            else:
                new_tp = tp
            new_tps.append(new_tp)
        result = separator.join(new_tps)
        return result

    def get_transitions(
        self,
        j,
        count=True,
        norm=False,
        separator=" > ",
    ):
        """
        Returns all the transitions between two touch points that occured in the
        journey. If the optional parameter count is set to True, the occurency counts
        for each transition is also returned

        j: str. The string representing the journey. Expected in the format
        'tp_0 > tp_1 > tp_2 ... tp_n'

        count: bool. If True, the occurrency counts of each transition is returned.Default: True.

        norm: bool. If True, the occurency counts are normalized according to the
        total number of transitions

        separator: str. Character, or sequence of characters, used to
        separate the touch points of the journey indicated in j. Default: ' > '

        Returns: pandas.Series or list. If the parameter count is set to True, returns a
        pandas.Series where the indexes are tuples representing each distinct transition
        present in the journey and the values are the correnponding counts.

          If the paramenter count is set to False, returns a list where each element is a
        tuple representing the distinct transitions present in the journey.
        """

        splitted_j = j.split(" > ")
        shf = splitted_j[1:]
        transitions = list(zip(splitted_j, shf))
        if count:
            result = pd.Series(transitions).value_counts(normalize=norm)
        else:
            result = transitions
        return result

    def channels_by_tp(self, df, j, ocurrencies, max_journey_size, separator=" > "):
        """
        How many times did each channel appear at each stage of the journeys.

        Parameters:
        df: pandas.Dataframe. Dataframe that will be counted.

        j: pandas.Series. Collumn representing the journey. Expected in the
        format 'tp_0 > tp_1 > tp_2 ... tp_n'

        ocurrencies: dataframe's collumm. Collumn representing those times that
        journey occured.

        separator: str. Character, or sequence of characters, used to separate
        the touch points of the journey given in j. Default: ' > '

        Returns: pandas.Dataframe. Dataframe with the number of times each channel
        appeared at each stage of the journeys.

        """

        # Criando um df com uma coluna com os canais únicos do dataframe para dar merge lá em baixo
        df_result = pd.DataFrame(
            {"channels": list(df[j].str.split(separator).explode().unique())}
        )
        dataframe = df.copy()

        # Transformando o dataframe com explode para pode contar com o value counts
        dataframe["lista_vazia"] = dataframe[ocurrencies].apply(
            lambda j: list(range(j))
        )
        dataframe = dataframe.explode("lista_vazia")
        dataframe = dataframe[j].str.split(separator, expand=True)

        # Iterando pela quantidade de colunas (que é a quantidade de canais)
        for n in range(max_journey_size):
            if max_journey_size > len(dataframe.columns):
                result = f"out of range, max journey size is {len(dataframe.columns)}"
                return result

            else:
                # Criando um dataframe que tem uma coluna com os canais e outra com a quantidade de vezes que ele apareceu
                aux = dataframe[n].value_counts().reset_index()
                # Renomeando as colunas
                aux.columns = ["channels", f"tp_{n+1}"]
                # Dando merge no df original
                df_result = df_result.merge(aux, how="outer", on="channels")

        # Substituindo os NaN por 0
        df_result = df_result.fillna(0)

        # Transformando os valores em inteiro
        df_result.iloc[:, [1, -1]] = df_result.iloc[:, [1, -1]].astype(int)
        return df_result

    def tps_by_channel(self, df, j, ocurrencies, separator=" > "):
        """
        How many times each channel appeared on the journeys.

        Parameters:
        df: pandas.Dataframe. Dataframe that will be counted.

        j: pandas.Series. Collumn representing the journey. Expected in the
        format 'tp_0 > tp_1 > tp_2 ... tp_n'

        ocurrencies: dataframe's collumm. Collumn representing those times that
        journey occured.

        separator: str. Character, or sequence of characters, used to separate
        the touch points of the journey given in j. Default: ' > '

        Returns: pandas.Dataframe. Dataframe with the number of times each channel
        appeared on the journeys.

        """

        def multiplicador(dicionario, valor):
            for item in dicionario.keys():
                dicionario[item] = dicionario[item] * valor
            return dicionario

        aux = df.copy()
        aux["dict"] = aux[j].apply(lambda x: Counter(x.split(separator)))
        aux["dict"] = aux.apply(
            lambda x: multiplicador(x["dict"], x[ocurrencies]), axis=1
        )
        df_tps_counts = pd.DataFrame.from_dict(
            aux["dict"].sum(), orient="index"
        ).reset_index()
        df_tps_counts.columns = ["Channel", "Count"]
        return df_tps_counts
