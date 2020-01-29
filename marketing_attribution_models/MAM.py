import numpy as np
import pandas as pd
import itertools
import math
import re
import matplotlib.pyplot as plt
import seaborn as sns
plt.style.use('seaborn-white')


class DP6tribution:
    """
    MAM (Marketing Attribution Models) is a class inspired on the R Package ‘GameTheoryAllocation’ from Alejandro Saavedra-Nieves
    and ‘ChannelAttribution’ from Davide Altomare and David Loris that was created to bring these concepts to
    Python and to help us understand how the different marketing channels behave during the customer journey.

    Parameters:

      df = None by default, but should only be None if choosing to use a random dataframe. Otherwise,
          it has to receive a Pandas dataframe;

      time_till_conv_colname = None by default. Column name in the df containing the time in hours untill
                              the moment of the conversion. The column must have the same elements as the
                              channels_colname has.

                              Values could be on a list ou a string with a separator;

      conversion_value = 1 by default. Integer that represents a monetary value of a 'conversion', can
                          also receive a string indicating the column name on the dataframe containing the
                          conversion values;

      channels_colname = None by default. Column name in the df containing the different channels during the
                        customer journey. The column must have the same elements as the time_till_conv_colname
                        has.

                        Values could be on a list ou a string with a separator;

      journey_with_conv_colname = None by default.

      group_channels = False by default. Most important parameter on this class. This indicates the input
                      format of the dataframe.

                      True = Each row represents a user session that will be grouped
                      into a user journey;

                      False = Each row represents a user journey and the columns

      group_channels_by_id_list = Empty list by default.

      group_timestamp_colname = None by default.

      create_journey_id_based_on_conversion = False by default.

      path_separator = ' > ' by default. If using 'group_channels = True', this should match the separator
                      being used on the inputed dataframe in the channels_colname;

      verbose = False by default. Internal parameter for printing while working with MAM;

      random_df = False by default. Will create a random dataframe with testing purpose;

    """

    def __init__(
            self,
            df=None,
            time_till_conv_colname=None,
            conversion_value=1,
            channels_colname=None,
            journey_with_conv_colname=None,
            group_channels=False,
            group_channels_by_id_list=[],
            group_timestamp_colname=None,
            create_journey_id_based_on_conversion = False,
            path_separator=' > ',
            verbose=False,
            random_df=False):

        self.verbose = verbose
        self.sep = path_separator
        self.group_by_channels_models = None

        ##########################################################
        ##### Section 0: Funcions needed to create the class #####
        ##########################################################

        def journey_id_based_on_conversion(df,
                                           group_id,
                                           transaction_colname):
          """
          Internal function that creates a journey_id column into a DF containing a User ID and Boolean column
          that indicates if there has been a conversion on that instance
          """
          df_temp = df.copy()

          for i in group_id:
            df_temp[i] = df_temp[i].apply(str)

          #Converting bool column to int
          df_temp['journey_id'] = df_temp[transaction_colname].map(lambda x: 0 if x == False else 1)

          #Cumsum for each transaction to expand the value for the rows that did not have a transaction
          df_temp['journey_id'] = df_temp.groupby(group_id)['journey_id'].cumsum()

          #Subtracting 1 only for the row that had a transaction
          t = df_temp['journey_id'] - 1
          df_temp['journey_id'] = df_temp['journey_id'].where((df_temp[transaction_colname] == False), t).apply(str)
          df_temp['journey_id'] = 'id:' + df_temp[group_id[0]] + '_J:' + df_temp['journey_id']

          del t
          return df_temp

        def random_mam_data_frame(user_id = 300, k = 50000, conv_rate = 0.4):
          import random
          channels = ['Direct', 'Direct', 'Facebook', 'Facebook', 'Facebook',
                      'Google Search', 'Google Search', 'Google Search', 'Google Search', 'Google Display',
                      'Organic', 'Organic', 'Organic', 'Organic', 'Organic', 'Organic',
                      'Email Marketing', 'Youtube', 'Instagram']
          has_transaction = ([True] * int(conv_rate * 100)) + ([False] * int((1 - conv_rate) * 100))
          user_id = list(range(0, 700))
          day = range(1, 30)
          month = range(1, 12)

          res = []
          for i in [channels,has_transaction, user_id, day, month]:
            res.append(random.choices(population=i, k=k))

          df = pd.DataFrame(res).transpose()
          df.columns = ['channels', 'has_transaction', 'user_id', 'day', 'month']
          df['visitStartTime'] = '2020-' + df['month'].apply(lambda val: str(val) if val > 9 else '0' + str(val)) +'-'+ df['day'].apply(lambda val: str(val) if val > 9 else '0' + str(val))

          return df

        #####################################################
        ##### Section 1: Creating object and attributes #####
        #####################################################

        ###########################
        #### random_df == True ####
        ###########################

        if random_df:
          df = random_mam_data_frame()
          group_channels=True
          channels_colname = 'channels'
          journey_with_conv_colname= 'has_transaction'
          group_channels_by_id_list=['user_id']
          group_timestamp_colname = 'visitStartTime'
          create_journey_id_based_on_conversion = True


        ################################
        #### group_channels == True ####
        ################################

        if group_channels:

          # Copying, sorting and converting variables
          df = df.reset_index().copy()
          df[group_timestamp_colname] = pd.to_datetime( df[group_timestamp_colname])
          df.sort_values( group_channels_by_id_list + [group_timestamp_colname], inplace=True)

          if create_journey_id_based_on_conversion:

            df = journey_id_based_on_conversion(df = df,
                                                group_id = group_channels_by_id_list,
                                                transaction_colname = journey_with_conv_colname)

            group_channels_by_id_list = ['journey_id']

            # Grouping channels based on group_channels_by_id_list
            ######################################################
            self.print('group_channels == True')
            self.print('Grouping channels...')
            temp_channels = df.groupby(group_channels_by_id_list)[
                channels_colname].apply(list).reset_index()
            self.channels = temp_channels[channels_colname]
            self.print('Status: Done')

            # Grouping timestamp based on group_channels_by_id_list
            ####################################################
            self.print('Grouping timestamp...')
            df_temp = df[group_channels_by_id_list + [group_timestamp_colname]]
            df_temp = df_temp.merge(
                df.groupby(group_channels_by_id_list)[group_timestamp_colname].max(),
                on=group_channels_by_id_list)

            # calculating the time till conversion
            ######################################
            df_temp['time_till_conv'] = (df_temp[group_timestamp_colname + '_y'] -
                                         df_temp[group_timestamp_colname + '_x']).astype('timedelta64[h]')

            df_temp = df_temp.groupby(group_channels_by_id_list)[
                'time_till_conv'].apply(list).reset_index()
            self.time_till_conv = df_temp['time_till_conv']
            self.print('Status: Done')

            if journey_with_conv_colname is None:

                # If journey_with_conv_colname is None, we will assume that
                # all journeys ended in a conversion
                ###########################################################
                self.journey_with_conv = self.channels.apply(lambda x: True)
                self.journey_id = pd.Series(df[group_channels_by_id_list].unique())

            else:
                # Grouping unique journeys and whether the journey ended with a
                # conversion
                ##########################################################
                self.print('Grouping journey_id and journey_with_conv...')
                df_temp = df[group_channels_by_id_list +
                             [journey_with_conv_colname]]
                temp_journey_id_conv = df_temp.groupby(group_channels_by_id_list)[
                    journey_with_conv_colname].max().reset_index()
                self.journey_id = temp_journey_id_conv[group_channels_by_id_list]
                self.print('Status: Done')
                self.journey_with_conv = temp_journey_id_conv[journey_with_conv_colname]
                self.print('Status: Done')

        #################################
        #### group_channels == False ####
        #################################
        else:
            self.journey_id = df[group_channels_by_id_list]

            #####################
            ### self.channels ###
            #####################

            # converts channels str to list of channels
            if isinstance(df[channels_colname][0], str):
              self.channels = df[channels_colname].apply(lambda x: x.split(self.sep))
            else:
              self.channels = df[channels_colname]

            ###########################
            ### self.time_till_conv ###
            ###########################
            if time_till_conv_colname is None:
              self.time_till_conv = self.channels.apply(lambda x: list(range(len(x)))[::-1])
              self.time_till_conv = self.time_till_conv.apply(lambda x: list(np.asarray(x) * 24 ))
            else:
              if isinstance(df[channels_colname][0], str):
                self.time_till_conv = df[time_till_conv_colname].apply(lambda x: [float(value) for value in x.split(self.sep)])
              else:
                self.time_till_conv = df[time_till_conv_colname]

            ##############################
            ### self.journey_with_conv ###
            ##############################
            if journey_with_conv_colname is None:
                self.journey_with_conv = self.channels.apply(lambda x: True)
            else:
              self.journey_with_conv = df[journey_with_conv_colname]

        ########################
        ### conversion_value ###
        ########################

        # conversion_value could be a single int value or a panda series
        if isinstance(conversion_value, int):
          self.conversion_value = self.journey_with_conv.apply(lambda valor: conversion_value if valor else 0)
        else:
          self.conversion_value = df[conversion_value]

        #################
        ### DataFrame ###
        #################

        self.DataFrame = None
        self.as_pd_dataframe()


    ######################################
    ##### Section 2: Output methods  #####
    ######################################

    def print(self, *args, **kwargs):
      if self.verbose:
          print(*args, **kwargs)

    def as_pd_dataframe(self):
      """
      Return inputed attributes as a Pandas Data Frame on self.DataFrame
      """
      if not(isinstance(self.DataFrame, pd.DataFrame)):
        if isinstance(self.journey_id, pd.DataFrame):
            self.DataFrame = self.journey_id
            self.DataFrame['channels_agg'] = self.channels.apply(lambda x: self.sep.join(x))
            self.DataFrame['time_till_conv_agg'] = self.time_till_conv.apply(lambda x : self.sep.join([str(value) for value in x]))
            self.DataFrame['converted_agg'] = self.journey_with_conv
            self.DataFrame['conversion_value'] = self.conversion_value
        else:
            self.DataFrame = pd.DataFrame({'journey_id': self.journey_id,
                                    'channels_agg': self.channels.apply(lambda x: self.sep.join(x)),
                                    'time_till_conv_agg': self.time_till_conv.apply(lambda x : self.sep.join([str(value) for value in x])),
                                    'converted_agg': self.journey_with_conv,
                                    'conversion_value': self.conversion_value})


      return self.DataFrame

    def attribution_all_models(
            self,
            model_type='all',
            last_click_non_but_not_this_channel='Direct',
            time_decay_decay_over_time=0.5,
            time_decay_frequency=128,
            shapley_size=4,
            shapley_order=False,
            shapley_values_col= 'conv_rate',
            markov_transition_to_same_state=False,
            group_by_channels_models=True):
        """
        Runs all heuristic models on this class and returns a data frame.
        Models: attribution_last_click_non, attribution_first_click, attribution_linear, attribution_position_based, attribution_time_decay

        Parameters:
        model_type = ['all',
                     'heuristic'
                     'algorithmic']


        """

        if model_type == 'all':
          heuristic = True
          algorithmic = True
        elif model_type == 'heuristic':
          heuristic = True
          algorithmic = False
        else:
          heuristic = False
          algorithmic = True

        if heuristic:
          # Running attribution_last_click
          self.attribution_last_click(group_by_channels_models=group_by_channels_models)

          # Running attribution_last_click_non
          self.attribution_last_click_non(but_not_this_channel = last_click_non_but_not_this_channel)

          # Running attribution_first_click
          self.attribution_first_click(group_by_channels_models=group_by_channels_models)

          # Running attribution_linear
          self.attribution_linear(
                        group_by_channels_models=group_by_channels_models)

          # Running attribution_position_based
          self.attribution_position_based(group_by_channels_models=group_by_channels_models)

          # Running attribution_time_decay
          self.attribution_time_decay(
              decay_over_time = time_decay_decay_over_time,
              frequency=time_decay_frequency,
              group_by_channels_models=group_by_channels_models)

        if algorithmic:

          # Running attribution_shapley
          self.attribution_shapley(size=shapley_size,
                                    order=shapley_order,
                                    group_by_channels_models=group_by_channels_models,
                                    values_col=shapley_values_col)

          # Running attribution_shapley
          self.attribution_markov(transition_to_same_state=markov_transition_to_same_state)


        return self.group_by_channels_models

    def plot(self,
             model_type='all',
             sort_model=None,
             number_of_channels=10,
             other_df = None,
             *args, **kwargs):

      """
      Barplot of the results that were generated and stored on the variable self.group_by_channels_models

      Parameters:
      model_type = ['all',
                     'heuristic'
                     'algorithmic']
      sort_model = has to be a string and accept regex by inputing r'example'

      other_df = None. In case the user wants to use a new data frame

      """

      model_types = {'all':'all',
                     'heuristic': r'heuristic',
                     'algorithmic': r'algorithmic'}

      if not isinstance(other_df, pd.DataFrame):
        # Checking if there are any results on self.group_by_channels_models
        if isinstance(self.group_by_channels_models, pd.DataFrame):
          df_plot = self.group_by_channels_models
        else:
          ax = 'self.group_by_channels_models == None'
      else:
        df_plot = other_df

      # Sorting self.group_by_channels_models
      if sort_model != None:
        # List comprehension to accept regex
        df_plot = df_plot.sort_values([[x for x in df_plot.columns if (re.search(sort_model, x))]][0],
                                      ascending=True)

      #Selecting columns that matches the pattern
      if model_types[model_type] != 'all':
        df_plot = df_plot[['channels'] + [x for x in df_plot.columns if re.search(model_types[model_type], x)]]

      # Subsetting the results based on the number of channels to be shown
      df_plot = df_plot.tail(number_of_channels)

      # Melting DF so the results are devided into 'channels', 'variable' and 'value'
      df_plot = pd.melt(df_plot,id_vars='channels')

      # Plot Parameters
      ax, fig = plt.subplots(figsize=(20,7))
      ax = sns.barplot(data = df_plot, hue = 'variable', y = 'value', x = 'channels', *args, **kwargs)
      plt.xticks(rotation=15)
      ax.legend(loc = 'upper left', frameon = True, fancybox = True)
      ax.axhline(0, color='black', linestyle='-', alpha=1,lw=2)
      ax.grid(color='gray', linestyle=':', linewidth=1, axis='y')
      ax.set_frame_on(False)

      return ax


    def channels_journey_time_based_overwrite(
            self, selected_channel='Direct', time_window=24, order=1, inplace=False):
        """
        Overwrites channels in the conversion jorney that matches the criteria with the previous
        channel in the journey:
          - Is equal to the selected_channel;
          - The diference between the contacts is less than the time_window selected;

        Parameters:
        selected_channel = channel to be overwritten;
        time_window = the time window in hours that the selected channel will be overwritten;
        order = how many times the function will loop throught the same journey;
            ex: journey [Organic > Direct > Direct]
              order 1 output: [Organic > Organic > Direct]
              order 2 output: [Organic > Organic > Organic]
        """
        frame = self.channels.to_frame(name='channels')
        frame['time_till_conv_window'] = self.time_till_conv.apply(lambda time_till_conv: [time_window + 1] + [
                                                                   time - time_till_conv[i + 1] for i, time in enumerate(time_till_conv) if i < len(time_till_conv) - 1])
        frame['time_till_conv_window'] = frame['time_till_conv_window'].apply(
            lambda time_till_conv: np.absolute(np.asarray(time_till_conv)).tolist())
        loop_count = 0
        while loop_count < order:
            frame['channels'] = frame.apply(lambda x: [x.channels[i - 1] if ((canal == selected_channel) & (
                time < time_window)) else canal for i, (canal, time) in enumerate(zip(x.channels, x.time_till_conv_window))], axis=1)
            loop_count += 1

        if inplace:
          self.channels = frame['channels'].copy()
          new_channels = None
        else:
          new_channels = frame['channels'].copy()

        return new_channels

    def group_by_results_function(self, channels_value, model_name):
      """
      Internal function to generate the group_by_channels_models. A pandas DF containing
      the attributed values for each channel
      """
      channels_list = []
      self.channels.apply(lambda x: channels_list.extend(x))
      values_list = []
      channels_value.apply(lambda x: values_list.extend(x))

      frame = pd.DataFrame(
          {'channels': channels_list, 'value': values_list})
      frame = frame.groupby(['channels'])['value'].sum()

      if isinstance(self.group_by_channels_models, pd.DataFrame):
        frame = frame.reset_index()
        frame.columns = ['channels', model_name]
        self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame,
                                          how='outer', on=['channels']).fillna(0)
      else:
        self.group_by_channels_models = frame.reset_index()
        self.group_by_channels_models.columns = ['channels', model_name]

      return frame


    ###################################################
    ##### Section 3: Channel Attribution methods  #####
    ###################################################

    def attribution_last_click(self, group_by_channels_models=True):
        """
        The last touchpoint receives all the credit

        Parameters:
        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models

        """
        model_name = 'attribution_last_click_heuristic'

        # Results part 1: Column values
        # Results in the same format as the DF
        channels_value = self.channels.apply(
            lambda channels: np.asarray(([0] * (len(channels) - 1)) + [1]))
        # multiplying the results with the conversion value
        channels_value = channels_value * self.conversion_value
        # multiplying with the boolean column that indicates whether the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))


        # Results part 2: Results
        if group_by_channels_models:


          # Selecting last channel from the series
          channels_series = self.channels.apply(lambda x: x[-1])

          # Creating a data_frame where we have the last channel and the
          # conversion values
          frame = channels_series.to_frame(name='channels')
          # multiplying with the boolean column that indicates if the conversion
          # happened
          frame['value'] = self.conversion_value * \
              self.journey_with_conv.apply(int)

          # Grouping by channels and adding the values
          frame = frame.groupby(['channels'])['value'].sum()

          # Grouped Results
          if isinstance(self.group_by_channels_models, pd.DataFrame):
            frame = frame.reset_index()
            frame.columns = ['channels', model_name]
            self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame, how='outer', on=['channels']).fillna(0)
          else:
            self.group_by_channels_models = frame.reset_index()
            self.group_by_channels_models.columns = ['channels', model_name]
        else:
          frame = 'group_by_channels_models = False'

        return (channels_value, frame)

    def attribution_last_click_non(self, but_not_this_channel='Direct', group_by_channels_models=True):
        """
        All the traffic from a Specific channel is ignored,
        and 100% of the credit for the sale goes to the last channel that the customer clicked through from before converting

        Parameters:
        but_not_this_channel = channel to be overwritten

        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models

        """
        model_name = 'attribution_last_click_non_' + but_not_this_channel + '_heuristic'

        # Results part 1: Column values
        # Results in the same format as the DF
        channels_value = self.channels.apply(
            lambda canais: np.asarray(
                [
                    1 if i == max(
                        [
                            i if canal != but_not_this_channel else 0 for i,
                            canal in enumerate(canais)]) else 0 for i,
                    canal in enumerate(canais)]))
        # multiplying the results with the conversion value
        channels_value = channels_value * self.conversion_value
        # multiplying with the boolean column that indicates if the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Results part 2: Results
        if group_by_channels_models:

          # Selecting the last channel that is not the one chosen
          channels_series = self.channels.apply(
              lambda canais: (
                  canais[-1] if len([canal for canal in canais if canal != but_not_this_channel]) == 0
                  else canais[max([i for i, canal in enumerate(canais) if canal != but_not_this_channel])]))

          # Creating a data_frame where we have the last channel and the
          # conversion values
          frame = channels_series.to_frame(name='channels')
          # multiplying with the boolean column that indicates whether the conversion
          # happened
          frame['value'] = self.conversion_value * \
              self.journey_with_conv.apply(int)

          # Grouping by channels and adding the values
          frame = frame.groupby(['channels'])['value'].sum()

          if isinstance(self.group_by_channels_models, pd.DataFrame):
            frame = frame.reset_index()
            frame.columns = ['channels', model_name]
            self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame, how='outer', on=['channels']).fillna(0)
          else:
            self.group_by_channels_models = frame.reset_index()
            self.group_by_channels_models.columns = ['channels', model_name]

        return (channels_value, frame)

    def attribution_first_click(self, group_by_channels_models=True):
        """
        The first touchpoint recieves all the credit

        Parameters:
        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models
        """
        model_name = 'attribution_first_click_heuristic'

        # Results part 1: Column values
        ###############################

        # Results in the same format as the DF
        channels_value = self.channels.apply(
            lambda channels: np.asarray([1] + ([0] * (len(channels) - 1))))
        # multiplying the results with the conversion value
        channels_value = channels_value * self.conversion_value
        # multiplying with the boolean column that indicates if the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Results part 2: Grouped Results
        #################################

        if group_by_channels_models:
          # Selecting first channel from the series
          channels_series = self.channels.apply(lambda x: x[0])

          # Creating a data_frame where we have the last channel and the
          # conversion values
          frame = channels_series.to_frame(name='channels')
          # multiplying with the boolean column that indicates if the conversion
          # happened
          frame['value'] = self.conversion_value * \
              self.journey_with_conv.apply(int)

          # Grouping by channels and adding the values
          frame = frame.groupby(['channels'])['value'].sum()

          if isinstance(self.group_by_channels_models, pd.DataFrame):
            frame = frame.reset_index()
            frame.columns = ['channels', model_name]
            self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame, how='outer', on=['channels']).fillna(0)
          else:
            self.group_by_channels_models = frame.reset_index()
            self.group_by_channels_models.columns = ['channels', model_name]

        return (channels_value, frame)

    def attribution_linear(self, group_by_channels_models=True):
        """
        Each touchpoint in the conversion path has an equal value

        Parameters:
        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models
        """
        model_name = 'attribution_linear_heuristic'

        channels_count = self.channels.apply(lambda x: len(x))
        channels_value = (self.conversion_value * self.journey_with_conv.apply(int) /
                                                  channels_count).apply(lambda x: [round(x, 2)]) * channels_count

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Grouping the attributed values for each channel
        if group_by_channels_models:
          frame = self.group_by_results_function(channels_value, model_name)
        else:
          frame = 'group_by_channels_models = False'

        return (channels_value, frame)

    def attribution_position_based(
        self, list_positions_first_middle_last=[
            0.4, 0.2, 0.4], group_by_channels_models=True):
        """
        First and last contact have preset values, middle touchpoints are evenly distributed with the chosen weight.

        default:
         - First channel = 0.4
         - Distributed among the middle channels = 0.2
         - Last channel = 0.4

        Parameters:
        list_positions_first_middle_last = list with percentages that will be given to each position

        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models
        """
        model_name = 'attribution_position_based_' + '_'.join([str(value) for value in list_positions_first_middle_last]) + '_heuristic'

        # Selecting last channel from the series
        channels_value = self.channels.apply(
            lambda canais: np.asarray([1]) if len(canais) == 1
            else np.asarray([list_positions_first_middle_last[0] + list_positions_first_middle_last[1] / 2, list_positions_first_middle_last[2] + list_positions_first_middle_last[1] / 2]) if len(canais) == 2
            else np.asarray([list_positions_first_middle_last[0]] + [list_positions_first_middle_last[1] / (len(canais) - 2)] * (len(canais) - 2) + [list_positions_first_middle_last[0]]))
        # multiplying the results with the conversion value
        channels_value = channels_value * self.conversion_value
        # multiplying with the boolean column that indicates if the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Grouping the attributed values for each channel
        if group_by_channels_models:
          frame = self.group_by_results_function(channels_value, model_name)
        else:
          frame = 'group_by_channels_models = False'

        return (channels_value, frame)

    def attribution_position_decay(self, group_by_channels_models=True):
        """
        OBS: This function is in working progress
        Linear decay for each touchpoint further from conversion.

        Parameters:
        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models

        """
        model_name = 'attribution_position_decay_heuristic'

        channels_value = self.channels.apply(
            lambda channels: np.asarray(
                [1]) if len(channels) == 1 else (
                np.asarray(
                    list(
                        range(
                            1,
                            len(channels) +
                            1))) /
                np.sum(
                    np.asarray(
                        list(
                            range(
                                1,
                                len(channels) +
                                1))))))
        # multiplying the results with the conversion value
        channels_value = channels_value * self.conversion_value
        # multiplying with the boolean column that indicates if the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Grouping the attributed values for each channel
        if group_by_channels_models:
          frame = self.group_by_results_function(channels_value, model_name)
        else:
          frame = 'group_by_channels_models = False'

        return (channels_value, frame)

    def attribution_time_decay(
            self,
            decay_over_time=0.5,
            frequency=168,
            group_by_channels_models=True):
        """
        Decays for each touchpoint further from conversion

        Parameters:
        decay_over_time = percentage that will be lost by time away from the conversion

        frequency = The frequency in hours that the decay will happen

        group_by_channels_models= True by default. Will aggregate the attributed results by each channel on
        self.group_by_channels_models
        """
        model_name = 'attribution_time_decay' + str(decay_over_time) + '_freq' + str(frequency) + '_heuristic'

        # Removing zeros and dividing by the frequency
        time_till_conv_window = self.time_till_conv.apply(lambda time_till_conv:
                                                    np.exp(math.log(decay_over_time) * np.floor(np.asarray(time_till_conv) / frequency)) /
                                                    sum(np.exp(math.log(decay_over_time) * np.floor(np.asarray(time_till_conv) / frequency))) )


        # multiplying the results with the conversion value
        channels_value = time_till_conv_window * self.conversion_value
        # multiplying with the boolean column that indicates if the conversion
        # happened
        channels_value = channels_value * self.journey_with_conv.apply(int)
        channels_value = channels_value.apply(lambda values: values.tolist())

        # Adding the results to self.DataFrame
        self.as_pd_dataframe()
        self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))

        # Grouping the attributed values for each channel
        if group_by_channels_models:
          frame = self.group_by_results_function(channels_value, model_name)
        else:
          frame = 'group_by_channels_models = False'

        return (channels_value, frame)


    def attribution_markov(self, transition_to_same_state=False, group_by_channels_models=True):
      """

      """
      model_name = 'attribution_markov'
      model_type = '_algorithmic'
      if transition_to_same_state:
        model_name = model_name + '_same_state' + model_type
      else:
        model_name = model_name + model_type

      def power_to_infinity(matrix):
          """
          Raises a square matrix to an infinite power using eigendecomposition.
          All matrix rows must add to 1.
          M = Q*L*inv(Q), where L = eigenvalue diagonal values, Q = eigenvector matrix
          M^N = Q*(L^N)*inv(Q)
          """
          eigen_value, eigen_vectors = np.linalg.eig(matrix)

          # At infinity everything converges to 0 or 1, thus we use np.trunc()
          diagonal = np.diag(np.trunc(eigen_value.real + 0.001))

          return (eigen_vectors @ diagonal @
                  np.linalg.inv(eigen_vectors)).real

      def normalize_rows(matrix):
          size = matrix.shape[0]
          mean = matrix.sum(axis=1).reshape((size, 1))
          mean = np.where(mean == 0, 1, mean)
          return matrix / mean

      def calc_total_conversion(matrix):
          normal_matrix = normalize_rows(matrix)
          infinity_matrix = power_to_infinity(normal_matrix)
          return infinity_matrix[0, -1]

      def removal_effect(matrix):
          size = matrix.shape[0]
          conversions = np.zeros(size)
          for column in range(1, size - 2):
              temp = matrix.copy()
              temp[:, -2] = temp[:, -2] + temp[:, column]
              temp[:, column] = 0
              conversions[column] = calc_total_conversion(temp)
          conversion_orig = calc_total_conversion(matrix)
          return 1 - (conversions / conversion_orig)

      def path_to_matrix(paths):
          channel_max = int(paths[:, 0:2].max()) + 1
          matrix = np.zeros((channel_max, channel_max), dtype="float")
          for x, y, val in paths:
              matrix[int(x), int(y)] = val
          matrix[-1, -1] = 1
          matrix[-2, -2] = 1
          return matrix

      temp = self.channels.apply(
          lambda x: ["(inicio)"] + x) + self.journey_with_conv.apply(
          lambda x: [
              "(conversion)" if x else "(null)"])

      orig = []
      dest = []
      journey_length = []

      def save_orig_dest(arr):
        orig.extend(arr[:-1])
        dest.extend(arr[1:])
        journey_length.append(len(arr))

      temp.apply(save_orig_dest)

      # copying conversion_quantity to each new row
      if type(self.conversion_value) in (int, float):
          #we do not hava a frequency column yet so we are using self.conversion_value.apply(lambda x: 1)
          # to count each line
          conversion_quantity = self.conversion_value.apply(lambda x: 1)
      else:
          conversion_quantity = []
          for a,b in zip(self.conversion_value.apply(lambda x: 1), journey_length):
              conversion_quantity.extend([a] * (b-1))

      temp = pd.DataFrame({"orig": orig, "dest": dest, "count": conversion_quantity})
      temp = temp.groupby(["orig", "dest"], as_index=False).sum()

      if not transition_to_same_state:
          temp = temp[temp.orig != temp.dest]

      # Converting channels_names to index and pass a numpy array foward
      channels_names = (
          ["(inicio)"]
          + list(
              (set(temp.orig) - set(["(inicio)"]))
              | (set(temp.dest) - set(["(conversion)", "(null)"]))
          )
          + ["(null)", "(conversion)"]
      )
      temp["orig"] = temp.orig.apply(channels_names.index)
      temp["dest"] = temp.dest.apply(channels_names.index)
      matrix = path_to_matrix(temp[["orig", "dest", "count"]].values)
      removal_effect_result = removal_effect(matrix)[1:-2]
      results = removal_effect_result / removal_effect_result.sum(axis=0)

      # Channels weights
      frame = pd.DataFrame({"value": results}, index=channels_names[1:-2])
      removal_effect_result = pd.DataFrame({"removal_effect": removal_effect_result}, index=channels_names[1:-2])

      # Transition matrix
      matrix = normalize_rows(matrix)
      matrix = pd.DataFrame(matrix, columns=channels_names, index=channels_names)

      # Apply weights back to each journey
      chmap = {a: b[0] for a,b in zip(frame.index.values, frame.values)}
      channels_value = self.channels.apply(lambda y: [chmap[x] for x in y])
      channels_value = channels_value.apply(lambda x: list(np.array(x) / sum(x)))

      # Adding the results to self.DataFrame
      self.as_pd_dataframe()
      self.DataFrame[model_name] = channels_value.apply(lambda x : self.sep.join([str(value) for value in x]))


      # Grouping the attributed values for each channel
      if group_by_channels_models:
        if isinstance(self.group_by_channels_models, pd.DataFrame):
          frame = frame.reset_index()
          frame.columns = ['channels', model_name]
          frame[model_name] = frame[model_name] * self.conversion_value.sum()
          self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame, how='outer', on=['channels']).fillna(0)
        else:
          frame = frame.reset_index()
          frame.columns = ['channels', model_name]
          frame[model_name] = frame[model_name] * self.conversion_value.sum()
          self.group_by_channels_models = frame
      else:
        frame = 'group_by_channels_models = False'

      return (channels_value, frame, matrix, removal_effect_result)

    def journey_conversion_table(self, order = False, size = None):
      """
      Transforms journey channels in boolean columns,
      count the number of conversions and journeys and
      compute the conversion rate of the channel combination

      """
      #Creating Channels DF
      df_temp = self.journey_id.copy()

      if order:
        df_temp['combinations'] = self.channels.apply(lambda channels: sorted(list(set(channels)), key=lambda x: channels.index(x))  ).copy()
      else:
        df_temp['combinations'] = self.channels.apply(lambda channels: sorted(list(set(channels))) ).copy()

      if size != None:
        df_temp['combinations'] = df_temp['combinations'].apply(lambda channels: self.sep.join(channels[size * -1:]) )
      else:
        df_temp['combinations'] = df_temp['combinations'].apply(lambda channels: self.sep.join(channels) )

      #Adding journey_with_conv column
      df_temp['journey_with_conv'] = self.journey_with_conv.apply(int)
      df_temp['conversion_value'] = self.conversion_value


      #Grouping journey_with_conv
      conv_val = df_temp.groupby(['combinations'])['conversion_value'].sum().reset_index()['conversion_value']
      df_temp = df_temp.groupby(['combinations'])['journey_with_conv'].agg([('conversions', 'sum'), ('total_sequences', 'count')]).reset_index()
      df_temp['conversion_value'] = conv_val
      #Calculating the conversion rate
      df_temp['conv_rate'] = df_temp['conversions'] / df_temp['total_sequences']


      return df_temp

    def coalitions(self, size = 4, unique_channels = None, order=False):
      """
      This function gives all the coalitions of different channels in a matrix. Most of the extra parameters
      are used when calculating Shapley's value with order.

      **size** = limits max size of unique channels in a single journey

      **unique_channels** = By default will check self.channels unique values, or a list of channels can be passed
      as well.

      **order** = Boolean that indicates if the order of channels matters during the process.
      """
      if unique_channels is None:
        unique_channels =  list(set(sum(self.channels.values, [])))
      else:
        unique_channels = unique_channels
      channels_combination = []

      # Creating a list with all the permutations if order is True
      if order is True:
        for L in range(0, size + 1):
          for subset in itertools.combinations(unique_channels, L):
            channels_combination.append(list(subset))
      else:
        for L in range(0, size + 1):
          for subset in itertools.combinations(sorted(unique_channels), L):
            channels_combination.append(list(subset))


      #Creating a DF with the channels as the boolean columns
      df_temp = pd.Series(channels_combination).to_frame(name='combinations')
      for channel in unique_channels:
        df_temp[channel] = df_temp.combinations.apply( lambda channels: any(channel in s for s in channels))

      return df_temp

    def attribution_shapley(self, size=4, order=False, values_col='conv_rate', group_by_channels_models = True):
      """
      Defined by Wikipedia:
      The Shapley value is a solution concept in Cooperative Game Theory. It was named in honor of Lloyd
      Shapley, who introduced it in 1953.To each cooperative game it assigns a unique
      distribution (among the players) of a total surplus generated by the coalition of all players.

      Here in the context of marketing channels we can use the model to understand the valeu of the cooperation
      of channels to generate a conversion.

      Parameters:

      size = limits max size of unique channels in a single journey. If there is a journey that has more channels
      than the defined limit, the last N channels will be considered.
                It's also important to accentuate that increasing the number of channels, increases the number calculations
                exponentially.

      order = Boolean that indicates if the order of channels matters during the process.

      values_col = The conversion rate is used by default, but the other columns in the journey_conversion_table
      can be used as well like 'conversions', 'conversion_value'.


      group_by_channels_models = True by default. Will aggregate the attributed results by each channel on
      self.group_by_channels_models
      """

      # Creating conv_table that will contain the aggregated results based on the journeys
      conv_table = self.journey_conversion_table(order=order, size=size)
      # Removing all jouneys that have not converted
      conv_table = conv_table[conv_table.conversions > 0]
      channels_shapley = conv_table.combinations.apply(lambda x: x.split(self.sep)).copy()
      results = []


      for journey in channels_shapley:

        n = len(journey)

        coalitions = self.coalitions(n, journey, order=order)
        coalitions.combinations = coalitions.combinations.apply(lambda x: self.sep.join(x))
        coa = coalitions[1:].drop('combinations',axis = 1).astype(int).astype(float).reset_index(drop=True)


        valores = pd.merge(coalitions, conv_table, on='combinations', how='left')[values_col].fillna(0).values


        v = valores[1:]
        coaux = coa.copy()

        for line in list(range(0,((2**n)-1))):

          for channel in coa.columns:
            s = len(coaux.iloc[line,:][coaux.iloc[line,:] != 0])
            if coa[channel][line] == 0:
              a = -(math.factorial(s) * math.factorial(n-s-1)) / math.factorial(n) * v[line]
              coa[channel][line] = a
            else:
              b =  (math.factorial(s-1) * math.factorial(n-s)) / math.factorial(n) * v[line]
              coa[channel][line] = b

        results.append(list(coa.sum()))

      # Model col_name
      model_name = 'attribution_shapley_size' + str(size) + '_' + values_col
      model_type = '_algorithmic'
      if order:
        model_name = model_name+ '_order' + model_type
      else:
        model_name = model_name + model_type


      if values_col == 'conv_rate':
        conv_table[model_name] = results
        conv_table[model_name] = conv_table[model_name].apply(lambda x: np.asarray(x)) * conv_table['total_sequences']
        conv_table[model_name] = conv_table[model_name].apply(lambda x: x / x.sum() ) * conv_table['conversion_value']
        conv_table[model_name] = conv_table[model_name].apply(lambda x: x.tolist())
      else:
        conv_table[model_name] = results

      ##########################
      #group_by_channels_models#
      ##########################


      # Aggregating the results by unique channel
      if group_by_channels_models:
        channels_list = sum(channels_shapley, [])
        values_list = sum(conv_table[model_name].values, [])
        frame = pd.DataFrame(
              {'channels': channels_list, 'value': values_list})
        frame = frame.groupby(['channels'])['value'].sum()

        if isinstance(self.group_by_channels_models, pd.DataFrame):
          frame = frame.reset_index()
          frame.columns = ['channels', model_name]
          self.group_by_channels_models = pd.merge(self.group_by_channels_models, frame, how='outer', on=['channels']).fillna(0)
        else:
          self.group_by_channels_models = frame.reset_index()
          self.group_by_channels_models.columns = ['channels', model_name]
      else:
        frame = 'group_by_channels_models=False'

      return (conv_table, frame)
