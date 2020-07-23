import datetime
import json
import re
import time
from pathlib import Path

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

    # Return input if already datetime object
    if type(dt_string) == pd._libs.tslibs.timestamps.Timestamp:
        return dt_string

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
    delta = int(gui.master_df.loc[first_dp_index, "data_point"] - first_dp_index)

    # Determine if first vertex is an off start or on start
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
        if total_bouts[i].middle >= first_index:
            left_limit = i
            break

    # Determine last bout in range
    for i in range((len(total_bouts) - 1), -1, -1):
        if total_bouts[i].middle <= last_index:
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


def write_stats(gui, date_blocks, master_block):
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
        header += "Time above " + gui.time_above_temper_E.get() + " (minutes),"
    if gui.time_below_temper_BV.get():
        header += "Time below " + gui.time_below_temper_E.get() + " (minutes),"
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

    day_rows = []
    # Print individual day stats
    for i, block in enumerate(date_blocks):
        day_row = ""

        partial = " (Partial)" if block.partial_day else " (Full)"

        if gui.day_num_BV.get():
            day_row += f"{i + 1}{partial},"
        if gui.date_BV.get():
            day_row += f"{block.date},"

        if gui.off_count_BV.get():
            day_row += f"{block.off_count},"
        if gui.off_dur_BV.get():
            day_row += f"{block.mean_off_dur},"
        if gui.off_dur_sd_BV.get():
            day_row += f"{block.off_dur_stdev},"
        if gui.off_dec_BV.get():
            day_row += f"{block.mean_off_dec},"
        if gui.off_dec_sd_BV.get():
            day_row += f"{block.off_dec_stdev},"
        if gui.mean_off_temper_BV.get():
            day_row += f"{block.mean_off_temper},"
        if gui.off_time_sum_BV.get():
            day_row += f"{block.off_time_sum},"

        if gui.on_count_BV.get():
            day_row += f"{block.on_count},"
        if gui.on_dur_BV.get():
            day_row += f"{block.mean_on_dur},"
        if gui.on_dur_sd_BV.get():
            day_row += f"{block.on_dur_stdev},"
        if gui.on_inc_BV.get():
            day_row += f"{block.mean_on_inc},"
        if gui.on_inc_sd_BV.get():
            day_row += f"{block.on_inc_stdev},"
        if gui.mean_on_temper_BV.get():
            day_row += f"{block.mean_on_temper},"
        if gui.on_time_sum_BV.get():
            day_row += f"{block.on_time_sum},"

        if gui.time_above_temper_BV.get():
            day_row += f"{block.time_above_temper},"
        if gui.time_below_temper_BV.get():
            day_row += f"{block.time_below_temper},"
        if gui.bouts_dropped_BV.get():
            day_row += f"{block.bouts_dropped},"

        if gui.mean_temper_d_BV.get():
            day_row += f"{block.mean_egg_temper_day},"
        if gui.mean_temper_d_sd_BV.get():
            day_row += f"{block.egg_temper_stdev_day},"
        if gui.median_temper_d_BV.get():
            day_row += f"{block.median_egg_temper_day},"
        if gui.min_temper_d_BV.get():
            day_row += f"{block.min_egg_temper_day},"
        if gui.max_temper_d_BV.get():
            day_row += f"{block.max_egg_temper_day},"

        if gui.mean_temper_n_BV.get():
            day_row += f"{block.mean_egg_temper_night},"
        if gui.mean_temper_n_sd_BV.get():
            day_row += f"{block.egg_temper_stdev_night},"
        if gui.median_temper_n_BV.get():
            day_row += f"{block.median_egg_temper_night},"
        if gui.min_temper_n_BV.get():
            day_row += f"{block.min_egg_temper_night},"
        if gui.max_temper_n_BV.get():
            day_row += f"{block.max_egg_temper_night},"

        if gui.mean_temper_dn_BV.get():
            day_row += f"{block.mean_egg_temper},"
        if gui.mean_temper_dn_sd_BV.get():
            day_row += f"{block.egg_temper_stdev},"
        if gui.median_temper_dn_BV.get():
            day_row += f"{block.median_temper},"
        if gui.min_temper_dn_BV.get():
            day_row += f"{block.min_egg_temper},"
        if gui.max_temper_dn_BV.get():
            day_row += f"{block.max_egg_temper},"

        if gui.air_valid:
            if gui.mean_air_temper_BV.get():
                day_row += f"{block.mean_air_temper},"
            if gui.mean_air_temper_sd_BV.get():
                day_row += f"{block.air_temper_stdev},"
            if gui.min_air_temper_BV.get():
                day_row += f"{block.min_air_temper},"
            if gui.max_air_temper_BV.get():
                day_row += f"{block.max_air_temper},"

        day_rows.append(day_row)

    gui.multi_in_full_day_count += len(date_blocks)

    # -----------------------------------------------------------------------------------------------

    # Output stats summary for entire input file
    summary_row = ""
    if gui.day_num_BV.get():
        summary_row += f"--,"
    if gui.date_BV.get():
        summary_row += f"ALL DATA,"

    if gui.off_count_BV.get():
        summary_row += f"{master_block.off_count},"
    if gui.off_dur_BV.get():
        summary_row += f"{master_block.mean_off_dur},"
    if gui.off_dur_sd_BV.get():
        summary_row += f"{master_block.off_dur_stdev},"
    if gui.off_dec_BV.get():
        summary_row += f"{master_block.mean_off_dec},"
    if gui.off_dec_sd_BV.get():
        summary_row += f"{master_block.off_dec_stdev},"
    if gui.mean_off_temper_BV.get():
        summary_row += f"{master_block.mean_off_temper},"
    if gui.off_time_sum_BV.get():
        summary_row += f"{master_block.off_time_sum},"

    if gui.on_count_BV.get():
        summary_row += f"{master_block.on_count},"
    if gui.on_dur_BV.get():
        summary_row += f"{master_block.mean_on_dur},"
    if gui.on_dur_sd_BV.get():
        summary_row += f"{master_block.on_dur_stdev},"
    if gui.on_inc_BV.get():
        summary_row += f"{master_block.mean_on_inc},"
    if gui.on_inc_sd_BV.get():
        summary_row += f"{master_block.on_inc_stdev},"
    if gui.mean_on_temper_BV.get():
        summary_row += f"{master_block.mean_on_temper},"
    if gui.on_time_sum_BV.get():
        summary_row += f"{master_block.on_time_sum},"

    if gui.time_above_temper_BV.get():
        summary_row += f"{master_block.time_above_temper},"
    if gui.time_below_temper_BV.get():
        summary_row += f"{master_block.time_below_temper},"
    if gui.bouts_dropped_BV.get():
        summary_row += f"{master_block.bouts_dropped},"

    if gui.mean_temper_d_BV.get():
        summary_row += f"{master_block.mean_egg_temper_day},"
    if gui.mean_temper_d_sd_BV.get():
        summary_row += f"{master_block.egg_temper_stdev_day},"
    if gui.median_temper_d_BV.get():
        summary_row += f"{master_block.median_egg_temper_day},"
    if gui.min_temper_d_BV.get():
        summary_row += f"{master_block.min_egg_temper_day},"
    if gui.max_temper_d_BV.get():
        summary_row += f"{master_block.max_egg_temper_day},"

    if gui.mean_temper_n_BV.get():
        summary_row += f"{master_block.mean_egg_temper_night},"
    if gui.mean_temper_n_sd_BV.get():
        summary_row += f"{master_block.egg_temper_stdev_night},"
    if gui.median_temper_n_BV.get():
        summary_row += f"{master_block.median_egg_temper_night},"
    if gui.min_temper_n_BV.get():
        summary_row += f"{master_block.min_egg_temper_night},"
    if gui.max_temper_n_BV.get():
        summary_row += f"{master_block.max_egg_temper_night},"

    if gui.mean_temper_dn_BV.get():
        summary_row += f"{master_block.mean_egg_temper},"
    if gui.mean_temper_dn_sd_BV.get():
        summary_row += f"{master_block.egg_temper_stdev},"
    if gui.median_temper_dn_BV.get():
        summary_row += f"{master_block.median_temper},"
    if gui.min_temper_dn_BV.get():
        summary_row += f"{master_block.min_egg_temper},"
    if gui.max_temper_dn_BV.get():
        summary_row += f"{master_block.max_egg_temper},"

    if gui.air_valid:
        if gui.mean_air_temper_BV.get():
            summary_row += f"{master_block.mean_air_temper},"
        if gui.mean_air_temper_sd_BV.get():
            summary_row += f"{master_block.air_temper_stdev},"
        if gui.min_air_temper_BV.get():
            summary_row += f"{master_block.min_air_temper},"
        if gui.max_air_temper_BV.get():
            summary_row += f"{master_block.max_air_temper},"

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

    bouts = master_block.bouts

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


def generate_plot(gui, days_list, edit_mode=False, out_path=None):
    """
        Uses the Bokeh module to generate an interactive plot for the current input file.

        Args:
            gui (GUIClass):
            days_list (list): used to place vertical day delimiting line
            edit_mode (bool): generates a modified plot that allows for vertex manipulation
	"""

    def get_plot_dims():
        """ 
            Determine plot dimientions based on either user provided values or 
            monitor dimension detection. 
        """

        if not gui.manual_plot_dims.get():
            try:
                mon_dims = (gui.root.winfo_screenwidth(), gui.root.winfo_screenheight())
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

        return plot_width, plot_height
    
    def get_plot_axes():
        """ Determine proper constrains of y axis """

        y_min = float("inf")
        y_max = float("-inf")

        if gui.plot_egg_BV.get():
            y_min = min(y_min, df["egg_temper"].min())
            y_max = max(y_max, df["egg_temper"].max())

        if gui.plot_air_BV.get() and gui.air_valid:
            y_min = min(y_min, df["air_temper"].min())
            y_max = max(y_max, df["air_temper"].max())

        if gui.plot_adj_BV.get():
            y_min = min(y_min, df["smoothed_adj_temper"].min())
            y_max = max(y_max, df["smoothed_adj_temper"].max())

        y_min -= 2
        y_max += 2

        return y_min, y_max

    def generate_table():
        """ Generate table with vertex information """

        table_title = "Egg Temperature"
        verts = get_verts_from_master_df(df)
        x_list, y_list = [], []

        # Add vertices to table (allow egg_tempers or adj_tempers, not both)
        if gui.plot_egg_BV.get():
            x_list += [df.loc[vert.index, "data_point"] for vert in verts]
            y_list += [df.loc[vert.index, "egg_temper"] for vert in verts]
        elif gui.plot_adj_BV.get():
            table_title = "Adjusted Temperature"
            x_list += [df.loc[vert.index, "data_point"] for vert in verts]
            y_list += [df.loc[vert.index, "smoothed_adj_temper"] for vert in verts]

        data = {"x": x_list, "y": y_list}

        src = ColumnDataSource(data)
        columns = [TableColumn(field="x", title="Transition Data Point"), TableColumn(field="y", title=table_title)]

        # FLAG shoud make height dynamic
        data_table = DataTable(source=src, columns=columns, width=500, height=100000)
        
        return data_table

    def append_input_info(path):
        # Get number of seconds between each data point
        first = df["date_time"].iloc[0]
        last = df["date_time"].iloc[-1]
        delta_sec = (last - first).total_seconds()
        interval = round(delta_sec / len(df))

        # Create dictionary summarizing critical input file information
        input_dict = {
            "first_dp": int(df["data_point"].iloc[0]),
            "first_dt": df["date_time"].iloc[0].strftime(r"%m/%d/%Y %H:%M:%S"),
            "dt_interval": interval,
            "egg_temper": df["egg_temper"].tolist(),
            "air_temper": df["air_temper"].tolist()
        }

        # Append input file information to the HTML file
        with open(path, "a") as file:
            file.write("\n\n<!--NestIQ input data\n")
            file.write(json.dumps(input_dict))
            file.write("\n-->\n")


    df = gui.master_df
    master_array = df_to_array(df)

    # Clears previous plots from memory
    reset_output()

    # Set output file
    out_path = out_path if out_path is not None else Path(gui.plot_file_E.get())
    output_file(out_path)


    plot_width, plot_height = get_plot_dims()

    TOOLTIPS = [("Data Point", "$x{int}"), ("Temperature", "$y")]

    hover = HoverTool(tooltips=TOOLTIPS)

    # Set plot title
    plot_name = Path(gui.input_file_E.get()).stem
    if gui.plot_title_E.get() != "":
        plot_name = gui.plot_title_E.get()

    # Set plot axes
    y_min, y_max = get_plot_axes()

    dp_col_num = df.columns.get_loc("data_point")

    # Create core plot
    plot = figure(
        tools=[hover, "box_select, box_zoom, wheel_zoom, pan, reset, save"],
        x_range=[df.iloc[0, dp_col_num], df.iloc[-1, dp_col_num]],
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
                location=int(df.loc[day.first, "data_point"]),
                dimension="height",
                line_color=gui.day_marker_color.get(),
                line_width=float(gui.day_marker_width_E.get()),
                line_alpha=0.4,
            )

            plot.renderers.extend([vertical_line])

    plot.grid.visible = True if gui.show_grid_BV.get() else False

    # Define data point colors
    if edit_mode:
        # Set static color
        color_ = "gray"
        alpha_ = 1
    else:
        # Set color based on bout state
        bout_state_col_num = 2
        color_key = {0: gui.off_point_color.get(), 1: gui.on_point_color.get(), 2: "lightgray"}
        color_ = np.vectorize(color_key.get)(master_array[:, bout_state_col_num])
        alpha_key = {0: 1, 1: 1, 2: 1}
        alpha_ = np.vectorize(alpha_key.get)(master_array[:, bout_state_col_num])

    radius = int(gui.smoothing_radius_E.get())

    # Get array of air temperatures and smooth if requested
    if gui.air_valid and gui.plot_air_BV.get():
        air_array = df["air_temper"]
        if gui.smooth_status_IV.get():
            air_array = smooth_series(radius, air_array)

        # Plot air temperatures
        plot.line(
            df["data_point"],
            air_array,
            line_width=float(gui.air_line_width_E.get()),
            color=gui.air_line_color.get(),
            line_alpha=1,
            legend="Air temperature",
        )

    # Get array of egg temperatures and smooth if requested
    if gui.plot_egg_BV.get():
        egg_array = df["egg_temper"]
        if gui.smooth_status_IV.get():
            egg_array = smooth_series(radius, egg_array)

        # Update legend
        if not edit_mode:
            legend_ = "On-bout (egg)" if gui.plot_adj_BV.get() else "On-bout"
            plot.circle(df.loc[0, "data_point"], egg_array[0], size=float(gui.on_point_size_E.get()), color=gui.on_point_color.get(), legend=legend_)

            legend_ = "Off-bout (egg)" if gui.plot_adj_BV.get() else "Off-bout"
            plot.circle(df.loc[0, "data_point"], egg_array[0], size=float(gui.on_point_size_E.get()), color=gui.off_point_color.get(), legend=legend_)

        # Plot egg temperatures
        if float(gui.bout_line_width_E.get()) > 0:
            plot.line(df["data_point"], egg_array, line_width=float(gui.bout_line_width_E.get()), color=gui.bout_line_color.get())

        plot.circle(df["data_point"], egg_array, size=float(gui.on_point_size_E.get()), color=color_, alpha=alpha_)

    # Get array of adjusted (egg - air) temperatures and smooth if requested
    if gui.plot_adj_BV.get():
        adj_array = df["smoothed_adj_temper"]

        # Plot line
        if float(gui.bout_line_width_E.get()) > 0:
            plot.line(df["data_point"], adj_array, line_width=float(gui.bout_line_width_E.get()), color=gui.bout_line_color.get())

        # Plot adjusted temperatures as triangles if egg temperatures are also being plotted
        plot_shape = plot.triangle if gui.plot_egg_BV.get() else plot.circle
        # Add legend values
        if edit_mode:
            plot.circle(df.loc[0, "data_point"], adj_array, size=float(gui.on_point_size_E.get()), color="gray", legend="Temperature reading")
        else:
            plot_shape(
                df.loc[0, "data_point"], adj_array, size=float(gui.on_point_size_E.get()), color=gui.on_point_color.get(), legend="On-bout (egg - air)",
            )

            plot_shape(
                df.loc[0, "data_point"],
                adj_array,
                size=float(gui.on_point_size_E.get()),
                color=gui.off_point_color.get(),
                legend="Off-bout (egg - air)",
            )

        # Add data points
        plot_shape(df["data_point"], adj_array, size=float(gui.on_point_size_E.get()), color=color_, alpha=alpha_)


    data_table = generate_table()

    if edit_mode:
        # Plot vertices as large circles in select mode
        renderer = plot.circle("x", "y", size=float(gui.on_point_size_E.get()), color="red", fill_alpha=0.8, legend="Incubation State Change", source=data_table.source)

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

    append_input_info(out_path)


def get_verts_from_master_df(master_df):
    """
        Extracts vertex objects based on state transitions in master_df.

        Args:
            master_df (pd.DataFrame)
	"""

    if "bout_state" not in master_df.columns:
        return []

    # Convert bout_states to integers
    temp_df = master_df.copy()
    int_states = temp_df.loc[:, "bout_state"].replace(["off", "on", "None"], [0, 1, 2])

    # Create Boolean Series that stores if the state has changed
    state_changed = int_states.diff().astype(bool)
    state_changed.iloc[0] = False

    # Extract indices of rows where the state changes
    vert_indices = master_df[state_changed].index.tolist()

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


def filter_by_dur(gui):
    """
			Purges the master df of state clusters failing to meet a given duration threshold.

			Args:
					gui (GUI)
	"""

    dur_thresh = int(gui.dur_thresh_E.get())
    df = gui.master_df
    bouts_dropped_locs = set()

    for bout in gui.master_block.bouts:
        dur = bout.last - bout.first
        # If duration threshold not met
        if dur < dur_thresh:
            # Set bout_state for corrisponding rows to that of adjacent row
            new_state = "on" if bout.bout_type == "off" else "off"
            df.loc[bout.first:bout.last, "bout_state"] = new_state
            bouts_dropped_locs.add(bout.middle)
            # Delete bout
            gui.master_block.bouts.remove(bout)

    return df, bouts_dropped_locs


def set_unique_path(entry, path, ext):
    """
        Incriments an identificaiton number until a unique file name is found then
        fills entry box with unique path.

        Args:
            entry (tk.Entry): entry box being updated
            path (pathlib.Path): path to check for uniqueness
            ext (str): file extension
	"""

    counter = 0
    ori_stem = path.stem
    file_path = Path(path).with_suffix(ext)

    # Adds trailing number until unique path is found
    while file_path.exists():
        counter += 1
        file_path = (file_path.parent / (ori_stem + "_" + str(counter).zfill(3))).with_suffix(ext)

    replace_entry(entry, file_path)


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

        Columns:
            0 - data point
            1 - delta temper (emision), change in smoothed_egg_temper or smoothed_adj_temper depending on user setting
            2 - bout state
    """

    # If array is passed, just return
    if type(df) == np.ndarray:
        return df

    # Grab appropriate columns
    if "bout_state" in df.columns:
        mod_df = df.loc[:, ["data_point", "delta_temper", "bout_state"]].copy()
        # Convert bout stats to integers
        mod_df.loc[:, "bout_state"].replace(["off", "on", "None"], [0, 1, 2], inplace=True)
    else:
        mod_df = df[["data_point", "delta_temper"]]

    return mod_df.to_numpy()


def get_bouts_from_verts(gui, verts):
    """
            Extracts bout objects based on vertex locations.

            Args:
                    gui (GUIClass)
    """
    bouts = []

    # Return if insufficient number of vertices supplied
    if verts is None or len(verts) < 2:
        return bouts

    # Create bout objects
    cur_vert = verts[0]
    for next_vert in verts[1:]:
        # Skip if cur_vert is start of nighttime period
        if cur_vert.vert_type != "None" and next_vert.index > cur_vert.index:
            bouts.append(niq_classes.Bout(gui, cur_vert.index, next_vert.index - 1, cur_vert.vert_type)) 

        cur_vert = next_vert

    bouts.sort(key=lambda x: x.first)
    return bouts
