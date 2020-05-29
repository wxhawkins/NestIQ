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


def extract_time(date_time_cell):
    """
			Pulls time out of cell containing date and time (MM/DD/YYYY HH:MM)

			Args:
					date_time_cell (str): input file cell containing the date and time string to be extracted from
	"""

    return re.search(r"(\d+:\d+)", date_time_cell).group(1)


def extract_date(date_time_cell):
    """
			Pulls date out of cell containing date and time (MM/DD/YYYY HH:MM)

			Args:
					date_time_cell (str): input file cell containing the date and time string to be extracted from
	"""

    return re.search(r"(\d+\/\d+\/\d+)", date_time_cell).group(1)


def check_time_in_daytime(day_start, night_start, time):
    """
			Checks if a given time is inside of user-provided daytime period.

			Args:
					day_start (str): time considered the start of daytime
					night_start (str): time considered the end of daytime
					time (str): time being analyzed
	"""

    day = re.search(r"(\d+)(:)(\d+)", day_start)
    day_float = float(day.group(1)) + (float(day.group(3)) / 60)

    night = re.search(r"(\d+)(:)(\d+)", night_start)
    night_float = float(night.group(1)) + (float(night.group(3)) / 60)

    cur_time = re.search(r"(\d+)(:)(\d+)", time)
    cur_time_float = float(cur_time.group(1)) + (float(cur_time.group(3)) / 60)

    if (cur_time_float > night_float) or (cur_time_float < day_float):
        return False

    return True


def split_days(gui, modifier=0):
    """
			Splits the entire data set into individual day and night objects based on user-provided day and
			night start times.

			Args:
					gui (GUIClass)
					modifier (int): amount in minutes to modify given times by
	"""

    def shift_time(ori_time):
        """
				Slightly offsets the time from the input file to try to address skipping of critical times being
				searched for.

				Args:
						ori_time (str): original time (prior to modification)
		"""

        if modifier == 0:
            new_time = ori_time
        else:
            # Convert string time value to datetime format
            search = re.search(r"((\d+):(\d+))", ori_time)
            hour = int(search.group(2))
            minute = int(search.group(3))
            time = datetime.datetime(1, 1, 1, hour, minute, 0)

            # Add modifer and strip unnecessary characters
            new_time = time + datetime.timedelta(minutes=modifier)
            new_time = str(new_time)[11:-3]
            if new_time[0] == "0":
                new_time = new_time[1:]

        return " " + new_time.strip()

    days_list, nights_list = [], []

    reached_end = False
    day_start = shift_time(gui.day_start_E.get())
    night_start = shift_time(gui.night_start_E.get())
    day_dur = get_day_dur(day_start, night_start)
    night_dur = 1440 - day_dur
    day_interval = 1440 / gui.time_interval
    day_start_index = -1
    night_start_index = -1

    # Look for first day or night
    for i in range(0, len(gui.master_df)):
        # If day_start found before night_start
        if re.search(day_start, gui.master_df.loc[i, "date_time"]):
            # Set start of first day to this index
            day_start_index = i
            # Set start of first night to day index + duration of daytime
            night_start_index = i + (day_dur / gui.time_interval)
            # Check if this sets night_start_index past length of master DataFrame
            if night_start_index > (len(gui.master_df) - 1):
                reached_end = True
                night_start_index = len(gui.master_df) - 1
                days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, True))

            break
        # If night_start found before day_start
        elif re.search(night_start, gui.master_df.loc[i, "date_time"]):
            # Set start of first night to this index
            night_start_index = i
            # Set start of first day to night index + duration of nighttime
            day_start_index = i + (night_dur / gui.time_interval)
            # Check if this sets day_start_index past length of master DataFrame
            if day_start_index > (len(gui.master_df) - 1):
                reached_end = True
                day_start_index = len(gui.master_df) - 1

            break

    # Check if data starts at night and process to achieve uniformity going into following while loop
    # Catch partial day at start of master DataFrame
    if night_start_index < day_start_index:
        days_list.append(niq_classes.Block(gui, 0, night_start_index - 1, True))
        nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, reached_end))
        night_start_index += day_interval
    # Catch partial night at start of master DataFrame
    elif day_start_index < night_start_index:
        nights_list.append(niq_classes.Block(gui, 0, day_start_index - 1, True))
    # If neither day_start or night_start found, append partial day or night
    elif day_start_index == night_start_index:
        reached_end = True
        if check_time_in_daytime(day_start, night_start, gui.master_df.loc[i, "date_time"]):
            days_list.append(niq_classes.Block(gui, 0, (len(gui.master_df) - 1), True))
        else:
            nights_list.append(niq_classes.Block(gui, 0, (len(gui.master_df) - 1), True))

    # Save each day and night as object
    while not reached_end:
        days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, False))
        day_start_index += day_interval

        # Make final night stop at end of master DataFrame
        if day_start_index > len(gui.master_df):
            day_start_index = len(gui.master_df) - 1
            nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, True))
            reached_end = True
            break
        else:
            nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, False))
            night_start_index += day_interval

        # Make final day stop at end of master DataFrame
        if night_start_index > len(gui.master_df):
            night_start_index = len(gui.master_df) - 1
            days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, True))
            reached_end = True

    # Address problem of start time skipping
    if len(days_list) == 0 or len(nights_list) == 0:
        if (modifier + 1) < gui.time_interval:
            days_list.clear()
            nights_list.clear()
            # Recursively call split_days with incremented modifier
            days_list, nights_list = split_days(gui, modifier=(modifier + 1))
        # If still no days or nights found, provide text warning
        elif (gui.time_interval * len(gui.master_df)) > 1440:
            if gui.show_warns_BV.get():
                messagebox.showwarning(
                    "Warning",
                    (
                        "If daytime periods are not being identified correctly, try manually"
                        + ' setting "data_time_interval" variable in the defaultConfig.ini file'
                        + " found in the cofig_files folder."
                    ),
                )

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
            return True
        except ValueError:
            return False

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
    df["date_time"] = df["date_time"].astype(str)
    df["egg_temper"] = df["egg_temper"].astype(float).round(4)
    df["air_temper"] = df["air_temper"].astype(float).round(4)

    # Reassign data_point column to be continuous
    start = int(df["data_point"].iloc[0])
    new_col = range(start, (start + len(df)))
    df["data_point"] = new_col

    # Add adjusted (egg - air temperature) temperatures column
    df["adj_temper"] = df["egg_temper"] - df["air_temper"]

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

    return df


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
    vert_type = 0 if first_vert_temper > second_vert_temper else 1

    # Generate vertices
    for data_point in vertex_data_points:
        index = data_point - delta
        vertices.append(niq_classes.Vertex(index, gui.master_df.loc[index, "egg_temper"], vert_type))
        vert_type = abs(vert_type - 1)

    return vertices


def extract_verts_in_range(gui, total_vertices, start_index, stop_index):
    """
			Extracts vertices falling into a specified window of index values.

			Args:
					gui (GUIClass)
					total_vertices (list): every vertex identified for the current input file
					start_index (int)
					stop_index (int)
	"""

    verts_in_range = []
    left_limit, right_limit = 0, 0

    if any((
        len(total_vertices) < 1, 
        stop_index < total_vertices[0].index, 
        start_index > total_vertices[-1].index
    )):
        return verts_in_range

    # Determine first vertex in range
    for i in range(len(total_vertices)):
        if total_vertices[i].index >= start_index:
            left_limit = i
            break

    # Determine last vertex in range
    for i in range((len(total_vertices) - 1), -1, -1):
        if total_vertices[i].index <= stop_index:
            right_limit = i
            break

    verts_in_range = total_vertices[left_limit : (right_limit + 1)]
    return verts_in_range


def get_bouts(gui, block):
    """
			Extracts bout objects based on vertex locations.

			Args:
					gui (GUIClass)
					block (Block): custom class object holding vertex locations
	"""
    # Get minimum bout duration
    dur_thresh = int(gui.dur_thresh_E.get())

    # Return if insufficient number of vertices supplied
    verts = block.vertices
    if verts == None or len(verts) < 2:
        return

    if gui.count_partial_BV.get():
        # Handle first bout
        if verts[0].index > dur_thresh:
            if verts[0].vert_type == 0:  # Start of off-bout
                block.bouts.append(niq_classes.Bout(gui, block.start, verts[0].index, 1))
                block.on_count += 1
            elif verts[0].vert_type == 1:  # Start of on-bout
                block.bouts.append(niq_classes.Bout(gui, block.start, verts[0].index, 0))
                block.off_count += 1

    # Acquire full bouts
    for i, cur_vert in enumerate(verts[:-1]):
        cur_type = cur_vert.vert_type
        block.bouts.append(niq_classes.Bout(gui, cur_vert.index, verts[i + 1].index, cur_type))

        if cur_type == 0:
            block.off_count += 1
        elif cur_type == 1:
            block.on_count += 1

    if gui.count_partial_BV.get():
        # Handle last bout
        if (block.stop - verts[-1].index) > dur_thresh:
            if verts[-1].vert_type == 0:  # Start of off-bout
                block.bouts.append(niq_classes.Bout(gui, verts[-1].index, block.stop, 0))
                block.off_count += 1
            elif verts[-1].vert_type == 1:  # Start of on-bout
                block.bouts.append(niq_classes.Bout(gui, verts[-1].index, block.stop, 1))
                block.on_count += 1


def get_day_night_pairs(gui, days_list, nights_list):
    """
			Pairs one day block object and one night block object to create one block object representing
			a complete 24 hr period.

			Args:
					gui (GUIClass)
					days_list (list): collection of all day blocks for the current input file
					nights_list (list): collection of all night blocks for the current input file
	"""

    day_night_pairs_list = []

    # Set modifier based on if day or night comes first
    modifier = 1 if days_list[0].start > nights_list[0].start else 0

    # Checks for a night corresponding to day at index i and creates a pair if both are complete
    for i in range(len(days_list)):
        if (i + modifier) >= (len(nights_list)):
            break

        if not days_list[i].partial_day and not nights_list[i + modifier].partial_day:
            day_night_pairs_list.append(niq_classes.Block(gui, days_list[i].start, nights_list[i + modifier].stop, False))

    return day_night_pairs_list


def write_stats(gui, days, nights, day_night_pairs, master_block):
    """
			Calculates and gathers several statistics and subsequently dumps them into the individual
			statistics file and/or the multi-input file statistics file depending on the user's requested
			output.

			Args:
					gui (GUIClass)
					days (BlockGroup): contains every day object and information about the group as a whole
					nights (BlockGroup): contains every night object and information about the group as a whole
					day_night_pairs (BlockGroup): contains every day/night pair object and information about the group as a whole
					master_block (block): block built from the entire input file
	"""

    all_egg_tempers, all_air_tempers = [], []
    master_time_above_temper, master_time_below_temper = 0, 0

    if gui.get_stats_BV.get() or gui.multi_in_stats_BV.get():
        # Compile all egg and air temperatures
        all_egg_tempers += gui.master_df.loc[:, "egg_temper"].tolist()
        all_air_tempers += gui.master_df.loc[:, "air_temper"].tolist()

        # Get time exceeding critical temperatures
        for temper in all_egg_tempers:
            if temper > float(gui.time_above_temper_E.get()):
                master_time_above_temper += gui.time_interval

            if temper < float(gui.time_below_temper_E.get()):
                master_time_below_temper += gui.time_interval

    if gui.get_stats_BV.get():
        out_file = gui.stats_file_E.get()
    elif gui.multi_in_stats_BV.get():
        out_file = gui.multi_in_stats_file_E.get()

    if gui.get_stats_BV.get() or gui.multi_in_stats_BV.get():
        with open(out_file, "a") as stat_summary_file:
            # Used to indictate scope of certain statistics
            qualifier = " (D)," if gui.restrict_search_BV.get() else " (DN),"

            # Print input file name first (remove path)
            if out_file == gui.multi_in_stats_file_E.get():
                header = os.path.basename(os.path.normpath(gui.inFile))
            else:
                header = "Cumulative Statistics"

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
                header += "Time above (minutes) " + gui.time_above_temper_E.get()
            if gui.time_below_temper_BV.get():
                header += "Time below (minutes) " + gui.time_below_temper_E.get()
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

            print(header, end="\n", file=stat_summary_file)

            if len(days.block_list) > 0 and len(nights.block_list) > 0:
                # Set modifier based on if day or night comes first
                modifier = 1 if days.block_list[0].start > nights.block_list[0].start else 0
                full_day_counter = 0

                # Print individual day stats
                for i, cur_day in enumerate(days.block_list):
                    day_row = ""

                    # Check if there are any night blocks left
                    if (i + modifier) >= (len(nights.block_list)):
                        break

                    cur_night = nights.block_list[i + modifier]

                    # Only report on complete days
                    if cur_day.partial_day or cur_night.partial_day:
                        continue

                    # Pull stats from only daytime period if restriction was requested
                    if gui.restrict_search_BV.get():
                        core_block = cur_day
                    else:
                        core_block = day_night_pairs.block_list[full_day_counter]

                    if gui.day_num_BV.get():
                        day_row += f"{full_day_counter + 1},"
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
                        day_row += f"{day_night_pairs.block_list[full_day_counter].time_above_temper},"
                    if gui.time_below_temper_BV.get():
                        day_row += f"{day_night_pairs.block_list[full_day_counter].time_below_temper},"
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
                        day_row += f"{day_night_pairs.block_list[full_day_counter].mean_egg_temper},"
                    if gui.mean_temper_dn_sd_BV.get():
                        day_row += f"{day_night_pairs.block_list[full_day_counter].egg_temper_stdev},"
                    if gui.median_temper_dn_BV.get():
                        day_row += f"{day_night_pairs.block_list[full_day_counter].median_temper},"
                    if gui.min_temper_dn_BV.get():
                        day_row += f"{day_night_pairs.block_list[full_day_counter].min_egg_temper},"
                    if gui.max_temper_dn_BV.get():
                        day_row += f"{day_night_pairs.block_list[full_day_counter].max_egg_temper},"

                    if gui.air_valid:
                        if gui.mean_air_temper_BV.get():
                            day_row += f"{day_night_pairs.block_list[full_day_counter].mean_air_temper},"
                        if gui.mean_air_temper_sd_BV.get():
                            day_row += f"{day_night_pairs.block_list[full_day_counter].air_temper_stdev},"
                        if gui.min_air_temper_BV.get():
                            day_row += f"{day_night_pairs.block_list[full_day_counter].min_air_temper},"
                        if gui.max_air_temper_BV.get():
                            day_row += f"{day_night_pairs.block_list[full_day_counter].max_air_temper},"

                    full_day_counter += 1

                    print(day_row, file=stat_summary_file)

                gui.multi_in_full_day_count += full_day_counter

            multi_file_core = days if gui.restrict_search_BV.get() else master_block

            # Output stats summary for entire input file
            summary_row = ""
            if gui.day_num_BV.get():
                summary_row += f"--,"
            if gui.date_BV.get():
                summary_row += f"ALL DATA,"

            if gui.off_count_BV.get():
                summary_row += f"{multi_file_core.off_count},"
            if gui.off_dur_BV.get():
                summary_row += f"{multi_file_core.mean_off_dur},"
            if gui.off_dur_sd_BV.get():
                summary_row += f"{multi_file_core.off_dur_stdev},"
            if gui.off_dec_BV.get():
                summary_row += f"{multi_file_core.mean_off_dec},"
            if gui.off_dec_sd_BV.get():
                summary_row += f"{multi_file_core.off_dec_stdev},"
            if gui.mean_off_temper_BV.get():
                summary_row += f"{multi_file_core.mean_off_temper},"
            if gui.off_time_sum_BV.get():
                summary_row += f"{multi_file_core.off_time_sum},"

            if gui.on_count_BV.get():
                summary_row += f"{multi_file_core.on_count},"
            if gui.on_dur_BV.get():
                summary_row += f"{multi_file_core.mean_on_dur},"
            if gui.on_dur_sd_BV.get():
                summary_row += f"{multi_file_core.on_dur_stdev},"
            if gui.on_inc_BV.get():
                summary_row += f"{multi_file_core.mean_on_inc},"
            if gui.on_inc_sd_BV.get():
                summary_row += f"{multi_file_core.on_inc_stdev},"
            if gui.mean_on_temper_BV.get():
                summary_row += f"{multi_file_core.mean_on_temper},"
            if gui.on_time_sum_BV.get():
                summary_row += f"{multi_file_core.on_time_sum},"

            if gui.time_above_temper_BV.get():
                summary_row += f"{master_time_above_temper},"
            if gui.time_below_temper_BV.get():
                summary_row += f"{master_time_below_temper},"
            if gui.bouts_dropped_BV.get():
                summary_row += f"{multi_file_core.bouts_dropped},"

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
                summary_row += f"{round(statistics.mean(all_egg_tempers), 3)},"
            if gui.mean_temper_dn_sd_BV.get():
                summary_row += f"{round(statistics.stdev(all_egg_tempers), 3)},"
            if gui.median_temper_dn_BV.get():
                summary_row += f"{statistics.median(all_egg_tempers)},"
            if gui.min_temper_dn_BV.get():
                summary_row += f"{min(all_egg_tempers)},"
            if gui.max_temper_dn_BV.get():
                summary_row += f"{max(all_egg_tempers)},"

            if gui.air_valid:
                if gui.mean_air_temper_BV.get():
                    summary_row += f"{round(statistics.mean(all_air_tempers), 3)},"
                if gui.mean_air_temper_sd_BV.get():
                    summary_row += f"{round(statistics.stdev(all_air_tempers), 3)},"
                if gui.min_air_temper_BV.get():
                    summary_row += f"{min(all_air_tempers)},"
                if gui.max_air_temper_BV.get():
                    summary_row += f"{max(all_air_tempers)},"

            if out_file == gui.multi_in_stats_file_E.get():
                summary_row += "\n\n"

            print(summary_row, file=stat_summary_file)

    # If both stat output options are selected, simply copy the summary
    if gui.get_stats_BV.get() and gui.multi_in_stats_BV.get():
        with open(gui.stats_file_E.get(), "r") as stat_file, open(gui.multi_in_stats_file_E.get(), "a") as multi_file_stats_file:
            print(os.path.basename(os.path.normpath(gui.input_file_E.get())), file=multi_file_stats_file)
            out_lines = stat_file.readlines()
            for line in out_lines[(len(out_lines) - (full_day_counter + 2)) : len(out_lines)]:
                multi_file_stats_file.write(line)

            print("\n\n", file=multi_file_stats_file)

    if not gui.get_stats_BV.get():
        return

    # Report information on individual bouts
    with open(gui.stats_file_E.get(), "a") as stats_file:
        print("\n\nIndividual Bout Stats", file=stats_file)

        indi_header = (
            "Date,Bout Type,Start Time,End Time,Start Data Point,End Data Point,Duration (min),Egg Temp Change,Start Egg Temp,End Egg Temp,Mean Egg Temp,"
        )

        if gui.air_valid:
            indi_header += "Start Air Temp, End Air Temp, Mean Air Temp"

        print(indi_header, file=stats_file)

        # If restricted, take only bouts from daytime periods, else take all bouts
        bouts = []
        if gui.restrict_search_BV.get():
            bouts += [bout for day in days.block_list for bout in day.bouts]
        else:
            bouts = master_block.bouts

        cur_date = ""
        for bout in bouts:
            row = ""
            # Print date if it is the first row corresponding to this date
            this_date = extract_date(gui.master_df.loc[bout.start, "date_time"])
            row += "," if this_date == cur_date else f"{this_date},"
            cur_date = this_date

            row += "Off," if bout.bout_type == 0 else "On,"

            row += (
                f"{extract_time(gui.master_df.loc[bout.start, 'date_time'])},"
                + f"{extract_time(gui.master_df.loc[bout.stop, 'date_time'])},"
                + f"{gui.master_df.loc[bout.start, 'data_point']},"
                + f"{gui.master_df.loc[bout.stop, 'data_point']},"
                + f"{bout.dur},"
                + f"{bout.temper_change},"
                + f"{gui.master_df.loc[bout.start, 'egg_temper']},"
                + f"{gui.master_df.loc[bout.stop, 'egg_temper']},"
                + f"{bout.mean_egg_temper},"
            )

            if gui.air_valid:
                row += f"{gui.master_df.loc[bout.start, 'air_temper']},{gui.master_df.loc[bout.stop, 'air_temper']},{bout.mean_air_temper},"

            print(row, end="\n", file=stats_file)

        print("\n\n", file=stats_file)


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

    hover = HoverTool(tooltips=[("Data Point", "$x{int}"), ("Temperature", "$y")])

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
        y_min = min(y_min, master_df["adj_temper"].min())
        y_max = max(y_max, master_df["adj_temper"].max())

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
                location=int(gui.master_df.loc[day.start, "data_point"]),
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
        adj_array = master_df["adj_temper"]
        if gui.smooth_status_IV.get():
            adj_array = smooth_series(radius, adj_array)

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
    if select_mode:
        data = {"x": [], "y": []}

        # Plot original vertices if provided
        if ori_verts:
            # FLAG Always plots as egg_temper even when plot shows egg - air
            data = {"x": [vert.index for vert in ori_verts], "y": [vert.egg_temper for vert in ori_verts]}
    else:
        # Append vertex info to table
        verts = get_verts_from_master_df(master_df)
        data = {"x": [vert.index for vert in verts], "y": [vert.egg_temper for vert in verts]}

    src = ColumnDataSource(data)
    columns = [TableColumn(field="x", title="Transition Data Point"), TableColumn(field="y", title="Egg Temperature")]

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
    state_changed = int_states.diff().apply(abs).astype(bool)
    state_changed.iloc[0] = False

    # Extract indices of rows where the state changes
    vert_indices = master_df[state_changed].index.tolist()

    # Create and append verticies
    master_array = df_to_array(master_df)
    cur_state = master_array[0, 6]
    vertices = []
    for index in vert_indices:
        row = master_df.loc[index]
        vertices.append(niq_classes.Vertex(index, row["egg_temper"], int(row["bout_state"] == "on")))

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
    for row, state in enumerate(master_array[:, 6]):
        if state == cur_state:
            count += 1
        elif count >= dur_thresh:
            last_count = count
            count = 0
            cur_state = state
        elif count < dur_thresh:
            cur_state = abs(cur_state - 1)
            master_array[row - count - 2 : row + 1, 6] = cur_state
            bouts_dropped_locs.add(row)
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


def get_datetime(gui, line):
    """
			Creates datetime object from date/time cell in the input file.

			Args:
					line (str): text from date/time cell
	"""

    print_file_name = "File: " + os.path.basename(os.path.normpath(gui.input_file_E.get())) + " \n\n"

    try:
        time_search = re.search(r"(\d+):(\d+)", line[gui.date_time_col])
        date_search = re.search(r"(\d+)\/(\d+)\/(\d+)", line[gui.date_time_col])

        if not time_search:
            messagebox.showerror(
                "Time Format Error", (print_file_name + "No time found for data point " + line[gui.data_point_col] + ".  Time should be in HH:MM format.")
            )
            print(line)
            return False

        if not date_search:
            messagebox.showerror(
                "Date Format Error", (print_file_name + "No date found for data point " + line[gui.data_point_col] + ".  Date should be in MM/DD/YYYY format.")
            )
            return False

        hour, minute = int(time_search.group(1)), int(time_search.group(2))
        month, day, year = int(date_search.group(1)), int(date_search.group(2)), int(date_search.group(3))

        datetime_ = datetime.datetime(year, month, day, hour, minute)
        return datetime_
    except:
        messagebox.showerror(
            "Date/Time Error", "".join((print_file_name, "Unknown error while processing date/time column. Ensure input file is in the correct format."))
        )
        return False


def list_to_gen(list_):
    for item in list_:
        yield item


def add_states(df, array=None, verts=None, states=None):
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
        if array:
            array = np.hstack((array, states.reshape(states.shape[0], 1)))

    # Convert "bout_state" column of df to numpy array
    if array:
        np_states = df.loc[:, "bout_state"].replace(["off", "on", "None"], [0, 1, 2]).to_numpy()
        array = np.hstack((array, np_states.reshape(len(df), 1)))
        return array, df

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
