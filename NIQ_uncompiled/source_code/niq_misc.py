import datetime
import os
import re
import statistics
import datetime
import time

import numpy as np
from bokeh.io import reset_output
from bokeh.layouts import column, widgetbox
from bokeh.models import HoverTool, PointDrawTool, Span
from bokeh.models.widgets import DataTable, TableColumn
from bokeh.plotting import ColumnDataSource, figure, output_file, show
from screeninfo import get_monitors
from tkinter import messagebox

import niq_classes

def extract_time(date_time_cell):
	"""
		Pulls time out of cell containing date and time (MM/DD/YYYY HH:MM)

		Args:
			date_time_cell (string): input file cell containing the date and time string to be extracted from
	"""

	return re.search("(\d+:\d+)", date_time_cell).group(1)
	
def extract_date(date_time_cell):
	"""
		Pulls date out of cell containing date and time (MM/DD/YYYY HH:MM)

		Args:
			date_time_cell (string): input file cell containing the date and time string to be extracted from
	"""

	return re.search("(\d+\/\d+\/\d+)", date_time_cell).group(1)
	
def check_time_in_daytime(day_start, night_start, time):
	"""
		Checks if a given time is inside of user-provided daytime period.

		Args:
			day_start (string): time considered the start of daytime
			night_start (string): time considered the end of daytime
			time (string): time being analyzed
	"""

	day = re.search("(\d+)(:)(\d+)", day_start)
	day_float = float(day.group(1)) + (float(day.group(3)) / 60)

	night = re.search("(\d+)(:)(\d+)", night_start)
	night_float = float(night.group(1)) + (float(night.group(3)) / 60)
	
	cur_time = re.search("(\d+)(:)(\d+)", time)
	cur_time_float = float(cur_time.group(1)) + (float(cur_time.group(3)) / 60)
	
	if (cur_time_float > night_float) or (cur_time_float < day_float):
		return False
	
	return True
	
def split_days(gui, modifier = 0):
	"""
		Splits the entire data set into individual day and night objects based on user-provided day and
		night start times.

		Args:
			gui (GUIClass)
			modifier (int): amount in minutes to modify given times by
	"""

	def modify_time(ori_time):
		"""
			Slightly offsets the time from the input file to try to address skipping of critical times being 
			searched for. 

			Args:
				ori_time (string): original time (prior to modification)
		"""

		if modifier == 0:
			new_time = ori_time
		else:
			# Convert string time value to datetime format
			search = re.search("((\d+):(\d+))", ori_time)
			hour = int(search.group(2))
			minute = int(search.group(3))
			time = datetime.datetime(1, 1, 1, hour, minute, 0)
			
			# Add modifer and strip unnecessary characters
			new_time = (time + datetime.timedelta(minutes = modifier))
			new_time = str(new_time)[11:-3]
			if new_time[0] == "0":
				new_time = new_time[1:]

		return (" " + new_time.strip())
		
	days_list, nights_list = [], []

	reached_end = False
	day_start = modify_time(gui.day_start_E.get())
	night_start = modify_time(gui.night_start_E.get())
	day_dur = get_day_dur(day_start, night_start)
	night_dur = (1440 - day_dur)
	day_interval = (1440 / gui.time_interval)
	day_start_index = -1
	night_start_index = -1
	
	# Look for first day or night
	for i in range(0, len(gui.master_list)):
		# If day_start found before night_start
		if re.search(day_start, gui.master_list[i][gui.date_time_col]):
			# Set start of first day to this index
			day_start_index = i
			# Set start of first night to day index + duration of daytime
			night_start_index = (i + (day_dur / gui.time_interval))
			# Check if this sets night_start_index past length of gui.master_list
			if night_start_index > (len(gui.master_list) - 1):
				reached_end = True
				night_start_index = (len(gui.master_list) - 1)
				days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, True))
				
			break
		# If night_start found before day_start
		elif re.search(night_start, gui.master_list[i][gui.date_time_col]):
			# Set start of first night to this index
			night_start_index = i
			# Set start of first day to night index + duration of nighttime
			day_start_index = (i + (night_dur / gui.time_interval))
			# Check if this sets day_start_index past length of gui.master_list
			if day_start_index > (len(gui.master_list) - 1):
				reached_end = True
				day_start_index = (len(gui.master_list) - 1)
				
			break
	
	# Check if data starts at night and process to achieve uniformity going into following while `
	# Catch partial day at start of gui.master_list
	if night_start_index < day_start_index:
		days_list.append(niq_classes.Block(gui, 0, night_start_index - 1, True))
		nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, reached_end))
		night_start_index += day_interval
	# Catch partial night at start of gui.master_list
	elif day_start_index < night_start_index:
		nights_list.append(niq_classes.Block(gui, 0, day_start_index - 1, True))
	# If neither day_start or night_start found, append partial day or night
	elif day_start_index == night_start_index:
		reached_end = True
		if check_time_in_daytime(day_start, night_start, gui.master_list[0][gui.date_time_col]):
			days_list.append(niq_classes.Block(gui, 0, (len(gui.master_list) - 1), True))
		else:
			nights_list.append(niq_classes.Block(gui, 0, (len(gui.master_list) - 1), True))
			
	# Save each day and night as object
	while not reached_end:
		days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, False))
		day_start_index += day_interval
		
		# Make final night stop at end of gui.master_list
		if day_start_index > len(gui.master_list):
			day_start_index = (len(gui.master_list) - 1)
			nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, True))
			reached_end = True
			break
		else:
			nights_list.append(niq_classes.Block(gui, night_start_index, day_start_index - 1, False))
			night_start_index += day_interval
		
		# Make final day stop at end of gui.master_list
		if night_start_index > len(gui.master_list):
			night_start_index = (len(gui.master_list) - 1)
			days_list.append(niq_classes.Block(gui, day_start_index, night_start_index - 1, True))
			reached_end = True

	# Address problem of start time skipping
	if len(days_list) == 0 or len(nights_list) == 0:
		if (modifier + 1) < gui.time_interval:
			days_list.clear()
			nights_list.clear()
			# Recursively call split_days with incremented modifier
			days_list, nights_list = split_days(gui, modifier = (modifier + 1))
		# If still no days or nights found, provide text warning
		elif (gui.time_interval * int(gui.master_array.shape[0])) > 1440:
			if gui.show_warns_BV.get():
				messagebox.showwarning("Warning", 
										("If daytime periods are not being identified correctly, try manually" +
										" setting \"data_time_interval\" variable in the defaultConfig.ini file" +
										" found in the cofig_files folder."))

	return days_list, nights_list	

def get_day_dur(day_start, night_start):
	"""
		Finds the duration of the daytime period specified by the user.

		Args:
			day_start (string): start of daytime period
			night_start (string): end of daytime period
	"""

	day = re.search("(\d+)(:)(\d+)", day_start)
	day_float = float(day.group(1)) + (float(day.group(3)) / 60)
	
	night = re.search("(\d+)(:)(\d+)", night_start)
	night_float = float(night.group(1)) + (float(night.group(3)) / 60)
	
	return ((night_float - day_float) * 60)	
		
def get_master_list(gui, source_file):
	"""
		Creates 2D list from input CSV.  Also performs some gap filling and trimming of unnecessary lines.

		Args:
			gui (GUIClass)
			source_file (string): path to and name of input CSV file
	"""

	pop_indices = []
	
	with open(source_file, "r") as input_csv:
		csv_lines = input_csv.readlines()
	
	master_list = [line.strip().rstrip(",").split(",") for line in csv_lines]
		
	for i, cur_line in enumerate(master_list[:-1]):
		# print("line = ", master_list[i])
		if any(( 
				re.search("\D", master_list[i][gui.data_point_col]),
				not re.search("\d", master_list[i][gui.data_point_col])
				)):
			
			pop_indices.append(i)
		
	for pop_count, index in enumerate(pop_indices):
		master_list.pop(index - pop_count)
	master_list.pop(len(master_list) - 1)

	# Remove extra columns
	master_list = [row[0:4] for row in master_list] if gui.air_valid else [row[0:3] for row in master_list]

	# Delete extra line created as a result of the above for loop		
	del master_list[-1]
	
	# Clear formatting characters if present
	digit_search = re.search("\d+", master_list[0][gui.data_point_col])
	master_list[0][gui.data_point_col] = digit_search.group(0)
	
	return master_list	

def get_master_arr(gui, master_list):
	"""
		Converts the 2D list containing input data to a 2D numpy array. The date/time column is not
		tranfered. Additionally, delta temperature, smoothed delta temperature, and temperature
		change from previous columns are added. Later a state (on or off bout) column is also added.

			Column 0 = data point
			Column 1 = egg temperature
			Column 2 = air temperature (0s if not provided)
			Column 3 = delta temperature (egg temper - air temper)
			Column 4 = smoothed column 3 (just a copy if smoothing radius is 0)
			Column 5 = temperature change from previous

		Args:
			master_list (list of lists): contains the information from the input file being analyzed
	"""

	master_array = np.array(master_list)
	master_array = np.delete(master_array, 1, axis = 1).astype(float)

	# Fill column 3 with 0s if valid air temperatures not provided
	if not gui.air_valid:
		if master_array.shape[1] == 3:
			master_array = np.delete(master_array, 2, axis = 1)

		master_array = np.hstack((master_array.astype(float), np.zeros((master_array.shape[0], 1), dtype = float)))

	try:
		delta_temps = (master_array[:, 1] - master_array[:, 2]).reshape(((master_array.shape[0], 1)))
		master_array = np.hstack((master_array, delta_temps))
	except IndexError:
		gui.air_valid = False
		return get_master_arr(master_list)

	radius = int(gui.smoothing_radius_E.get())
	master_array = np.hstack((master_array, smooth_col(radius, delta_temps)))

	index_range = len(master_list)
	emis_array = np.zeros((index_range, 1))

	for i in range(1, index_range):
		delta = master_array[i, 4] - master_array[i - 1, 4]
		emis_array[i] = delta

	emis_array[0] = emis_array[1]
	master_array = np.hstack((master_array, emis_array))

	return master_array

def get_verts_from_html(gui, in_file):
	"""
		Creates vertex objects from vertices placed by the user in the provided HTML file.

		Args:
			gui (GUIClass)
			in_file (string): path to and name of HTML file containing user-provided vertex locations
	"""
	
	def get_data_points_from_html(gui, in_file):
		"""
			Extracts the corresponding data point for each point placed by the user in the HTML file.

		Args:
			gui (GUIClass)
			in_file (string): path to and name of HTML file containing user-provided vertex locations
		"""

		data_point_list = []
		max_dp = int(gui.master_array[-1, 0])
		min_dp = int(gui.master_array[0, 0])
		
		with open(in_file, "r") as vertex_file:
			vertex_file_lines = vertex_file.readlines()
			
		# Remove superfluous lines of table data if present
		found = False
		with open(in_file, "w") as vertex_file:
			for line in vertex_file_lines:
				if line.find("<div class") == -1:
					# Retain all non-table data containing lines
					vertex_file.write(line)	
				elif not found:
					found = True
					vertex_file.write(line)

		with open(in_file, "r") as cleaned_vertex_file_:
			cleaned_vertex_file = cleaned_vertex_file_.read()
			
		# Gets all data points and temperatures from table
		tokens = re.finditer("((\d+\.)?\d+)</span>", cleaned_vertex_file)
		
		for counter, match in enumerate(tokens):
			if (counter % 2) == 0:
				data_point = round(float(match.group(1)))
				if data_point < min_dp: data_point = min_dp
				if data_point > max_dp: data_point = max_dp
				if data_point not in data_point_list:
					data_point_list.append(data_point)	

		return sorted(data_point_list)

	vertices = []

	vertex_data_points = get_data_points_from_html(gui, in_file)
	for i in range(len(gui.master_list)):
		# Search for gap between index value and corresponding datapoint
		if int(gui.master_list[i][gui.data_point_col]) == int(vertex_data_points[0]):
			# Delta is discrepency between index and data point number
			delta = (vertex_data_points[0] - i)
			break
			
	first_vert_temper = gui.master_list[vertex_data_points[0] - delta][gui.egg_temper_col]
	second_vert_temper = gui.master_list[vertex_data_points[1] - delta][gui.egg_temper_col]
	
	# Determine if first vertex is an offStart or onStart
	vert_type = 0 if first_vert_temper > second_vert_temper else 1
	
	# (flag) may lead to some issues due to invalid assumption
	for data_point in vertex_data_points:
		index = (data_point - delta)
		vertices.append(niq_classes.Vertex(index, gui.master_list[index][gui.egg_temper_col], vert_type))
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

	if len(total_vertices) < 1 or stop_index < total_vertices[0].index or start_index > total_vertices[-1].index:
		return verts_in_range
	
	for i in range(len(total_vertices)):
		if total_vertices[i].index >= start_index:
			left_limit = i
			break
		
	for i in range((len(total_vertices)- 1), -1, -1):
		if total_vertices[i].index <= stop_index:
			right_limit = i
			break
			
	verts_in_range = total_vertices[left_limit:(right_limit + 1)]
	return verts_in_range	
	
def get_bouts(gui, block):
	"""
		Extracts bout objects based on vertex locations.

		Args:
			gui (GUIClass)
			block (Block): custom class object holding vertex locations
	"""

	verts = block.vertices
	if verts == None or len(verts) < 2:
		return
		
	for i, cur_vert in enumerate(verts[:-1]):
		if cur_vert.vert_type == 0:
			block.bouts.append(niq_classes.Bout(gui, cur_vert.index, verts[i + 1].index, 0))
			block.off_count += 1
		elif cur_vert.vert_type == 1:
			block.bouts.append(niq_classes.Bout(gui, cur_vert.index, verts[i + 1].index, 1))
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
		if (i + modifier) < (len(nights_list)):
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
			master_block (block): block build from the entire input file
	"""

	all_egg_tempers, all_air_tempers = [], []
	master_time_above_temper, master_time_below_temper = 0, 0
	
	# Compile all egg and air temperatures
	if gui.get_stats_BV.get() or gui.multi_in_stats_BV.get():
		for line in gui.master_list:
			all_egg_tempers.append(float(line[gui.egg_temper_col]))
			if gui.air_valid:
				all_air_tempers.append(float(line[gui.air_temper_col]))
			else:
				all_air_tempers.append(0)
		
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
				print(os.path.basename(os.path.normpath(gui.inFile)), file = stat_summary_file)
			else:
				print("Day and Cumulative Stats", file = stat_summary_file)
		
			if gui.day_num_BV.get()          :  print("Day Number,", end = "", file = stat_summary_file)
			if gui.date_BV.get()             :  print("Date,", end = "", file = stat_summary_file)
			
			if gui.off_count_BV.get()        :  print("Off-bout Count" + qualifier, end = "", file = stat_summary_file)
			if gui.off_dur_BV.get()          :  print("Mean Off Duration" + qualifier, end = "", file = stat_summary_file)
			if gui.off_dur_sd_BV.get()       :  print("Off Dur StDev" + qualifier, end = "", file = stat_summary_file)
			if gui.off_dec_BV.get()          :  print("Mean Off Temp Drop" + qualifier, end = "", file = stat_summary_file)
			if gui.off_dec_sd_BV.get()       :  print("Off Drop StDev" + qualifier, end = "", file = stat_summary_file)
			if gui.mean_off_temper_BV.get()  :  print("Mean Off-Bout Temp" + qualifier, end = "", file = stat_summary_file)
			if gui.off_time_sum_BV.get()     :  print("Off-Bout Time Sum" + qualifier, end = "", file = stat_summary_file)
			
			if gui.on_count_BV.get()         :  print("On-bout Count" + qualifier, end = "", file = stat_summary_file)
			if gui.on_dur_BV .get()          :  print("Mean On Duration" + qualifier, end = "", file = stat_summary_file)
			if gui.on_dur_sd_BV.get()        :  print("On Dur StDev" + qualifier, end = "", file = stat_summary_file)
			if gui.on_inc_BV.get()           :  print("Mean On Temp Rise" + qualifier, end = "", file = stat_summary_file)
			if gui.on_inc_sd_BV.get()        :  print("On Rise StDev" + qualifier, end = "", file = stat_summary_file)
			if gui.mean_on_temper_BV.get()   :  print("Mean On-Bout Temp" + qualifier, end = "", file = stat_summary_file)
			if gui.on_time_sum_BV.get()      :  print("On-Bout Time Sum" + qualifier, end = "", file = stat_summary_file)
			
			if gui.time_above_temper_BV.get():  print("Time above (minutes)", gui.time_above_temper_E.get(), "(DN),", end = "", file = stat_summary_file)
			if gui.time_below_temper_BV.get():  print("Time below (minutes)", gui.time_below_temper_E.get(), "(DN),", end = "", file = stat_summary_file)
			if gui.bouts_dropped_BV.get()    :  print("Vertices Dropped" + qualifier, end = "", file = stat_summary_file)
			
			if gui.mean_temper_d_BV.get()    :  print("Mean Daytime Egg Temp,", end = "", file = stat_summary_file)
			if gui.mean_temper_d_sd_BV.get() :  print("Day Egg Temp StDev,", end = "", file = stat_summary_file)
			if gui.median_temper_d_BV.get()  :  print("Median Daytime Egg Temp,", end = "", file = stat_summary_file)
			if gui.min_temper_d_BV.get()     :  print("Min Daytime Egg Temp,", end = "", file = stat_summary_file)
			if gui.max_temper_d_BV.get()     :  print("Max Daytime Egg Temp,", end = "", file = stat_summary_file)
			
			if gui.mean_temper_n_BV.get()    :  print("Mean Nighttime Egg Temp,", end = "", file = stat_summary_file)
			if gui.mean_temper_n_sd_BV.get() :  print("Night Egg Temp StDev,", end = "", file = stat_summary_file)
			if gui.median_temper_n_BV.get()  :  print("Median Nighttime Egg Temp,", end = "", file = stat_summary_file)
			if gui.min_temper_n_BV.get()     :  print("Min Nighttime Egg Temp,", end = "", file = stat_summary_file)
			if gui.max_temper_n_BV.get()     :  print("Max Nighttime Egg Temp,", end = "", file = stat_summary_file)
			
			if gui.mean_temper_dn_BV.get()   :  print("Mean Egg Temp (DN),", end = "", file = stat_summary_file)
			if gui.mean_temper_dn_sd_BV.get():  print("Egg Temp StDev (DN),", end = "", file = stat_summary_file)
			if gui.median_temper_dn_BV.get() :  print("Median Egg Temp (DN),", end = "", file = stat_summary_file)
			if gui.min_temper_dn_BV.get()    :  print("Min Egg Temp (DN),", end = "", file = stat_summary_file)
			if gui.max_temper_dn_BV.get()    :  print("Max Egg Temp (DN),", end = "", file = stat_summary_file)
			
			if gui.air_valid:
				if gui.mean_air_temper_BV.get()   :  print("Mean Air Temp (DN),", end = "", file = stat_summary_file)
				if gui.mean_air_temper_sd_BV.get():  print("Air Temp StDev (DN),", end = "", file = stat_summary_file)
				if gui.min_air_temper_BV.get()    :  print("Min Air Temp (DN),", end = "", file = stat_summary_file)
				if gui.max_air_temper_BV.get()    :  print("Max Air Temp (DN),", end = "", file = stat_summary_file)
			
			print("", file = stat_summary_file)
			
			if len(days.block_list) > 0 and len(nights.block_list) > 0:
				# Set modifier based on if day or night comes first
				modifier = 1 if days.block_list[0].start > nights.block_list[0].start else 0
				full_day_counter = 0

				# Print individual day stats
				for i, cur_day in enumerate(days.block_list):	
					if (i + modifier) < (len(nights.block_list)):
						cur_night = nights.block_list[i + modifier]
						if not cur_day.partial_day and not cur_night.partial_day:
							if gui.restrict_search_BV.get():
								core_block = cur_day
							else:
								core_block = day_night_pairs.block_list[full_day_counter]
						
							if gui.day_num_BV.get()          :  print(str(full_day_counter + 1) + ",", end = "", file = stat_summary_file)
							if gui.date_BV.get()             :  print(str(core_block.date) + ",", end = "", file = stat_summary_file)
							
							if gui.off_count_BV.get()        :  print(str(core_block.off_count) + ",", end = "", file = stat_summary_file)
							if gui.off_dur_BV.get()          :  print(str(core_block.mean_off_dur) + ",", end = "", file = stat_summary_file)
							if gui.off_dur_sd_BV.get()       :  print(str(core_block.off_dur_stdev) + ",", end = "", file = stat_summary_file)
							if gui.off_dec_BV.get()          :  print(str(core_block.mean_off_dec) + ",", end = "", file = stat_summary_file)
							if gui.off_dec_sd_BV.get()       :  print(str(core_block.off_dec_stdev) + ",", end = "", file = stat_summary_file)
							if gui.mean_off_temper_BV.get()  :  print(str(core_block.mean_off_temper) + ",", end = "", file = stat_summary_file)
							if gui.off_time_sum_BV.get()     :  print(str(core_block.off_time_sum) + ",", end = "", file = stat_summary_file)
							
							if gui.on_count_BV.get()         :  print(str(core_block.on_count) + ",", end = "", file = stat_summary_file)
							if gui.on_dur_BV .get()          :  print(str(core_block.mean_on_dur) + ",", end = "", file = stat_summary_file)
							if gui.on_dur_sd_BV.get()        :  print(str(core_block.on_dur_stdev) + ",", end = "", file = stat_summary_file)
							if gui.on_inc_BV.get()           :  print(str(core_block.mean_on_inc) + ",", end = "", file = stat_summary_file)
							if gui.on_inc_sd_BV.get()        :  print(str(core_block.on_inc_stdev) + ",", end = "", file = stat_summary_file)
							if gui.mean_on_temper_BV.get()	 :  print(str(core_block.mean_on_temper) + ",", end = "", file = stat_summary_file)
							if gui.on_time_sum_BV.get()      :  print(str(core_block.on_time_sum) + ",", end = "", file = stat_summary_file)
							
							if gui.time_above_temper_BV.get():  print(str(day_night_pairs.block_list[full_day_counter].time_above_temper) + ",",  end = "", file = stat_summary_file)
							if gui.time_below_temper_BV.get():  print(str(day_night_pairs.block_list[full_day_counter].time_below_temper) + ",",  end = "", file = stat_summary_file)
							if gui.bouts_dropped_BV.get()    :  print(str(core_block.bouts_dropped) + ",",  end = "", file = stat_summary_file)
							
							if gui.mean_temper_d_BV.get()    :  print(str(cur_day.mean_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.mean_temper_d_sd_BV.get() :  print(str(cur_day.egg_temper_stdev) + ",", end = "", file = stat_summary_file)
							if gui.median_temper_d_BV.get()  :  print(str(cur_day.median_temper) + ",", end = "", file = stat_summary_file)
							if gui.min_temper_d_BV.get()     :  print(str(cur_day.min_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.max_temper_d_BV.get()     :  print(str(cur_day.max_egg_temper) + ",", end = "", file = stat_summary_file)
							
							if gui.mean_temper_n_BV.get()    :  print(str(cur_night.mean_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.mean_temper_n_sd_BV.get() :  print(str(cur_night.egg_temper_stdev) + ",", end = "", file = stat_summary_file)
							if gui.median_temper_n_BV.get()  :  print(str(cur_night.median_temper) + ",", end = "", file = stat_summary_file)
							if gui.min_temper_n_BV.get()     :  print(str(cur_night.min_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.max_temper_n_BV.get()     :  print(str(cur_night.max_egg_temper) + ",", end = "", file = stat_summary_file)
							
							if gui.mean_temper_dn_BV.get()   :  print(str(day_night_pairs.block_list[full_day_counter].mean_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.mean_temper_dn_sd_BV.get():  print(str(day_night_pairs.block_list[full_day_counter].egg_temper_stdev) + ",", end = "", file = stat_summary_file)
							if gui.median_temper_dn_BV.get() :  print(str(day_night_pairs.block_list[full_day_counter].median_temper) + ",", end = "", file = stat_summary_file)
							if gui.min_temper_dn_BV.get()    :  print(str(day_night_pairs.block_list[full_day_counter].min_egg_temper) + ",", end = "", file = stat_summary_file)
							if gui.max_temper_dn_BV.get()    :  print(str(day_night_pairs.block_list[full_day_counter].max_egg_temper) + ",", end = "", file = stat_summary_file)
							
							if gui.air_valid:
								if gui.mean_air_temper_BV.get()   :  print(str(day_night_pairs.block_list[full_day_counter].mean_air_temper) + ",", end = "", file = stat_summary_file)
								if gui.mean_air_temper_sd_BV.get():  print(str(day_night_pairs.block_list[full_day_counter].air_temper_stdev) + ",", end = "", file = stat_summary_file)
								if gui.min_air_temper_BV.get()    :  print(str(day_night_pairs.block_list[full_day_counter].min_air_temper) + ",", end = "", file = stat_summary_file)
								if gui.max_air_temper_BV.get()    :  print(str(day_night_pairs.block_list[full_day_counter].max_air_temper) + ",", end = "", file = stat_summary_file)
								
							full_day_counter += 1
							
							print("", file = stat_summary_file)
				
				gui.milti_in_full_day_count += full_day_counter
			
			multi_file_core = days if gui.restrict_search_BV.get() else master_block
			
			# Output stats summary for entire input file
			if gui.day_num_BV.get()          :  print("--,",  end = "", file = stat_summary_file)
			if gui.date_BV.get()             :  print("ALL DATA,",  end = "", file = stat_summary_file)
			
			if gui.off_count_BV.get()        :  print(str(multi_file_core.off_count) + ",",  end = "", file = stat_summary_file)
			if gui.off_dur_BV.get()          :  print(str(multi_file_core.mean_off_dur) + ",",  end = "", file = stat_summary_file)
			if gui.off_dur_sd_BV.get()       :  print(str(multi_file_core.off_dur_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.off_dec_BV.get()          :  print(str(multi_file_core.mean_off_dec) + ",",  end = "", file = stat_summary_file)
			if gui.off_dec_sd_BV.get()       :  print(str(multi_file_core.off_dec_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.mean_off_temper_BV.get()  :  print(str(multi_file_core.mean_off_temper) + ",",  end = "", file = stat_summary_file)
			if gui.off_time_sum_BV.get()     :  print(str(multi_file_core.off_time_sum) + ",", end = "", file = stat_summary_file)
			
			if gui.on_count_BV.get()         :  print(str(multi_file_core.on_count) + ",",  end = "", file = stat_summary_file)
			if gui.on_dur_BV .get()          :  print(str(multi_file_core.mean_on_dur) + ",",  end = "", file = stat_summary_file)
			if gui.on_dur_sd_BV.get()        :  print(str(multi_file_core.on_dur_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.on_inc_BV.get()           :  print(str(multi_file_core.mean_on_inc) + ",",  end = "", file = stat_summary_file)
			if gui.on_inc_sd_BV.get()        :  print(str(multi_file_core.on_inc_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.mean_on_temper_BV.get()   :  print(str(multi_file_core.mean_on_temper) + ",",  end = "", file = stat_summary_file)
			if gui.on_time_sum_BV.get()      :  print(str(multi_file_core.on_time_sum) + ",", end = "", file = stat_summary_file)
			
			if gui.time_above_temper_BV.get():  print(str(master_time_above_temper) + ",",  end = "", file = stat_summary_file)
			if gui.time_below_temper_BV.get():  print(str(master_time_below_temper) + ",",  end = "", file = stat_summary_file)
			if gui.bouts_dropped_BV.get()    :  print(str(multi_file_core.bouts_dropped) + ",",  end = "", file = stat_summary_file)
			
			if gui.mean_temper_d_BV.get()    :  print(str(days.mean_egg_temper) + ",",  end = "", file = stat_summary_file)
			if gui.mean_temper_d_sd_BV.get() :  print(str(days.egg_temper_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.median_temper_d_BV.get()  :  print(str(days.median_temper) + ",",  end = "", file = stat_summary_file)
			if gui.min_temper_d_BV.get()     :  print(str(days.min_egg_temper) + ",",  end = "", file = stat_summary_file)
			if gui.max_temper_d_BV.get()     :  print(str(days.max_egg_temper) + ",",  end = "", file = stat_summary_file)

			if gui.mean_temper_n_BV.get()    :  print(str(nights.mean_egg_temper) + ",",  end = "", file = stat_summary_file)
			if gui.mean_temper_n_sd_BV.get() :  print(str(nights.egg_temper_stdev) + ",",  end = "", file = stat_summary_file)
			if gui.median_temper_n_BV.get()  :  print(str(nights.median_temper) + ",",  end = "", file = stat_summary_file)
			if gui.min_temper_n_BV.get()     :  print(str(nights.min_egg_temper) + ",",  end = "", file = stat_summary_file)
			if gui.max_temper_n_BV.get()     :  print(str(nights.max_egg_temper) + ",",  end = "", file = stat_summary_file)
			
			if gui.mean_temper_dn_BV.get()   :  print(str(round(statistics.mean(all_egg_tempers), 3)) + ",",  end = "", file = stat_summary_file)
			if gui.mean_temper_dn_sd_BV.get():  print(str(round(statistics.stdev(all_egg_tempers), 3)) + ",",  end = "", file = stat_summary_file)
			if gui.median_temper_dn_BV.get() :  print(str(statistics.median(all_egg_tempers)) + ",",  end = "", file = stat_summary_file)
			if gui.min_temper_dn_BV.get()    :  print(str(min(all_egg_tempers)) + ",",  end = "", file = stat_summary_file)
			if gui.max_temper_dn_BV.get()    :  print(str(max(all_egg_tempers)) + ",",  end = "", file = stat_summary_file)
			
			if gui.air_valid:
				if gui.mean_air_temper_BV.get()   :  print(str(round(statistics.mean(all_air_tempers), 3)) + ",",  end = "", file = stat_summary_file)
				if gui.mean_air_temper_sd_BV.get():  print(str(round(statistics.stdev(all_air_tempers), 3)) + ",",  end = "", file = stat_summary_file)
				if gui.min_air_temper_BV.get()    :  print(str(min(all_air_tempers)) + ",",  end = "", file = stat_summary_file)
				if gui.max_air_temper_BV.get()    :  print(str(max(all_air_tempers)) + ",",  end = "", file = stat_summary_file)
			
			if out_file == gui.multi_in_stats_file_E.get():
				print("\n\n", file = stat_summary_file)
	
	# If both stat output options are selected, simply copy the summary
	if gui.get_stats_BV.get() and gui.multi_in_stats_BV.get():
		with open(gui.stats_file_E.get(), "r") as stat_file:
			with open(gui.multi_in_stats_file_E.get(), "a") as multi_file_stats_file:
				print(os.path.basename(os.path.normpath(gui.input_file_E.get())), file = multi_file_stats_file)
				outLines = stat_file.readlines()
				for line in outLines[(len(outLines) - (full_day_counter + 2)):len(outLines)]:
					multi_file_stats_file.write(line)
					
				print("\n\n", file = multi_file_stats_file)
	
	if not gui.get_stats_BV.get(): 
		return
		
	with open(gui.stats_file_E.get(), "a") as stats_file:
		print("\n\n", "Individual Bout Stats", file = stats_file)
		print("Date,Bout Type,Start Time,End Time,Start Data Point,End Data Point,Duration (min)," +
			   "Egg Temp Change,Start Egg Temp,End Egg Temp,Mean Egg Temp,", end = "", file = stats_file)

		if gui.air_valid:
			print("Start Air Temp, End Air Temp, Mean Air Temp", end = "", file = stats_file)
		
		print("", file = stats_file)
			
		if gui.restrict_search_BV.get():
			for day in days.block_list:
				first_bout = True
				print(day.date + ",", end = "", file = stats_file)

				for bout in day.bouts:
					# First bout in day must be printed differently due to presence of date
					first_bout = False if first_bout else print(",", end = "", file = stats_file)
						
					if bout.bout_type == 0:
						print("Off" + ",", end = "", file = stats_file)
					else:
						print("On" + ",", end = "", file = stats_file)
						
					print(extract_time(gui.master_list[bout.start][gui.date_time_col]) + "," + 
						   extract_time(gui.master_list[bout.stop][gui.date_time_col]) + ",", end = "", file = stats_file)
						   
					print(gui.master_list[bout.start][gui.data_point_col] + "," + 
						   gui.master_list[bout.stop][gui.data_point_col] + ",", end = "", file = stats_file)

					print(str(bout.dur) + "," + str(bout.temper_change) + ",", end = "", file = stats_file)
					print(gui.master_list[bout.start][gui.egg_temper_col].strip() + "," + 
						   gui.master_list[bout.stop][gui.egg_temper_col].strip() + "," + 
						   str(bout.mean_egg_temper) + ",", end = "", file = stats_file)
					
					if gui.air_valid:
						print(gui.master_list[bout.start][gui.air_temper_col].strip() + "," + gui.master_list[bout.stop][gui.air_temper_col].strip() + "," + str(bout.mean_air_temper) + ",", end = "", file = stats_file)
					
					print("", file = stats_file)
			
			print("\n\n", file = stats_file)
		else:
			if len(master_block.bouts) <= 0:
				return
		
			cur_date = ""
			for bout in master_block.bouts:
				# First bout in day must be printed differently due to presence of date
				if extract_date(gui.master_list[bout.start][gui.date_time_col]) == cur_date:
					print(",", end = "", file = stats_file)
				else:
					cur_date = extract_date(gui.master_list[bout.start][gui.date_time_col])
					print(cur_date + ",", end = "", file = stats_file)
				
				text_ = "Off," if bout.bout_type == 0 else "On,"
				print(text_, end = "", file = stats_file)
					
				print(
						extract_time(gui.master_list[bout.start][gui.date_time_col]) + "," + 
						extract_time(gui.master_list[bout.stop][gui.date_time_col]) + "," +
						gui.master_list[bout.start][gui.data_point_col] + "," + 
						gui.master_list[bout.stop][gui.data_point_col] + "," + 
						str(bout.dur) + "," + str(bout.temper_change) + "," + 
						str(gui.master_list[bout.start][gui.egg_temper_col]).strip() + "," + 
						str(gui.master_list[bout.stop][gui.egg_temper_col]).strip() + "," + 
						str(bout.mean_egg_temper) + ",", end = "", file = stats_file)

				if gui.air_valid:
					print(	
							gui.master_list[bout.start][gui.air_temper_col].strip() + "," +
							gui.master_list[bout.stop][gui.air_temper_col].strip() + "," + 
							str(bout.mean_air_temper) + ",", end = "", file = stats_file
						 )
									
				print("", file = stats_file)
									
			print("\n\n", file = stats_file)

def smooth_col(radius, col):
	"""
		Generates "smoothed" copy of input data by applying a rolling mean of the requested radius.

		Args:
			radius (int): number of values to include in rolling mean 
						  (e.g. radius = 1 means average values i, i-1 and i+1)
	"""

	if radius <= 0: 
		return col
	
	smoothed_arr = np.zeros((col.shape[0], 1), dtype = float)
	for i in range(radius, col.shape[0] - radius):
		sum_ = sum(val for val in col[i - radius: i + radius + 1])
		smoothed_arr[i] = sum_ / ((radius * 2) + 1)

	# Fill in ends
	for i in range(radius):
		smoothed_arr[i] = col[i]
		smoothed_arr[-(i + 1)] = col[-(i + 1)]

	return smoothed_arr

def generate_plot(gui, master_array, days_list, select_mode = False):
	"""
		Uses the Bokeh module to generate an interactive plot for the current input file.

		Args:
			gui (GUIClass):
			master_array (numpy array): contains all of the critical information for plot creation
			days_list (list): simply used to place vertical day delimiting line
			select_mode (bool): generates a modified plot that allows for vertex placement
	"""

	# Clears previous plots from memory
	reset_output()
	
	if not select_mode:
		output_file(gui.plot_file_E.get())
	else:
		output_file(os.path.join(gui.core_dir, "misc_files", "temp_plot.html"))
	
	# Set plot dimensions
	if not gui.manual_plot_dims.get():
		monitor_resolutions = [str(monitor) for monitor in get_monitors()]
		res_search = re.search("(\d+)x(\d+)", monitor_resolutions[0])
		mon_x = int(res_search.group(1))
		mon_y = int(res_search.group(2))
		plot_width = (mon_x - 100)
		plot_height = (mon_y - 200)
	else:
		plot_width = int(gui.plot_dim_x_E.get())
		plot_height = int(gui.plot_dim_y_E.get())
	
	hover = HoverTool(tooltips = [("Data Point", "$x{int}"), ("Temperature", "$y")])

	if gui.plot_title_E.get() != "":
		plot_name = gui.plot_title_E.get()
	else:
		if select_mode:
			plot_name_search = re.search((".*\."), os.path.basename(os.path.normpath(gui.input_file_E.get())))
			plot_name = plot_name_search.group(0)[:-1] if plot_name_search else "Vertex Selection Plot"
		else:
			quary = (gui.plot_file_E.get()[::-1] + "\\")
			search_ = re.search(("[^\\\\|/]*(\\\\|/)"), quary).group(0)[::-1]
			plot_name = search_[1:-5] if ".html" in search_ else search_[1:]

	y_min = float("inf")
	y_max = float("-inf")

	if not (select_mode and gui.air_valid): # Prevents incorrect vertex selection axes
		if gui.plot_egg_BV.get():
			y_min = min(y_min, min(master_array[:, 1]))
			y_max = max(y_max, max(master_array[:, 1]))

	if gui.plot_air_BV.get() and gui.air_valid:
		y_min = min(y_min, min(master_array[:, 2]))
		y_max = max(y_max, max(master_array[:, 2]))

	if gui.plot_delta_BV.get():
		y_min = min(y_min, min(master_array[:, 3]))
		y_max = max(y_max, max(master_array[:, 3]))

	y_min -= 2
	y_max += 2

	# Create core plot
	plot = figure(tools = [hover, "box_select, box_zoom, wheel_zoom, pan, reset, save"],
				x_range = [int(master_array[0, 0]), int(master_array[-1, 0])],
				y_range = [y_min, y_max],
				title = plot_name,
				x_axis_label= "Data Point", y_axis_label = "Temperature (C)", plot_width = plot_width, plot_height = plot_height)
				
	# Add vertical lines delimiting days
	if gui.show_day_markers_BV.get() is True:
		for day in days_list:
			vertical_line = Span(
									location = int(gui.master_list[day.start][gui.data_point_col]), 
									dimension = "height", line_color = gui.day_marker_color.get(),
									line_width = float(gui.day_marker_width_E.get()), line_alpha = 0.4
								)
			
			plot.renderers.extend([vertical_line])

	plot.grid.visible = False if not gui.show_grid_BV.get() else True
	
	if select_mode:
		color_ = "gray"
		alpha_ = 1
	else:
		color_key = {0: gui.off_point_color.get(), 1: gui.on_point_color.get(), 2: "lightgray"}
		color_ = np.vectorize(color_key.get)(master_array[:, 6])
		alpha_key = {0: 1, 1: 1, 2: 1}
		alpha_ = np.vectorize(alpha_key.get)(master_array[:, 6])

	radius = int(gui.smoothing_radius_E.get())
	if gui.air_valid and (gui.plot_air_BV.get() or select_mode):
		if gui.smooth_status_IV.get():
			air_arr = smooth_col(radius, master_array[:, 2]).flatten()
		else:
			air_arr = master_array[:, 2]

		# Plot air temperatures
		air_temper_line = plot.line(
									master_array[:, 0], air_arr, line_width = float(gui.air_line_width_E.get()), 
									color = gui.air_line_color.get(), line_alpha = 1, legend = "Air temperature"
								   )

	if gui.plot_egg_BV.get() and not select_mode:
		if gui.smooth_status_IV.get():
			egg_arr = smooth_col(radius, master_array[:, 1]).flatten()
		else:
			egg_arr = master_array[:, 1]

		# Update legend
		legend_ = "On-bout (egg)" if gui.plot_delta_BV.get() else "On-bout"
		plot.circle(
					master_array[0, 0], egg_arr[0], size = float(gui.on_point_size_E.get()), 
					color = gui.on_point_color.get(), legend = legend_
				   )

		legend_ = "Off-bout (egg)" if gui.plot_delta_BV.get() else "Off-bout"
		plot.circle(
					master_array[0, 0], egg_arr[0], size = float(gui.on_point_size_E.get()), 
					color = gui.off_point_color.get(), legend = legend_
				   )

		# Multi-color bout-connecting lines
		# Will be officially added later
		
		# cur_state = master_array[0, 6]
		# prev_trans = 0
		# trans_locs = []
		# trans_locs.append(0)
		# for line_num, line in enumerate(master_array):
		# 	state = line[6]

		# 	if int(state) != int(cur_state):
		# 		trans_locs.append(line_num)
		# 		prev_trans = line_num
		# 		cur_state = state

		# trans_locs.append(master_array.shape[0])
		# prev_loc = 0
		# color_tup = ("gray", "darkred", "lightgray")
		# for loc in trans_locs[1:]:
		# 	cur_loc = loc + 1 if loc + 1 < master_array.shape[0] else loc
		# 	plot.line(
		# 				master_array[prev_loc:cur_loc, 0], 
		# 				egg_arr[prev_loc:cur_loc],
		# 				line_width = float(gui.bout_line_width_E.get()),
		# 				color = color_tup[int(master_array[prev_loc, 6])]
		# 			 )
		# 	prev_loc = loc
		


		# Plot egg temperatures
		if float(gui.bout_line_width_E.get()) > 0:
			plot.line(
						master_array[:, 0], egg_arr, 
						line_width = float(gui.bout_line_width_E.get()), 
						color = gui.bout_line_color.get()
					 )

		plot.circle(
					master_array[:, 0], egg_arr, 
					size = float(gui.on_point_size_E.get()),
					color = color_,	alpha = alpha_
					)	

	if gui.plot_delta_BV.get() or select_mode:
		delta_col = 4 if gui.smooth_status_IV.get() else 3
		if float(gui.bout_line_width_E.get()) > 0:
			plot.line(
						master_array[:, 0], master_array[:, delta_col], 
						line_width = float(gui.bout_line_width_E.get()), 
						color = gui.bout_line_color.get()
					 )

		if not select_mode and gui.plot_egg_BV.get():
			# Add legend values
			plot.triangle(
						  master_array[0, 0], master_array[0, delta_col], size = float(gui.on_point_size_E.get()), 
						  color = gui.on_point_color.get(), legend = "On-bout (egg - air)"
						 )

			plot.triangle(
						  master_array[0, 0], master_array[0, delta_col], size = float(gui.on_point_size_E.get()), 
						  color = gui.off_point_color.get(), legend = "Off-bout (egg - air)"
						 )

			plot.triangle(
						  master_array[:, 0], master_array[:, delta_col],
						  size = float(gui.on_point_size_E.get()), 
						  color = color_, alpha = alpha_
						 )
		else:
			# Add legend values
			if select_mode:
				plot.circle(master_array[0, 0], master_array[0, delta_col], 
							size = float(gui.on_point_size_E.get()), 
							color = "gray", legend = "Temperature reading"
						   )
			else:
				plot.circle(
							master_array[0, 0], master_array[0, delta_col], 
							size = float(gui.on_point_size_E.get()), 
							color = gui.on_point_color.get(), legend = "On-bout"
						   )

				plot.circle(
							master_array[0, 0], master_array[0, delta_col], 
							size = float(gui.on_point_size_E.get()), 
							color = gui.off_point_color.get(), legend = "Off-bout"
						   )

			plot.circle(
						master_array[:, 0], master_array[:, delta_col], 
						size = float(gui.on_point_size_E.get()), 
						color = color_, alpha = alpha_
					   )	
	
	# Generate table with vertex information
	data = {"x": [], "y": []}

	src = ColumnDataSource(data)
	columns = [
				TableColumn(field = "x", title = "Data Point"),
				TableColumn(field = "y", title = "Temperature")
			  ]
			
	data_table = DataTable(source = src, columns = columns, width = 500, height = 20000)

	if select_mode:
		# Plot vertices as large circles in select mode
		renderer = plot.circle(
								"x", "y", size = float(gui.on_point_size_E.get()), color = "red", 
								fill_alpha = 0.8, legend = "Incubation State Change", source = src
							  )
		
		draw_tool = PointDrawTool(renderers = [renderer], empty_value = 1)
		plot.add_tools(draw_tool)
		plot.toolbar.active_drag = draw_tool

	# Get size/width settings from GUI
	plot.title.text_font_size = (gui.title_font_size_E.get() + "pt")
	plot.axis.axis_label_text_font_size  = (gui.axis_title_font_size_E.get() + "pt")
	plot.axis.major_label_text_font_size  = (gui.axis_label_font_size_E.get() + "pt")	
	plot.axis.major_tick_line_width = int(gui.axis_tick_size_E.get())
	plot.axis.minor_tick_line_width = int(gui.axis_tick_size_E.get())
	plot.axis.major_tick_out = int(gui.axis_tick_size_E.get())
	plot.axis.minor_tick_out = int(gui.axis_tick_size_E.get())

	plot.legend.label_text_font_size = (gui.legend_font_size_E.get() + "pt")
	plot.legend.click_policy = "hide"
	plot.legend.location = gui.legend_loc.get()
	plot.background_fill_color = None
	plot.border_fill_color = None
			
	show(column(plot, widgetbox(data_table)))
	# show(plot)

def get_verts_from_master_arr(master_array):
	"""
		Extracts vertex objects based on state transitions in master_array.

		Args:
			master_array (numpy array)
	"""

	cur_state = master_array[0, 6]
	vertices = []
	
	for index, row in enumerate(master_array[:]):
		if row[6] != cur_state:
			cur_state = row[6]
			vertices.append(niq_classes.Vertex(index, row[1], cur_state))
			
	return vertices

def replace_entry(entry, new_value):
	entry.delete(0, "end")
	entry.insert(0, new_value)

def filter_by_dur(master_array, dur_thresh):
	"""
		Purges the master array of state clusters failing to meet a given duration threshold.

		Args:
			master_array (numpy array)
			dur_thresh (int): minimum duration for a cluster of state values to not be erased
	"""

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
			master_array[row - count - 2:row + 1, 6] = cur_state
			bouts_dropped_locs.add(row)
			count += last_count
			
	return master_array, bouts_dropped_locs

def get_novel_name(entry, core_name):
	"""
		Incriments an identificaiton number until a nonexistant file name is found.

		Args:
			entry (tk.Entry): entry box being updated
			core_name (string): base file name to be used, "NUM" must be present in the string
								as this is where the identification number is placed.
	"""

	num_loc = core_name.find("NUM")
	if num_loc == -1:
		return
		
	before_num = core_name[:num_loc]
	after_num = core_name[num_loc + 3:]

	i = 1
	while os.path.exists(entry.get()):
		replace_entry(entry, (before_num + str(i) + after_num))
		i += 1

def extract_in_files(in_file_string):
	"""
		Parses sting of paths for individual input files.

		Args:
			in_file_string (string): collection of paths
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
			line (string): text from date/time cell
	"""

	print_file_name = ("File: " + os.path.basename(os.path.normpath(gui.input_file_E.get())) + " \n\n")

	try:
		time_search = re.search("(\d+):(\d+)", line[gui.date_time_col])
		date_search = re.search("(\d+)\/(\d+)\/(\d+)", line[gui.date_time_col])

		if not time_search:
			messagebox.showerror("Time Format Error", 
			(print_file_name + "No time found for data point " + line[gui.data_point_col] + ".  Time should be in HH:MM format."))
			return False
		
		if not date_search:
			messagebox.showerror("Date Format Error", 
			(print_file_name + "No date found for data point " + line[gui.data_point_col] + ".  Date should be in MM/DD/YYYY format."))
			return False

		hour, minute = int(time_search.group(1)), int(time_search.group(2))
		month, day, year = int(date_search.group(1)), int(date_search.group(2)), int(date_search.group(3))

		datetime_ = datetime.datetime(year, month, day, hour, minute)
		return datetime_
	except:
		messagebox.showerror("Date/Time Error", 
		"".join((print_file_name, "Unknown error while processing date/time column. Ensure input file is in the correct format.")))
		return False		

def list_to_gen(list_):
	for item in list_:
		yield item