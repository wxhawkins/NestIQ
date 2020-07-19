from pathlib import Path

import numpy as np
import pandas as pd


class Vertex:
    """
            Stores information about a transition point between one bout state to the other.


            Atributes:
                    index (int)
                    egg_temper (float): egg temperature at the point of transition
                    vert_type (str): off, on, or None (start of night)

    """

    def __init__(self, index_, egg_temper_, vert_type_):
        self.index = int(index_)
        self.egg_temper = float(egg_temper_)
        self.vert_type = vert_type_

    def __str__(self):
        return f"Index: {self.index}"


class Bout:
    """
            Stores information for a single on or off-bout.

            Atributes:
                    first (int): index where the bout begins
                    last (int): index where the bout ends
                    bout_type (int): off or on
                    dur (int): duration in number of data points
                    mean_egg_temper (float)
                    mean_air_temper (float)
                    egg_tempers (list of floats): list of egg temperatures for each data point in bout
    """

    def __init__(self, gui, first_, last_, bout_type_):
        self.first = first_
        self.last = last_
        self.middle = int(round(np.mean([first_, last_])))
        self.bout_type = bout_type_
        self.is_daytime = gui.master_df.loc[self.middle, "is_daytime"]
        self.dur = gui.time_interval * (last_ - first_)
        self.mean_egg_temper = None
        self.mean_air_temper = None

        # Flag convert to series
        
        self.egg_tempers = gui.master_df.loc[self.first : self.last, "egg_temper"].tolist()
        self.mean_egg_temper = round(np.mean(self.egg_tempers), 3)
        self.air_tempers = gui.master_df.loc[self.first : self.last, "air_temper"].tolist()
        self.mean_air_temper = round(np.mean(self.air_tempers), 3)
        self.temper_change = gui.master_df.loc[self.last, "egg_temper"] - gui.master_df.loc[self.first, "egg_temper"]

        self.main_date = gui.master_df.loc[self.middle, "date_time"].date()


class Block:
    """
            Descrete section of time such as a single daytime period, nightime period, or date.

            Atributes:
                    first (int): index where the block begins
                    last (int): index where the block ends
                    partial_day (bool): True if block does not represent a full 24 hr day
                    date (string)
                    egg_tempers (list of floats)
                    air_tempers (list of floats)
                    vertices (list of Vertices): every Vertex object falling into the scope of this block
                    bouts (list of Bouts): every Bout object falling into the scope of this block
                    off_count (int): total number of off-bouts
                    mean_off_dur (float): mean off-bout duration
                    off_dur_stdev (float): standard deviation of off-bout durations
                    mean_off_dec (float): mean egg temperature decrease across off-bouts
                    off_dec_stdev (float): standard deviation of off-bout egg temperature decreases
                    mean_off_temper (float): mean egg temperature of all off-bout data points in this block
                    off_time_sum (float): total time spent as off-bout
                    on_count (int): total number of on-bouts
                    mean_on_dur (float): mean on-bout duration
                    on_dur_stdev (float): standard deviation of on-bout-durations
                    mean_on_inc (float): mean egg temperature increase across on-bouts
                    on_inc_stdev (float): standard deviation of on-bout egg temperature increases
                    mean_on_temper (float): mean egg temperature of all on-bout data points in this block
                    on_time_sum (float): total time spent as on-bout
                    mean_egg_temper (float): mean egg temperature across entire block
                    egg_temper_stdev (float): standard deviation of all egg temperatures in block
                    median_temper (float): median egg temperature
                    min_egg_temper (float): lowest egg temperature in block
                    max_egg_temper (float): highest egg temperature in block
                    mean_air_temper (float): mean air temeprature across entire block
                    air_temper_dtdev (float): standard deviation of all air temperatures in block
                    min_air_temper (float): lowest air temeprature in block
                    max_air_temper (float): highest air temperature in block
                    time_above_temper (float): time above the critical temperature provided by the user
                    time_below_temper (float): time below the critical temperature provided by the user
                    bouts_dropped (int): number of bouts discarded due to failing to meet one or more thresholds
                    date_count (int): number of dates represented at least once in this Block
    """

    def __init__(self, gui, first_, last_, partial_day_):
        self.first = int(first_)
        self.last = int(last_)
        self.partial_day = partial_day_
        self.date = ""

        self.egg_tempers = []
        self.air_tempers = []
        self.vertices = []
        self.bouts = []
        self.bout_df = pd.DataFrame()
        self.bout_tempers = pd.DataFrame()
        self.block_tempers = pd.DataFrame()

        self.off_count = 0
        self.mean_off_dur = None
        self.off_dur_stdev = None
        self.mean_off_dec = None
        self.off_dec_stdev = None
        self.mean_off_temper = None
        self.off_time_sum = 0

        self.on_count = 0
        self.mean_on_dur = None
        self.on_dur_stdev = None
        self.mean_on_inc = None
        self.on_inc_stdev = None
        self.mean_on_temper = None
        self.on_time_sum = 0

        self.mean_egg_temper = None
        self.egg_temper_stdev = None
        self.median_temper = None
        self.min_egg_temper = None
        self.max_egg_temper = None

        self.mean_air_temper = None
        self.air_temper_stdev = None
        self.min_air_temper = None
        self.max_air_temper = None

        self.mean_egg_temper_day = None
        self.median_egg_temper_day = None
        self.min_egg_temper_day = None
        self.max_egg_temper_day = None
        self.egg_temper_stdev_day = None

        self.mean_egg_temper_night = None
        self.median_egg_temper_night = None
        self.min_egg_temper_night = None
        self.max_egg_temper_night = None
        self.egg_temper_stdev_night = None

        self.time_above_temper = 0
        self.time_below_temper = 0
        self.bouts_dropped = 0
        self.date_count = 0

    def get_sub_dfs(self, gui):
        """
            bout_df columns:
                duration
                egg_temper
                air_temper
                temper_change
                type
                is_daytime
            
            bout_tempers columns:
                egg_temper
                air_temper
                type
                is_daytime

            block_tempers columns:
                egg_temper
                air_temper
                is_daytime
        """

        self.bout_df["date"] = [bout.main_date for bout in self.bouts]
        self.bout_df["duration"] = [bout.dur for bout in self.bouts]
        self.bout_df["egg_temper"] = [bout.egg_tempers for bout in self.bouts]
        self.bout_df["air_temper"] = [bout.air_tempers for bout in self.bouts]
        self.bout_df["temper_change"] = [bout.temper_change for bout in self.bouts]
        self.bout_df["type"] = [bout.bout_type for bout in self.bouts]
        self.bout_df["is_daytime"] = [bout.is_daytime for bout in self.bouts]

        self.bout_tempers["egg_temper"] = [temper for bout in self.bouts for temper in bout.egg_tempers]
        self.bout_tempers["air_temper"] = [temper for bout in self.bouts for temper in bout.air_tempers]
        self.bout_tempers["type"] = [bout.bout_type for bout in self.bouts for _ in range(len(bout.egg_tempers))]

        self.block_tempers["egg_temper"] = gui.master_df[self.first : self.last + 1]["egg_temper"]
        self.block_tempers["air_temper"] = gui.master_df[self.first : self.last + 1]["air_temper"]
        self.block_tempers["is_daytime"] = gui.master_df[self.first : self.last + 1]["is_daytime"]

    def get_stats(self, gui):
        """
                Calculate and store various statistics for this Block.
        """

        self.get_sub_dfs(gui)

        self.date = gui.master_df.loc[self.first, "date_time"].strftime(r"%m/%d/%Y")

        self.off_count = len([bout for bout in self.bouts if bout.bout_type == "off"])
        self.on_count = len([bout for bout in self.bouts if bout.bout_type == "on"])

        # This sets the temper containers to Series
        self.egg_tempers = gui.master_df.loc[self.first : self.last, "egg_temper"]
        self.air_tempers = gui.master_df.loc[self.first : self.last, "air_temper"]

        # Get number of data points passing threshold and multiply by duration
        data_points_above_temper = len(self.egg_tempers.loc[self.egg_tempers > float(gui.time_above_temper_E.get())])
        data_points_below_temper = len(self.egg_tempers.loc[self.egg_tempers < float(gui.time_below_temper_E.get())])
        self.time_above_temper = data_points_above_temper * gui.time_interval
        self.time_below_temper = data_points_below_temper * gui.time_interval

        # Get off-bout stats
        if self.off_count > 0:
            off_bout_df = self.bout_df[self.bout_df["type"] == "off"]
            off_tempers_df = self.bout_tempers[self.bout_tempers["type"] == "off"]
            self.mean_off_dur = round(off_bout_df["duration"].mean(), 2)
            self.mean_off_dec = round(off_bout_df["temper_change"].mean(), 3)
            self.mean_off_temper = round(off_tempers_df["egg_temper"].mean(), 3)
            self.off_time_sum = round(off_bout_df["duration"].sum().mean(), 2)
            if self.off_count > 1:
                self.off_dur_stdev = round(off_bout_df["duration"].std(), 2)
                self.off_dec_stdev = round(off_bout_df["temper_change"].std(), 3)

        # Get on-bout stats
        if self.on_count > 0:
            on_bout_df = self.bout_df[self.bout_df["type"] == "on"]
            on_tempers_df = self.bout_tempers[self.bout_tempers["type"] == "on"]
            self.mean_on_dur = round(on_bout_df["duration"].mean(), 2)
            self.mean_on_inc = round(on_bout_df["temper_change"].mean(), 3)
            self.mean_on_temper = round(on_tempers_df["egg_temper"].mean(), 3)
            self.on_time_sum = round(on_bout_df["duration"].sum().mean(), 2)
            if self.on_count > 1:
                self.on_dur_stdev = round(on_bout_df["duration"].std(), 2)
                self.on_inc_stdev = round(on_bout_df["temper_change"].std(), 3)

        # Calculate egg temperature statistics
        if len(self.block_tempers) > 1:
            self.mean_egg_temper = round(self.block_tempers["egg_temper"].mean(), 3)
            self.median_temper = round(self.block_tempers["egg_temper"].median(), 3)
            self.min_egg_temper = self.block_tempers["egg_temper"].min()
            self.max_egg_temper = self.block_tempers["egg_temper"].max()
            self.egg_temper_stdev = round(self.block_tempers["egg_temper"].std(), 3)

        # Calculate air temperature statistics
        if gui.air_valid and len(self.block_tempers) > 1:
            self.mean_air_temper = round(self.block_tempers["air_temper"].mean(), 3)
            self.min_air_temper = self.block_tempers["air_temper"].min()
            self.max_air_temper = self.block_tempers["air_temper"].max()
            self.air_temper_stdev = round(self.block_tempers["air_temper"].std(), 3)

        # Calculate daytime egg temperature statistics
        egg_tempers_day = self.block_tempers[self.block_tempers["is_daytime"] == True]
        if len(egg_tempers_day) > 1:
            self.mean_egg_temper_day = round(egg_tempers_day["egg_temper"].mean(), 3)
            self.median_egg_temper_day = round(egg_tempers_day["egg_temper"].median(), 3)
            self.min_egg_temper_day = egg_tempers_day["egg_temper"].min()
            self.max_egg_temper_day = egg_tempers_day["egg_temper"].max()
            self.egg_temper_stdev_day = round(egg_tempers_day["egg_temper"].std(), 3)

        # Calculate nighttime egg temperature statistics
        egg_tempers_night = self.block_tempers[self.block_tempers["is_daytime"] == False]
        if len(egg_tempers_night) > 1:
            self.mean_egg_temper_night = round(egg_tempers_night["egg_temper"].mean(), 3)
            self.median_egg_temper_night = round(egg_tempers_night["egg_temper"].median(), 3)
            self.min_egg_temper_night = egg_tempers_night["egg_temper"].min()
            self.max_egg_temper_night = egg_tempers_night["egg_temper"].max()
            self.egg_temper_stdev_night = round(egg_tempers_night["egg_temper"].std(), 3)

        for index in gui.bouts_dropped_locs:
            if index >= self.first and index <= self.last:
                self.bouts_dropped += 1

        self.date_count = len(self.bout_df["date"].unique())

        return True

    def deposit_multi_file_stats(self, gui):
        """
                Deposits information about this block into GUI variables that can later be used to 
                calculate statistics across multiple input files if multiple are provided by the user.
        """

        off_bout_df = self.bout_df[self.bout_df["type"] == "off"]
        gui.multi_file_off_durs += off_bout_df["duration"].tolist()
        gui.multi_file_off_decs += off_bout_df["temper_change"].tolist()

        on_bout_df = self.bout_df[self.bout_df["type"] == "on"]
        gui.multi_file_on_durs += on_bout_df["duration"].tolist()
        gui.multi_in_on_incs += on_bout_df["temper_change"].tolist()


class MultiFileStats:
    def __init__(self, gui):
        self.out_path = Path(gui.multi_in_stats_file_E.get())

        # Used to indictate scope of certain statistics
        self.qualifier = "(D)" if gui.restrict_search_BV.get() else "(DN)"

        self.blocks = []
        self.bout_df = pd.DataFrame()
        self.bout_tempers = pd.DataFrame()
        self.block_tempers = pd.DataFrame()

        self.off_count = 0
        self.mean_off_dur = None
        self.off_dur_stdev = None
        self.mean_off_temper_change = None
        self.off_temper_change_stdev = None

        self.on_count = 0
        self.mean_on_dur = None
        self.on_dur_stdev = None
        self.mean_on_temper_change = None
        self.on_temper_change_stdev = None

        self.date_count = 0
        self.mean_egg_temper = None
        self.egg_temper_stdev = None
        self.mean_daytime_egg_temper = None
        self.daytime_egg_temper_stdev = None
        self.mean_nighttime_egg_temper = None
        self.nighttime_egg_temper_stdev = None
        self.min_egg_temper = None
        self.max_egg_temper = None

        self.mean_air_temper = None
        self.air_temper_stdev = None
        self.min_air_temper = None
        self.max_air_temper = None

    def add_block(self, block):
        self.blocks.append(block)

    def get_stats(self, gui):
        self.bout_df = pd.concat([block.bout_df for block in self.blocks])
        self.block_tempers = pd.concat([block.block_tempers for block in self.blocks])

        self.off_count = np.sum([block.off_count for block in self.blocks])
        if self.off_count > 1:
            off_bout_df = self.bout_df[self.bout_df["type"] == "off"]
            self.mean_off_dur = round(off_bout_df["duration"].mean(), 2)
            self.off_dur_stdev = round(off_bout_df["duration"].std(), 2)
            self.mean_off_temper_change = round(off_bout_df["temper_change"].mean(), 3)
            self.off_temper_change_stdev = round(off_bout_df["temper_change"].std(), 3)

        self.on_count = np.sum(block.on_count for block in self.blocks)
        if self.on_count > 1:
            on_bout_df = self.bout_df[self.bout_df["type"] == "on"]
            self.mean_on_dur = round(on_bout_df["duration"].mean(), 2)
            self.on_dur_stdev = round(on_bout_df["duration"].std(), 2)
            self.mean_on_temper_change = round(on_bout_df["temper_change"].mean(), 3)
            self.on_temper_change_stdev = round(on_bout_df["temper_change"].std(), 3)

        self.date_count = np.sum([block.date_count for block in self.blocks])

        if len(self.block_tempers) > 1:
            self.mean_egg_temper = round(self.block_tempers["egg_temper"].mean(), 3)
            self.egg_temper_stdev = round(self.block_tempers["egg_temper"].std(), 3)
            self.min_egg_temper = self.block_tempers["egg_temper"].min()
            self.max_egg_temper = self.block_tempers["egg_temper"].max()

        egg_tempers_day = self.block_tempers[self.block_tempers["is_daytime"] == True]
        if len(egg_tempers_day) > 1:
            self.mean_daytime_egg_temper = round(egg_tempers_day["egg_temper"].mean(), 3)
            self.daytime_egg_temper_stdev = round(egg_tempers_day["egg_temper"].std(), 3)

        egg_tempers_night = self.block_tempers[self.block_tempers["is_daytime"] == False]
        if len(egg_tempers_night) > 1:
            self.mean_nighttime_egg_temper = round(egg_tempers_night["egg_temper"].mean(), 3)
            self.nighttime_egg_temper_stdev = round(egg_tempers_night["egg_temper"].std(), 3)

        # Calculate air temperature statistics
        if gui.air_valid and len(self.block_tempers) > 1:
            self.mean_air_temper = round(self.block_tempers["air_temper"].mean(), 3)
            self.air_temper_stdev = round(self.block_tempers["air_temper"].std(), 3)
            self.min_air_temper = self.block_tempers["air_temper"].min()
            self.max_air_temper = self.block_tempers["air_temper"].max()

    def write(self, gui):
        """
                        Dumps cumulative, multi-file statistics into compiled stats file.
        """

        self.get_stats(gui)

        stats_text = ""
        stats_text += "Cumulative Summary\n"

        stats_text += f"Off-Bout Count {self.qualifier}, {self.off_count}\n"
        stats_text += f"Mean Off Dur {self.qualifier}, {self.mean_off_dur}\n"
        stats_text += f"Off Dur StDev {self.qualifier}, {self.off_dur_stdev}\n"
        stats_text += f"Mean Off Temp Change {self.qualifier}, {self.mean_off_temper_change}\n"
        stats_text += f"Off Temp Change StDev {self.qualifier}, {self.off_temper_change_stdev}\n"

        stats_text += f"On-Bout Count {self.qualifier}, {self.on_count}\n"
        stats_text += f"Mean On Dur {self.qualifier}, {self.mean_on_dur}\n"
        stats_text += f"On Dur StDev {self.qualifier}, {self.on_dur_stdev}\n"
        stats_text += f"Mean On Temp Change {self.qualifier}, {self.mean_on_temper_change}\n"
        stats_text += f"On Temp Change StDev {self.qualifier}, {self.on_temper_change_stdev}\n"

        stats_text += f"Day Count, {self.date_count}\n"
        stats_text += f"Mean Egg Temp, {self.mean_egg_temper}\n"
        stats_text += f"Egg Temp StDev, {self.egg_temper_stdev}\n"
        stats_text += f"Mean Daytime Egg Temp, {self.mean_daytime_egg_temper}\n"
        stats_text += f"Daytime Egg Temp StDev, {self.daytime_egg_temper_stdev}\n"
        stats_text += f"Mean Nighttime Egg Temp, {self.mean_nighttime_egg_temper}\n"
        stats_text += f"Nighttime Egg Temp StDev, {self.nighttime_egg_temper_stdev}\n"
        stats_text += f"Min Egg Temp, {self.min_egg_temper}\n"
        stats_text += f"Max Egg Temp, {self.max_egg_temper}\n"

        stats_text += f"Mean Air Temp, {self.mean_air_temper}\n"
        stats_text += f"Air Temp StDev, {self.air_temper_stdev}\n"
        stats_text += f"Min Air Temp, {self.min_air_temper}\n"
        stats_text += f"Max Air Temp, {self.max_air_temper}\n"

        with open(self.out_path, "a") as compiled_stats_file:
            compiled_stats_file.write(stats_text)
