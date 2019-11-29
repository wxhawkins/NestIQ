import datetime, time
import os, sys, subprocess
import configparser
import csv
import re
import statistics

import traceback
import numpy as np
from shutil import copyfile
import tkinter as tk
from tkinter import filedialog, font, messagebox, ttk
from PIL import Image, ImageTk

import niq_misc
from niq_misc import get_novel_name, replace_entry
import niq_classes
import niq_hmm

root = tk.Tk()

STANDARD_FONT = font.Font(size = 10)
HELP_FONT = font.Font(size = 8)
HEADER_FONT = font.Font(size = 12, weight = "bold")
SUBHEADER_FONT = "Helvetica 10 bold"
TITLE_FONT = ("Helvetica", 18)

class GUIClass():
	"""
		Large class storing all information present on the graphical user interface: parameters, file names, 
		output options, etc. This class also stores a lot of critical information not displayed on the user 
		interface as well as many methods for interacting/altering the GUI.
	"""

	def __init__(self):
		# Store core working directory path
		self.core_dir = os.path.normpath(os.getcwd() + os.sep + os.pardir)
		self.init_config()
			
		# Initialize column identities -- currently static
		self.data_point_col = 0
		self.date_time_col = 1
		self.egg_temper_col = 2
		self.air_temper_col = 3
			
		# Variables used for storing information accross multiple input files
		self.multi_file_off_durs     = []
		self.multi_file_off_decs     = []
		self.multi_file_on_durs      = []
		self.milti_in_on_incs        = []
		self.multi_in_day_tempers    = []
		self.multi_in_night_tempers  = []
		self.multi_in_air_tempers    = []
		self.milti_in_full_day_count = 0

		self.master_input = tuple()
		self.input_root = None
		self.time_interval = None
		self.air_valid = True
		self.bouts_dropped_locs = set()

		self.master_array = None
		self.master_hmm = niq_hmm.HMM()
				
		# Configure root
		root.wm_title("NestIQ")
		root.geometry("370x720")
		root.configure(background = "white")
		
		# Create 1 x 30 grid
		for row in range(30):
			root.rowconfigure(row, weight = 1)
			
		root.columnconfigure(0, weight = 1)
		nb = ttk.Notebook(root)
		nb.grid(row = 1, rowspan = 28, columnspan = 1, sticky = "NESW")

		tab1 = ttk.Frame(nb)
		tab3 = ttk.Frame(nb)
		tab4 = ttk.Frame(nb)
		tab2 = ttk.Frame(nb)
		nb.add(tab1, text = "Main")
		nb.add(tab2, text = "Advanced")
		nb.add(tab3, text = "Plot Options")
		nb.add(tab4, text = "Stats Options")
		
		# ----------------------------------------------- Main tab ---------------------------------------------------
		# ----- Header -----
		title_background = tk.Label(tab1, text = "", bg = "red4")
		title_background.grid(row = 0, sticky = "NSEW")
		
		title_L = tk.Label(tab1, text = "NestIQ", fg = "white", bg = "red4", font = TITLE_FONT)
		title_L.grid(row = 0, sticky = "NSW", padx = 10, pady = 5)
				
		help_B = tk.Button(tab1, text = "Help", command = self.help)
		help_B.grid(row = 0, sticky = "NW", padx = 335)
		help_B.configure(width = 4, height = 0)
		help_B["font"] = HELP_FONT

		# ----- Input file -----
		self.input_file_L = tk.Label(tab1, text = "Input file:", font = SUBHEADER_FONT)
		self.input_file_L.grid(row = 1, sticky = "W", padx = 10, pady = (5, 0))
		self.input_file_E = tk.Entry(tab1, width = 33)
		self.input_file_E.grid(row = 1, sticky = "W", padx = 77, pady = (10, 0))
		self.input_file_B = tk.Button(tab1, text = "Browse File", command = (lambda : self.get_input_file_name()))
		self.input_file_B.grid(row = 1, sticky = "W", padx = 285, pady = (10, 0))
		self.input_file_B.configure(background = "white")


		# ----- Output path -----
		output_path_L = tk.Label(tab1, text = "Output path:", font = STANDARD_FONT)
		output_path_L.grid(row = 5, sticky = "W", padx = 10, pady = (15, 20))
		self.out_path_E = tk.Entry(tab1, width = 25)
		self.out_path_E.grid(row = 5, sticky = "W", padx = 94, pady = (15, 20))
		self.out_path_B = tk.Button(tab1, text = "Browse Directory", command = (lambda : self.get_dir(self.out_path_E)))
		self.out_path_B.grid(row = 5, sticky = "W", padx = 255, pady = (15, 20))
		self.out_path_B.configure(background = "white")

		
		# ----- Plot file -----
		self.make_plot_BV = tk.BooleanVar()
		self.plot_CB = tk.Checkbutton(tab1, text = "Generate Plot", variable = self.make_plot_BV, font = STANDARD_FONT)
		self.plot_CB.grid(row = 8, sticky = "W", padx = 10)
		self.plot_file_L = tk.Label(tab1, text = "File name:", font = STANDARD_FONT)
		self.plot_file_E = tk.Entry(tab1, width = 24)
		self.plot_file_E.insert(0, "plot.html")
		self.plot_B = tk.Button(tab1, text = "Browse Directory", command = (lambda : self.get_dir(self.plot_file_E)))
		get_novel_name(self.plot_file_E, "plot(NUM).html")
			
		self.plot_CB.select()
		self.plot_file_L.grid(row = 9, sticky = "W", padx = 32)
		self.plot_file_E.grid(row = 9, sticky = "W", padx = 102)
		self.plot_B.grid(row = 9, sticky = "W", padx = 255)
		self.plot_B.configure(background = "white")

		# ----- Statistics file -----
		self.get_stats_BV = tk.BooleanVar()
		self.stats_CB = tk.Checkbutton(tab1, text = "Output Statistics", variable = self.get_stats_BV, font = STANDARD_FONT)
		self.stats_CB.grid(row = 10, sticky = "NW", padx = 10, pady = (10, 0))
		self.stats_file_L = tk.Label(tab1, text = "File name:", font = STANDARD_FONT)
		self.stats_file_E = tk.Entry(tab1, width = 24)
		self.stats_file_E.insert(0, "stats.csv")
		self.stats_B = tk.Button(tab1, text = "Browse Directory", command = (lambda : self.get_dir(self.stats_file_E)))
		get_novel_name(self.stats_file_E, "stats(NUM).csv")

		self.stats_CB.select()
		self.stats_file_L.grid(row = 11, sticky = "W", padx = 32)
		self.stats_file_E.grid(row = 11, sticky = "W", padx = 102)
		self.stats_B.grid(row = 11, sticky = "W", padx = 255)
		self.stats_B.configure(background = "white")

		# ----- Multi-file statistics file -----
		self.multi_in_stats_BV = tk.BooleanVar()
		self.multi_in_stats_CB = tk.Checkbutton(tab1, text = "Compile Statistics", variable = self.multi_in_stats_BV, font = STANDARD_FONT)
		self.multi_in_stats_CB.grid(row = 12, sticky = "W", padx = 10, pady = (10, 0))
		self.multi_in_stats_file_L = tk.Label(tab1, text = "File name:", font = STANDARD_FONT)
		self.multi_in_stats_file_E = tk.Entry(tab1, width = 24)
		self.multi_in_stats_file_E.insert(0, "multi_file_stats.csv")
		self.multi_in_stats_B = tk.Button(tab1, text = "Browse Directory", command = (lambda : self.get_dir(self.multi_in_stats_file_E)))

		ttk.Separator(tab1, orient = "horizontal").grid(row = 14, sticky = "NSEW", pady = (20, 10))

		# ----- Daytime/nighttime -----
		daytime_L = tk.Label(tab1, text = "Daytime period:                to", font = STANDARD_FONT)
		self.day_start_E = tk.Entry(tab1, width = 7)
		self.night_start_E = tk.Entry(tab1, width = 7)

		daytime_L.grid(row = 19, sticky = "W", padx = 10)
		self.day_start_E.grid(row = 19, sticky = "W", padx = 110)
		self.night_start_E.grid(row = 19, sticky = "W", padx = 190)
		
		self.restrict_search_BV = tk.BooleanVar()
		self.restrict_search_CB = tk.Checkbutton(tab1, text = "Restrict analysis to daytime", variable = self.restrict_search_BV, font = STANDARD_FONT)
		self.restrict_search_CB.grid(row = 21, sticky = "NW", padx = 10, pady = (10, 0))

		# ----- Core algorithm parameters -----
		smoothing_radius_L = tk.Label(tab1, text = "Data smoothing radius:", font = STANDARD_FONT)
		smoothing_radius_L.grid(row = 23, sticky = "W", padx = 10, pady = (30, 0))
		self.smoothing_radius_E = tk.Entry(tab1, width = 5)
		self.smoothing_radius_E.grid(row = 23, sticky = "W", padx = 207, pady = (30, 0))		

		dur_thresh_L = tk.Label(tab1, text = "Duration threshold (data points):", font = STANDARD_FONT)
		dur_thresh_L.grid(row = 24, sticky = "W", padx = 10, pady = 10)
		self.dur_thresh_E = tk.Entry(tab1, width = 5)
		self.dur_thresh_E.grid(row = 24, sticky = "W", padx = 207)

		# Display and retract file entry boxes based on selection status					
		def main_tab_callback(*args):				
			if self.make_plot_BV.get():
				self.plot_file_L.grid(row = 9, sticky = "W", padx = 30)
				self.plot_file_E.grid(row = 9, sticky = "W", padx = 102)
				self.plot_B.grid(row = 9, sticky = "W", padx = 255)
				self.plot_B.configure(background = "white")
			else:
				self.plot_file_L.grid_forget()
				self.plot_file_E.grid_forget()
				self.plot_B.grid_forget()
			
			if self.get_stats_BV.get():
				self.stats_file_L.grid(row = 11, sticky = "W", padx = 32)
				self.stats_file_E.grid(row = 11, sticky = "W", padx = 102)
				self.stats_B.grid(row = 11, sticky = "W", padx = 255)
				self.stats_B.configure(background = "white")
			else:
				self.stats_file_L.grid_forget()
				self.stats_file_E.grid_forget()
				self.stats_B.grid_forget()
				
			if self.multi_in_stats_BV.get():
				self.multi_in_stats_file_L.grid(row = 13, sticky = "W", padx = 32)
				self.multi_in_stats_file_E.grid(row = 13, sticky = "W", padx = 102)
				self.multi_in_stats_B.grid(row = 13, sticky = "W", padx = 255)
				self.multi_in_stats_B.configure(background = "white")
			else:
				self.multi_in_stats_file_E.grid_forget()
				self.multi_in_stats_file_L.grid_forget()
				self.multi_in_stats_B.grid_forget()

		main_tab_callback()
				
		# Establish tracing
		self.make_plot_BV.trace("w", main_tab_callback)
		self.get_stats_BV.trace("w", main_tab_callback)
		self.multi_in_stats_BV.trace("w", main_tab_callback)
		

		# ------------------------------------------------- Advanced tab -------------------------------------------------
		# ----- Header -----
		tab4BG = tk.Label(tab2, text = "", bg = "red4")
		tab4BG.grid(row = 2, sticky = "NSEW")
				
		save_config_B = tk.Button(tab2, text = "Save Settings", command = (lambda : self.save_config()))
		save_config_B.grid(row = 2, sticky = "W", padx = 10, pady = (10, 10))
		save_config_B.configure(background = "white")
		
		load_config_B = tk.Button(tab2, text = "Load Settings", command = (lambda : self.load_config()))
		load_config_B.grid(row = 2, sticky = "W", padx = 97, pady = (10, 10))
		load_config_B.configure(background = "white")
		
		save_defaults_B = tk.Button(tab2, text = "Set as Default", command = (lambda : self.set_defaults()))
		save_defaults_B.grid(row = 2, sticky = "W", padx = 275, pady = (10, 10))
		save_defaults_B.configure(background = "white")

		# ----- Unsupervised learning -----
		UL_train_B = tk.Button(tab2, text ="Unsupervised Learning", command = (lambda : self.unsupervised_learning()))
		UL_train_B.grid(row = 5, sticky = "W", padx = 10, pady = (10, 0))
		UL_train_B.configure(background = "white")

		self.UL_default_BV = tk.BooleanVar()
		self.UL_default_CB = tk.Checkbutton(tab2, text = "Run unsup. learning by defualt", variable = self.UL_default_BV, font = STANDARD_FONT)
		self.UL_default_CB.grid(row = 5, sticky = "NW", padx = 150, pady =(10, 0))

		# ----- Supervised learning -----
		SL_train_B = tk.Button(tab2, text ="Supervised Learning", command = (lambda : self.supervised_learning()))
		SL_train_B.grid(row = 6, sticky = "W", padx = 10, pady = (10, 0))
		SL_train_B.configure(background = "white")

		select_verticies_B = tk.Button(tab2, text = "Select Vertices", command = (lambda : self.select_vertices()))
		select_verticies_B.grid(row = 6, sticky = "W", padx = 133, pady = (10, 0))
		select_verticies_B.configure(background = "white")

		vertex_file_L = tk.Label(tab2, text = "Vertex File:", font = STANDARD_FONT)
		vertex_file_L.grid(row = 10, sticky = "W", padx = 10, pady = (10, 0))
		self.vertex_file_E = tk.Entry(tab2, width = 32)
		self.vertex_file_E.grid(row = 10, sticky = "W", padx = 85, pady = (10, 0))
		vertex_file_B = tk.Button(tab2, text = "Browse File", command = (lambda : self.get_vertex_file(self.vertex_file_E)))
		vertex_file_B.grid(row = 10, sticky = "W", padx = 287, pady = (10, 0))
		vertex_file_B.configure(background = "white")

		# ----- Iniitial probabilities -----
		init_probs_L = tk.Label(tab2, text = "Initial Probabilities:", font = SUBHEADER_FONT)
		init_probs_L.grid(row = 12, sticky = "W", padx = 10, pady = (30, 0))

		ttk.Separator(tab2, orient = "horizontal").grid(row = 13, sticky = "NSEW", pady = (0, 10))

		tk.Label(tab2, text = "Off", font = STANDARD_FONT).grid(row = 14, sticky = "W", padx = 120)
		tk.Label(tab2, text = "On", font = STANDARD_FONT).grid(row = 14, sticky = "W", padx = 220)

		self.init_off_E = tk.Entry(tab2, width = 10)
		self.init_off_E.grid(row = 15, sticky = "W", padx = 120)
		self.init_on_E = tk.Entry(tab2, width = 10)
		self.init_on_E.grid(row = 15, sticky = "W", padx = 220)

		# ----- Transition probabilities -----
		trans_probs_L = tk.Label(tab2, text = "Transition Probabilites:", font = SUBHEADER_FONT)
		trans_probs_L.grid(row = 16, sticky = "W", padx = 10, pady = (20, 0))

		ttk.Separator(tab2, orient = "horizontal").grid(row = 17, sticky = "NSEW", pady = (0, 10))

		x_axis_off_L = tk.Label(tab2, text = "Off", font = STANDARD_FONT)
		x_axis_off_L.grid(row = 18, sticky = "W", padx = 120)
		x_axis_on_L = tk.Label(tab2, text = "On", font = STANDARD_FONT)
		x_axis_on_L.grid(row = 18, sticky = "W", padx = 220)

		y_axis_off_L = tk.Label(tab2, text = "Off", font = STANDARD_FONT)
		y_axis_off_L.grid(row = 19, sticky = "W", padx = 90)
		y_axis_on_L = tk.Label(tab2, text = "On", font = STANDARD_FONT)
		y_axis_on_L.grid(row = 20, sticky = "W", padx = 90)

		self.off_off_trans_E = tk.Entry(tab2, width = 10)
		self.off_off_trans_E.grid(row = 19, sticky = "W", padx = 120)
		self.off_on_trans_E = tk.Entry(tab2, width = 10)
		self.off_on_trans_E.grid(row = 19, sticky = "W", padx = 220)
		self.on_off_trans_E = tk.Entry(tab2, width = 10)
		self.on_off_trans_E.grid(row = 20, sticky = "W", padx = 120)
		self.on_on_trans_E = tk.Entry(tab2, width = 10)
		self.on_on_trans_E.grid(row = 20, sticky = "W", padx = 220)

		# ----- Temperature change distribution -----
		distrib_params_L = tk.Label(tab2, text = "Temperature Change Distribution Parameters:", font = SUBHEADER_FONT)
		distrib_params_L.grid(row = 23, sticky = "W", padx = 10, pady = (20, 0))

		separator = ttk.Separator(tab2, orient = "horizontal")
		separator.grid(row = 24, sticky = "NSEW", pady = (0, 10))

		distrib_mean_L = tk.Label(tab2, text = "Mean", font = STANDARD_FONT)
		distrib_mean_L.grid(row = 25, sticky = "W", padx = 120)
		distrib_stdev_L = tk.Label(tab2, text = "Std. Deviation", font = STANDARD_FONT)
		distrib_stdev_L.grid(row = 25, sticky = "W", padx = 220)


		distrib_off_L = tk.Label(tab2, text = "Off", font = STANDARD_FONT)
		distrib_off_L.grid(row = 26, sticky = "W", padx = 90)
		distrib_on_L = tk.Label(tab2, text = "On", font = STANDARD_FONT)
		distrib_on_L.grid(row = 27, sticky = "W", padx = 90)

		self.off_mean_E = tk.Entry(tab2, width = 10)
		self.off_mean_E.grid(row = 26, sticky = "W", padx = 120)
		self.on_mean_E = tk.Entry(tab2, width = 10)
		self.on_mean_E.grid(row = 27, sticky = "W", padx = 120)
		self.off_stdev_E = tk.Entry(tab2, width = 10)
		self.off_stdev_E.grid(row = 26, sticky = "W", padx = 220)
		self.on_stdev_E = tk.Entry(tab2, width = 10)
		self.on_stdev_E.grid(row = 27, sticky = "W", padx = 220)

		# ----------------------------------------------- Plot Options tab -----------------------------------------------
		# ----- Header -----
		tab3_BG = tk.Label(tab3, text = "", bg = "red4")
		tab3_BG.grid(row = 0, sticky = "NSEW")
		header_title = tk.Label(tab3, text = "NestIQ", fg = "white", bg = "red4", font = ("Helvetica", 18))
		header_title.grid(row = 0, sticky = "NSW", padx = 10, pady = 5)
		
		self.plot_title_L = tk.Label(tab3, text = "Plot title:", font = STANDARD_FONT)
		self.plot_title_L.grid(row = 2, sticky = "W", padx = 10, pady = (5, 10))
		self.plot_title_E = tk.Entry(tab3, width = 30)
		self.plot_title_E.grid(row = 2, sticky = "W", padx = 77, pady = (10, 10))

		# ----- Plot dimensions -----
		plot_dim_L = tk.Label(tab3, text = "Plot dimensions", font = STANDARD_FONT)
		plot_dim_L.grid(row = 4, sticky = "W", padx = 10, pady = (5, 0))
		
		self.manual_plot_dims = tk.IntVar()
		auto_dim_RB = tk.Radiobutton(tab3, text = "Auto", variable = self.manual_plot_dims, value = 0)
		auto_dim_RB.grid(row = 5, sticky = "W", padx = 25)
		man_dim_RB = tk.Radiobutton(tab3, text="Manual", variable = self.manual_plot_dims, value = 1)
		man_dim_RB.grid(row = 6, sticky = "W", padx = 25, pady = (0, 0))
		
		plot_dim_x_L = tk.Label(tab3, text = "x:", font = STANDARD_FONT)
		plot_dim_y_L = tk.Label(tab3, text = "y:", font = STANDARD_FONT)
		plot_dim_x_L.grid(row = 6, sticky = "W", padx = 95)
		plot_dim_y_L.grid(row = 6, sticky = "W", padx = 150)
		self.plot_dim_x_E = tk.Entry(tab3, width = 5)
		self.plot_dim_y_E = tk.Entry(tab3, width = 5)
		self.plot_dim_x_E.grid(row = 6, sticky = "W", padx = 110)
		self.plot_dim_y_E.grid(row = 6, sticky = "W", padx = 165)
		
		# ----- Font sizes -----
		title_font_size_L = tk.Label(tab3, text = "Plot title font size:", font = STANDARD_FONT)
		title_font_size_L.grid(row = 8, sticky = "W", padx = 10, pady = (15, 5))
		self.title_font_size_E = tk.Entry(tab3, width = 5)
		self.title_font_size_E.grid(row = 8, sticky = "W", padx = 140, pady = (15, 5))
		
		axis_title_font_size_L = tk.Label(tab3, text = "Axis title font size:", font = STANDARD_FONT)
		axis_title_font_size_L.grid(row = 9, sticky = "W", padx = 10, pady = 5)
		self.axis_title_font_size_E = tk.Entry(tab3, width = 5)
		self.axis_title_font_size_E.grid(row = 9, sticky = "W", padx = 140, pady = 5)
		
		axis_label_font_size_L = tk.Label(tab3, text = "Axis label font size:", font = STANDARD_FONT)
		axis_label_font_size_L.grid(row = 10, sticky = "W", padx = 10, pady = 5)
		self.axis_label_font_size_E = tk.Entry(tab3, width = 5)
		self.axis_label_font_size_E.grid(row = 10, sticky = "W", padx = 140, pady = 5)
		
		axis_tick_size_L = tk.Label(tab3, text = "Axis tick size:", font = STANDARD_FONT)
		axis_tick_size_L.grid(row = 11, sticky = "W", padx = 10, pady = 5)
		self.axis_tick_size_E = tk.Entry(tab3, width = 5)
		self.axis_tick_size_E.grid(row = 11, sticky = "W", padx = 140, pady = 5)

		legend_font_size_L = tk.Label(tab3, text = "Legend font size:", font = STANDARD_FONT)
		legend_font_size_L.grid(row = 12, sticky = "W", padx = 10, pady = 5)
		self.legend_font_size_E = tk.Entry(tab3, width = 5)
		self.legend_font_size_E.grid(row = 12, sticky = "W", padx = 140, pady = 5)

		tk.Label(tab3, text = "Plot data", font = STANDARD_FONT).grid(row = 4, sticky = "W", padx = 223, pady = (5, 0))

		# ----- Plot data check buttons -----
		self.plot_egg_BV = tk.BooleanVar()
		self.plot_egg_CB = tk.Checkbutton(tab3, text = "Egg", variable = self.plot_egg_BV, font = STANDARD_FONT)
		self.plot_egg_CB.grid(row = 5, sticky = "W", padx = 240)

		self.plot_air_BV = tk.BooleanVar()
		self.plot_air_CB = tk.Checkbutton(tab3, text = "Air", variable = self.plot_air_BV, font = STANDARD_FONT)
		self.plot_air_CB.grid(row = 6, sticky = "W", padx = 240)

		self.plot_delta_BV = tk.BooleanVar()
		self.plot_delta_CB = tk.Checkbutton(tab3, text = "Egg - Air", variable = self.plot_delta_BV, font = STANDARD_FONT)
		self.plot_delta_CB.grid(row = 8, sticky = "NW", padx = 240)

		# ----- Smoothing status -----
		smooth_status_L = tk.Label(tab3, text = "Smoothing status", font = STANDARD_FONT)
		smooth_status_L.grid(row = 9, sticky = "W", padx = 223)
		
		self.smooth_status_IV = tk.IntVar()
		raw_RB = tk.Radiobutton(tab3, text = "Raw", variable = self.smooth_status_IV, value = 0)
		raw_RB.grid(row = 10, sticky = "W", padx = 240)
		smoothed_RB = tk.Radiobutton(tab3, text = "Smoothed", variable = self.smooth_status_IV, value = 1)
		smoothed_RB.grid(row = 11, sticky = "W", padx = 240)

		# ----- Legend location -----
		self.legend_loc = tk.StringVar()
		_legend_loc_options = [ 
								"top_left", "top_center", "top_right", "bottom_left", 
								"bottom_center", "bottom_right", "center_left", "center_right"
							  ]

		tk.Label(tab3, text = "Legend location").grid(row = 12, sticky = "W", padx = 223)
		self.legend_loc_OM = tk.OptionMenu(tab3, self.legend_loc, *_legend_loc_options)
		self.legend_loc_OM.grid(row = 13, sticky = "NW", padx = 240)
		self.legend_loc_OM.config(bg = "white")

		ttk.Separator(tab3, orient = "horizontal").grid(row = 14, sticky = "NSEW", pady = 10)
		
		tk.Label(tab3, text = "Color", font = SUBHEADER_FONT).grid(row = 15, sticky = "NW", padx = (160, 0))
		tk.Label(tab3, text = "Size/Width", font = SUBHEADER_FONT).grid(row = 15, sticky = "NW", padx = (272, 0))
		
		_color_choices = ["pink", "salmon", "red", "darkred", "orangered", "orange", "gold",  "darkkhaki", "beige", "saddlebrown", 
						"yellow", "lime", "greenyellow", "yellowgreen", "olive", "green", "cyan", "aquamarine", "lightskyblue", 
						"blue", "darkblue", "indigo", "darkviolet", "black", "gray", "slategray", "lightgray", "white"]

		self.on_point_color = tk.StringVar()		
		self.off_point_color = tk.StringVar()		
		self.bout_line_color = tk.StringVar()
		self.air_line_color = tk.StringVar()
		self.day_marker_color = tk.StringVar()

		# ----- Plot element sizes/colors -----
		tk.Label(tab3, text = "On-bouts (point):").grid(row = 16, sticky = "NW", padx = (10, 0))
		tk.Label(tab3, text = "Off-bouts (point):").grid(row = 17, sticky = "NW", padx = (10, 0))
		tk.Label(tab3, text = "Bouts (line):").grid(row = 18, sticky = "NW", padx = (10, 0))
		tk.Label(tab3, text = "Air temperature:").grid(row = 19, stick = "NW", padx = (10, 0))
		
		self.on_point_color_OM = tk.OptionMenu(tab3, self.on_point_color, *_color_choices)
		self.on_point_color_OM.grid(row = 16, sticky = "NW", padx = 150)
		self.off_point_color_OM = tk.OptionMenu(tab3, self.off_point_color, *_color_choices)
		self.off_point_color_OM.grid(row = 17, sticky = "NW", padx = 150)
		self.bout_line_color_OM = tk.OptionMenu(tab3, self.bout_line_color, *_color_choices)
		self.bout_line_color_OM.grid(row = 18, sticky = "NW", padx = 150)
		self.air_line_color_OM = tk.OptionMenu(tab3, self.air_line_color, *_color_choices)
		self.air_line_color_OM.grid(row = 19, sticky = "NW", padx = 150)
		self.day_marker_color_OM = tk.OptionMenu(tab3, self.day_marker_color, *_color_choices)
		self.day_marker_color_OM.grid(row = 20, sticky = "NW", padx = 150)
		
		on_point_size_SV = tk.StringVar()
		off_point_size_SV = tk.StringVar()
		self.on_point_size_E = tk.Entry(tab3, textvariable = on_point_size_SV, width = 5)
		self.on_point_size_E.grid(row = 16, sticky = "W", padx = 286)
		tk.Label(tab3, textvariable = off_point_size_SV).grid(row = 17, sticky = "NW", padx = (285, 0))
		self.bout_line_width_E = tk.Entry(tab3, width = 5)
		self.bout_line_width_E.grid(row = 18, sticky = "W", padx = 286)
		self.air_line_width_E = tk.Entry(tab3, width = 5)
		self.air_line_width_E.grid(row = 19, sticky = "W", padx = 286)
		self.day_marker_width_E = tk.Entry(tab3, width = 5)
		self.day_marker_width_E.grid(row = 20, sticky = "W", padx = 286)
		
		self.show_day_markers_BV = tk.BooleanVar()
		self.show_day_markers_CB = tk.Checkbutton(tab3, text = "Day markers:", variable = self.show_day_markers_BV, font = STANDARD_FONT)
		self.show_day_markers_CB.grid(row = 20, sticky = "W", padx = (10, 0), pady = (5, 0))
		
		self.show_grid_BV = tk.BooleanVar()
		self.show_grid_CB = tk.Checkbutton(tab3, text = "Show grid", variable = self.show_grid_BV, font = STANDARD_FONT)
		self.show_grid_CB.grid(row = 21, sticky = "W", padx = (10, 0))	
	
		self.on_point_color.set("black")
		self.off_point_color.set("black")
		self.bout_line_color.set("black")
		self.air_line_color.set("black")
		self.day_marker_color.set("black")	
		
		# Update buttons to display selected color
		def color_menus_callback(*args):
			self.on_point_color_OM.config(bg = self.on_point_color.get())
			self.off_point_color_OM.config(bg = self.off_point_color.get())
			self.bout_line_color_OM.config(bg = self.bout_line_color.get())
			self.air_line_color_OM.config(bg = self.air_line_color.get())
			self.day_marker_color_OM.config(bg = self.day_marker_color.get())

		# Off point size is label that is automatically set equal to on_point_size
		def off_point_size_callback(*args):
			off_point_size_SV.set(str(self.on_point_size_E.get()))
		
		off_point_size_callback()
		
		# Display or retract entry boxes based on selection status
		def plot_setting_CKs_callback(*args):
			if self.show_day_markers_BV.get():
				self.day_marker_color_OM.grid(row = 20, sticky = "NW", padx = 150)
				self.day_marker_width_E.grid(row = 20, sticky = "W", padx = 286)
			else:
				self.day_marker_color_OM.grid_forget()
				self.day_marker_width_E.grid_forget()
		
		# Establish tracing
		self.on_point_color.trace("w", color_menus_callback)
		self.off_point_color.trace("w", color_menus_callback)
		self.bout_line_color.trace("w", color_menus_callback)
		self.air_line_color.trace("w", color_menus_callback)
		self.day_marker_color.trace("w", color_menus_callback)
		self.show_day_markers_BV.trace("w", plot_setting_CKs_callback)
		on_point_size_SV.trace("w", off_point_size_callback)
		
		# --------------------------------------------------- Stat Options tab --------------------------------------------
		# ----- Header -----
		tab4BG = tk.Label(tab4, text = "", bg = "red4")
		tab4BG.grid(row = 2, sticky = "NSEW")

		add_col1_B = tk.Button(tab4, text = "Select Column", command = (lambda : self.toggle_col(col1, "select")))
		add_col1_B.grid(row = 2, sticky = "W", padx = 10, pady = (10, 10))
		add_col1_B.configure(background = "white")
		drop_col1_B = tk.Button(tab4, text = "Deselect", command = (lambda : self.toggle_col(col1, "deselect")))
		drop_col1_B.grid(row = 2, sticky = "W", padx = 100, pady = (10, 10))
		drop_col1_B.configure(background = "white")

		add_col2_B = tk.Button(tab4, text = "Select Column", command = (lambda : self.toggle_col(col2, "select")))
		add_col2_B.grid(row = 2, sticky = "W", padx = 200, pady = (10, 10))
		add_col2_B.configure(background = "white")
		drop_col2_B = tk.Button(tab4, text = "Deselect", command = (lambda : self.toggle_col(col2, "deselect")))
		drop_col2_B.grid(row = 2, sticky = "W", padx = 290, pady = (10, 10))
		drop_col2_B.configure(background = "white")	
		
		self.day_num_BV            = tk.BooleanVar()
		self.date_BV               = tk.BooleanVar()
		self.off_count_BV          = tk.BooleanVar()
		self.off_dur_BV            = tk.BooleanVar()
		self.off_dur_sd_BV         = tk.BooleanVar()
		self.off_dec_BV            = tk.BooleanVar()
		self.off_dec_sd_BV         = tk.BooleanVar()
		self.mean_off_temper_BV    = tk.BooleanVar()
		self.off_time_sum_BV       = tk.BooleanVar()
		self.on_count_BV           = tk.BooleanVar()
		self.on_dur_BV             = tk.BooleanVar()
		self.on_dur_sd_BV          = tk.BooleanVar()
		self.on_inc_BV             = tk.BooleanVar()
		self.on_inc_sd_BV          = tk.BooleanVar()
		self.mean_on_temper_BV     = tk.BooleanVar()
		self.on_time_sum_BV        = tk.BooleanVar()
		self.bouts_dropped_BV      = tk.BooleanVar()
		self.time_above_temper_BV  = tk.BooleanVar()
		self.time_below_temper_BV  = tk.BooleanVar()
		self.mean_temper_d_BV      = tk.BooleanVar()
		self.mean_temper_d_sd_BV   = tk.BooleanVar() 
		self.median_temper_d_BV    = tk.BooleanVar()
		self.min_temper_d_BV       = tk.BooleanVar()
		self.max_temper_d_BV       = tk.BooleanVar()
		self.mean_temper_n_BV      = tk.BooleanVar()
		self.mean_temper_n_sd_BV   = tk.BooleanVar()
		self.median_temper_n_BV    = tk.BooleanVar()
		self.min_temper_n_BV       = tk.BooleanVar()
		self.max_temper_n_BV       = tk.BooleanVar()
		self.mean_temper_dn_BV     = tk.BooleanVar()
		self.mean_temper_dn_sd_BV  = tk.BooleanVar()
		self.median_temper_dn_BV   = tk.BooleanVar()
		self.min_temper_dn_BV      = tk.BooleanVar()
		self.max_temper_dn_BV      = tk.BooleanVar()
		self.mean_air_temper_BV    = tk.BooleanVar()
		self.mean_air_temper_sd_BV = tk.BooleanVar()
		self.min_air_temper_BV     = tk.BooleanVar()
		self.max_air_temper_BV     = tk.BooleanVar()

		self.day_num_CB            = tk.Checkbutton(tab4, text = "Day Number", variable = self.day_num_BV)
		self.date_CB               = tk.Checkbutton(tab4, text = "Date", variable = self.date_BV)
		self.off_count_CB          = tk.Checkbutton(tab4, text = "Off-Bout Count", variable = self.off_count_BV)
		self.off_dur_CB            = tk.Checkbutton(tab4, text = "Mean Off-Bout Duration", variable = self.off_dur_BV)
		self.off_dur_sd_CB         = tk.Checkbutton(tab4, text = "Off-Bout Duration StDev", variable = self.off_dur_sd_BV)
		self.off_dec_CB            = tk.Checkbutton(tab4, text = "Mean Off-Bout Temp Drop", variable = self.off_dec_BV)
		self.off_dec_sd_CB         = tk.Checkbutton(tab4, text = "Off-Bout Temp Drop StDev", variable = self.off_dec_sd_BV)
		self.mean_off_temper_CB    = tk.Checkbutton(tab4, text = "Mean Off-Bout Temp", variable  = self.mean_off_temper_BV)
		self.off_time_sum_CB       = tk.Checkbutton(tab4, text = "Off-Bout Time Sum", variable = self.off_time_sum_BV)
		self.on_count_CB           = tk.Checkbutton(tab4, text = "On-Bout Count", variable = self.on_count_BV)
		self.on_dur_CB             = tk.Checkbutton(tab4, text = "Mean On-Bout Duration", variable = self.on_dur_BV)
		self.on_dur_sd_CB          = tk.Checkbutton(tab4, text = "On-Bout Duration StDev", variable = self.on_dur_sd_BV)
		self.on_inc_CB             = tk.Checkbutton(tab4, text = "Mean On-Bout Temp Rise", variable = self.on_inc_BV)
		self.on_inc_sd_CB          = tk.Checkbutton(tab4, text = "On-Bout Temp Rise StDev", variable = self.on_inc_sd_BV)
		self.mean_on_temper_CB     = tk.Checkbutton(tab4, text = "Mean On-Bout Temp", variable = self.mean_on_temper_BV)
		self.on_time_sum_CB        = tk.Checkbutton(tab4, text = "On-Bout Time Sum", variable = self.on_time_sum_BV)
		self.bouts_dropped_CB      = tk.Checkbutton(tab4, text = "Vertices Dropped", variable = self.bouts_dropped_BV)
		self.time_above_temper_CB  = tk.Checkbutton(tab4, text = "Time above             degrees", variable = self.time_above_temper_BV)
		self.time_below_temper_CB  = tk.Checkbutton(tab4, text = "Time under             degrees", variable = self.time_below_temper_BV)
		self.mean_temper_d_CB      = tk.Checkbutton(tab4, text = "Mean Temperature (D)", variable = self.mean_temper_d_BV)
		self.mean_temper_d_sd_CB   = tk.Checkbutton(tab4, text = "Mean Temp StDev (D)", variable = self.mean_temper_d_sd_BV)
		self.median_temper_d_CB    = tk.Checkbutton(tab4, text = "Median Temp (D)", variable = self.median_temper_d_BV)
		self.min_temper_d_CB       = tk.Checkbutton(tab4, text = "Minimum Temp (D)", variable = self.min_temper_d_BV)
		self.max_temper_d_CB       = tk.Checkbutton(tab4, text = "Maximum Temp (D)", variable = self.max_temper_d_BV)
		self.mean_temper_n_CB      = tk.Checkbutton(tab4, text = "Mean Temperature (N)", variable = self.mean_temper_n_BV)
		self.mean_temper_n_sd_CB   = tk.Checkbutton(tab4, text = "Mean Temp StDev (N)", variable = self.mean_temper_n_sd_BV)
		self.median_temper_n_CB    = tk.Checkbutton(tab4, text = "Median Temp (N)", variable = self.median_temper_n_BV)
		self.min_temper_n_CB       = tk.Checkbutton(tab4, text = "Minimum Temp (N)", variable = self.min_temper_n_BV)
		self.max_temper_n_CB       = tk.Checkbutton(tab4, text = "Maximum Temp (N)", variable = self.max_temper_n_BV)
		self.mean_temper_dn_CB     = tk.Checkbutton(tab4, text = "Mean Temperature (DN)", variable = self.mean_temper_dn_BV)
		self.mean_temper_dn_sd_CB  = tk.Checkbutton(tab4, text = "Mean Temp StDev (DN)", variable = self.mean_temper_dn_sd_BV)
		self.median_temper_db_CB   = tk.Checkbutton(tab4, text = "Median Temp (DN)", variable = self.median_temper_dn_BV)
		self.min_temper_dn_CB      = tk.Checkbutton(tab4, text = "Minimum Temp (DN)", variable = self.min_temper_dn_BV)
		self.max_temper_dn_CB      = tk.Checkbutton(tab4, text = "Maximum Temp (DN)", variable = self.max_temper_dn_BV)
		self.mean_air_temper_CB    = tk.Checkbutton(tab4, text = "Mean Air Temp (DN)", variable = self.mean_air_temper_BV)
		self.mean_air_temper_sd_CB = tk.Checkbutton(tab4, text = "Mean Air Temp StDev (DN)", variable = self.mean_air_temper_sd_BV)
		self.min_air_temper_CB     = tk.Checkbutton(tab4, text = "Min Air Temp (DN)", variable = self.min_air_temper_BV)
		self.max_air_temper_CB     = tk.Checkbutton(tab4, text = "Max Air Temp (DN)", variable = self.max_air_temper_BV)
		
		# List of options in each column for mass selection and deselection
		col1 = [self.day_num_CB, self.date_CB, self.off_count_CB, self.off_dur_CB, self.off_dur_sd_CB, self.off_dec_CB, self.off_dec_sd_CB, self.mean_off_temper_CB, self.off_time_sum_CB, self.on_count_CB,
				self.on_dur_CB, self.on_dur_sd_CB, self.on_inc_CB, self.on_inc_sd_CB, self.mean_on_temper_CB, self.on_time_sum_CB, self.time_above_temper_CB, self.time_below_temper_CB, self.bouts_dropped_CB]

		col2 = [self.mean_temper_d_CB, self.mean_temper_d_sd_CB, self.median_temper_d_CB, self.min_temper_d_CB, self.max_temper_d_CB, self.mean_temper_n_CB, self.mean_temper_n_sd_CB, self.median_temper_n_CB, self.min_temper_n_CB,
				self.max_temper_n_CB, self.mean_temper_dn_CB, self.mean_temper_dn_sd_CB, self.median_temper_db_CB,  self.min_temper_dn_CB, self.max_temper_dn_CB, self.mean_air_temper_CB, self.mean_air_temper_sd_CB, self.min_air_temper_CB, self.max_air_temper_CB]

		self.toggle_col(col1, "select")
		self.toggle_col(col2, "select")	
		
		self.day_num_CB.grid(row = 3, sticky = "W", padx = 10, pady = (10, 0))
		self.date_CB.grid(row = 4, sticky = "W", padx = 10)
		self.off_count_CB.grid(row = 7, sticky = "W", padx = 10)
		self.off_dur_CB.grid(row = 8, sticky = "W", padx = 10)
		self.off_dur_sd_CB.grid(row = 9, sticky = "W", padx = 10)
		self.off_dec_CB.grid(row = 10, sticky = "W", padx = 10)
		self.off_dec_sd_CB.grid(row = 11, sticky = "W", padx = 10)
		self.mean_off_temper_CB.grid(row = 12, sticky = "W", padx = 10)
		self.off_time_sum_CB.grid(row = 13, sticky = "W", padx = 10)
		self.on_count_CB.grid(row = 15, sticky = "W", padx = 10)
		self.on_dur_CB.grid(row = 16, sticky = "W", padx = 10)
		self.on_dur_sd_CB.grid(row = 17, sticky = "W", padx = 10)
		self.on_inc_CB.grid(row = 18, sticky = "W", padx = 10)
		self.on_inc_sd_CB.grid(row = 19, sticky = "W", padx = 10)
		self.mean_on_temper_CB.grid(row = 20, sticky = "W", padx = 10)
		self.on_time_sum_CB.grid(row = 21, sticky = "W", padx = 10)
		self.bouts_dropped_CB.grid(row = 23, sticky = "W", padx = 10)	
		self.time_above_temper_CB.grid(row = 24, sticky = "W", padx = 10)
		self.time_below_temper_CB.grid(row = 25, sticky = "W", padx = 10)	
		self.mean_temper_d_CB.grid(row = 3, sticky = "W", padx = 200, pady = (10, 0))
		self.mean_temper_d_sd_CB.grid(row = 4, sticky = "W", padx = 200)
		self.median_temper_d_CB.grid(row = 6, sticky = "W", padx = 200)
		self.min_temper_d_CB.grid(row = 7, sticky = "W", padx = 200)
		self.max_temper_d_CB.grid(row = 8, sticky = "W", padx = 200)
		self.mean_temper_n_CB.grid(row = 10, sticky = "W", padx = 200)
		self.mean_temper_n_sd_CB.grid(row = 11, sticky = "W", padx = 200)
		self.median_temper_n_CB.grid(row = 12, sticky = "W", padx = 200)
		self.min_temper_n_CB.grid(row = 13, sticky = "W", padx = 200)
		self.max_temper_n_CB.grid(row = 14, sticky = "W", padx = 200)
		self.mean_temper_dn_CB.grid(row = 16, sticky = "W", padx = 200)
		self.mean_temper_dn_sd_CB.grid(row = 17, sticky = "W", padx = 200)
		self.median_temper_db_CB.grid(row = 18, sticky = "W", padx = 200)
		self.min_temper_dn_CB.grid(row = 19, sticky = "W", padx = 200)
		self.max_temper_dn_CB.grid(row = 20, sticky = "W", padx = 200)
		self.mean_air_temper_CB.grid(row = 22, sticky = "W", padx = 200)
		self.mean_air_temper_sd_CB.grid(row = 23, sticky = "W", padx = 200)
		self.min_air_temper_CB.grid(row = 24, sticky = "W", padx = 200)
		self.max_air_temper_CB.grid(row = 25, sticky = "W", padx = 200)
		
		self.time_above_temper_E = tk.Entry(tab4, width = 5)
		self.time_above_temper_E.grid(row = 24, sticky = "W", padx = 97)
		self.time_below_temper_E = tk.Entry(tab4, width = 5)
		self.time_below_temper_E.grid(row = 25, sticky = "W", padx = 97)

		# -----------------------------------------------------------------------------------------------------------
		# ----- Footer -----
		path1 = "./../misc_files/NIQ_Sups/uark.png"
		path2 = "./../misc_files/NIQ_Sups/durant.png"
		uark_logo = ImageTk.PhotoImage(Image.open(path1))
		durant_logo = ImageTk.PhotoImage(Image.open(path2))
		uark_logo_L = tk.Label(root, background = "white", image = uark_logo)
		uark_logo_L.grid(row = 29, sticky = "W", padx = 20)
		durant_logo_L = tk.Label(root, background = "white", image = durant_logo)
		durant_logo_L.grid(row = 29, sticky = "W", padx = 80)

		self.run = False
		self.run_B = tk.Button(root, text = "Run", command = (lambda : self.trigger_run(root)))
		self.run_B.grid(row = 29, sticky = "NE", padx = 10, pady = (10, 0))
		self.run_B.configure(bg = "red4", fg = "white", width = 10, height = 1)
		self.run_B["font"] = HEADER_FONT

		self.show_warns_BV = tk.BooleanVar()
		self.show_warns_CB = tk.Checkbutton(
												root, 
												text = "Show warnings", 
												variable = self.show_warns_BV,
												background = "white", 
												activebackground = "white", 
												font = STANDARD_FONT
											)
		self.show_warns_CB.grid(row = 29, sticky = "SE", padx = 10, pady = (10, 0))

		self.load_config(program_startup = True)

		# Call function to handle user closing GUI window
		root.protocol("WM_DELETE_WINDOW", lambda : self.close_niq(root))
		
		_ = None
		root.bind("<Return>", lambda _ : self.trigger_run(root))
		# Flag
		root.bind("<`>", lambda _ : self.test_run(root))
		root.bind("<Control-`>", lambda _ : self.test_stats(root))
			
		self.valid = True
		while self.valid and not self.run:
			self.runloop(root)
	
	def runloop(self, root):
		"""
			Updates GUI and sets program clock

			Args:
				root (tk root widget): base widget of GUI
		"""

		root.update_idletasks()
		root.update()
		time.sleep(0.01)
		
	def save_config(self):
		"""
			Prompts user to provide a save file name and location then generates a configuration file from
			the current GUI settings and statuses.

		"""

		out_file = filedialog.asksaveasfilename()
		
		if not re.search("\.ini", out_file):
			out_file = (out_file + ".ini")
		
		# Copy over config_static as template
		copyfile(os.path.join(self.core_dir, "misc_files", "config_static.ini"), out_file)
		self.update_config(out_file)

	def load_config(self, program_startup = False, config_file_ = None):
		"""
			Updates all GUI settings and statuses according to a configuration file. If this file is not immediately 
			provided to the function, the user is prompted to select a file from a dialog box.

			Args:
				program_startup (bool): True if is the initial call used populate GUI upon program startup 
				config_file_ (string): Path to configuration file to be loaded

		"""

		if not program_startup and config_file_ is None:
			config_file = filedialog.askopenfilename()
		
			if config_file == "": return False 
		
			if not os.path.exists(config_file):
				messagebox.showerror(("Config File Loading Error"), 
				"Configuration file could not be found.")
				return False
			
			try: self.config.read(config_file)
			except:
				messagebox.showerror(("Config File Loading Error"), 
				"Configuration file appears invalid.  Please try a differnt file.")
			
		if config_file_ is not None: 
			config_file = config_file_
			self.config.read(config_file)

		try:
			replace_entry(self.out_path_E, self.config.get("Main Settings", "output_dir"))
			os.chdir(self.out_path_E.get())

			self.time_interval = self.config.get("Main Settings", "data_time_interval")
			self.show_warns_CB.select() if self.config.get("Main Settings", "show_warnings").lower() == "true" else self.show_warns_CB.deselect()
			self.restrict_search_CB.select() if self.config.get("Main Settings", "restrict_bout_search").lower() == "true" else self.restrict_search_CB.deselect()
			self.UL_default_CB.select() if self.config.get("Advanced Settings", "run_unsup_by_default").lower() == "true" else self.UL_default_CB.deselect()
			replace_entry(self.day_start_E, self.config.get("Main Settings", "day_Start_Time"))
			replace_entry(self.night_start_E, self.config.get("Main Settings", "night_Start_Time"))
			replace_entry(self.smoothing_radius_E, self.config.get("Main Settings", "smoothing_radius"))
			replace_entry(self.dur_thresh_E, self.config.get("Main Settings", "duration_threshold"))
			replace_entry(self.init_off_E, self.config.get("Advanced Settings", "off_bout_initial"))
			replace_entry(self.init_on_E, self.config.get("Advanced Settings", "on_bout_initial"))
			replace_entry(self.off_off_trans_E, self.config.get("Advanced Settings", "off_off_trans"))
			replace_entry(self.off_on_trans_E, self.config.get("Advanced Settings", "off_on_trans"))
			replace_entry(self.on_on_trans_E, self.config.get("Advanced Settings", "on_on_trans"))
			replace_entry(self.on_off_trans_E, self.config.get("Advanced Settings", "on_off_trans"))
			replace_entry(self.off_mean_E, self.config.get("Advanced Settings", "off_bout_emis_mean"))
			replace_entry(self.off_stdev_E, self.config.get("Advanced Settings", "off_bout_emis_stdev"))
			replace_entry(self.on_mean_E, self.config.get("Advanced Settings", "on_bout_emis_mean"))
			replace_entry(self.on_stdev_E, self.config.get("Advanced Settings", "on_bout_emis_stdev"))
			self.manual_plot_dims.set(0) if self.config.get("Plot Options", "manual_plot_dimensions").lower() == "false" else self.manual_plot_dims.set(1)
			replace_entry(self.plot_dim_x_E, self.config.get("Plot Options", "plot_x_dim"))
			replace_entry(self.plot_dim_y_E, self.config.get("Plot Options", "plot_y_dim"))
			replace_entry(self.title_font_size_E, self.config.get("Plot Options", "title_font_size"))
			replace_entry(self.axis_title_font_size_E, self.config.get("Plot Options", "axis_title_font_size"))
			replace_entry(self.axis_label_font_size_E, self.config.get("Plot Options", "axis_label_font_size"))
			replace_entry(self.axis_tick_size_E, self.config.get("Plot Options", "axis_tick_size"))
			replace_entry(self.legend_font_size_E, self.config.get("Plot Options", "legend_font_size"))
			self.plot_egg_CB.select() if self.config.get("Plot Options", "plot_egg_tempers").lower() == "true" else self.plot_egg_CB.deselect()
			self.plot_air_CB.select() if self.config.get("Plot Options", "plot_air_tempers").lower() == "true" else self.plot_air_CB.deselect()
			self.plot_delta_CB.select() if self.config.get("Plot Options", "plot_egg_minus_air").lower() == "true" else self.plot_delta_CB.deselect()
			self.smooth_status_IV.set(0) if self.config.get("Plot Options", "plot_smoothed").lower() == "false" else self.smooth_status_IV.set(1)
			self.legend_loc.set(self.config.get("Plot Options", "legend_location"))
			self.on_point_color.set(self.config.get("Plot Options", "on_point_color"))
			self.off_point_color.set(self.config.get("Plot Options", "off_point_color"))
			self.bout_line_color.set(self.config.get("Plot Options", "bout_line_color"))
			self.air_line_color.set(self.config.get("Plot Options", "air_line_color"))
			self.day_marker_color.set(self.config.get("Plot Options", "day_marker_color"))
			replace_entry(self.on_point_size_E, self.config.get("Plot Options", "on_point_size"))
			replace_entry(self.bout_line_width_E, self.config.get("Plot Options", "bout_line_width"))
			replace_entry(self.air_line_width_E, self.config.get("Plot Options", "air_line_width"))
			replace_entry(self.day_marker_width_E, self.config.get("Plot Options", "day_marker_width"))
			self.show_day_markers_CB.select() if self.config.get("Plot Options", "show_day_marker").lower() == "true" else self.show_day_markers_CB.deselect()				
			self.show_grid_CB.select() if self.config.get("Plot Options", "show_grid").lower() == "true" else self.show_grid_CB.deselect()
			self.day_num_CB.select() if self.config.get("Stats Options", "day_Number").lower() == "true" else self.day_num_CB.deselect()
			self.date_CB.select() if self.config.get("Stats Options", "date").lower() == "true" else self.date_CB.deselect()		
			self.off_count_CB.select() if self.config.get("Stats Options", "off_Bout_Count").lower() == "true" else self.off_count_CB.deselect()	
			self.off_dur_CB.select() if self.config.get("Stats Options", "mean_Off_Bout_Duration").lower() == "true" else self.off_dur_CB.deselect()
			self.off_dur_sd_CB.select() if self.config.get("Stats Options", "off_Bout_Duration_StDev").lower() == "true" else self.off_dur_sd_CB.deselect()
			self.off_dec_CB.select() if self.config.get("Stats Options", "mean_Off_Bout_Temp_Drop").lower() == "true" else self.off_dec_CB.deselect()			
			self.off_dec_sd_CB.select() if self.config.get("Stats Options", "off_Bout_Temp_Drop_StDev").lower() == "true" else self.off_dec_sd_CB.deselect()
			self.mean_off_temper_CB.select() if self.config.get("Stats Options", "mean_Off_Bout_Temp").lower() == "true" else self.mean_off_temper_CB.deselect()
			self.off_time_sum_CB.select() if self.config.get("Stats Options", "off_bout_time_sum").lower() == "true" else self.off_time_sum_CB.deselect()
			self.on_count_CB.select() if self.config.get("Stats Options", "on_Bout_Count").lower() == "true" else self.on_count_CB.deselect()					
			self.on_dur_CB.select() if self.config.get("Stats Options", "mean_On_Bout_Duration").lower() == "true" else self.on_dur_CB.deselect()					
			self.on_dur_sd_CB.select() if self.config.get("Stats Options", "on_Bout_Duration_StDev").lower() == "true" else self.on_dur_sd_CB.deselect()					
			self.on_inc_CB.select() if self.config.get("Stats Options", "mean_On_Bout_Temp_Rise").lower() == "true" else self.on_inc_CB.deselect()						
			self.on_inc_sd_CB.select() if self.config.get("Stats Options", "on_Bout_Temp_Rise_StDev").lower() == "true" else self.on_inc_sd_CB.deselect()				
			self.mean_on_temper_CB.select() if self.config.get("Stats Options", "mean_On_Bout_Temp").lower() == "true" else self.mean_on_temper_CB.deselect()
			self.on_time_sum_CB.select() if self.config.get("Stats Options", "on_bout_time_sum").lower() == "true" else self.on_time_sum_CB.deselect()
			self.bouts_dropped_CB.select() if self.config.get("Stats Options", "bouts_Dropped").lower() == "true" else self.bouts_dropped_CB.deselect()		
			self.time_above_temper_CB.select() if self.config.get("Stats Options", "time_above_critical").lower() == "true" else self.time_above_temper_CB.deselect()		
			self.time_below_temper_CB.select() if self.config.get("Stats Options", "time_below_critical").lower() == "true" else self.time_below_temper_CB.deselect()					
			self.mean_temper_d_CB.select() if self.config.get("Stats Options", "mean_Daytime_Temperature").lower() == "true" else self.mean_temper_d_CB.deselect()		
			self.mean_temper_d_sd_CB.select() if self.config.get("Stats Options", "daytime_Temp_StDev").lower() == "true" else self.mean_temper_d_sd_CB.deselect()	
			self.median_temper_d_CB.select() if self.config.get("Stats Options", "median_Daytime_Temp").lower() == "true" else self.median_temper_d_CB.deselect()		
			self.min_temper_d_CB.select() if self.config.get("Stats Options", "min_Daytime_Temp").lower() == "true" else self.min_temper_d_CB.deselect()		
			self.max_temper_d_CB.select() if self.config.get("Stats Options", "max_Daytime_Temp").lower() == "true" else self.max_temper_d_CB.deselect()		
			self.mean_temper_n_CB.select() if self.config.get("Stats Options", "mean_Nighttime_Temp").lower() == "true" else self.mean_temper_n_CB.deselect()		
			self.mean_temper_n_sd_CB.select() if self.config.get("Stats Options", "nighttime_Temp_StDev").lower() == "true" else self.mean_temper_n_sd_CB.deselect()		
			self.median_temper_n_CB.select() if self.config.get("Stats Options", "median_Nighttime_Temp").lower() == "true" else self.median_temper_n_CB.deselect()	
			self.min_temper_n_CB.select() if self.config.get("Stats Options", "min_Nighttime_Temp").lower() == "true" else self.min_temper_n_CB.deselect()		
			self.max_temper_n_CB.select() if self.config.get("Stats Options", "max_Nighttime_Temp").lower() == "true" else self.max_temper_n_CB.deselect()			
			self.mean_temper_dn_CB.select() if self.config.get("Stats Options", "mean_DayNight_Temp").lower() == "true" else self.mean_temper_dn_CB.deselect()		
			self.mean_temper_dn_sd_CB.select() if self.config.get("Stats Options", "dayNight_Temp_StDev").lower() == "true" else self.mean_temper_dn_sd_CB.deselect()			
			self.median_temper_db_CB.select() if self.config.get("Stats Options", "median_DayNight_Temp").lower() == "true" else self.median_temper_db_CB.deselect()		
			self.min_temper_dn_CB.select() if self.config.get("Stats Options", "min_DayNight_Temp").lower() == "true" else self.min_temper_dn_CB.deselect()		
			self.max_temper_dn_CB.select() if self.config.get("Stats Options", "max_DayNight_Temp").lower() == "true" else self.max_temper_dn_CB.deselect()	
			self.mean_air_temper_CB.select() if self.config.get("Stats Options", "mean_air_temp").lower() == "true" else self.mean_air_temper_CB.deselect()	
			self.mean_air_temper_sd_CB.select() if self.config.get("Stats Options", "mean_air_temp_stdev").lower() == "true" else self.mean_air_temper_sd_CB.deselect()	
			self.min_air_temper_CB.select() if self.config.get("Stats Options", "min_air_temp").lower() == "true" else self.min_air_temper_CB.deselect()	
			self.max_air_temper_CB.select() if self.config.get("Stats Options", "max_air_temp").lower() == "true" else self.max_air_temper_CB.deselect()	
			replace_entry(self.time_above_temper_E, self.config.get("Stats Options", "custom_time_above_temperature"))
			replace_entry(self.time_below_temper_E, self.config.get("Stats Options", "custom_time_below_temperature"))
				
		except Exception:
			if program_startup:
				messagebox.showerror(("Config File Loading Error"), 
				"default_config.ini could not be read, reverting to static config file.")
				traceback.print_exc()

				# If an error is encountered, try loading "config_static.ini"
				copyfile(os.path.join(self.core_dir, "misc_files", "config_static.ini"), 
						os.path.join(self.core_dir, "config_files", "default_config.ini"))
					
				self.config.read(os.path.join(self.core_dir, "config_files", "default_config.ini"))
				self.load_config(program_startup = True)
			else:
				messagebox.showerror(("Config File Loading Error"), 
				config_file + " could not be read.")	
				traceback.print_exc()
	
	def set_defaults(self):
		"""
			Updates default configureation file with current GUI status.
		"""

		try:
			self.update_config()
			messagebox.showinfo("Default Parameters Saved", 
			"defaultParameters.ini has been updated.")	
		except:
			messagebox.showerror(("Default Settings Error"), 
			"An error was encountered while updating default parameters.  Check if provided parameters are valid.")
	
	def check_vertex_file(self):
		"""
			Checks user-provided vertex selection file (HTML) for issues that could cause errors with 
			downstream processes.

			Returns:
				True if file passes all tests, else displays error message and returns False
		"""

		vertex_file = self.vertex_file_E.get()
		if vertex_file == "":
			messagebox.showerror("Vertex File Error", "Please provide a vertex file.")
			return False
		
		if not os.path.exists(vertex_file):
			# Check for curly brace addition (sometimes added for paths with spaces)
			if vertex_file[0] != "{":
				messagebox.showerror("Vertex Selection Error", "Provided vertex selection file not found.")
				return False
			
			if not os.path.exists(vertex_file[1:(len(vertex_file) - 1)]):
				messagebox.showerror("Vertex Selection Error", "Provided vertex selection file not found.")
				return False

			replace_entry(self.vertex_file_E, (vertex_file[1:(len(vertex_file) - 1)]))
			vertex_file = self.vertex_file_E.get()
				
		if vertex_file[-5:] != ".html":
			messagebox.showerror("Vertex Selection Error", "Vertex selection file must end in \".html\".")
			return False		

		try:
			with open(vertex_file, "r") as original_file:
				original_lines = original_file.readlines()
		except FileNotFoundError:
			messagebox.showerror(("Vertex File Error"), 
			"Vertex file could not be found with the given path.")	
			return False
		
		# Remove extra table data lines if present
		found = False
		with open("temp_file", "w") as temp_file:
			for line in original_lines:
				if line.find("<div class") != -1:
					if not found:
						found = True
						temp_file.write(line)
				# Retain all non-table data containing lines
				else:
					temp_file.write(line)				
		
		with open("temp_file", "r") as temp_file:
			cleaned_file = temp_file.read()
			
		os.remove("temp_file")
		
		# Get datapoints
		tokens = re.finditer(">([\d\.-]+)</span>", cleaned_file)
		counter = 0

		try:
			# Every other value in tokens will be temperature and so is ignored
			for counter, match in enumerate(tokens):
				if not (counter % 2) == 0:
					data_point_ = round(float(match.group(1)))
		except:
			messagebox.showerror(("Vertex File Error"), 
			"Vertex file is unreadable. Please try another.")
			return False

		if counter < 2:
			messagebox.showerror(("Vertex File Error"), "No vertices detected in vertex file.")
			return False

		return True
		
	# Flag
	def test_run(self, root):
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:\\Users\\wxhaw\\Desktop\\github\\whereabout\\inputFiles\\Static\\testInFile.csv")

		# GREAT TIT
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/GRTI/stat_testing.csv")
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/stat_testing_in.csv")
		self.input_file_E.delete(0, "end")
		self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/GitHub/NestIQ/inputFiles/hellaBirds/WODUA1B_fullinc.csv")
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/GitHub/NestIQ/inputFiles/hellaBirds/CanaryCtrlB68-1.csv")
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/GitHub/NestIQ/inputFiles/hellaBirds/KTallam.csv")
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/GitHub/NestIQ/inputFiles/hellaBirds/CanaryMGB23-1.csv")
		
		# self.inputFileAdvE.delete(0, "end")
		# self.inputFileAdvE.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/GRTI/GRTI2.csv")
		# self.vertex_file_E.delete(0, "end")
		# self.vertex_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/GRTI/GRTI_train_verts_minus_amb.html")

		# TREE SWALLOW
		# self.input_file_E.delete(0, "end")
		# self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/tree_swallow/TRES8crop_minus_amb_alt.csv")
		# self.inputFileAdvE.delete(0, "end")
		# self.inputFileAdvE.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/tree_swallow/TRES8crop_minus_amb_alt.csv")
		# self.vertex_file_E.delete(0, "end")
		# self.vertex_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/NIQ_test_input/tree_swallow/TRES_minus_amb_verts_alt.html")

	# Flag
	def test_stats(self, root):
		# Load config file
		self.load_config(config_file_ = "C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/stat_testing_config.ini")
		# Get run get stats for reduced input file
		self.input_file_E.delete(0, "end")
		self.input_file_E.insert(0, "C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/stat_testing_in.csv")

		self.stats_file_E.delete(0, "end")
		self.stats_file_E.insert(0, "stat_testing_out.csv")

		outPath = "C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/"
		os.chdir(outPath)

		self.trigger_run(root)

		# Compare primary stat line for reference vs newly generated stats
		with open ("C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/stat_reference.csv", "r") as ref_file:
			ref_lines = ref_file.readlines()
			ref_line = ref_lines[2]
			ref_split = ref_line.split(",")

		with open ("C:/Users/wxhaw/OneDrive/Desktop/Github/NestIQ/testing/stat_testing_out.csv", "r") as test_file:
			test_lines = test_file.readlines()
			test_line = test_lines[2]
			test_split = test_line.split(",")

		perfect = True
		for index, (test_item, ref_item) in enumerate(zip(test_split[2:], ref_split[2:])):
			same = (float(ref_item) == float(test_item))
			print(index, ":", same)
			if not same: 
				print("ref =", ref_item)
				print("test =", test_item)
				perfect = False

		print("PASSED") if perfect else print("FAILED")
		
	def help(self):
		"""
			Launches user manual.
		"""
		subprocess.Popen(os.path.join(self.core_dir, "NIQ_manual.pdf"), shell = True)
		
	def toggle_col(self, column, command):
		"""
			Selects or deselects entire columns of Stat Options tab

			Args:
				column (list): list of variables to be selected or deselected
				command (string)
		"""
		for option in column:
			option.select() if command == "select" else option.deselect()
	
	def update_multi_in_default_outs(self, in_file):
		"""
			Automatically updates input and output file entry boxes before each run if multiple files
			are being processed.

			Args:
				in_file (string): path to file currently being proceessed
		"""

		replace_entry(self.input_file_E, in_file)

		self.time_interval = self.config.get("Main Settings", "data_time_interval")
		
		temp_re = re.search((".*\."), os.path.basename(os.path.normpath(in_file)))
		self.input_root = temp_re.group(0)[:-1] if temp_re else temp_re.group(0)[:-1]
				
		replace_entry(self.plot_file_E, (self.input_root + "plot.html"))
		niq_misc.get_novel_name(self.plot_file_E, (self.input_root + "plot(NUM).html"))

		replace_entry(self.stats_file_E, (self.input_root + "stats.csv"))
		niq_misc.get_novel_name(self.stats_file_E, (self.input_root + "stats(NUM).csv"))
		
	def update_default_outs(self):
		"""
			Updates default output file names to unique values.
		"""

		# Initialize regular expresssions
		plot_re = ("plot(\((\d)\))?\.html")
		stats_re = ("stats(\((\d)\))?\.csv")

		if self.input_root:
			input_root_plot_re = (self.input_root + "Plot(\((\d)\))?\.html")
			input_root_stats_re = (self.input_root + "Stats(\((\d)\))?\.csv")

		if os.path.exists(self.plot_file_E.get()):
			if re.search(plot_re, self.plot_file_E.get()):
				get_novel_name(self.plot_file_E, "plot(NUM).html")
			elif self.input_root:		
				if re.search(input_root_plot_re, self.plot_file_E.get()):
					get_novel_name(self.plot_file_E, (self.input_root + "Plot(NUM).html"))

		if os.path.exists(self.stats_file_E.get()):
			if re.search(stats_re, self.stats_file_E.get()):
				get_novel_name(self.stats_file_E, "stats(NUM).csv")
					
			elif self.input_root:		
				if re.search(input_root_stats_re, self.stats_file_E.get()):
					get_novel_name(self.stats_file_E, (self.input_root + "Stats(NUM).csv"))

	def check_valid_main(self, first_in = True, check_output = True):
		"""
			Checks for valid configuration of all parameters housed on the Main tab.  This includes extensive
			review of the input file provided.

			Args:
				first_in (bool): False if current file is second or later in a queue of multiple input files
				check_output (bool): if Flase, output file names are not examined
		"""

		def check_input_file_generator(self):
			"""
				Checks several aspects of the input file to ensure it is compatable with all downstream processing.
				Also displays warnings for less severe format violations.
			"""

			in_file = self.input_file_E.get().lstrip("{").rstrip("}")

			datetime_valid = True

			print_file_name = ("For file: " + os.path.normpath(in_file) + "\n\n")

			if in_file == "":
				messagebox.showerror("Input error (Main tab)", "No input file provided.")
				return False
		
			try:
				if not os.path.exists(in_file):	
					# Check for curly brace addition (sometimes done for paths with spaces)
					if in_file[0] == "{":
						if os.path.exists(in_file[1:(len(in_file) - 1)]):
							replace_entry(self.input_file_E, (in_file[1:(len(in_file) - 1)]))
							in_file = self.input_file_E.get()
						else: raise ValueError
					else: raise ValueError
			except ValueError:
				messagebox.showerror("Input File Error", 
				"".join((print_file_name, "File with provided path could not be found.")))
				return False
				
			if in_file[-4:] != ".csv":
				messagebox.showerror("Input File Error", 
				"".join((print_file_name, "Input file must end in \".csv\" (comma separated value file format).")))
				return False

			# Flag
			try:
				with open(in_file, "r") as csv_file:
					csv_reader = csv.reader(csv_file)
					sample = ""
					# Test if fist line is blank and generate sample to give to CSV sniffer
					for i in range(10):
						row = next(csv_reader)
						has_header = True if i == 0 and row[0] == "" else False
						for cell in row[:3]:
							sample += "".join(cell)
							sample += ","
						sample += "\n"
						
					has_header = has_header or csv.Sniffer().has_header(sample)

					# Get data time interval
					csv_file.seek(0)
					csv_reader = csv.reader(csv_file)
					prev_line = next(csv_reader)
					if has_header:
						prev_line = next(csv_reader)

					if not (self.get_data_time_interval(csv_reader, prev_line)):
						return False 

					# Reset generator and remove header
					csv_file.seek(0)
					csv_reader = csv.reader(csv_file)
					prev_line = next(csv_reader)
					if has_header:
						prev_line = next(csv_reader)
					
					if len(prev_line) < 3:
						self.air_valid = False

					if not niq_misc.get_datetime(self, prev_line):
						return False

					interval_clock = 0 if self.time_interval >= 1 else round(1 / self.time_interval)
					interval_time = 1
					start_found = False
					
					for line_num, line in enumerate(csv_reader):
						line.remove("")
						# Check if data points are continuous and sequential
						if not line_num == 0:
							try:
								if not int(line[self.data_point_col]) == (int(prev_line[self.data_point_col]) + 1):
									raise ValueError
							except:
								print("line = ", line)
								messagebox.showerror("Data Point Error", 
								"".join((print_file_name + "Error near data point " + str(prev_line[self.data_point_col]) + 
								". Data point number is not sequential with regrad to previous data point.")))
								return False
						
						prev_datetime = niq_misc.get_datetime(self, prev_line)
						cur_datetime = niq_misc.get_datetime(self, line)
						datetime_diff = (cur_datetime - prev_datetime).seconds / 60

						if datetime_diff == 0 or datetime_diff == self.time_interval:
							start_found = True

						if datetime_valid and start_found:
							if cur_datetime == False:
								return False 
								
							if datetime_diff != self.time_interval:
								if not interval_clock > 0:
									datetime_valid = False
								else:
									if datetime_diff == 0:
										interval_time += 1
									elif datetime_diff != 1:
										datetime_valid = False
									else:
										if interval_time == interval_clock:
											interval_time = 1
										else:
											datetime_valid = False

							if not datetime_valid:
								if self.show_warns_BV.get():
									messagebox.showwarning("Date/time Warning",
									"".join((print_file_name + "Discontinuous date/time found for data point " + line[self.data_point_col] +
									". The program will continue, but this could cause inacurate statistical output.")))

						if line[self.egg_temper_col] == "":
							if self.show_warns_BV.get():
								messagebox.showwarning("Egg Temperature Warning", 
								"".join((print_file_name + "No egg temperature detected for data point " + line[self.data_point_col] + 
								".  If left, the program will populate this cell with the temperature above it.")))
						else:
							try: float(line[self.egg_temper_col])
							except:
								messagebox.showerror("Temperature Error",
								"".join((print_file_name + "Invalid temperature given for data point " + line[self.data_point_col] + ".")))
								return False
						
						if self.air_valid:
							try:
								if line[self.air_temper_col] == "":
									self.air_valid = False
									if self.show_warns_BV.get():
										messagebox.showwarning("Air Temperature Warning", 
										"".join((print_file_name + "No air temperature detected for data point " + line[self.data_point_col] + 
										". Air temperatures will not be plotted or included in statistical output.")))
								else:
									try: float(line[self.air_temper_col])
									except:
										self.air_valid = False
										if self.show_warns_BV.get():
											messagebox.showwarning("Air Temperature Warning", 
											"".join((print_file_name + "Invalid air temperature detected for data point " + line[self.data_point_col] + 
											". Air temperatures will not be plotted or included in statistical output.")))
							except IndexError:
								self.air_valid = False

						prev_line = line

					return True
				
			# flag
			except Exception as e:
				print(e)
				print_file_name = ("File: " + os.path.basename(os.path.normpath(in_file)) + " \n\n")
				messagebox.showerror("Unknown Error",
				"".join((print_file_name + "There was an unidentifiable error with the provided input file. " +
				"This is sometimes the result of \"extra\" cells in the input file.\n\n" +
				"Please reference the NestIQ manual for details regarding proper input file format." +
				" This can be accessed by clicking \"Help\" in the top right.")))
				return False

		def check_input_file(self):
			"""
				Checks several aspects of the input file to ensure it is compatable with all downstream processing.
				Also displays warnings for less severe format violations.
			"""

			in_file = self.input_file_E.get().lstrip("{").rstrip("}")
			datetime_valid = True

			print_file_name = ("For file: " + os.path.normpath(in_file) + "\n\n")

			if in_file == "":
				messagebox.showerror("Input error (Main tab)", "No input file provided.")
				return False
		
			try:
				if not os.path.exists(in_file):	
					# Check for curly brace addition (sometimes done for paths with spaces)
					if in_file[0] == "{":
						if os.path.exists(in_file[1:(len(in_file) - 1)]):
							replace_entry(self.input_file_E, (in_file[1:(len(in_file) - 1)]))
							in_file = self.input_file_E.get()
						else: raise ValueError
					else: raise ValueError
			except ValueError:
				messagebox.showerror("Input File Error", 
				"".join((print_file_name, "File with provided path could not be found.")))
				return False
				
			if in_file[-4:] != ".csv":
				messagebox.showerror("Input File Error", 
				"".join((print_file_name, "Input file must end in \".csv\" (comma separated value file format).")))
				return False

			# Flag
			try:
				with open(in_file, "r") as csv_file:
					csv_lines = csv_file.readlines()
					master_list = [line.strip().rstrip(",").split(",") for line in csv_lines]

					pop_indices = []
					# Remove lines not conforming to expected format (such as headers)	
					for i, cur_line in enumerate(master_list[:-1]):
						# print("line = ", master_list[i])
						if any(( 
								re.search("\D", master_list[i][self.data_point_col]),
								not re.search("\d", master_list[i][self.data_point_col])
							)):
							
							pop_indices.append(i)
						
					for pop_count, index in enumerate(pop_indices):
						master_list.pop(index - pop_count)
					master_list.pop(len(master_list) - 1)

					prev_line = master_list[0]

					if not (self.get_data_time_interval(niq_misc.list_to_gen(master_list[1:]), prev_line)):
						return False 

					if len(prev_line) < 3:
						self.air_valid = False

					if not niq_misc.get_datetime(self, prev_line):
						return False

					interval_clock = 0 if self.time_interval >= 1 else round(1 / self.time_interval)
					interval_time = 1
					start_found = False
					
					for line_num, line in enumerate(master_list[1:]):
						line = line[:4] if self.air_valid else line[:3]

						# Check if data points are continuous and sequential
						try:
							if not int(line[self.data_point_col]) == (int(prev_line[self.data_point_col]) + 1):
								raise ValueError
						except:
							messagebox.showerror("Data Point Error", 
							"".join((print_file_name + "Error after data point " + str(prev_line[self.data_point_col]) + 
							". Data point number is not sequential with regard to previous data point.")))
							return False
						
						prev_datetime = niq_misc.get_datetime(self, prev_line)
						cur_datetime = niq_misc.get_datetime(self, line)
						datetime_diff = (cur_datetime - prev_datetime).seconds / 60

						if datetime_diff == 0 or datetime_diff == self.time_interval:
							start_found = True

						if datetime_valid and start_found:
							if cur_datetime == False:
								return False 
								
							if datetime_diff != self.time_interval:
								if not interval_clock > 0:
									datetime_valid = False
								else:
									if datetime_diff == 0:
										interval_time += 1
									elif datetime_diff != 1:
										datetime_valid = False
									else:
										if interval_time == interval_clock:
											interval_time = 1
										else:
											datetime_valid = False

							if not datetime_valid:
								if self.show_warns_BV.get():
									messagebox.showwarning("Date/time Warning",
									"".join((print_file_name + "Discontinuous date/time found for data point " + line[self.data_point_col] +
									". The program will continue, but this could cause inaccurate statistical output.")))


						try:
							float(line[self.egg_temper_col])

							if line[self.egg_temper_col] == "":
								raise ValueError
						
						except:
							messagebox.showerror("Temperature Error",
							"".join((print_file_name + "Invalid temperature given for data point " + line[self.data_point_col] + ".")))
							return False
						
						if self.air_valid:
							try:
								if line[self.air_temper_col] == "":
									self.air_valid = False
									if self.show_warns_BV.get():
										messagebox.showwarning("Air Temperature Warning", 
										"".join((print_file_name + "No air temperature detected for data point " + line[self.data_point_col] + 
										". Air temperatures will not be plotted or included in statistical output.")))
								else:
									try: float(line[self.air_temper_col])
									except:
										self.air_valid = False
										if self.show_warns_BV.get():
											messagebox.showwarning("Air Temperature Warning", 
											"".join((print_file_name + "Invalid air temperature detected for data point " + line[self.data_point_col] + 
											". Air temperatures will not be plotted or included in statistical output.")))
							except IndexError:
								self.air_valid = False

						prev_line = line

					return True
				
			# flag
			except Exception as e:
				print(e)
				print_file_name = ("File: " + os.path.basename(os.path.normpath(in_file)) + " \n\n")
				messagebox.showerror("Unknown Error",
				"".join((print_file_name + "There was an unidentifiable error with the provided input file. " +
				"This is sometimes the result of \"extra\" cells in the input file.\n\n" +
				"Please reference the NestIQ manual for details regarding proper input file format." +
				" This can be accessed by clicking \"Help\" in the top right.")))
				return False

		def check_out_file(gui, entry, title):
			"""
				Checks if the name provided for a given output file is valid.  This includes asking the user if
				they want to override if a file with the same name already exists.

				Args:
					entry (tk.Entry): entry box being examined
					title (string): how to reference the current entry box if error messeage is triggered
			"""

			if entry.get().strip() == "":
				messagebox.showerror((title + " Error"), "File name is empty.") 
				return False
			
			if entry.get()[-1] == "/" or entry.get()[-1] == "\\":
				messagebox.showerror((title + " Error"), "Directory provided but no file name.")
				return False
						
			# Check if plot file already exists and if so, ask to override
			if entry == gui.plot_file_E:
				if not re.search("(.html$)", gui.plot_file_E.get()):
					new_name = (gui.plot_file_E.get() + ".html")
					replace_entry(gui.plot_file_E, new_name)

				if os.path.exists(entry.get()):
					if messagebox.askyesno("Override?", ("The file \"" + entry.get() + "\" already exists.  Do you want to override?")):
						try: 
							os.remove(entry.get())
						except: 
							os.remove(entry.get() + ".html")
					else: 
						return False
						
			# Check if output or compile statistics file already exists and if so, ask to override
			if entry == gui.stats_file_E or entry == gui.multi_in_stats_file_E:
				if not re.search("(.csv$)", gui.stats_file_E.get()):
					new_name = (gui.stats_file_E.get() + ".csv")
					replace_entry(gui.stats_file_E, new_name)

				if not re.search("(.csv$)", gui.multi_in_stats_file_E.get()):
					new_name = (gui.multi_in_stats_file_E.get() + ".csv")
					replace_entry(gui.multi_in_stats_file_E, new_name)

				if os.path.exists(entry.get()) or os.path.exists(entry.get() + ".csv"):
					if not messagebox.askyesno("Override?", ("The file \"" + entry.get() + "\" already exists.  Do you want to override?")):
						return False
					try: 
						os.remove(entry.get())
					except:
						try: 
							os.remove(entry.get() + ".csv")
						except:
							messagebox.showerror(("Override Error"), ("Could not override file.  Please close \"" + entry.get() + "\" if open and try again."))
							return False
			
			if not os.path.exists(entry.get()):
				try:
					with open(entry.get(), "a+") as _:
						pass
				except:
					messagebox.showerror((title + " Error"), "Invalid directory/file name.")
					return False
					
				os.remove(entry.get())
			
			return True
			
		def check_time(time, DN):
			"""
				Checks if times provided for daytime start and nighttime start are valid.

				Args:
					time (string): string provided in the entry box
					DN (string): "day" or "night" depending on entry box being analyzed
			"""

			time_re = re.search("(\d+)(:)(\d+)", time)
			show_default_error = False

			# If time found, store hour and minute values
			if time_re:
				hour = int(time_re.group(1))
				minute = int(time_re.group(3))
			else: show_default_error = True
			
			# Detects non-numerical characters (possibly due to use of 12hr, am/pm format)
			if re.search("([^0-9:])", time):
				messagebox.showerror("Start Time Error", (DN + " start time must be entered in 24 hr format."))
				return False
			elif hour < 0 or hour > 23: 
				show_default_error = True
			elif minute < 0 or minute > 59: 
				show_default_error = True

			if show_default_error:
				messagebox.showerror("Start Time Error", ("Invalid " + DN + " start time."))
				return False

			return True

		# Check output
		try:
			os.chdir(self.out_path_E.get())
		except:
			messagebox.showerror("Output Path Error", 
			"Provided output path could not be found. Ensure the path is to a directory not a file (path should end with a slash).")
			return False
			
		if not check_time(self.day_start_E.get(), "day") or not check_time(self.night_start_E.get(), "night"):
			return False
			
		try:
			if not float(self.smoothing_radius_E.get()).is_integer():
				raise ValueError
				
			if not int(self.smoothing_radius_E.get()) >= 0:
				messagebox.showerror("Data Smoothing Radius Error", "Data smoothing radius must be greater than or equal to zero.")
				return False
		except ValueError:
				messagebox.showerror("Data Smoothing Radius Error", "Data smoothing radius must be an integer.")
				return False
		
		try:
			if int(float(self.dur_thresh_E.get())) < 0:
				messagebox.showerror("Duration Threshold Error", "Duration threshold cannot be less than zero.")
				return False
		except ValueError:
			messagebox.showerror("Duration Threshold Error", "Invalid duration threshold (could not convert to integer).")
			return False

		if not check_input_file(self): 
			return False 

		if check_output:
			if self.make_plot_BV.get():
				if not check_out_file(self, self.plot_file_E, "Plot File"): 
					return False

			if self.get_stats_BV.get():
				if not check_out_file(self, self.stats_file_E, "Stats Output File"): 
					return False
					
			if self.multi_in_stats_BV.get() and first_in:
				if not check_out_file(self, self.multi_in_stats_file_E, "Compile Summary"): 
					return False

		return True
	
	def check_valid_plot_ops(self):
		"""
			Checks for valid configuration of all parameters housed on the Plot Options tab.  
		"""

		# Check plot dimensions
		if self.manual_plot_dims.get():
			valid = True
			try:
				if int(self.plot_dim_x_E.get()) < 1 or int(self.plot_dim_y_E.get()) < 1:
					valid = False
			except:
				valid = False
		
			if not valid:
				messagebox.showwarning("Plot Dimensions Warning", 
				("Provided plot dimensions are not valid; please provide positive integers. Automatic resolution detection will be used."))
				self.manual_plot_dims.set(0)
		
		try:
			if float(self.title_font_size_E.get()) < 0:
				raise ValueError("Provided plot title font size is less than 0")
		except ValueError:
			messagebox.showerror("Plot title Font Size Error (Plot Options tab)", "Invalid plot title font size was provided.")
			return False
			
		try:
			if float(self.axis_title_font_size_E.get()) < 0:
				raise ValueError("Provided axis title font size is less than 0")
		except ValueError:
			messagebox.showerror("Axis Title Font Size Error (Plot Options tab)", "Invalid axis title font size was provided.")
			return False
			
		try:
			if float(self.axis_label_font_size_E.get()) < 0:
				raise ValueError("Provided axis label font size is less than 0")
		except ValueError:
			messagebox.showerror("Axis Label Font Size Error (Plot Options tab)", "Invalid axis label font size was provided.")
			return False
			
		try:
			if int(self.axis_tick_size_E.get()) < 0:
				raise ValueError("Provided axis tick size is less than 0")
		except ValueError:
			messagebox.showerror("Axis Tick Size Error (Plot Options tab)", "Invalid axis tick size was provided.")
			return False

		try:
			if float(self.legend_font_size_E.get()) < 0:
				raise ValueError("Provided legend font size is less than 0")
		except ValueError:
			messagebox.showerror("Legend Font Size Error (Plot Options tab)", "Invalid legend font size was provided.")
			return False
		
		# Check plot element sizes/widths
		try:
			if float(self.on_point_size_E.get()) < 0:
				raise ValueError("Provided on-bout point size is less than 0")
		except ValueError:
			messagebox.showerror("Point Size Error (Plot Options tab)", "Invalid on-bout point size was provided.")
			return False
			
		try:
			if float(self.bout_line_width_E.get()) < 0:
				raise ValueError("Provided bout line width is less than 0")
		except ValueError:
			messagebox.showerror("Line Width Error (Plot Options tab)", "Invalid bout line width was provided.")
			return False

		try:
			if float(self.air_line_width_E.get()) < 0:
				raise ValueError("Provided air line width is less than 0")
		except ValueError:
			messagebox.showerror("Line Width Error (Plot Options tab)", "Invalid air temperature line width was provided.")
			return False

		if self.show_day_markers_BV.get():
			try:
				if float(self.day_marker_width_E.get()) < 0:
					raise ValueError("Provided day marker size is less than 0")
			except ValueError:
				messagebox.showerror("Day Marker Size Error (Plot Options tab)", "Invalid day marker size was provided.")
				return False

		return True

	def check_valid_stat_ops(self):
		"""
			Checks for valid configuration of all parameters housed on the Stat Options tab.  
		"""

		try: float(self.time_above_temper_E.get())
		except:
			messagebox.showerror("Custom Temperature Error (Stat Options tab)", "Invalid \"Time above\" temperature.")
			return False
		
		try: float(self.time_below_temper_E.get())
		except:
			messagebox.showerror("Custom Temperature Error (Stat Options tab)", "Invalid \"Time below\" temperature.")
			return False

		return True


	def check_valid_adv(self):	
		"""
			Checks for valid configuration of all parameters housed on the Advanced tab.  
		"""
		def try_autofill():
			"""
				Checks if all Markov model parameter boxes are empty and runs unsupervised learning if so.
			"""

			for entry in (  self.init_off_E, self.init_on_E, self.off_off_trans_E,
							self.off_on_trans_E, self.on_on_trans_E, self.on_off_trans_E,
							self.off_mean_E, self.on_mean_E,
							self.off_stdev_E, self.on_stdev_E
						):
				if entry.get() != "":
					return False
			
			self.unsupervised_learning(auto_run = True)

			return True

		try:
			for entry in (	self.init_off_E, self.init_on_E, self.off_off_trans_E,
							self.off_on_trans_E, self.on_on_trans_E, self.on_off_trans_E
						 ):
				if float(entry.get()) < 0:
					raise ValueError("Probability less than 0 provided.")
		except:
			if self.UL_default_BV.get():
				if try_autofill():
					return True

			messagebox.showerror("Parameter Error (Advanced tab)",
								"Probabilities must be real numbers greater than 0.")

			return False

		try:
			(float(mean) for mean in (self.off_mean_E.get(), self.on_mean_E.get()))

		except TypeError:
			messagebox.showerror("Parameter Error (Advanced tab)",
								"Distribution means must be real numbers.")
			return False
		try:
			for stdev in (self.off_stdev_E.get(), self.on_stdev_E.get()):
				if float(stdev) <= 0:
					raise ValueError("Standard deviation less than 0 provided.")
		except:
			messagebox.showerror("Parameter Error (Advanced tab)",
								"Distribution standard deviations must be real numbers greater than 0.")
			return False
		
		return True
	
	def get_data_time_interval(self, reader, first_line):
		"""
			Attempts to determine the time gap between individual data points and sets self.time_interval
			accordingly.

			Args:
				reader (csv.reader): generator-like object used to get individual lines from the input file
				first_line (list): first line of data from the input file
		"""

		# If interval value is provided in config file, convert to float and return
		if self.time_interval != "auto":
			try:
				self.time_interval = float(self.time_interval)
				return True
			except:
				if self.show_warns_BV.get():
					messagebox.showwarning("Data Interval Parameter Error", 
					"Interval value provided in configuration file is invalid. Automatic detection of data interval will proceed.")

		copy_count = 1
		# Parse until second unique value is found
		cur_line = next(reader)
		while cur_line[self.date_time_col] == first_line[self.date_time_col]:
			cur_line = next(reader)
		
		# Count sequential occurances of second unique value
		ref_line =	cur_line
		cur_line = next(reader)
		while cur_line[self.date_time_col] == ref_line[self.date_time_col]:
			copy_count += 1
			cur_line = next(reader)
		
		if copy_count > 1:
			interval = (1 / copy_count)
		else:
			ref_datetime = niq_misc.get_datetime(self, ref_line)
			cur_datetime = niq_misc.get_datetime(self, cur_line)

			if ref_datetime == False or cur_datetime == False: 
				return False
			interval =  (cur_datetime - ref_datetime).seconds / 60

		self.time_interval = interval
		print("interval =", interval)

		return True

	def get_input_file_name(self):
		"""
			Handles input file browsing and selection.
		"""

		entry = self.input_file_E
		entry.delete(0, "end")
		
		root.update()
		self.master_input = filedialog.askopenfilename(multiple = True)
		root.update()
		
		if self.master_input == "":
			self.master_input = ("",)	
			return 

		if len(self.master_input) == 1:
			entry.insert(0, self.master_input[0])
			
			temp_re = re.search((".*\."), os.path.basename(os.path.normpath(self.master_input[0])))
			if temp_re:
				self.input_root = temp_re.group(0)[:-1]
			else:
				self.input_root = os.path.basename(os.path.normpath(self.master_input[0]))
					
			# Update default names
			replace_entry(self.plot_file_E, (self.input_root + "plot.html"))		
			get_novel_name(self.plot_file_E, (self.input_root + "plot(NUM).html"))
			replace_entry(self.stats_file_E, (self.input_root + "Stats.csv"))
			get_novel_name(self.stats_file_E, (self.input_root + "Stats(NUM).csv"))

		else:
			entry.insert(0, self.master_input)
			replace_entry(self.plot_file_E, "------------------")
			replace_entry(self.stats_file_E, "------------------")
	
	def get_vertex_file(self, entry):	
		"""
			Handles vertex file browsing and selection
		"""		
		root.update()
		path_ = filedialog.askopenfilename(multiple = True)
		root.update()
		
		if path_ != "": 
			replace_entry(entry, path_)				
				
	def get_dir(self, entry):
		"""
			Handles output file directory browsing and selection.

			Args:
				entry (tk.Entry): output file entry box being activated
		"""

		entry.delete(0, "end")
		path_ = ""
		root.update()
		path_ = filedialog.askdirectory()
		root.update()
		entry.insert(0, path_)
		if path_ != "":
			entry.insert(len(path_), "/")
			
	def append_multi_file_stats(self):
		"""
			Dumps cumulative, multi-file statistics into compiled stats file.
		"""

		with open(self.multi_in_stats_file_E.get(), "a") as compiled_stats_file:
			# Used to indictate scope of certain statistics
			qualifier = "(D)," if self.restrict_search_BV.get() else "(DN),"
		
			print("Cumulative Summary", file = compiled_stats_file)
			
			print("Off-Bout Count", qualifier, str(len(self.multi_file_off_durs)), file = compiled_stats_file)
			print("Mean Off Dur", qualifier, str(round(statistics.mean(self.multi_file_off_durs), 2)), file = compiled_stats_file)
			print("Off Dur StDev", qualifier, str(round(statistics.stdev(self.multi_file_off_durs), 2)), file = compiled_stats_file)
			print("Mean Off Temp Drop", qualifier, str(round(statistics.mean(self.multi_file_off_decs), 3)), file = compiled_stats_file)
			print("Off Drop StDev", qualifier, str(round(statistics.stdev(self.multi_file_off_decs), 3)), file = compiled_stats_file)
			
			print("On-Bout Count", qualifier, str(len(self.multi_file_on_durs)), file = compiled_stats_file)
			print("Mean On Dur", qualifier, str(round(statistics.mean(self.multi_file_on_durs), 2)), file = compiled_stats_file)
			print("On Dur StDev", qualifier, str(round(statistics.stdev(self.multi_file_on_durs), 2)), file = compiled_stats_file)
			print("Mean On Temp Rise", qualifier, str(round(statistics.mean(self.milti_in_on_incs), 3)), file = compiled_stats_file)
			print("On Rise StDev", qualifier, str(round(statistics.stdev(self.milti_in_on_incs), 3)), file = compiled_stats_file)
			
			print("Full Day Count,", str(self.milti_in_full_day_count), file = compiled_stats_file)
			print("Mean Egg Temp,", str(round(statistics.mean((self.multi_in_day_tempers + self.multi_in_night_tempers)), 3)), file = compiled_stats_file)
			print("Egg Temp StDev,", str(round(statistics.stdev((self.multi_in_day_tempers + self.multi_in_night_tempers)), 3)), file = compiled_stats_file)
			print("Mean Daytime Egg Temp,", str(round(statistics.mean(self.multi_in_day_tempers), 3)), file = compiled_stats_file)
			print("Day Egg Temp StDev,", str(round(statistics.stdev(self.multi_in_day_tempers), 3)), file = compiled_stats_file)
			print("Mean Nighttime Egg Temp,", str(round(statistics.mean(self.multi_in_night_tempers), 3)), file = compiled_stats_file)
			print("Night Egg Temp StDev,", str(round(statistics.stdev(self.multi_in_night_tempers), 3)), file = compiled_stats_file)
			print("Min Egg Temp,", str(min(self.multi_in_day_tempers + self.multi_in_night_tempers)), file = compiled_stats_file)
			print("Max Egg Temp,", str(max(self.multi_in_day_tempers + self.multi_in_night_tempers)), file = compiled_stats_file)
			
			if self.air_valid:
				print("Mean Air Temp,", str(round(statistics.mean(self.multi_in_air_tempers), 3)), file = compiled_stats_file)
				print("Air Temp StDev,", str(round(statistics.stdev(self.multi_in_air_tempers), 3)), file = compiled_stats_file)
				print("Min Air Temp,", str(min(self.multi_in_air_tempers)), file = compiled_stats_file)
				print("Max Air Temp,", str(max(self.multi_in_air_tempers)), file = compiled_stats_file)
					
			print("\n\n", file = compiled_stats_file)
	
	def reset_multi_file_var(self):
		"""
			Resets variables used to store data across multiple input files.
		"""

		self.multi_file_off_durs     = []
		self.multi_file_off_decs     = []
		self.multi_file_on_durs      = []
		self.milti_in_on_incs        = []
		self.multi_in_day_tempers    = []
		self.multi_in_night_tempers  = []		
		self.multi_in_air_tempers    = []
		self.milti_in_full_day_count = 0
	
	def select_vertices(self):
		"""
			Generates special plot for the user to select their ideal vertex locations. This plot can be 
			saved and later used for supervised parameter acquisition.
		"""
		days_list = []
		nights_list = []
		
		if self.check_valid_plot_ops() and self.check_valid_main(check_output = False) and self.check_valid_adv():			
			try:
				self.master_list = niq_misc.get_master_list(self, self.input_file_E.get())
				self.master_array = niq_misc.get_master_arr(self, self.master_list)
				self.master_block = niq_classes.Block(self, 0, (len(self.master_list) - 1), False)
				
				# Get days_list and nights_list for plotting vertical lines
				days_list, nights_list = niq_misc.split_days(self)
			except Exception:
				messagebox.showerror(("Input File Error (Advanced tab)"), 
				"Input file could not be processed. Try using the \"Check\" button in the main tab to identify the issue.")	
				traceback.print_exc()
				return False
			
			niq_misc.generate_plot(self, self.master_array, days_list, select_mode = True)
				
	def init_config(self):
		"""
			Initializes GUI from default_config.ini.  config_static.ini is used as a backup if anything goes wrong.
		"""
		self.config = configparser.RawConfigParser()
		# (flag) dont forget to add this file
		if not os.path.exists(os.path.join(self.core_dir, "config_files", "default_config.ini")):
			copyfile(os.path.join(self.core_dir, "misc_files", "config_static.ini"), 
					os.path.join(self.core_dir, "config_files", "default_config.ini"))
					
		self.config.read(os.path.join(self.core_dir, "config_files", "default_config.ini"))

	def update_config(self, config_file = None):
		"""
			Generates a configuration file from the current GUI parameters. If no file name if provided,
			this function saves to default_config.ini, resetting the default parameters for NestIQ.

			Args:
				config_file (string): path to and name of file to be saved
		"""

		if config_file is None:
			config_file = os.path.join(self.core_dir, "config_files", "default_config.ini")

		self.config.set("Main Settings", "output_dir", self.out_path_E.get())
		self.config.set("Main Settings", "show_warnings", self.show_warns_BV.get())
		self.config.set("Main Settings", "day_start_time", self.day_start_E.get())
		self.config.set("Main Settings", "night_start_time", self.night_start_E.get())
		self.config.set("Main Settings", "restrict_bout_search", self.restrict_search_BV.get())

		self.config.set("Main Settings", "smoothing_radius", self.smoothing_radius_E.get())
		self.config.set("Main Settings", "duration_threshold", self.dur_thresh_E.get())

		self.config.set("Advanced Settings", "run_unsup_by_default", self.UL_default_BV.get())
		self.config.set("Advanced Settings", "off_bout_initial", self.init_off_E.get())
		self.config.set("Advanced Settings", "on_bout_initial", self.init_on_E.get())
		self.config.set("Advanced Settings", "off_off_trans", self.off_off_trans_E.get())
		self.config.set("Advanced Settings", "off_on_trans", self.off_on_trans_E.get())
		self.config.set("Advanced Settings", "on_on_trans", self.on_on_trans_E.get())
		self.config.set("Advanced Settings", "on_off_trans", self.on_off_trans_E.get())
		self.config.set("Advanced Settings", "off_bout_emis_mean", self.off_mean_E.get())
		self.config.set("Advanced Settings", "off_bout_emis_stdev", self.off_stdev_E.get())
		self.config.set("Advanced Settings", "on_bout_emis_mean", self.on_mean_E.get())
		self.config.set("Advanced Settings", "on_bout_emis_stdev", self.on_stdev_E.get())
		
		self.config.set("Plot Options", "manual_plot_dimensions", bool(self.manual_plot_dims.get()))
		self.config.set("Plot Options", "plot_x_dim", self.plot_dim_x_E.get())
		self.config.set("Plot Options", "plot_y_dim", self.plot_dim_y_E.get())
		self.config.set("Plot Options", "title_font_size", self.title_font_size_E.get())
		self.config.set("Plot Options", "axis_title_font_size", self.axis_title_font_size_E.get())
		self.config.set("Plot Options", "axis_label_font_size", self.axis_label_font_size_E.get())
		self.config.set("Plot Options", "axis_tick_size", self.axis_tick_size_E.get())
		self.config.set("Plot Options", "legend_font_size", self.legend_font_size_E.get())
		
		self.config.set("Plot Options", "plot_egg_tempers", self.plot_egg_BV.get())
		self.config.set("Plot Options", "plot_air_tempers", self.plot_air_BV.get())
		self.config.set("Plot Options", "plot_egg_minus_air", self.plot_delta_BV.get())
		self.config.set("Plot Options", "plot_smoothed", bool(self.smooth_status_IV.get()))
		self.config.set("Plot Options", "legend_location", self.legend_loc.get())

		self.config.set("Plot Options", "on_point_color", self.on_point_color.get())
		self.config.set("Plot Options", "off_point_color", self.off_point_color.get())
		self.config.set("Plot Options", "bout_line_color", self.bout_line_color.get())
		self.config.set("Plot Options", "air_line_color", self.air_line_color.get())
		self.config.set("Plot Options", "day_marker_color", self.day_marker_color.get())
		
		self.config.set("Plot Options", "on_point_size", self.on_point_size_E.get())
		self.config.set("Plot Options", "bout_line_width", self.bout_line_width_E.get())
		self.config.set("Plot Options", "air_line_width", self.air_line_width_E.get())
		self.config.set("Plot Options", "day_marker_width", self.day_marker_width_E.get())
		
		self.config.set("Plot Options", "show_day_marker", self.show_day_markers_BV.get())
		self.config.set("Plot Options", "show_grid", self.show_grid_BV.get())

		self.config.set("Stats Options", "day_number", self.day_num_BV.get())
		self.config.set("Stats Options", "date", self.date_BV.get())
		self.config.set("Stats Options", "off_bout_count", self.off_count_BV.get())
		self.config.set("Stats Options", "mean_off_bout_duration", self.off_dur_BV.get())
		self.config.set("Stats Options", "off_bout_duration_stdev", self.off_dur_sd_BV.get())
		self.config.set("Stats Options", "mean_off_bout_temp_drop", self.off_dec_BV.get())
		self.config.set("Stats Options", "off_bout_temp_drop_stdev", self.off_dec_sd_BV.get())
		self.config.set("Stats Options", "mean_off_bout_temp", self.mean_off_temper_BV.get())
		self.config.set("Stats Options", "off_bout_time_sum", self.off_time_sum_BV.get())
		self.config.set("Stats Options", "on_bout_count", self.on_count_BV.get())
		self.config.set("Stats Options", "mean_on_bout_duration", self.on_dur_BV.get())
		self.config.set("Stats Options", "on_bout_duration_stdev", self.on_dur_sd_BV.get())
		self.config.set("Stats Options", "mean_on_bout_temp_rise", self.on_inc_BV.get())
		self.config.set("Stats Options", "on_bout_temp_rise_stdev", self.on_inc_sd_BV.get())
		self.config.set("Stats Options", "mean_on_bout_temp", self.mean_on_temper_BV.get())
		self.config.set("Stats Options", "on_bout_time_sum", self.on_time_sum_BV.get())
		self.config.set("Stats Options", "time_above_critical", self.time_above_temper_BV.get())
		self.config.set("Stats Options", "time_below_critical", self.time_below_temper_BV.get())
		self.config.set("Stats Options", "bouts_dropped", self.bouts_dropped_BV.get())
		self.config.set("Stats Options", "mean_daytime_temperature", self.mean_temper_d_BV.get())
		self.config.set("Stats Options", "daytime_temp_stdev", self.mean_temper_d_sd_BV.get())
		self.config.set("Stats Options", "median_daytime_temp", self.median_temper_d_BV.get())
		self.config.set("Stats Options", "min_daytime_temp", self.min_temper_d_BV.get())
		self.config.set("Stats Options", "max_daytime_temp", self.max_temper_d_BV.get())
		self.config.set("Stats Options", "mean_nighttime_temp", self.mean_temper_n_BV.get())
		self.config.set("Stats Options", "nighttime_temp_stdev", self.mean_temper_n_sd_BV.get())
		self.config.set("Stats Options", "median_nighttime_temp", self.median_temper_n_BV.get())
		self.config.set("Stats Options", "min_nighttime_temp", self.min_temper_n_BV.get())
		self.config.set("Stats Options", "max_nighttime_temp", self.max_temper_n_BV.get())
		self.config.set("Stats Options", "mean_daynight_temp", self.mean_temper_dn_BV.get())
		self.config.set("Stats Options", "daynight_temp_stdev", self.mean_temper_dn_sd_BV.get())
		self.config.set("Stats Options", "median_daynight_temp", self.median_temper_dn_BV.get())
		self.config.set("Stats Options", "min_daynight_temp", self.min_temper_dn_BV.get())
		self.config.set("Stats Options", "max_daynight_temp", self.max_temper_dn_BV.get())
		self.config.set("Stats Options", "mean_air_temp", self.mean_air_temper_BV.get())
		self.config.set("Stats Options", "mean_air_temp_stdev", self.mean_air_temper_sd_BV.get())		
		self.config.set("Stats Options", "min_air_temp", self.min_air_temper_BV.get())
		self.config.set("Stats Options", "max_air_temp", self.max_air_temper_BV.get())
		self.config.set("Stats Options", "custom_time_over_bool", self.time_above_temper_BV.get())
		self.config.set("Stats Options", "custom_time_below_bool", self.time_below_temper_BV.get())

		self.config.set("Stats Options", "custom_time_above_temperature", self.time_above_temper_E.get())
		self.config.set("Stats Options", "custom_time_below_temperature", self.time_below_temper_E.get())
		
		with open(config_file, "w") as configFile_:
			self.config.write(configFile_)
	
	# Check ensure valid parameters and execute processing
	def trigger_run(self, root):
		"""
			Ensure everything is in order and if so, initiate processing of the input file(s).

			Args:
				root (tk root widget): base widget of GUI
		"""

		# flag
		try:
			print("----------------------------------------------------------")
			print("Running NestIQ")

			self.run, valid_run, successful = True, True, True
			self.reset_multi_file_var()

			if len(self.master_input) == 0 or self.master_input == ("",):
				self.master_input = (self.input_file_E.get(),)

			for file_num, in_file in enumerate(self.master_input, 1):
				in_file = in_file.lstrip("{").rstrip("}")

				self.time_interval = self.config.get("Main Settings", "data_time_interval")
				self.air_valid = True

				if len(self.master_input) == 1:
					self.run_B["text"] = "Running..."
					self.run_B.config(bg = "gray", fg = "white", width = 10, height = 1)
					root.update()
				else:
					self.update_multi_in_default_outs(in_file)
					self.run_B["text"] = ("Running (file " + str(file_num) + ")...")
					self.run_B.config(bg = "gray", fg = "white", width = 15, height = 1)

				# Check if all inputs are valid
				if not (self.check_valid_main(check_output = (file_num == 1)) and 
						self.check_valid_adv() and
						self.check_valid_plot_ops() and
						self.check_valid_stat_ops()
					   ):
					successful = False
					break
					
				print("Active file:", in_file)

				self.master_hmm = niq_hmm.HMM()
				self.master_hmm.build_model_from_entries(self)
				self.master_list = niq_misc.get_master_list(self, in_file)
				self.master_array = niq_misc.get_master_arr(self, self.master_list)
				self.master_hmm.normalize_params(self)
				self.master_hmm.populate_hmm_entries(self)

				# Adds state column to master_array of input file
				self.master_array = self.master_hmm.decode(self.master_array)
				
				dur_thresh = int(self.dur_thresh_E.get())
				self.master_array, self.bouts_dropped_locs = niq_misc.filter_by_dur(self.master_array, dur_thresh)

				# flag
				try: 
					main(self)
				except:
					successful = False
					traceback.print_exc()
					break

				self.update_default_outs()

			if all((successful, self.multi_in_stats_BV.get(), len(self.master_input) > 1)):
				self.append_multi_file_stats()	

			if re.search(("[^\{\}]"), "".join(self.master_input)):
				replace_entry(self.input_file_E, self.master_input)

			replace_entry(self.input_file_E, self.input_file_E.get().lstrip("{").rstrip("}"))

			self.master_input = tuple()

			self.run_B["text"] = "Run"
			self.run_B.config(bg = "red4", fg = "white", width = 10, height = 1)
			self.run = False
			print("Done")

		except Exception:
			traceback.print_exc()
			messagebox.showerror(("Unidentified Error"), "An unknown error has occerred." +
			"Please report this error to NestIQHelp@gmail.com")
		
	def close_niq(self, root):
		"""
			Cleanly terminates the program.

			Args:
				root (tk root widget): base of GUI
		"""
		self.valid = False
		root.destroy()

	def daytime_mod(self, nights_list, master_array):
		"""
			Sets state of nightime data points to "nonsense" value of 2. These points will be ignored for the
			majority of downstream statistical calculations.

			Args:
				nights_list (list of blocks): used to get boudaries for nightime data points
				master_array (numpy array): master array which will have states column modified
		"""

		for night in nights_list:
			master_array[night.start:night.stop, 6] = 2

		return master_array	

	def unsupervised_learning(self, auto_run = False):
		"""
			Prepares master array from input data, runs the baum welch algorithm, and populates the GUI with
			resulting parameters.

			Args:
				auto_run (bool): False if this function call is from clicking button on the Advanced tab
		"""

		self.run_B["text"] = "Learning..."
		self.run_B.config(bg = "gray", fg = "white", width = 10, height = 1)
		root.update()

		input_ = niq_misc.extract_in_files(self.input_file_E.get())
		if len(input_) > 1:
			messagebox.showerror(("Unsupervised Learning Error"), 
			"Multiple input files provided. Unsupervised learning currently only supports single input files.")	
			return False

		# If auto_run, check_valid_main will be called in trigger_run
		if not auto_run:
			if not self.check_valid_main(check_output = False):
				self.run_B["text"] = "Run"
				self.run_B.config(bg = "red4", fg = "white", width = 10, height = 1)
				self.run = False	
				root.update()
				return False

		self.master_hmm = niq_hmm.HMM()
		self.master_list = niq_misc.get_master_list(self, input_[0])
		self.master_array = niq_misc.get_master_arr(self, self.master_list)
		emis_arr = self.master_array[:, 5]
		emis_arr = emis_arr.reshape(-1, 1)				
		self.master_hmm.baum_welch(emis_arr)
		self.master_hmm.populate_hmm_entries(self)

		self.run_B["text"] = "Run"
		self.run_B.config(bg = "red4", fg = "white", width = 10, height = 1)
		self.run = False			

	def supervised_learning(self):
		"""
			Calculates model parameters from user-provided vertex locations.
		"""

		input_ = niq_misc.extract_in_files(self.input_file_E.get())
		if len(input_) > 1:
			messagebox.showerror(("Supervised Learning Error"), 
			"Multiple input files provided. Please provide the single input file used to generate the vertex selection file.")	
			return False

		self.master_hmm = niq_hmm.HMM()

		if self.check_vertex_file():
			in_file = self.input_file_E.get()
			self.master_list = niq_misc.get_master_list(self, in_file)
			self.master_array = niq_misc.get_master_arr(self, self.master_list)

			training_verts = []
			training_verts = niq_misc.get_verts_from_html(self, self.vertex_file_E.get())
			self.master_hmm.extract_params_from_verts(self.master_array, training_verts)
			self.master_hmm.normalize_params(self)
			self.master_hmm.populate_hmm_entries(self)


def main(gui):
	"""
		Performs some final data reorganization and then executes all of the core data analyzation
		function. Vertex locations are initially collected for the entire file. These vertices are later
		allocated to individual day and night objects. Day/night pairs are grouped to represent full
		24 hr periods. Finally, "BlockGroup" objects are created for each of these three categories
		for the calculation of broader statistics.

		Args:
			gui (GUIClass)
	"""

	days_list, nights_list = niq_misc.split_days(gui)

	if gui.restrict_search_BV.get():
		gui.master_array = gui.daytime_mod(nights_list, gui.master_array)

	# Store all vertices in master block object for later allocation
	master_block = niq_classes.Block(gui, 0, (len(gui.master_list) - 1), False)
	master_block.vertices = niq_misc.get_verts_from_master_arr(gui.master_array)

	# Extract bouts based on vertex locations	
	niq_misc.get_bouts(gui, master_block)
	if not master_block.get_stats(gui):
		return False
	
	if not gui.restrict_search_BV.get():
		master_block.deposit_multi_file_stats(gui)
	if gui.air_valid:
		gui.multi_in_air_tempers += master_block.air_tempers
	
	master_block.vertices.sort(key = lambda x: x.index)

	for day in days_list:
		day.vertices = niq_misc.extract_verts_in_range(gui, master_block.vertices, day.start, day.stop)
		niq_misc.get_bouts(gui, day)
		day.get_stats(gui)
		gui.multi_in_day_tempers += day.egg_tempers
		
		if gui.restrict_search_BV.get():
			day.deposit_multi_file_stats(gui)
		
	for night in nights_list:
		if not gui.restrict_search_BV.get():
			night.vertices = niq_misc.extract_verts_in_range(gui, master_block.vertices, night.start, night.stop)
			niq_misc.get_bouts(gui, night)
		night.get_stats(gui)
		gui.multi_in_night_tempers += night.egg_tempers
		
	days = niq_classes.BlockGroup(gui, days_list)	
	if len(days_list) > 0:
		days.get_stats(gui, append = False)

	nights = niq_classes.BlockGroup(gui, nights_list)
	if len(nights_list) > 0:
		nights.get_stats(gui, append = False)

	pairs_list = []
	if len(days_list) > 0 and len(nights_list) > 0:
		pairs_list = niq_misc.get_day_night_pairs(gui, days_list, nights_list)
		for pair in pairs_list:
			if not gui.restrict_search_BV.get():
				pair.vertices = niq_misc.extract_verts_in_range(gui, master_block.vertices, pair.start, pair.stop)
				niq_misc.get_bouts(gui, pair)
			pair.get_stats(gui)
	
	pairs_block_group = niq_classes.BlockGroup(gui, pairs_list)
	if len(pairs_list) > 0:
		pairs_block_group.get_stats(gui, append = False)
	if gui.make_plot_BV.get():
		niq_misc.generate_plot(gui, gui.master_array, days_list)

	if gui.get_stats_BV.get():
		niq_misc.write_stats(gui, days, nights, pairs_block_group, master_block)

gui = GUIClass()
