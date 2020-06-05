import datetime
import os
import re
import statistics
import time
from pathlib import Path
from tkinter import messagebox

import numpy as np
import pandas as pd
from bokeh.io import reset_output
from bokeh.layouts import column, widgetbox
from bokeh.models import HoverTool, PointDrawTool, Span
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.plotting import ColumnDataSource, figure, output_file, show
from bs4 import BeautifulSoup

import niq_classes


def convert_to_datetime(dt_string):
    """
        Converts Date/Time cell from master DataFrame to datetime.datetime object.
        
        Args:
                dt_string (str): contents of date/time cell of input file provided by user
    """

    # Initially include seconds in search, then ommit if not found
    try:
        time_struct = time.strptime(dt_string, r"%m/%d/%Y %H:%M:%S")
    except ValueError:
        try:
            time_struct = time.strptime(dt_string, r"%m/%d/%Y %H:%M")
        except ValueError:
            time_struct = time.strptime(dt_string, r"%m/%d/%y %H:%M")

    dt = datetime.datetime(*time_struct[0:6])

    return dt

def is_partial(df, first_index, last_index, expected_dur):
    """
        Checks if given range of indices represents a complete daytime or nighttime period.

        Args:
                df (pd.DataFrame)
                first_index (int)
                last_index (int):
                expected_dur (int): expected duration in seconds
    """

    # Allow 5 min (300 sec) of discrepency from expected durration
    block_dur_thresh = expected_dur - 300
    start_time = df.loc[first_index, "date_time"]
    end_time = df.loc[last_index, "date_time"]
    block_dur = end_time - start_time
    if block_dur > datetime.timedelta(seconds=block_dur_thresh):
        return False

    return True


def split_days(gui):
    """
        Analyze dates of master DataFrame and parse row data into daytime and nighttime block objects.
    """

    def is_daytime(date_time):
        """
            Check if a given time falls within the daytime period defined by the user.

            Args:
                    date_time (datetime.datetime)
        """

        time = date_time.time()
        # When the start of daytime is earlier in the day than the start of nighttime
        if day_start < night_start:
            if time >= day_start and time < night_start:
                return True
        # When the start of nighttime is earlier in the day than the start of daytime
        elif night_start < day_start:
            if not (time >= night_start and time < day_start):
                return True

        return False

    def get_durs(day_start, night_start):
        """
            Get expected durations in seconds for complete daytime and nightime periods.

            Args:
                    day_start (datetime.time): user-defined start of daytime
                    night_start (datetime.time) user-defined start of nighttime
        """

        # Convert start times to datetime objects
        d = datetime.datetime(2020, 1, 1, day_start.hour, day_start.minute, day_start.second)
        n = datetime.datetime(2020, 1, 1, night_start.hour, night_start.minute, night_start.second)

        # When the start of daytime is earlier in the day than the start of nighttime
        if day_start < night_start:
            day_dur = (n - d).total_seconds()
            night_dur = 86400 - day_dur  # Total seconds in day - daytime duration
        # When the start of nighttime is earlier in the day than the start of daytime
        elif night_start < day_start:
            night_dur = (d - n).total_seconds()
            day_dur = 86400 - day_dur  # Total seconds in day - nighttime duration

        return day_dur, night_dur


    # Create time objects from entry box values
    day_start = convert_to_datetime(f"01/01/2020 {str(gui.day_start_E.get())}").time()
    night_start = convert_to_datetime(f"01/01/2020 {str(gui.night_start_E.get())}").time()

    # Get daytime and nighttime durations
    day_dur, night_dur = get_durs(day_start, night_start)

    # Create copy of master DataFrame to be appended to
    temp_df = gui.master_df.copy()
    temp_df["is_daytime"] = temp_df["date_time"].apply(is_daytime)

    # Detect day/night or night/day transitions
    int_states = temp_df.loc[:, "is_daytime"].replace([True, False], [1, 0])
    state_changed = int_states.diff().apply(abs).astype(bool)
    state_changed.iloc[0] = False
    temp_df["transition_point"] = state_changed

    # Collect indices of day/night transition points
    filt = temp_df["transition_point"] == True
    transition_indices = temp_df[filt].index.to_list()
    transition_indices.append(len(temp_df))

    # Construct day and night blocks from transition points
    days_list, nights_list = [], []
    if is_daytime(temp_df.loc[0, "date_time"]):
        block_list = days_list
        block_dur_thresh = day_dur
    else:
        block_list = nights_list
        block_dur_thresh = night_dur

    cur_index = 0
    for next_index in transition_indices:
        partial = is_partial(temp_df, cur_index, next_index - 1, block_dur_thresh)
        block_list.append(niq_classes.Block(gui, cur_index, (next_index - 1), partial))

        block_dur_thresh = day_dur if block_dur_thresh == night_dur else night_dur
        block_list = days_list if block_list == nights_list else nights_list
        cur_index = next_index

    return days_list, nights_list

def add_daytime(gui, master_df):
    """
        Analyze dates of master DataFrame and parse row data into daytime and nighttime block objects.
    """

    def is_daytime(date_time):
        """
            Check if a given time falls within the daytime period defined by the user.

            Args:
                    date_time (datetime.datetime)
        """

        time = date_time.time()
        # When the start of daytime is earlier in the day than the start of nighttime
        if day_start < night_start:
            if time >= day_start and time < night_start:
                return True
        # When the start of nighttime is earlier in the day than the start of daytime
        elif night_start < day_start:
            if not (time >= night_start and time < day_start):
                return True

        return False

    # Create time objects from entry box values
    day_start = convert_to_datetime(f"01/01/2020 {str(gui.day_start_E.get())}").time()
    night_start = convert_to_datetime(f"01/01/2020 {str(gui.night_start_E.get())}").time()

    master_df["is_daytime"] = master_df["date_time"].apply(is_daytime)

    return master_df



def get_day_dur(day_start, night_start):
    """
			Finds the duration of the daytime period specified by the user.

			Args:
					day_start (str): start of daytime period
					night_start (str): end of daytime period
	"""

    day = re.search(r"(\d+)(:)(\d+)", day_start)
    day_float = float(day.group(1)) + (float(day.group(3)) / 60)

    night = re.search(r"(\d+)(:)(\d+)", night_start)
    night_float = float(night.group(1)) + (float(night.group(3)) / 60)

    return (night_float - day_float) * 60


def smooth_series(radius, col):
    """
        Generates "smoothed" copy of input data by applying a rolling mean of the requested radius.

        Args:
            radius (int): number of values to include in rolling mean
                        (e.g. radius = 1 means average values i, i-1 and i+1)
            col (pd.Series): column data to be smoothed
    """

    # Return original column if radius is less than 1
    if radius <= 0:
        return col

    window = (radius * 2) + 1
    return col.rolling(window, min_periods=1, center=True).mean()


def get_master_df(gui, source_path):
    """
			Generates Pandas DataFrame from input CSV. Bout state (on or off bout) column is added later.

					data_point = data point
                    date_time = date and time of temperature recording
                    egg_temper = egg temperature
                    air_temper = ambient air temperature
                    adj_temper = adjusted temperature (egg - air temperature)
                    smoothed_adj_temper = adj_temper with rolling mean applied
                    delta_temper = change in smoothed_adj_temper from the previous row

			Args:
					df (DataFrame): Contains all information for the array in DataFrame form
	"""

    def csv_to_df(path):
        try:
            df = pd.read_csv(path)
        except UnicodeDecodeError:
            # Attempt to convert file encoding to UTF-8
            temp_path = gui.master_dir_path / "misc_files" / "temp_input.csv"
            with open(source_path, "r") as original_file, open(temp_path, "w", encoding="utf8") as mod_file:
                mod_file.write(original_file.read())

            df = pd.read_csv(temp_path)

        return df

    def is_number(string):
        try:
            float(string)
        except ValueError:
            return False

        return True

    df = csv_to_df(source_path)

    # Fill air_temper column with 0's if none provided
    if not gui.air_valid:
        df.iloc[:, 3] = np.zeros(len(df))

    # Remove any "extra" columns
    if len(df.columns) > 4:
        df = df.iloc[:, :4]

    # Rename columns
    old_col_names = list(df.columns)
    col_names = ["data_point", "date_time", "egg_temper", "air_temper"]
    col_rename_dict = {old: new for old, new in zip(old_col_names, col_names)}
    df.rename(columns=col_rename_dict, inplace=True)

    # Set any data_point, egg_temper or air_temper cells with non-number values to NaN
    numeric_cols = col_names[:1] + col_names[2:]
    for col in numeric_cols:
        filt = df[col].astype(str).apply(is_number)
        df.loc[~filt, col] = np.NaN

    # Delete any rows containing NaN value
    df.dropna(inplace=True)

    # Convert column object types
    df["data_point"] = df["data_point"].astype(int)
    df["date_time"] = df["date_time"].apply(convert_to_datetime)
    df["egg_temper"] = df["egg_temper"].astype(float).round(4)
    df["air_temper"] = df["air_temper"].astype(float).round(4)

    # Reassign data_point column to be continuous
    start = int(df["data_point"].iloc[0])
    new_col = range(start, (start + len(df)))
    df["data_point"] = new_col

    # Add adjusted (egg - air temperature) temperatures column
    df["adj_temper"] = (df["egg_temper"] - df["air_temper"]).round(4)

    # Add smoothed, adjusted temperatures column
    radius = int(gui.smoothing_radius_E.get())
    df["smoothed_adj_temper"] = smooth_series(radius, df["adj_temper"]).round(4)

    # Add column storing difference in adjusted temperature from previous entry to current
    df["delta_temper"] = np.zeros(df.shape[0])
    df.iloc[1:, df.columns.get_loc("delta_temper")] = df["smoothed_adj_temper"].diff()

    # Set first cell equal to second
    df.iloc[0, df.columns.get_loc("delta_temper")] = df.iloc[1, df.columns.get_loc("delta_temper")]

    # Set indices to data_point column
    # df.set_index("data_point", inplace=True)

    return df.reset_index(drop=True)


def get_verts_from_html(gui, in_file, alt=False):
    """
			Creates vertex objects from vertices placed by the user in the provided HTML file.

			Args:
					gui (GUIClass)
					in_file (str): path to and name of HTML file containing user-provided vertex locations
					alt (Bool): dictates if vertices are extracted from the table or alternative variable in HTML file
	"""

    def get_data_points_from_html(gui, in_file):
        """
				Extracts the corresponding data point for each point placed by the user in the HTML file.

				Args:
						gui (GUIClass)
						in_file (str): path to and name of HTML file containing user-provided vertex locations
		"""

        data_point_list = []
        dp_col_num = gui.master_df.columns.get_loc("data_point")
        max_dp = gui.master_df.iloc[-1, dp_col_num]
        min_dp = gui.master_df.iloc[0, dp_col_num]

        with open(in_file, "r") as vertex_file:
            content = vertex_file.read()

        # Extract list of vertex data points
        try:
            # Try using Beautiful soup method
            soup = BeautifulSoup(content, "html.parser")

            # Extract html behind table
            table_widget = "bk-widget-box bk-layout-fixed"
            table_content = soup.find("div", class_=table_widget)

            # Extract leftmost column of data (data points)
            hits = table_content.find_all("div", class_="slick-cell l1 r1")
            dp_list = [hit.find("span", style="text-align: left;").text for hit in hits]

            # Get selected vertex if exists
            cell_re = re.compile(r"slick-cell l1 r1 selected\"><span style=\"text-align: left;\">(\d+)")
            selected = re.search(cell_re, content)
            if selected is not None:
                dp_list.append(selected.group(1))
        except AttributeError:
            # Fall back to regex method
            dp_list = re.search(r'"data"\:\{"x":\[([^\]]*)', content).group(1).split(",")

        for hit in dp_list:
            # Clean hits and append
            data_point = round(float(hit))
            data_point = max(data_point, min_dp)
            data_point = min(data_point, max_dp)
            data_point_list.append(data_point)

        # Conversion to set removes redundant entries
        return sorted(set(data_point_list))

    vertices = []

    vertex_data_points = get_data_points_from_html(gui, in_file)
    for i in range(len(gui.master_df)):
        # Search for gap between index value and corresponding datapoint
        if int(gui.master_df.loc[i, "data_point"]) == int(vertex_data_points[0]):
            # Delta is discrepency between index and data point number
            delta = (vertex_data_points[0] - i) - 1
            break

    # Search for gap between index value and corresponding datapoint
    filt = gui.master_df.loc[:, "data_point"] == vertex_data_points[0]
    first_dp_index = gui.master_df.loc[filt].index
    delta = int((gui.master_df.loc[first_dp_index, "data_point"] - first_dp_index) - 1)

    # Determine if first vertex is an off start or on start
    # (FLAG) may lead to some issues due to invalid assumption
    first_vert_temper = gui.master_df.loc[vertex_data_points[0] - delta, "egg_temper"]
    second_vert_temper = gui.master_df.loc[vertex_data_points[1] - delta, "egg_temper"]
    vert_type = "off" if first_vert_temper > second_vert_temper else "on"

    # Generate vertices
    for data_point in vertex_data_points:
        index = data_point - delta
        vertices.append(niq_classes.Vertex(index, gui.master_df.loc[index, "egg_temper"], vert_type))
        vert_type = "on" if vert_type == "off" else "off"

    return vertices


def extract_bouts_in_range(gui, total_bouts, first_index, last_index):
    """
			Extracts vertices falling into a specified window of index values.

			Args:
					gui (GUIClass)
					total_bouts (list): every bout identified for the current input file
					first_index (int)
					last_index (int)
	"""

    bouts_in_range = []
    left_limit, right_limit = 0, 0

    if len(total_bouts) < 1 or last_index < total_bouts[0].first or first_index > total_bouts[-1].last:
        return bouts_in_range

    # Determine first bout in range
    for i in range(len(total_bouts)):
        if total_bouts[i].first >= first_index:
            left_limit = i
            break

    # Determine last bout in range
    for i in range((len(total_bouts) - 1), -1, -1):
        if total_bouts[i].last <= last_index:
            right_limit = i
            break

    bouts_in_range = total_bouts[left_limit : (right_limit + 1)]
    bouts_in_range.sort(key=lambda x: x.first)
    return bouts_in_range



def get_date_blocks(gui):
    """
        Creates Block objects for each date represented in the input file provided.

        Args:
            gui (GUIClass)
	"""

    # Get unique dates
    date_blocks = []
    dates = gui.master_df["date_time"].apply(datetime.datetime.date).unique()
    
    # Get data points corrisponding to each date
    for date in dates:
        sub_df = gui.master_df[gui.master_df["date_time"].apply(datetime.datetime.date) == date]
        # 86400 = number of seconds in 24 hr
        partial = is_partial(gui.master_df, sub_df.index.min(), sub_df.index.max(), 86400)
        # Create Block object
        date_blocks.append(niq_classes.Block(gui, sub_df.index.min(), sub_df.index.max(), partial))

    return date_blocks


def write_stats(gui, days, nights, date_blocks, master_block):
    """
        Calculates and gathers several statistics and subsequently dumps them into the individual
        statistics file and/or the multi-input file statistics file depending on the user's requested
        output.

        Args:
            gui (GUIClass)
            days (BlockGroup): contains every day object and information about the group as a whole
            nights (BlockGroup): contains every night object and information about the group as a whole
            date_blocks (BlockGroup): contains every date Block which cary informationa bout data for each date
            master_block (block): block built from the entire input file
	"""

    all_egg_tempers = gui.master_df.loc[:, "egg_temper"]
    all_air_tempers = gui.master_df.loc[:, "air_temper"]

    above_filt = all_egg_tempers > float(gui.time_above_temper_E.get())
    below_filt = all_egg_tempers < float(gui.time_below_temper_E.get())
    master_time_above_temper = len(all_egg_tempers[above_filt]) * gui.time_interval
    master_time_below_temper = len(all_egg_tempers[below_filt]) * gui.time_interval

    if gui.get_stats_BV.get():
        out_file = gui.stats_file_E.get()
    elif gui.multi_in_stats_BV.get():
        out_file = gui.multi_in_stats_file_E.get()

    if not (gui.get_stats_BV.get() or gui.multi_in_stats_BV.get()):
        return

    # Used to indictate scope of certain statistics
    qualifier = " (D)," if gui.restrict_search_BV.get() else " (DN),"

    # Print input file name on top (remove directories)
    header = f"{gui.active_input_path.name}\n"

    if gui.day_num_BV.get():
        header += "Day Number,"
    if gui.date_BV.get():
        header += "Date,"

    if gui.off_count_BV.get():
        header += "Off-bout Count" + qualifier
    if gui.off_dur_BV.get():
        header += "Mean Off Duration" + qualifier
    if gui.off_dur_sd_BV.get():
        header += "Off Dur StDev" + qualifier
    if gui.off_dec_BV.get():
        header += "Mean Off Temp Drop" + qualifier
    if gui.off_dec_sd_BV.get():
        header += "Off Drop StDev" + qualifier
    if gui.mean_off_temper_BV.get():
        header += "Mean Off-Bout Temp" + qualifier
    if gui.off_time_sum_BV.get():
        header += "Off-Bout Time Sum" + qualifier

    if gui.on_count_BV.get():
        header += "On-bout Count" + qualifier
    if gui.on_dur_BV.get():
        header += "Mean On Duration" + qualifier
    if gui.on_dur_sd_BV.get():
        header += "On Dur StDev" + qualifier
    if gui.on_inc_BV.get():
        header += "Mean On Temp Rise" + qualifier
    if gui.on_inc_sd_BV.get():
        header += "On Rise StDev" + qualifier
    if gui.mean_on_temper_BV.get():
        header += "Mean On-Bout Temp" + qualifier
    if gui.on_time_sum_BV.get():
        header += "On-Bout Time Sum" + qualifier

    if gui.time_above_temper_BV.get():
        header += "Time above (minutes) " + gui.time_above_temper_E.get() + ","
    if gui.time_below_temper_BV.get():
        header += "Time below (minutes) " + gui.time_below_temper_E.get() + ","
    if gui.bouts_dropped_BV.get():
        header += "Vertices Dropped" + qualifier

    if gui.mean_temper_d_BV.get():
        header += "Mean Daytime Egg Temp,"
    if gui.mean_temper_d_sd_BV.get():
        header += "Day Egg Temp StDev,"
    if gui.median_temper_d_BV.get():
        header += "Median Daytime Egg Temp,"
    if gui.min_temper_d_BV.get():
        header += "Min Daytime Egg Temp,"
    if gui.max_temper_d_BV.get():
        header += "Max Daytime Egg Temp,"

    if gui.mean_temper_n_BV.get():
        header += "Mean Nighttime Egg Temp,"
    if gui.mean_temper_n_sd_BV.get():
        header += "Night Egg Temp StDev,"
    if gui.median_temper_n_BV.get():
        header += "Median Nighttime Egg Temp,"
    if gui.min_temper_n_BV.get():
        header += "Min Nighttime Egg Temp,"
    if gui.max_temper_n_BV.get():
        header += "Max Nighttime Egg Temp,"

    if gui.mean_temper_dn_BV.get():
        header += "Mean Egg Temp (DN),"
    if gui.mean_temper_dn_sd_BV.get():
        header += "Egg Temp StDev (DN),"
    if gui.median_temper_dn_BV.get():
        header += "Median Egg Temp (DN),"
    if gui.min_temper_dn_BV.get():
        header += "Min Egg Temp (DN),"
    if gui.max_temper_dn_BV.get():
        header += "Max Egg Temp (DN),"

    if gui.air_valid:
        if gui.mean_air_temper_BV.get():
            header += "Mean Air Temp (DN),"
        if gui.mean_air_temper_sd_BV.get():
            header += "Air Temp StDev (DN),"
        if gui.min_air_temper_BV.get():
            header += "Min Air Temp (DN),"
        if gui.max_air_temper_BV.get():
            header += "Max Air Temp (DN),"

    # -----------------------------------------------------------------------------------------------

    try:
        # Set date_modifier based on if a date_block exists before the first day block
        date_modifier = 0 if date_blocks.block_list[0].date == days.block_list[0].date else 1
        # Set night_modifier based on if day or night comes first
        night_modifier = 1 if days.block_list[0].first > nights.block_list[0].last else 0
    except IndexError:
        date_modifier, night_modifier = 0, 0

    day_rows = []
    # Print individual day stats
    for i in range(len(days.block_list)):
        cur_day = days.block_list[i]
        cur_date_block = date_blocks.block_list[i + date_modifier]

        # Check if there are any night blocks left
        if len(nights.block_list) > i + night_modifier:
            cur_night = nights.block_list[i + night_modifier]
        else:
            cur_night = None


        # Pull stats from only daytime period if restriction was requested
        if gui.restrict_search_BV.get():
            core_block = cur_day
            partial = " (Partial)" if cur_day.partial_day else ""
        # Else take from entire date
        else:
            core_block = cur_date_block
            partial = " (Partial)" if cur_date_block.partial_day else ""

        day_row = ""

        if gui.day_num_BV.get():
            day_row += f"{i + 1}{partial},"
        if gui.date_BV.get():
            day_row += f"{core_block.date},"

        if gui.off_count_BV.get():
            day_row += f"{core_block.off_count},"
        if gui.off_dur_BV.get():
            day_row += f"{core_block.mean_off_dur},"
        if gui.off_dur_sd_BV.get():
            day_row += f"{core_block.off_dur_stdev},"
        if gui.off_dec_BV.get():
            day_row += f"{core_block.mean_off_dec},"
        if gui.off_dec_sd_BV.get():
            day_row += f"{core_block.off_dec_stdev},"
        if gui.mean_off_temper_BV.get():
            day_row += f"{core_block.mean_off_temper},"
        if gui.off_time_sum_BV.get():
            day_row += f"{core_block.off_time_sum},"

        if gui.on_count_BV.get():
            day_row += f"{core_block.on_count},"
        if gui.on_dur_BV.get():
            day_row += f"{core_block.mean_on_dur},"
        if gui.on_dur_sd_BV.get():
            day_row += f"{core_block.on_dur_stdev},"
        if gui.on_inc_BV.get():
            day_row += f"{core_block.mean_on_inc},"
        if gui.on_inc_sd_BV.get():
            day_row += f"{core_block.on_inc_stdev},"
        if gui.mean_on_temper_BV.get():
            day_row += f"{core_block.mean_on_temper},"
        if gui.on_time_sum_BV.get():
            day_row += f"{core_block.on_time_sum},"

        if gui.time_above_temper_BV.get():
            day_row += f"{cur_date_block.time_above_temper},"
        if gui.time_below_temper_BV.get():
            day_row += f"{cur_date_block.time_below_temper},"
        if gui.bouts_dropped_BV.get():
            day_row += f"{core_block.bouts_dropped},"

        if gui.mean_temper_d_BV.get():
            day_row += f"{cur_day.mean_egg_temper},"
        if gui.mean_temper_d_sd_BV.get():
            day_row += f"{cur_day.egg_temper_stdev},"
        if gui.median_temper_d_BV.get():
            day_row += f"{cur_day.median_temper},"
        if gui.min_temper_d_BV.get():
            day_row += f"{cur_day.min_egg_temper},"
        if gui.max_temper_d_BV.get():
            day_row += f"{cur_day.max_egg_temper},"

        if cur_night:
            if gui.mean_temper_n_BV.get():
                day_row += f"{cur_night.mean_egg_temper},"
            if gui.mean_temper_n_sd_BV.get():
                day_row += f"{cur_night.egg_temper_stdev},"
            if gui.median_temper_n_BV.get():
                day_row += f"{cur_night.median_temper},"
            if gui.min_temper_n_BV.get():
                day_row += f"{cur_night.min_egg_temper},"
            if gui.max_temper_n_BV.get():
                day_row += f"{cur_night.max_egg_temper},"

        if gui.mean_temper_dn_BV.get():
            day_row += f"{cur_date_block.mean_egg_temper},"
        if gui.mean_temper_dn_sd_BV.get():
            day_row += f"{cur_date_block.egg_temper_stdev},"
        if gui.median_temper_dn_BV.get():
            day_row += f"{cur_date_block.median_temper},"
        if gui.min_temper_dn_BV.get():
            day_row += f"{cur_date_block.min_egg_temper},"
        if gui.max_temper_dn_BV.get():
            day_row += f"{cur_date_block.max_egg_temper},"

        if gui.air_valid:
            if gui.mean_air_temper_BV.get():
                day_row += f"{cur_date_block.mean_air_temper},"
            if gui.mean_air_temper_sd_BV.get():
                day_row += f"{cur_date_block.air_temper_stdev},"
            if gui.min_air_temper_BV.get():
                day_row += f"{cur_date_block.min_air_temper},"
            if gui.max_air_temper_BV.get():
                day_row += f"{cur_date_block.max_air_temper},"

        day_rows.append(day_row)

    gui.multi_in_full_day_count += len(date_blocks.block_list)

    # -----------------------------------------------------------------------------------------------

    block_group = days if gui.restrict_search_BV.get() else master_block

    # Output stats summary for entire input file
    summary_row = ""
    if gui.day_num_BV.get():
        summary_row += f"--,"
    if gui.date_BV.get():
        summary_row += f"ALL DATA,"

    if gui.off_count_BV.get():
        summary_row += f"{block_group.off_count},"
    if gui.off_dur_BV.get():
        summary_row += f"{block_group.mean_off_dur},"
    if gui.off_dur_sd_BV.get():
        summary_row += f"{block_group.off_dur_stdev},"
    if gui.off_dec_BV.get():
        summary_row += f"{block_group.mean_off_dec},"
    if gui.off_dec_sd_BV.get():
        summary_row += f"{block_group.off_dec_stdev},"
    if gui.mean_off_temper_BV.get():
        summary_row += f"{block_group.mean_off_temper},"
    if gui.off_time_sum_BV.get():
        summary_row += f"{block_group.off_time_sum},"

    if gui.on_count_BV.get():
        summary_row += f"{block_group.on_count},"
    if gui.on_dur_BV.get():
        summary_row += f"{block_group.mean_on_dur},"
    if gui.on_dur_sd_BV.get():
        summary_row += f"{block_group.on_dur_stdev},"
    if gui.on_inc_BV.get():
        summary_row += f"{block_group.mean_on_inc},"
    if gui.on_inc_sd_BV.get():
        summary_row += f"{block_group.on_inc_stdev},"
    if gui.mean_on_temper_BV.get():
        summary_row += f"{block_group.mean_on_temper},"
    if gui.on_time_sum_BV.get():
        summary_row += f"{block_group.on_time_sum},"

    if gui.time_above_temper_BV.get():
        summary_row += f"{master_time_above_temper},"
    if gui.time_below_temper_BV.get():
        summary_row += f"{master_time_below_temper},"
    if gui.bouts_dropped_BV.get():
        summary_row += f"{block_group.bouts_dropped},"

    if gui.mean_temper_d_BV.get():
        summary_row += f"{days.mean_egg_temper},"
    if gui.mean_temper_d_sd_BV.get():
        summary_row += f"{days.egg_temper_stdev},"
    if gui.median_temper_d_BV.get():
        summary_row += f"{days.median_temper},"
    if gui.min_temper_d_BV.get():
        summary_row += f"{days.min_egg_temper},"
    if gui.max_temper_d_BV.get():
        summary_row += f"{days.max_egg_temper},"

    if gui.mean_temper_n_BV.get():
        summary_row += f"{nights.mean_egg_temper},"
    if gui.mean_temper_n_sd_BV.get():
        summary_row += f"{nights.egg_temper_stdev},"
    if gui.median_temper_n_BV.get():
        summary_row += f"{nights.median_temper},"
    if gui.min_temper_n_BV.get():
        summary_row += f"{nights.min_egg_temper},"
    if gui.max_temper_n_BV.get():
        summary_row += f"{nights.max_egg_temper},"

    if gui.mean_temper_dn_BV.get():
        summary_row += f"{all_egg_tempers.mean().round(3)},"
    if gui.mean_temper_dn_sd_BV.get():
        summary_row += f"{all_egg_tempers.std().round(3)},"
    if gui.median_temper_dn_BV.get():
        summary_row += f"{all_egg_tempers.median().round(3)},"
    if gui.min_temper_dn_BV.get():
        summary_row += f"{all_egg_tempers.min()},"
    if gui.max_temper_dn_BV.get():
        summary_row += f"{all_egg_tempers.max()},"

    if gui.air_valid:
        if gui.mean_air_temper_BV.get():
            summary_row += f"{all_air_tempers.mean().round(3)},"
        if gui.mean_air_temper_sd_BV.get():
            summary_row += f"{all_air_tempers.std().round(3)},"
        if gui.min_air_temper_BV.get():
            summary_row += f"{all_air_tempers.min()},"
        if gui.max_air_temper_BV.get():
            summary_row += f"{all_air_tempers.max()},"

    summary_row += "\n\n"

    # Determine what files to write day statistics to
    out_paths = []
    if gui.get_stats_BV.get():
        out_paths.append(Path(gui.stats_file_E.get()))
    if gui.multi_in_stats_BV.get():
        out_paths.append(Path(gui.multi_in_stats_file_E.get()))

    # Write day statistics
    for path in out_paths:
        with open(path, "a") as out_file:
            print(header, end="\n", file=out_file)
            print("\n".join(day_rows), end="\n", file=out_file)
            print(summary_row, end="\n", file=out_file)

    if not gui.get_stats_BV.get():
        return

    # -----------------------------------------------------------------------------------------------

    # Report information on individual bouts
    indi_header = "Individual Bout Stats\n"

    indi_header += (
        "Date,Bout Type,Start Time,End Time,Start Data Point,End Data Point,Duration (min),Egg Temp Change,Start Egg Temp,End Egg Temp,Mean Egg Temp,"
    )

    if gui.air_valid:
        indi_header += "Start Air Temp, End Air Temp, Mean Air Temp"

    # If restricted, take only bouts from daytime periods, else take all bouts
    bouts = []
    if gui.restrict_search_BV.get():
        bouts += [bout for day in days.block_list for bout in day.bouts]
    else:
        bouts += master_block.bouts

    bout_rows = []
    cur_date = ""
    for bout in bouts:
        row = ""
        # Print date if it is the first row corresponding to this date
        this_date = gui.master_df.loc[bout.first, "date_time"].strftime(r"%m/%d/%Y")
        row += "," if this_date == cur_date else f"{this_date},"
        cur_date = this_date

        row += f"{bout.bout_type},"

        row += (
            f"{gui.master_df.loc[bout.first, 'date_time'].strftime(r'%H:%M')},"
            + f"{gui.master_df.loc[bout.last, 'date_time'].strftime(r'%H:%M')},"
            + f"{gui.master_df.loc[bout.first, 'data_point']},"
            + f"{gui.master_df.loc[bout.last, 'data_point']},"
            + f"{bout.dur},"
            + f"{bout.temper_change},"
            + f"{gui.master_df.loc[bout.first, 'egg_temper']},"
            + f"{gui.master_df.loc[bout.last, 'egg_temper']},"
            + f"{bout.mean_egg_temper},"
        )

        if gui.air_valid:
            row += f"{gui.master_df.loc[bout.first, 'air_temper']},{gui.master_df.loc[bout.last, 'air_temper']},{bout.mean_air_temper},"

        bout_rows.append(row)

    with open(Path(gui.stats_file_E.get()), "a") as out_file:
        print(indi_header, end="\n", file=out_file)
        print("\n".join(bout_rows), file=out_file)


def generate_plot(gui, master_df, days_list, mon_dims, select_mode=False, ori_verts=None):
    """
			Uses the Bokeh module to generate an interactive plot for the current input file.

			Args:
					gui (GUIClass):
					master_df (DataFrame): contains all of the critical information for plot creation
					days_list (list): simply used to place vertical day delimiting line
					mon_dims (tuple): x and y dimensions of main display
					select_mode (bool): generates a modified plot that allows for vertex placement
	"""

    # Clears previous plots from memory
    reset_output()

    master_array = df_to_array(master_df)

    # Set output file
    output_file(Path(gui.plot_file_E.get()))

    if select_mode:
        output_file(gui.master_dir_path / "misc_files" / "temp_plot.html")

    # Set plot dimensions
    if not gui.manual_plot_dims.get():
        try:
            mon_x = mon_dims[0]
            mon_y = mon_dims[1]
            plot_width = int(mon_x) - 100
            plot_height = int(mon_y) - 200
        except:
            print("Defaulting to manual plot dimensions")
            plot_width = int(gui.plot_dim_x_E.get())
            plot_height = int(gui.plot_dim_y_E.get())
    else:
        plot_width = int(gui.plot_dim_x_E.get())
        plot_height = int(gui.plot_dim_y_E.get())

    TOOLTIPS = [("Data Point", "$x{int}"), ("Temperature", "$y")]

    hover = HoverTool(tooltips=TOOLTIPS)

    # Set plot title
    plot_name = Path(gui.input_file_E.get()).stem
    if gui.plot_title_E.get() != "":
        plot_name = gui.plot_title_E.get()

    # Set plot axes
    y_min = float("inf")
    y_max = float("-inf")

    if gui.plot_egg_BV.get():
        y_min = min(y_min, master_df["egg_temper"].min())
        y_max = max(y_max, master_df["egg_temper"].max())

    if gui.plot_air_BV.get() and gui.air_valid:
        y_min = min(y_min, master_df["air_temper"].min())
        y_max = max(y_max, master_df["air_temper"].max())

    if gui.plot_adj_BV.get():
        y_min = min(y_min, master_df["smoothed_adj_temper"].min())
        y_max = max(y_max, master_df["smoothed_adj_temper"].max())

    y_min -= 2
    y_max += 2

    dp_col_num = gui.master_df.columns.get_loc("data_point")

    # Create core plot
    plot = figure(
        tools=[hover, "box_select, box_zoom, wheel_zoom, pan, reset, save"],
        x_range=[master_df.iloc[0, dp_col_num], master_df.iloc[-1, dp_col_num]],
        y_range=[y_min, y_max],
        title=plot_name,
        x_axis_label="Data Point",
        y_axis_label="Temperature (C)",
        plot_width=plot_width,
        plot_height=plot_height,
    )

    # Add vertical lines delimiting days
    if gui.show_day_markers_BV.get():
        for day in days_list:
            vertical_line = Span(
                location=int(gui.master_df.loc[day.first, "data_point"]),
                dimension="height",
                line_color=gui.day_marker_color.get(),
                line_width=float(gui.day_marker_width_E.get()),
                line_alpha=0.4,
            )

            plot.renderers.extend([vertical_line])

    plot.grid.visible = True if gui.show_grid_BV.get() else False

    # Define data point colors
    if select_mode:
        # Set static color
        color_ = "gray"
        alpha_ = 1
    else:
        # Set color based on bout state
        bout_state_col_num = gui.master_df.columns.get_loc("bout_state") - 1
        color_key = {0: gui.off_point_color.get(), 1: gui.on_point_color.get(), 2: "lightgray"}
        color_ = np.vectorize(color_key.get)(master_array[:, bout_state_col_num])
        alpha_key = {0: 1, 1: 1, 2: 1}
        alpha_ = np.vectorize(alpha_key.get)(master_array[:, bout_state_col_num])

    radius = int(gui.smoothing_radius_E.get())

    # Get array of air temperatures and smooth if requested
    if gui.air_valid and (gui.plot_air_BV.get() or select_mode):
        air_array = master_df["air_temper"]
        if gui.smooth_status_IV.get():
            air_array = smooth_series(radius, air_array)

        # Plot air temperatures
        plot.line(
            master_df["data_point"],
            air_array,
            line_width=float(gui.air_line_width_E.get()),
            color=gui.air_line_color.get(),
            line_alpha=1,
            legend="Air temperature",
        )

    # Get array of egg temperatures and smooth if requested
    if gui.plot_egg_BV.get():
        egg_array = master_df["egg_temper"]
        if gui.smooth_status_IV.get():
            egg_array = smooth_series(radius, egg_array)

        # Update legend
        if not select_mode:
            legend_ = "On-bout (egg)" if gui.plot_adj_BV.get() else "On-bout"
            plot.circle(master_df.loc[0, "data_point"], egg_array[0], size=float(gui.on_point_size_E.get()), color=gui.on_point_color.get(), legend=legend_)

            legend_ = "Off-bout (egg)" if gui.plot_adj_BV.get() else "Off-bout"
            plot.circle(master_df.loc[0, "data_point"], egg_array[0], size=float(gui.on_point_size_E.get()), color=gui.off_point_color.get(), legend=legend_)

        # Plot egg temperatures
        if float(gui.bout_line_width_E.get()) > 0:
            plot.line(master_df["data_point"], egg_array, line_width=float(gui.bout_line_width_E.get()), color=gui.bout_line_color.get())

        plot.circle(master_df["data_point"], egg_array, size=float(gui.on_point_size_E.get()), color=color_, alpha=alpha_)

    # Get array of adjusted (egg - air) temperatures and smooth if requested
    if gui.plot_adj_BV.get():
        adj_array = master_df["smoothed_adj_temper"]

        # Plot line
        if float(gui.bout_line_width_E.get()) > 0:
            plot.line(master_df["data_point"], adj_array, line_width=float(gui.bout_line_width_E.get()), color=gui.bout_line_color.get())

        # Plot adjusted temperatures as triangles if egg temperatures are also being plotted
        plot_shape = plot.triangle if gui.plot_egg_BV.get() else plot.circle
        # Add legend values
        if select_mode:
            plot.circle(master_df.loc[0, "data_point"], adj_array, size=float(gui.on_point_size_E.get()), color="gray", legend="Temperature reading")
        else:
            plot_shape(
                master_df.loc[0, "data_point"], adj_array, size=float(gui.on_point_size_E.get()), color=gui.on_point_color.get(), legend="On-bout (egg - air)",
            )

            plot_shape(
                master_df.loc[0, "data_point"],
                adj_array,
                size=float(gui.on_point_size_E.get()),
                color=gui.off_point_color.get(),
                legend="Off-bout (egg - air)",
            )

        # Add data points
        plot_shape(master_df["data_point"], adj_array, size=float(gui.on_point_size_E.get()), color=color_, alpha=alpha_)

    # -------------------------------------------------------------------------------------------
    # Generate table with vertex information
    table_title = "Egg Temperature"
    ori_verts = [] if not ori_verts else ori_verts
    verts = get_verts_from_master_df(master_df) if not select_mode else ori_verts
    x_list, y_list = [], []

    # Add vertices to table (allow egg_tempers or adj_tempers, not both)
    if gui.plot_egg_BV.get():
        x_list += [gui.master_df.loc[vert.index, "data_point"] for vert in verts]
        y_list += [gui.master_df.loc[vert.index, "egg_temper"] for vert in verts]
    elif gui.plot_adj_BV.get():
        table_title = "Adjusted Temperature"
        x_list += [gui.master_df.loc[vert.index, "data_point"] for vert in verts]
        y_list += [gui.master_df.loc[vert.index, "smoothed_adj_temper"] for vert in verts]

    data = {"x": x_list, "y": y_list}

    src = ColumnDataSource(data)
    columns = [TableColumn(field="x", title="Transition Data Point"), TableColumn(field="y", title=table_title)]

    # FLAG shoud make height dynamic
    data_table = DataTable(source=src, columns=columns, width=500, height=100000)

    # -------------------------------------------------------------------------------------------

    if select_mode:
        # Plot vertices as large circles in select mode
        renderer = plot.circle("x", "y", size=float(gui.on_point_size_E.get()), color="red", fill_alpha=0.8, legend="Incubation State Change", source=src)

        draw_tool = PointDrawTool(renderers=[renderer], empty_value=1)
        plot.add_tools(draw_tool)
        plot.toolbar.active_drag = draw_tool

    # Get formatting settings from GUI
    plot.title.text_font_size = gui.title_font_size_E.get() + "pt"
    plot.axis.axis_label_text_font_size = gui.axis_title_font_size_E.get() + "pt"
    plot.axis.major_label_text_font_size = gui.axis_label_font_size_E.get() + "pt"
    plot.axis.major_tick_line_width = int(gui.axis_tick_size_E.get())
    plot.axis.minor_tick_line_width = int(gui.axis_tick_size_E.get())
    plot.axis.major_tick_out = int(gui.axis_tick_size_E.get())
    plot.axis.minor_tick_out = int(gui.axis_tick_size_E.get())

    plot.legend.label_text_font_size = gui.legend_font_size_E.get() + "pt"
    plot.legend.click_policy = "hide"
    plot.legend.location = gui.legend_loc.get()
    plot.background_fill_color = None
    plot.border_fill_color = None

    show(column(plot, widgetbox(data_table)))


def get_verts_from_master_df(master_df):
    """
			Extracts vertex objects based on state transitions in master_df.

			Args:
					master_df (pd.DataFrame)
	"""

    # Convert bout_states to integers
    temp_df = master_df.copy()
    int_states = temp_df.loc[:, "bout_state"].replace(["off", "on", "None"], [0, 1, 2])

    # Create Boolean Series that stores if the state has changed
    state_changed = int_states.diff().astype(bool)
    state_changed.iloc[0] = False

    # Extract indices of rows where the state changes
    vert_indices = master_df[state_changed].index.tolist()

    # Create and append verticies
    master_array = df_to_array(master_df)
    cur_state = master_array[0, 6]

    vertices = []
    for index in vert_indices:
        row = master_df.loc[index]
        vertices.append(niq_classes.Vertex(index, row["egg_temper"], row["bout_state"]))

    # Add vertices at begining and end of data set
    last = len(master_df) - 1
    vertices.append(niq_classes.Vertex(0, master_df.loc[0, "egg_temper"], master_df.loc[0, "bout_state"]))
    vertices.append(niq_classes.Vertex(last, master_df.loc[last, "egg_temper"], master_df.loc[last, "bout_state"]))

    vertices.sort(key=lambda x: x.index)
    return vertices


def replace_entry(entry, new_value):
    entry.delete(0, "end")
    entry.insert(0, new_value)


def filter_by_dur(master_df, dur_thresh):
    """
			Purges the master array of state clusters failing to meet a given duration threshold.

			Args:
					master_array (numpy array)
					dur_thresh (int): minimum duration for a cluster of state values to not be erased
	"""

    master_array = df_to_array(master_df)

    cur_state = master_array[0, 6]
    last_count, count = 0, 0
    bouts_dropped_locs = set()
    for row_num, state in enumerate(master_array[:, 6]):
        # If state is same as previous data point (still in same bout)
        if state == cur_state:
            count += 1
        # If state has changed (end of bout) and bout is greater than dur_thresh
        elif count >= dur_thresh:
            last_count = count
            count = 0
            cur_state = state
        # If state has changed and bout is less than dur_thresh
        elif count < dur_thresh:
            # Change previous bout to other state
            cur_state = abs(cur_state - 1)
            master_array[row_num - count - 2 : row_num + 1, 6] = cur_state
            bouts_dropped_locs.add(row_num)
            count += last_count

    master_df.loc[:, "bout_state"] = master_array[:, 6]
    master_df.loc[:, "bout_state"].replace([0, 1, 2], ["off", "on", "None"], inplace=True)
    return master_df, bouts_dropped_locs


def set_unique_path(entry, file_name, dir_path=Path.cwd(), ext=""):
    """
			Incriments an identificaiton number until a unique file name is found then
            fills entry box with unique path.

			Args:
					entry (tk.Entry): entry box being updated
					file_name (str): base or "stem" of path to be returned
					dir_path (str or pathlib.Path): path to parent directory
					ext (str): file extension
	"""

    counter = 0
    file_path = Path(dir_path) / file_name

    # Adds appropriate extension if not already present
    file_path = file_path.parent / (file_path.stem + ext)
    stem = file_path.stem

    # Adds trailing number until unique path is found
    while file_path.exists():
        counter += 1
        file_path = file_path.parent / (stem + "_" + str(counter).zfill(3) + file_path.suffix)

    replace_entry(entry, file_path.name)


def extract_in_files(in_file_string):
    """
			Parses sting of paths for individual input files.

			Args:
					in_file_string (str): collection of paths
	"""

    split_list = in_file_string.split(".csv")
    in_file_tup = ()
    for num, path in enumerate(split_list):
        in_file_tup += (path[1:] + ".csv",) if num != 0 else (path + ".csv",)

    return in_file_tup[:-1]


def add_states(df, verts=None, states=None):
    """
                Adds bout state column to master_df

                Args:   
                        array (numpy array)
                        df (DataFrame)
                        verts (list):
                        states (numpy array):

                Note: consider adding "partial_bout" argument that dictates if data at extremities of df is classified.
        """

    # Appends state values based on vertex locations
    if verts is not None:

        df["bout_state"] = "None"

        state = "off"  # Assume off-bout start -- is corrected by "swap_params_by_state" if necessary

        # Create list of vertex indices
        indices = [0]
        indices += [vert.index for vert in verts]
        indices.append(len(df))

        prev_i = indices[0]
        for next_i in indices[1:]:
            df.loc[prev_i : next_i - 1, "bout_state"] = state

            # Set up for next round
            prev_i = next_i
            state = "off" if state == "on" else "on"

    # If states are provided, simply append
    if states is not None:
        df.loc[:, "bout_state"] = states
        df.loc[:, "bout_state"].replace([0, 1, 2], ["off", "on", "None"], inplace=True)

    # Flip bout states if necessary
    on_bout_delta_temp = df.loc[df["bout_state"] == "on", "delta_temper"].mean()
    off_bout_delta_temp = df.loc[df["bout_state"] == "off", "delta_temper"].mean()
    if off_bout_delta_temp > on_bout_delta_temp:
        df.loc[:, "bout_state"].replace(["off", "on", "None"], ["on", "off", "None"], inplace=True)

    return df


def remove_curly(*entries, string=False):
    """
			Removes curly braces from entry box contents. These are often added for paths containing spaces.

			Args:
					entries (tk.Entry)
	"""

    if string:
        return entries[0].lstrip("{").rstrip("}")

    for entry in entries:
        replace_entry(entry, entry.get().lstrip("{").rstrip("}"))


def df_to_array(df):
    """
        Convert master DataFrame to numpy array.
    """

    # If array is passed, just return
    if type(df) == np.ndarray:
        return df

    # Remove date_time column as this data is not compatable with numpy arrays
    mod_df = df.drop("date_time", axis=1)

    # Convert bout_state values from strings to integers
    if "bout_state" in df.columns:
        mod_df.loc[:, "bout_state"].replace(["off", "on", "None"], [0, 1, 2], inplace=True)

    return mod_df.to_numpy()


def get_bouts_from_verts(gui, verts):
    """
            Extracts bout objects based on vertex locations.

            Args:
                    gui (GUIClass)
    """
    bouts = []

    # Return if insufficient number of vertices supplied
    if verts == None or len(verts) < 2:
        return bouts

    # Create bout objects
    cur_vert = verts[0]
    for next_vert in verts[1:]:
        # Skip if cur_vert is start of nighttime period
        if cur_vert.vert_type != "None":
            bouts.append(niq_classes.Bout(gui, cur_vert.index, next_vert.index - 1, cur_vert.vert_type)) 

        cur_vert = next_vert

    return bouts