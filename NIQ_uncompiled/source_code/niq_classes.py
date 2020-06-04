import numpy as np
import re


class Vertex:
    """
            Stores information about a transition point between one bout state to the other.


            Atributes:
                    index (int)
                    egg_temper (float): egg temperature at the point of transition
                    vert_type (int): 0 if vertex represents transition from on-bout to off-bout
                                                     1 if vertex represents transition from off-bout to on-bout

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
                    start (int): index where the bout begins
                    stop (int): index where the bout ends
                    bout_type (int): 0 if off-bout
                                                     1 if on-bout
                    dur (int): duration in number of data points
                    mean_egg_temper (float)
                    mean_air_temper (float)
                    egg_tempers (list of floats): list of egg temperatures for each data point in bout
    """

    def __init__(self, gui, start_, stop_, bout_type_):
        self.start = start_
        self.stop = stop_
        self.bout_type = bout_type_
        self.dur = gui.time_interval * (stop_ - start_)
        self.mean_egg_temper = None
        self.mean_air_temper = None

        # Flag convert to series
        self.egg_tempers = gui.master_df.loc[self.start : self.stop, "egg_temper"].tolist()
        self.mean_egg_temper = round(np.mean(self.egg_tempers), 3)
        self.air_tempers = gui.master_df.loc[self.start : self.stop, "egg_temper"].tolist()
        self.mean_air_temper = round(np.mean(self.air_tempers), 3)
        self.temper_change = gui.master_df.loc[self.stop, "egg_temper"] - gui.master_df.loc[self.start, "egg_temper"]

        self.start_date = gui.master_df.loc[self.start, "date_time"]

class Block:
    """
            Descrete section of time such as a single daytime period, nightime period, or date.

            Atributes:
                    start (int): index where the block begins
                    stop (int): index where the block ends
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
    """

    def __init__(self, gui, start_, stop_, partial_day_):
        self.start = int(start_)
        self.stop = int(stop_)
        self.partial_day = partial_day_
        self.date = ""

        self.egg_tempers = []
        self.air_tempers = []
        self.vertices = []
        self.bouts = []

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

        self.time_above_temper = 0
        self.time_below_temper = 0
        self.bouts_dropped = 0

    def get_stats(self, gui):
        """
                Calculate and store various statistics for this Block.
        """

        off_durs = []
        off_decs = []
        off_tempers = []
        on_durs = []
        on_incs = []
        on_tempers = []

        self.off_count = len([bout for bout in self.bouts if bout.bout_type == 0])
        self.on_count = len([bout for bout in self.bouts if bout.bout_type == 1])
                
        self.date = gui.master_df.loc[self.start, "date_time"].strftime(r"%m/%d/%Y")

        # This sets the temper containers to Series
        self.egg_tempers = gui.master_df.loc[self.start : self.stop, "egg_temper"]
        self.air_tempers = gui.master_df.loc[self.start : self.stop, "air_temper"]

        # Get number of data points passing threshold and multiply by duration
        data_points_above_temper = len(self.egg_tempers.loc[self.egg_tempers > float(gui.time_above_temper_E.get())])
        data_points_below_temper = len(self.egg_tempers.loc[self.egg_tempers < float(gui.time_below_temper_E.get())])
        self.time_above_temper = data_points_above_temper * gui.time_interval
        self.time_below_temper = data_points_below_temper * gui.time_interval

        self.egg_tempers = gui.master_df.loc[self.start : self.stop, "egg_temper"].to_list()
        self.air_tempers = gui.master_df.loc[self.start : self.stop, "air_temper"].to_list()


        for bout in self.bouts:
            if bout.bout_type == 0:
                # Compile off-bout data
                off_durs.append(bout.dur)
                off_decs.append(bout.temper_change)
                off_tempers += bout.egg_tempers
            elif bout.bout_type == 1:
                # Compile on-bout data
                on_durs.append(bout.dur)
                on_incs.append(bout.temper_change)
                on_tempers += bout.egg_tempers

        # Get means and standard deviations
        if self.off_count > 0:
            self.mean_off_dur = round(np.mean(off_durs), 2)
            self.mean_off_dec = round(np.mean(off_decs), 3)
            self.mean_off_temper = round(np.mean(off_tempers), 3)
            self.off_time_sum = round(sum(off_durs), 2)
            if self.off_count > 1:
                self.off_dur_stdev = round(np.std(off_durs), 2)
                self.off_dec_stdev = round(np.std(off_decs), 3)

        if self.on_count > 0:
            self.mean_on_dur = round(np.mean(on_durs), 2)
            self.mean_on_inc = round(np.mean(on_incs), 3)
            self.mean_on_temper = round(np.mean(on_tempers), 3)
            self.on_time_sum = round(sum(on_durs), 2)
            if self.on_count > 1:
                self.on_dur_stdev = round(np.std(on_durs), 2)
                self.on_inc_stdev = round(np.std(on_incs), 3)

        # Calculate temperature statistics for this block
        self.mean_egg_temper = round(np.mean(self.egg_tempers), 3)
        if len(self.egg_tempers) > 1:
            self.egg_temper_stdev = round(np.std(self.egg_tempers), 3)

        self.median_temper = round(np.median(self.egg_tempers), 3)
        self.min_egg_temper = min(self.egg_tempers)
        self.max_egg_temper = max(self.egg_tempers)

        if gui.air_valid:
            self.mean_air_temper = round(np.mean(self.air_tempers), 3)
            self.air_temper_stdev = round(np.std(self.air_tempers), 3)
            self.min_air_temper = min(self.air_tempers)
            self.max_air_temper = max(self.air_tempers)

        for index in gui.bouts_dropped_locs:
            if index >= self.start and index < self.stop:
                self.bouts_dropped += 1

        return True

    # Flag - can possibly simplify by just using off_decs list etc
    def deposit_multi_file_stats(self, gui):
        """
                Deposits information about this block into GUI variables that can later be used to 
                calculate statistics across multiple input files if multiple are provided by the user.
        """

        bulk_off_durs = []
        bulk_off_decs = []
        bulk_off_tempers = []
        bulk_on_durs = []
        bulk_on_incs = []

        # Compile various data for all block periods
        for bout in self.bouts:
            if bout.bout_type == 0:
                bulk_off_durs.append(bout.dur)
                bulk_off_decs.append(bout.temper_change)
            elif bout.bout_type == 1:
                bulk_on_durs.append(bout.dur)
                bulk_on_incs.append(bout.temper_change)

        # Compile lists used to calculate statistics across multiple input files
        gui.multi_file_off_durs += bulk_off_durs
        gui.multi_file_off_decs += bulk_off_decs
        gui.multi_file_on_durs += bulk_on_durs
        gui.multi_in_on_incs += bulk_on_incs


# Used to store stats for all days or all nights
class BlockGroup:
    """
            Stores information about all blocks of a single type such as daytime blocks, nightime
            blocks, or date blocks.

            Atributes:
                    block_list (list of Blocks)
                    egg_tempers (list of floats)
                    air_tempers (list of floats)
                    off_count (int): total number of off-bouts
                    mean_off_dur (float): mean off-bout duration
                    off_dur_stdev (float): standard deviation of off-bout durations
                    mean_off_dec (float): mean egg temperature decrease across off-bouts
                    off_dec_stdev (float): standard deviation of off-bout egg temperature decreases
                    mean_off_temper (float): mean egg temperature of off-bout data points
                    off_time_sum (float): total time spent as off-bout
                    on_count (int): total number of on-bouts
                    mean_on_dur (float): mean on-bout duration
                    on_dur_stdev (float): standard deviation of on-bout-durations
                    mean_on_inc (float): mean egg temperature increase across on-bouts
                    on_inc_stdev (float): standard deviation of on-bout egg temperature increases
                    mean_on_temper (float): mean egg temperature of on-bout data points
                    on_time_sum (float): total time spent as on-bout
                    mean_egg_temper (float): mean egg temperature
                    egg_temper_stdev (float): standard deviation of egg temperatures
                    median_temper (float): median egg temperature
                    min_egg_temper (float): lowest egg temperature
                    max_egg_temper (float): highest egg temperature
                    mean_air_temper (float): mean air temeprature
                    air_temper_dtdev (float): standard deviation of air temperatures
                    min_air_temper (float): lowest air temeprature
                    max_air_temper (float): highest air temperature
                    time_above_temper (float): time above the critical temperature provided by the user
                    time_below_temper (float): time below the critical temperature provided by the user
                    bouts_dropped (int): number of bouts discarded due to failing to meet one or more thresholds
    """

    def __init__(self, gui, block_list):
        self.block_list = block_list
        self.egg_tempers = []
        self.air_tempers = []

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

        self.time_above_temper = 0
        self.time_below_temper = 0
        self.bouts_dropped = 0

        self.get_stats(gui)

    def get_stats(self, gui):
        """
                Calculate and store various statistics for this BlockGroup.
        """

        bulk_off_durs = []
        bulk_off_decs = []
        bulk_off_tempers = []
        bulk_on_durs = []
        bulk_on_incs = []
        bulk_on_tempers = []

        for block in self.block_list:
            # Compile every temperature measurement for all blocks
            self.egg_tempers += block.egg_tempers

            if gui.air_valid:
                self.air_tempers += block.air_tempers

            self.off_count += block.off_count
            self.on_count += block.on_count

            self.time_above_temper += block.time_above_temper
            self.time_below_temper += block.time_below_temper

            self.bouts_dropped += block.bouts_dropped

            for bout in block.bouts:
                if bout.bout_type == 0:
                    bulk_off_durs.append(bout.dur)
                    bulk_off_decs.append(bout.temper_change)
                    bulk_off_tempers += bout.egg_tempers
                elif bout.bout_type == 1:
                    bulk_on_durs.append(bout.dur)
                    bulk_on_incs.append(bout.temper_change)
                    bulk_on_tempers += bout.egg_tempers

        # Get means and standard deviations
        if self.off_count > 0:
            self.mean_off_dur = round(np.mean(bulk_off_durs), 2)
            self.mean_off_dec = round(np.mean(bulk_off_decs), 3)
            self.mean_off_temper = round(np.mean(bulk_off_tempers), 3)
            self.off_time_sum = round(sum(bulk_off_durs), 2)
            if self.off_count > 1:
                self.off_dur_stdev = round(np.std(bulk_off_durs), 2)
                self.off_dec_stdev = round(np.std(bulk_off_decs), 3)

        if self.on_count > 0:
            self.mean_on_dur = round(np.mean(bulk_on_durs), 2)
            self.mean_on_inc = round(np.mean(bulk_on_incs), 3)
            self.mean_on_temper = round(np.mean(bulk_on_tempers), 3)
            self.on_time_sum = round(sum(bulk_on_durs), 2)
            if self.on_count > 1:
                self.on_dur_stdev = round(np.std(bulk_on_durs), 2)
                self.on_inc_stdev = round(np.std(bulk_on_incs), 3)

        # Calculate temperature statistics for all blocks
        if len(self.egg_tempers) > 2:
            self.mean_egg_temper = round(np.mean(self.egg_tempers), 3)
            self.egg_temper_stdev = round(np.std(self.egg_tempers), 3)

            self.median_temper = round(np.median(self.egg_tempers), 3)
            self.min_egg_temper = min(self.egg_tempers)
            self.max_egg_temper = max(self.egg_tempers)

        if gui.air_valid and len(self.air_tempers) > 2:
            self.mean_air_temper = round(np.mean(self.air_tempers), 3)
            self.air_temper_stdev = round(np.std(self.air_tempers), 3)
            self.min_air_temper = min(self.air_tempers)
            self.max_air_temper = max(self.air_tempers)
