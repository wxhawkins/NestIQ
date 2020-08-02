import datetime
import json
import subprocess
import time
import tkinter as tk
import traceback
from pathlib import Path
from shutil import copyfile
from tkinter import filedialog, font, messagebox, ttk

import numpy as np
import pandas as pd
from PIL import Image, ImageTk
from termcolor import colored

import niq_classes
import niq_hmm
import niq_misc
import testing
from check_valid import (check_valid_adv, check_valid_main,
                         check_valid_plot_ops, check_valid_stat_ops,
                         check_valid_vertex_file)
from configuration import init_config, load_config, save_config, set_defaults
from niq_misc import convert_to_datetime, remove_curly, replace_entry, set_unique_path

root = tk.Tk()
STANDARD_FONT = font.Font(size=10)
HELP_FONT = font.Font(size=8)
HEADER_FONT = font.Font(size=12, weight="bold")
SUBHEADER_FONT = "Helvetica 10 bold"
TITLE_FONT = ("Helvetica", 18)

root.iconbitmap(Path.cwd().parent / "misc_files" / "NestIQ.ico")


class GUIClass:
    """
        Large class storing all information present on the graphical user interface: parameters, file names,
        output options, etc. This class also stores a lot of critical information not displayed on the user
        interface as well as many methods for interacting/altering the GUI.
	"""

    def __init__(self, root):
        self.root = root

        # Store core working directory path
        self.master_dir_path = Path.cwd().parent
        init_config(self)

        # Variables used for storing information accross multiple input files
        self.multi_file_off_durs = []
        self.multi_file_off_decs = []
        self.multi_file_on_durs = []
        self.multi_in_on_incs = []
        self.multi_in_day_tempers = []
        self.multi_in_night_tempers = []
        self.multi_in_air_tempers = []
        self.multi_in_full_day_count = 0

        self.time_interval = None
        self.air_valid = True
        self.bouts_dropped_locs = set()

        self.master_hmm = niq_hmm.HMM()

        # Configure root
        self.root.wm_title("NestIQ")
        self.root.geometry("370x720")
        self.root.configure(background="white")

        # Create 1 x 30 grid
        for row in range(30):
            self.root.rowconfigure(row, weight=1)

        self.root.columnconfigure(0, weight=1)
        nb = ttk.Notebook(self.root)
        nb.grid(row=1, rowspan=28, columnspan=1, sticky="NESW")

        tab1 = ttk.Frame(nb)
        tab2 = ttk.Frame(nb)
        tab3 = ttk.Frame(nb)
        tab4 = ttk.Frame(nb)
        tab5 = ttk.Frame(nb)

        nb.add(tab1, text="Main")
        nb.add(tab2, text="Advanced")
        nb.add(tab3, text="Plot Options")
        nb.add(tab4, text="Stats Options")

        # ----------------------------------------------- Main tab ---------------------------------------------------
        # ----- Header -----
        title_background = tk.Label(tab1, text="", bg="red4")
        title_background.grid(row=0, sticky="NSEW")

        title_L = tk.Label(tab1, text="NestIQ", fg="white", bg="red4", font=TITLE_FONT)
        title_L.grid(row=0, sticky="NSW", padx=10, pady=5)

        help_B = tk.Button(tab1, text="Help", command=self.help)
        help_B.grid(row=0, sticky="NW", padx=335)
        help_B.configure(width=4, height=0)
        help_B["font"] = HELP_FONT

        # ----- Input file -----
        self.input_file_L = tk.Label(tab1, text="Input file:", font=SUBHEADER_FONT)
        self.input_file_L.grid(row=1, sticky="W", padx=10, pady=(5, 0))
        self.input_file_E = tk.Entry(tab1, width=33)
        self.input_file_E.grid(row=1, sticky="W", padx=77, pady=(10, 0))
        self.input_file_B = tk.Button(tab1, text="Browse File", command=(lambda: self.get_input_file_name()))
        self.input_file_B.grid(row=1, sticky="W", padx=285, pady=(10, 0))
        self.input_file_B.configure(background="white")

        # ----- Plot file -----
        self.make_plot_BV = tk.BooleanVar()
        self.plot_CB = tk.Checkbutton(tab1, text="Generate Plot", variable=self.make_plot_BV, font=STANDARD_FONT)
        self.plot_CB.grid(row=7, sticky="W", padx=10)

        self.edit_mode_BV = tk.BooleanVar()
        self.edit_mode_CB = tk.Checkbutton(tab1, text="Edit mode", variable=self.edit_mode_BV, font=STANDARD_FONT)
        self.edit_mode_CB.grid(row=8, sticky="W", padx=27)
        
        self.plot_file_E = tk.Entry(tab1, width=44)
        self.plot_file_E.grid(row=9, sticky="W", padx=33)

        self.plot_save_as_B = tk.Button(tab1, text="Save as", command=(lambda: self.handle_save_as(self.plot_file_E)))
        self.plot_save_as_B.grid(row=9, sticky="W", padx=308)
        self.plot_save_as_B.configure(background="white")

        # Initialize
        set_unique_path(self.plot_file_E, self.master_dir_path / "output_files" / "niq_plot", ".html")
        self.plot_CB.select()

        # ----- Statistics file -----
        self.get_stats_BV = tk.BooleanVar()
        self.stats_CB = tk.Checkbutton(tab1, text="Output Statistics", variable=self.get_stats_BV, font=STANDARD_FONT)
        self.stats_CB.grid(row=10, sticky="NW", padx=10, pady=(10, 0))

        self.stats_file_E = tk.Entry(tab1, width=44)
        self.stats_file_E.grid(row=11, sticky="W", padx=33)

        self.stats_save_as_B = tk.Button(tab1, text="Save as", command=(lambda: self.handle_save_as(self.stats_file_E)))
        self.stats_save_as_B.grid(row=11, sticky="W", padx=308)
        self.stats_save_as_B.configure(background="white")

        # Initialize
        set_unique_path(self.stats_file_E, self.master_dir_path / "output_files" / "niq_stats", ".csv")
        self.stats_CB.select()

        # ----- Multi-file statistics file -----
        self.multi_in_stats_BV = tk.BooleanVar()
        self.multi_in_stats_CB = tk.Checkbutton(tab1, text="Compile Statistics", variable=self.multi_in_stats_BV, font=STANDARD_FONT)
        self.multi_in_stats_CB.grid(row=12, sticky="W", padx=10, pady=(10, 0))

        self.multi_in_stats_file_E = tk.Entry(tab1, width=44)

        self.multi_in_stats_save_as_B = tk.Button(tab1, text="Save as", command=(lambda: self.handle_save_as(self.multi_in_stats_file_E)))
        self.multi_in_stats_save_as_B.grid(row=13, sticky="W", padx=308)
        self.multi_in_stats_save_as_B.configure(background="white")

        # Initialize
        set_unique_path(self.multi_in_stats_file_E, self.master_dir_path / "output_files" / "multi_file_stats", ".csv")

        ttk.Separator(tab1, orient="horizontal").grid(row=14, sticky="NSEW", pady=(20, 10))

        # ----- Daytime/nighttime -----
        daytime_L = tk.Label(tab1, text="Daytime period:                to", font=STANDARD_FONT)
        self.day_start_E = tk.Entry(tab1, width=7)
        self.night_start_E = tk.Entry(tab1, width=7)

        daytime_L.grid(row=19, sticky="W", padx=10)
        self.day_start_E.grid(row=19, sticky="W", padx=110)
        self.night_start_E.grid(row=19, sticky="W", padx=190)

        self.restrict_search_BV = tk.BooleanVar()
        self.restrict_search_CB = tk.Checkbutton(tab1, text="Restrict analysis to daytime", variable=self.restrict_search_BV, font=STANDARD_FONT)
        self.restrict_search_CB.grid(row=21, sticky="NW", padx=10, pady=(10, 0))

        # ----- Core algorithm parameters -----
        smoothing_radius_L = tk.Label(tab1, text="Data smoothing radius:", font=STANDARD_FONT)
        smoothing_radius_L.grid(row=23, sticky="W", padx=10, pady=(30, 0))
        self.smoothing_radius_E = tk.Entry(tab1, width=5)
        self.smoothing_radius_E.grid(row=23, sticky="W", padx=207, pady=(30, 0))

        dur_thresh_L = tk.Label(tab1, text="Duration threshold (data points):", font=STANDARD_FONT)
        dur_thresh_L.grid(row=24, sticky="W", padx=10, pady=10)
        self.dur_thresh_E = tk.Entry(tab1, width=5)
        self.dur_thresh_E.grid(row=24, sticky="W", padx=207)

        # ----- Training (emission) values -----
        train_from_L = tk.Label(tab1, text="Train from:", font=STANDARD_FONT)
        train_from_L.grid(row=25, sticky="W", padx=10)

        self.train_from_IV = tk.IntVar()
        egg_RB = tk.Radiobutton(tab1, text="Egg temperature", variable=self.train_from_IV, value=0)
        egg_RB.grid(row=26, sticky="W", padx=30)
        adj_RB = tk.Radiobutton(tab1, text="Adjusted temperature", variable=self.train_from_IV, value=1)
        adj_RB.grid(row=27, sticky="W", padx=30)

        # Display and retract file entry boxes based on selection status
        def main_tab_callback(*args):
            if self.make_plot_BV.get():
                self.edit_mode_CB.grid(row=8, sticky="W", padx=27)
                self.plot_file_E.grid(row=9, sticky="W", padx=32)
                self.plot_save_as_B.grid(row=9, sticky="W", padx=308)
                self.plot_save_as_B.configure(background="white")
            else:
                self.edit_mode_CB.grid_forget()
                self.plot_file_E.grid_forget()
                self.plot_save_as_B.grid_forget()

            if self.get_stats_BV.get():
                self.stats_file_E.grid(row=11, sticky="W", padx=33)
                self.stats_save_as_B.grid(row=11, sticky="W", padx=308)
                self.stats_save_as_B.configure(background="white")

            else:
                self.stats_file_E.grid_forget()
                self.stats_save_as_B.grid_forget()

            if self.multi_in_stats_BV.get():
                self.multi_in_stats_file_E.grid(row=13, sticky="W", padx=33)
                self.multi_in_stats_save_as_B.grid(row=13, sticky="W", padx=308)
                self.multi_in_stats_save_as_B.configure(background="white")

            else:
                self.multi_in_stats_file_E.grid_forget()
                self.multi_in_stats_save_as_B.grid_forget()

        main_tab_callback()

        # Establish tracing
        self.make_plot_BV.trace("w", main_tab_callback)
        self.get_stats_BV.trace("w", main_tab_callback)
        self.multi_in_stats_BV.trace("w", main_tab_callback)

        # ------------------------------------------------- Advanced tab -------------------------------------------------
        # ----- Header -----
        tab4BG = tk.Label(tab2, text="", bg="red4")
        tab4BG.grid(row=2, sticky="NSEW")

        save_config_B = tk.Button(tab2, text="Save Settings", command=(lambda: save_config(self)))
        save_config_B.grid(row=2, sticky="W", padx=10, pady=(10, 10))
        save_config_B.configure(background="white")

        load_config_B = tk.Button(tab2, text="Load Settings", command=(lambda: load_config(self)))
        load_config_B.grid(row=2, sticky="W", padx=97, pady=(10, 10))
        load_config_B.configure(background="white")

        save_defaults_B = tk.Button(tab2, text="Set as Default", command=(lambda: set_defaults(self)))
        save_defaults_B.grid(row=2, sticky="W", padx=275, pady=(10, 10))
        save_defaults_B.configure(background="white")

        # ----- Unsupervised learning -----
        UL_train_B = tk.Button(tab2, text="Unsupervised Learning", command=(lambda: self.unsupervised_learning()))
        UL_train_B.grid(row=5, sticky="W", padx=10, pady=(10, 0))
        UL_train_B.configure(background="white")

        self.UL_default_BV = tk.BooleanVar()
        self.UL_default_CB = tk.Checkbutton(tab2, text="Run unsup. learning by defualt", variable=self.UL_default_BV, font=STANDARD_FONT)
        self.UL_default_CB.grid(row=5, sticky="NW", padx=150, pady=(10, 0))

        # ----- Supervised learning -----
        SL_train_B = tk.Button(tab2, text="Supervised Learning", command=(lambda: self.supervised_learning()))
        SL_train_B.grid(row=6, sticky="W", padx=10, pady=(10, 0))
        SL_train_B.configure(background="white")

        select_verticies_B = tk.Button(tab2, text="Select Vertices", command=(lambda: self.select_vertices()))
        select_verticies_B.grid(row=6, sticky="W", padx=133, pady=(10, 0))
        select_verticies_B.configure(background="white")

        vertex_file_L = tk.Label(tab2, text="Vertex File:", font=STANDARD_FONT)
        vertex_file_L.grid(row=10, sticky="W", padx=10, pady=(10, 0))
        self.vertex_file_E = tk.Entry(tab2, width=32)
        self.vertex_file_E.grid(row=10, sticky="W", padx=85, pady=(10, 0))
        vertex_file_B = tk.Button(tab2, text="Browse File", command=(lambda: self.get_plot_file(self.vertex_file_E)))
        vertex_file_B.grid(row=10, sticky="W", padx=287, pady=(10, 0))
        vertex_file_B.configure(background="white")

        # ----- Iniitial probabilities -----
        init_probs_L = tk.Label(tab2, text="Initial Probabilities:", font=SUBHEADER_FONT)
        init_probs_L.grid(row=12, sticky="W", padx=10, pady=(30, 0))

        ttk.Separator(tab2, orient="horizontal").grid(row=13, sticky="NSEW", pady=(0, 10))

        tk.Label(tab2, text="Off", font=STANDARD_FONT).grid(row=14, sticky="W", padx=120)
        tk.Label(tab2, text="On", font=STANDARD_FONT).grid(row=14, sticky="W", padx=220)

        self.init_off_E = tk.Entry(tab2, width=10)
        self.init_off_E.grid(row=15, sticky="W", padx=120)
        self.init_on_E = tk.Entry(tab2, width=10)
        self.init_on_E.grid(row=15, sticky="W", padx=220)

        # ----- Transition probabilities -----
        trans_probs_L = tk.Label(tab2, text="Transition Probabilites:", font=SUBHEADER_FONT)
        trans_probs_L.grid(row=16, sticky="W", padx=10, pady=(20, 0))

        ttk.Separator(tab2, orient="horizontal").grid(row=17, sticky="NSEW", pady=(0, 10))

        x_axis_off_L = tk.Label(tab2, text="Off", font=STANDARD_FONT)
        x_axis_off_L.grid(row=18, sticky="W", padx=120)
        x_axis_on_L = tk.Label(tab2, text="On", font=STANDARD_FONT)
        x_axis_on_L.grid(row=18, sticky="W", padx=220)

        y_axis_off_L = tk.Label(tab2, text="Off", font=STANDARD_FONT)
        y_axis_off_L.grid(row=19, sticky="W", padx=90)
        y_axis_on_L = tk.Label(tab2, text="On", font=STANDARD_FONT)
        y_axis_on_L.grid(row=20, sticky="W", padx=90)

        self.off_off_trans_E = tk.Entry(tab2, width=10)
        self.off_off_trans_E.grid(row=19, sticky="W", padx=120)
        self.off_on_trans_E = tk.Entry(tab2, width=10)
        self.off_on_trans_E.grid(row=19, sticky="W", padx=220)
        self.on_off_trans_E = tk.Entry(tab2, width=10)
        self.on_off_trans_E.grid(row=20, sticky="W", padx=120)
        self.on_on_trans_E = tk.Entry(tab2, width=10)
        self.on_on_trans_E.grid(row=20, sticky="W", padx=220)

        # ----- Temperature change distribution -----
        distrib_params_L = tk.Label(tab2, text="Temperature Change Parameters:", font=SUBHEADER_FONT)
        distrib_params_L.grid(row=23, sticky="W", padx=10, pady=(20, 0))

        separator = ttk.Separator(tab2, orient="horizontal")
        separator.grid(row=24, sticky="NSEW", pady=(0, 10))

        distrib_mean_L = tk.Label(tab2, text="Mean", font=STANDARD_FONT)
        distrib_mean_L.grid(row=25, sticky="W", padx=120)
        distrib_stdev_L = tk.Label(tab2, text="Std. Deviation", font=STANDARD_FONT)
        distrib_stdev_L.grid(row=25, sticky="W", padx=220)

        distrib_off_L = tk.Label(tab2, text="Off", font=STANDARD_FONT)
        distrib_off_L.grid(row=26, sticky="W", padx=90)
        distrib_on_L = tk.Label(tab2, text="On", font=STANDARD_FONT)
        distrib_on_L.grid(row=27, sticky="W", padx=90)

        self.off_mean_E = tk.Entry(tab2, width=10)
        self.off_mean_E.grid(row=26, sticky="W", padx=120)
        self.on_mean_E = tk.Entry(tab2, width=10)
        self.on_mean_E.grid(row=27, sticky="W", padx=120)
        self.off_stdev_E = tk.Entry(tab2, width=10)
        self.off_stdev_E.grid(row=26, sticky="W", padx=220)
        self.on_stdev_E = tk.Entry(tab2, width=10)
        self.on_stdev_E.grid(row=27, sticky="W", padx=220)

        # ----------------------------------------------- Plot Options tab -----------------------------------------------
        # ----- Header -----
        tab3_BG = tk.Label(tab3, text="", bg="red4")
        tab3_BG.grid(row=0, sticky="NSEW")
        header_title = tk.Label(tab3, text="NestIQ", fg="white", bg="red4", font=("Helvetica", 18))
        header_title.grid(row=0, sticky="NSW", padx=10, pady=5)

        self.plot_title_L = tk.Label(tab3, text="Plot title:", font=STANDARD_FONT)
        self.plot_title_L.grid(row=2, sticky="W", padx=10, pady=(5, 10))
        self.plot_title_E = tk.Entry(tab3, width=30)
        self.plot_title_E.grid(row=2, sticky="W", padx=77, pady=(10, 10))

        # ----- Plot dimensions -----
        plot_dim_L = tk.Label(tab3, text="Plot dimensions", font=STANDARD_FONT)
        plot_dim_L.grid(row=4, sticky="W", padx=10, pady=(5, 0))

        self.manual_plot_dims = tk.IntVar()
        auto_dim_RB = tk.Radiobutton(tab3, text="Auto", variable=self.manual_plot_dims, value=0)
        auto_dim_RB.grid(row=5, sticky="W", padx=25)
        man_dim_RB = tk.Radiobutton(tab3, text="Manual", variable=self.manual_plot_dims, value=1)
        man_dim_RB.grid(row=6, sticky="W", padx=25, pady=(0, 0))

        plot_dim_x_L = tk.Label(tab3, text="x:", font=STANDARD_FONT)
        plot_dim_y_L = tk.Label(tab3, text="y:", font=STANDARD_FONT)
        plot_dim_x_L.grid(row=6, sticky="W", padx=95)
        plot_dim_y_L.grid(row=6, sticky="W", padx=150)
        self.plot_dim_x_E = tk.Entry(tab3, width=5)
        self.plot_dim_y_E = tk.Entry(tab3, width=5)
        self.plot_dim_x_E.grid(row=6, sticky="W", padx=110)
        self.plot_dim_y_E.grid(row=6, sticky="W", padx=165)

        # ----- Font sizes -----
        title_font_size_L = tk.Label(tab3, text="Plot title font size:", font=STANDARD_FONT)
        title_font_size_L.grid(row=8, sticky="W", padx=10, pady=(15, 5))
        self.title_font_size_E = tk.Entry(tab3, width=5)
        self.title_font_size_E.grid(row=8, sticky="W", padx=140, pady=(15, 5))

        axis_title_font_size_L = tk.Label(tab3, text="Axis title font size:", font=STANDARD_FONT)
        axis_title_font_size_L.grid(row=9, sticky="W", padx=10, pady=5)
        self.axis_title_font_size_E = tk.Entry(tab3, width=5)
        self.axis_title_font_size_E.grid(row=9, sticky="W", padx=140, pady=5)

        axis_label_font_size_L = tk.Label(tab3, text="Axis label font size:", font=STANDARD_FONT)
        axis_label_font_size_L.grid(row=10, sticky="W", padx=10, pady=5)
        self.axis_label_font_size_E = tk.Entry(tab3, width=5)
        self.axis_label_font_size_E.grid(row=10, sticky="W", padx=140, pady=5)

        axis_tick_size_L = tk.Label(tab3, text="Axis tick size:", font=STANDARD_FONT)
        axis_tick_size_L.grid(row=11, sticky="W", padx=10, pady=5)
        self.axis_tick_size_E = tk.Entry(tab3, width=5)
        self.axis_tick_size_E.grid(row=11, sticky="W", padx=140, pady=5)

        legend_font_size_L = tk.Label(tab3, text="Legend font size:", font=STANDARD_FONT)
        legend_font_size_L.grid(row=12, sticky="W", padx=10, pady=5)
        self.legend_font_size_E = tk.Entry(tab3, width=5)
        self.legend_font_size_E.grid(row=12, sticky="W", padx=140, pady=5)

        tk.Label(tab3, text="Plot data", font=STANDARD_FONT).grid(row=4, sticky="W", padx=223, pady=(5, 0))

        # ----- Plot data check buttons -----
        self.plot_egg_BV = tk.BooleanVar()
        self.plot_egg_CB = tk.Checkbutton(tab3, text="Egg", variable=self.plot_egg_BV, font=STANDARD_FONT)
        self.plot_egg_CB.grid(row=5, sticky="W", padx=240)

        self.plot_air_BV = tk.BooleanVar()
        self.plot_air_CB = tk.Checkbutton(tab3, text="Air", variable=self.plot_air_BV, font=STANDARD_FONT)
        self.plot_air_CB.grid(row=6, sticky="W", padx=240)

        self.plot_adj_BV = tk.BooleanVar()
        self.plot_adj_CB = tk.Checkbutton(tab3, text="Egg - Air", variable=self.plot_adj_BV, font=STANDARD_FONT)
        self.plot_adj_CB.grid(row=8, sticky="NW", padx=240)

        # ----- Smoothing status -----
        smooth_status_L = tk.Label(tab3, text="Smoothing status", font=STANDARD_FONT)
        smooth_status_L.grid(row=9, sticky="W", padx=223)

        self.smooth_status_IV = tk.IntVar()
        raw_RB = tk.Radiobutton(tab3, text="Raw", variable=self.smooth_status_IV, value=0)
        raw_RB.grid(row=10, sticky="W", padx=240)
        smoothed_RB = tk.Radiobutton(tab3, text="Smoothed", variable=self.smooth_status_IV, value=1)
        smoothed_RB.grid(row=11, sticky="W", padx=240)

        # ----- Legend location -----
        self.legend_loc = tk.StringVar()
        _legend_loc_options = ["top_left", "top_center", "top_right", "bottom_left", "bottom_center", "bottom_right", "center_left", "center_right"]

        tk.Label(tab3, text="Legend location").grid(row=12, sticky="W", padx=223)
        self.legend_loc_OM = tk.OptionMenu(tab3, self.legend_loc, *_legend_loc_options)
        self.legend_loc_OM.grid(row=13, sticky="NW", padx=240)
        self.legend_loc_OM.config(bg="white")

        ttk.Separator(tab3, orient="horizontal").grid(row=14, sticky="NSEW", pady=10)

        tk.Label(tab3, text="Color", font=SUBHEADER_FONT).grid(row=15, sticky="NW", padx=(160, 0))
        tk.Label(tab3, text="Size/Width", font=SUBHEADER_FONT).grid(row=15, sticky="NW", padx=(272, 0))

        _color_choices = [
            "pink",
            "salmon",
            "red",
            "darkred",
            "orangered",
            "orange",
            "gold",
            "darkkhaki",
            "beige",
            "saddlebrown",
            "yellow",
            "lime",
            "greenyellow",
            "yellowgreen",
            "olive",
            "green",
            "cyan",
            "aquamarine",
            "lightskyblue",
            "blue",
            "darkblue",
            "indigo",
            "darkviolet",
            "black",
            "gray",
            "slategray",
            "lightgray",
            "white",
        ]

        self.on_point_color = tk.StringVar()
        self.off_point_color = tk.StringVar()
        self.bout_line_color = tk.StringVar()
        self.air_line_color = tk.StringVar()
        self.day_marker_color = tk.StringVar()

        # ----- Plot element sizes/colors -----
        tk.Label(tab3, text="On-bouts (point):").grid(row=16, sticky="NW", padx=(10, 0))
        tk.Label(tab3, text="Off-bouts (point):").grid(row=17, sticky="NW", padx=(10, 0))
        tk.Label(tab3, text="Bouts (line):").grid(row=18, sticky="NW", padx=(10, 0))
        tk.Label(tab3, text="Air temperature:").grid(row=19, stick="NW", padx=(10, 0))

        self.on_point_color_OM = tk.OptionMenu(tab3, self.on_point_color, *_color_choices)
        self.on_point_color_OM.grid(row=16, sticky="NW", padx=150)
        self.off_point_color_OM = tk.OptionMenu(tab3, self.off_point_color, *_color_choices)
        self.off_point_color_OM.grid(row=17, sticky="NW", padx=150)
        self.bout_line_color_OM = tk.OptionMenu(tab3, self.bout_line_color, *_color_choices)
        self.bout_line_color_OM.grid(row=18, sticky="NW", padx=150)
        self.air_line_color_OM = tk.OptionMenu(tab3, self.air_line_color, *_color_choices)
        self.air_line_color_OM.grid(row=19, sticky="NW", padx=150)
        self.day_marker_color_OM = tk.OptionMenu(tab3, self.day_marker_color, *_color_choices)
        self.day_marker_color_OM.grid(row=20, sticky="NW", padx=150)

        on_point_size_SV = tk.StringVar()
        off_point_size_SV = tk.StringVar()
        self.on_point_size_E = tk.Entry(tab3, textvariable=on_point_size_SV, width=5)
        self.on_point_size_E.grid(row=16, sticky="W", padx=286)
        tk.Label(tab3, textvariable=off_point_size_SV).grid(row=17, sticky="NW", padx=(285, 0))
        self.bout_line_width_E = tk.Entry(tab3, width=5)
        self.bout_line_width_E.grid(row=18, sticky="W", padx=286)
        self.air_line_width_E = tk.Entry(tab3, width=5)
        self.air_line_width_E.grid(row=19, sticky="W", padx=286)
        self.day_marker_width_E = tk.Entry(tab3, width=5)
        self.day_marker_width_E.grid(row=20, sticky="W", padx=286)

        self.show_day_markers_BV = tk.BooleanVar()
        self.show_day_markers_CB = tk.Checkbutton(tab3, text="Day markers:", variable=self.show_day_markers_BV, font=STANDARD_FONT)
        self.show_day_markers_CB.grid(row=20, sticky="W", padx=(10, 0), pady=(5, 0))

        self.show_grid_BV = tk.BooleanVar()
        self.show_grid_CB = tk.Checkbutton(tab3, text="Show grid", variable=self.show_grid_BV, font=STANDARD_FONT)
        self.show_grid_CB.grid(row=21, sticky="W", padx=(10, 0))

        self.on_point_color.set("black")
        self.off_point_color.set("black")
        self.bout_line_color.set("black")
        self.air_line_color.set("black")
        self.day_marker_color.set("black")

        # Update buttons to display selected color
        def color_menus_callback(*args):
            self.on_point_color_OM.config(bg=self.on_point_color.get())
            self.off_point_color_OM.config(bg=self.off_point_color.get())
            self.bout_line_color_OM.config(bg=self.bout_line_color.get())
            self.air_line_color_OM.config(bg=self.air_line_color.get())
            self.day_marker_color_OM.config(bg=self.day_marker_color.get())

        # Off point size is label that is automatically set equal to on_point_size
        def off_point_size_callback(*args):
            off_point_size_SV.set(str(self.on_point_size_E.get()))

        off_point_size_callback()

        # Display or retract entry boxes based on selection status
        def plot_setting_CKs_callback(*args):
            if self.show_day_markers_BV.get():
                self.day_marker_color_OM.grid(row=20, sticky="NW", padx=150)
                self.day_marker_width_E.grid(row=20, sticky="W", padx=286)
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
        tab4BG = tk.Label(tab4, text="", bg="red4")
        tab4BG.grid(row=2, sticky="NSEW")

        add_col1_B = tk.Button(tab4, text="Select Column", command=(lambda: self.toggle_col(col1, "select")))
        add_col1_B.grid(row=2, sticky="W", padx=10, pady=(10, 10))
        add_col1_B.configure(background="white")
        drop_col1_B = tk.Button(tab4, text="Deselect", command=(lambda: self.toggle_col(col1, "deselect")))
        drop_col1_B.grid(row=2, sticky="W", padx=100, pady=(10, 10))
        drop_col1_B.configure(background="white")

        add_col2_B = tk.Button(tab4, text="Select Column", command=(lambda: self.toggle_col(col2, "select")))
        add_col2_B.grid(row=2, sticky="W", padx=200, pady=(10, 10))
        add_col2_B.configure(background="white")
        drop_col2_B = tk.Button(tab4, text="Deselect", command=(lambda: self.toggle_col(col2, "deselect")))
        drop_col2_B.grid(row=2, sticky="W", padx=290, pady=(10, 10))
        drop_col2_B.configure(background="white")

        self.day_num_BV = tk.BooleanVar()
        self.date_BV = tk.BooleanVar()
        self.off_count_BV = tk.BooleanVar()
        self.off_dur_BV = tk.BooleanVar()
        self.off_dur_sd_BV = tk.BooleanVar()
        self.off_dec_BV = tk.BooleanVar()
        self.off_dec_sd_BV = tk.BooleanVar()
        self.mean_off_temper_BV = tk.BooleanVar()
        self.off_time_sum_BV = tk.BooleanVar()
        self.on_count_BV = tk.BooleanVar()
        self.on_dur_BV = tk.BooleanVar()
        self.on_dur_sd_BV = tk.BooleanVar()
        self.on_inc_BV = tk.BooleanVar()
        self.on_inc_sd_BV = tk.BooleanVar()
        self.mean_on_temper_BV = tk.BooleanVar()
        self.on_time_sum_BV = tk.BooleanVar()
        self.bouts_dropped_BV = tk.BooleanVar()
        self.time_above_temper_BV = tk.BooleanVar()
        self.time_below_temper_BV = tk.BooleanVar()
        self.mean_temper_d_BV = tk.BooleanVar()
        self.mean_temper_d_sd_BV = tk.BooleanVar()
        self.median_temper_d_BV = tk.BooleanVar()
        self.min_temper_d_BV = tk.BooleanVar()
        self.max_temper_d_BV = tk.BooleanVar()
        self.mean_temper_n_BV = tk.BooleanVar()
        self.mean_temper_n_sd_BV = tk.BooleanVar()
        self.median_temper_n_BV = tk.BooleanVar()
        self.min_temper_n_BV = tk.BooleanVar()
        self.max_temper_n_BV = tk.BooleanVar()
        self.mean_temper_dn_BV = tk.BooleanVar()
        self.mean_temper_dn_sd_BV = tk.BooleanVar()
        self.median_temper_dn_BV = tk.BooleanVar()
        self.min_temper_dn_BV = tk.BooleanVar()
        self.max_temper_dn_BV = tk.BooleanVar()
        self.mean_air_temper_BV = tk.BooleanVar()
        self.mean_air_temper_sd_BV = tk.BooleanVar()
        self.min_air_temper_BV = tk.BooleanVar()
        self.max_air_temper_BV = tk.BooleanVar()

        self.day_num_CB = tk.Checkbutton(tab4, text="Day Number", variable=self.day_num_BV)
        self.date_CB = tk.Checkbutton(tab4, text="Date", variable=self.date_BV)
        self.off_count_CB = tk.Checkbutton(tab4, text="Off-Bout Count", variable=self.off_count_BV)
        self.off_dur_CB = tk.Checkbutton(tab4, text="Mean Off-Bout Duration", variable=self.off_dur_BV)
        self.off_dur_sd_CB = tk.Checkbutton(tab4, text="Off-Bout Duration StDev", variable=self.off_dur_sd_BV)
        self.off_dec_CB = tk.Checkbutton(tab4, text="Mean Off-Bout Temp Drop", variable=self.off_dec_BV)
        self.off_dec_sd_CB = tk.Checkbutton(tab4, text="Off-Bout Temp Drop StDev", variable=self.off_dec_sd_BV)
        self.mean_off_temper_CB = tk.Checkbutton(tab4, text="Mean Off-Bout Temp", variable=self.mean_off_temper_BV)
        self.off_time_sum_CB = tk.Checkbutton(tab4, text="Off-Bout Time Sum", variable=self.off_time_sum_BV)
        self.on_count_CB = tk.Checkbutton(tab4, text="On-Bout Count", variable=self.on_count_BV)
        self.on_dur_CB = tk.Checkbutton(tab4, text="Mean On-Bout Duration", variable=self.on_dur_BV)
        self.on_dur_sd_CB = tk.Checkbutton(tab4, text="On-Bout Duration StDev", variable=self.on_dur_sd_BV)
        self.on_inc_CB = tk.Checkbutton(tab4, text="Mean On-Bout Temp Rise", variable=self.on_inc_BV)
        self.on_inc_sd_CB = tk.Checkbutton(tab4, text="On-Bout Temp Rise StDev", variable=self.on_inc_sd_BV)
        self.mean_on_temper_CB = tk.Checkbutton(tab4, text="Mean On-Bout Temp", variable=self.mean_on_temper_BV)
        self.on_time_sum_CB = tk.Checkbutton(tab4, text="On-Bout Time Sum", variable=self.on_time_sum_BV)
        self.bouts_dropped_CB = tk.Checkbutton(tab4, text="Vertices Dropped", variable=self.bouts_dropped_BV)
        self.time_above_temper_CB = tk.Checkbutton(tab4, text="Time above             degrees", variable=self.time_above_temper_BV)
        self.time_below_temper_CB = tk.Checkbutton(tab4, text="Time under             degrees", variable=self.time_below_temper_BV)
        self.mean_temper_d_CB = tk.Checkbutton(tab4, text="Mean Temperature (D)", variable=self.mean_temper_d_BV)
        self.mean_temper_d_sd_CB = tk.Checkbutton(tab4, text="Mean Temp StDev (D)", variable=self.mean_temper_d_sd_BV)
        self.median_temper_d_CB = tk.Checkbutton(tab4, text="Median Temp (D)", variable=self.median_temper_d_BV)
        self.min_temper_d_CB = tk.Checkbutton(tab4, text="Minimum Temp (D)", variable=self.min_temper_d_BV)
        self.max_temper_d_CB = tk.Checkbutton(tab4, text="Maximum Temp (D)", variable=self.max_temper_d_BV)
        self.mean_temper_n_CB = tk.Checkbutton(tab4, text="Mean Temperature (N)", variable=self.mean_temper_n_BV)
        self.mean_temper_n_sd_CB = tk.Checkbutton(tab4, text="Mean Temp StDev (N)", variable=self.mean_temper_n_sd_BV)
        self.median_temper_n_CB = tk.Checkbutton(tab4, text="Median Temp (N)", variable=self.median_temper_n_BV)
        self.min_temper_n_CB = tk.Checkbutton(tab4, text="Minimum Temp (N)", variable=self.min_temper_n_BV)
        self.max_temper_n_CB = tk.Checkbutton(tab4, text="Maximum Temp (N)", variable=self.max_temper_n_BV)
        self.mean_temper_dn_CB = tk.Checkbutton(tab4, text="Mean Temperature (DN)", variable=self.mean_temper_dn_BV)
        self.mean_temper_dn_sd_CB = tk.Checkbutton(tab4, text="Mean Temp StDev (DN)", variable=self.mean_temper_dn_sd_BV)
        self.median_temper_db_CB = tk.Checkbutton(tab4, text="Median Temp (DN)", variable=self.median_temper_dn_BV)
        self.min_temper_dn_CB = tk.Checkbutton(tab4, text="Minimum Temp (DN)", variable=self.min_temper_dn_BV)
        self.max_temper_dn_CB = tk.Checkbutton(tab4, text="Maximum Temp (DN)", variable=self.max_temper_dn_BV)
        self.mean_air_temper_CB = tk.Checkbutton(tab4, text="Mean Air Temp (DN)", variable=self.mean_air_temper_BV)
        self.mean_air_temper_sd_CB = tk.Checkbutton(tab4, text="Mean Air Temp StDev (DN)", variable=self.mean_air_temper_sd_BV)
        self.min_air_temper_CB = tk.Checkbutton(tab4, text="Min Air Temp (DN)", variable=self.min_air_temper_BV)
        self.max_air_temper_CB = tk.Checkbutton(tab4, text="Max Air Temp (DN)", variable=self.max_air_temper_BV)

        # List of options in each column for mass selection and deselection
        col1 = [
            self.day_num_CB,
            self.date_CB,
            self.off_count_CB,
            self.off_dur_CB,
            self.off_dur_sd_CB,
            self.off_dec_CB,
            self.off_dec_sd_CB,
            self.mean_off_temper_CB,
            self.off_time_sum_CB,
            self.on_count_CB,
            self.on_dur_CB,
            self.on_dur_sd_CB,
            self.on_inc_CB,
            self.on_inc_sd_CB,
            self.mean_on_temper_CB,
            self.on_time_sum_CB,
            self.time_above_temper_CB,
            self.time_below_temper_CB,
            self.bouts_dropped_CB,
        ]

        col2 = [
            self.mean_temper_d_CB,
            self.mean_temper_d_sd_CB,
            self.median_temper_d_CB,
            self.min_temper_d_CB,
            self.max_temper_d_CB,
            self.mean_temper_n_CB,
            self.mean_temper_n_sd_CB,
            self.median_temper_n_CB,
            self.min_temper_n_CB,
            self.max_temper_n_CB,
            self.mean_temper_dn_CB,
            self.mean_temper_dn_sd_CB,
            self.median_temper_db_CB,
            self.min_temper_dn_CB,
            self.max_temper_dn_CB,
            self.mean_air_temper_CB,
            self.mean_air_temper_sd_CB,
            self.min_air_temper_CB,
            self.max_air_temper_CB,
        ]

        self.toggle_col(col1, "select")
        self.toggle_col(col2, "select")

        self.day_num_CB.grid(row=3, sticky="W", padx=10, pady=(10, 0))
        self.date_CB.grid(row=4, sticky="W", padx=10)
        self.off_count_CB.grid(row=7, sticky="W", padx=10)
        self.off_dur_CB.grid(row=8, sticky="W", padx=10)
        self.off_dur_sd_CB.grid(row=9, sticky="W", padx=10)
        self.off_dec_CB.grid(row=10, sticky="W", padx=10)
        self.off_dec_sd_CB.grid(row=11, sticky="W", padx=10)
        self.mean_off_temper_CB.grid(row=12, sticky="W", padx=10)
        self.off_time_sum_CB.grid(row=13, sticky="W", padx=10)
        self.on_count_CB.grid(row=15, sticky="W", padx=10)
        self.on_dur_CB.grid(row=16, sticky="W", padx=10)
        self.on_dur_sd_CB.grid(row=17, sticky="W", padx=10)
        self.on_inc_CB.grid(row=18, sticky="W", padx=10)
        self.on_inc_sd_CB.grid(row=19, sticky="W", padx=10)
        self.mean_on_temper_CB.grid(row=20, sticky="W", padx=10)
        self.on_time_sum_CB.grid(row=21, sticky="W", padx=10)
        self.bouts_dropped_CB.grid(row=23, sticky="W", padx=10)
        self.time_above_temper_CB.grid(row=24, sticky="W", padx=10)
        self.time_below_temper_CB.grid(row=25, sticky="W", padx=10)
        self.mean_temper_d_CB.grid(row=3, sticky="W", padx=200, pady=(10, 0))
        self.mean_temper_d_sd_CB.grid(row=4, sticky="W", padx=200)
        self.median_temper_d_CB.grid(row=6, sticky="W", padx=200)
        self.min_temper_d_CB.grid(row=7, sticky="W", padx=200)
        self.max_temper_d_CB.grid(row=8, sticky="W", padx=200)
        self.mean_temper_n_CB.grid(row=10, sticky="W", padx=200)
        self.mean_temper_n_sd_CB.grid(row=11, sticky="W", padx=200)
        self.median_temper_n_CB.grid(row=12, sticky="W", padx=200)
        self.min_temper_n_CB.grid(row=13, sticky="W", padx=200)
        self.max_temper_n_CB.grid(row=14, sticky="W", padx=200)
        self.mean_temper_dn_CB.grid(row=16, sticky="W", padx=200)
        self.mean_temper_dn_sd_CB.grid(row=17, sticky="W", padx=200)
        self.median_temper_db_CB.grid(row=18, sticky="W", padx=200)
        self.min_temper_dn_CB.grid(row=19, sticky="W", padx=200)
        self.max_temper_dn_CB.grid(row=20, sticky="W", padx=200)
        self.mean_air_temper_CB.grid(row=22, sticky="W", padx=200)
        self.mean_air_temper_sd_CB.grid(row=23, sticky="W", padx=200)
        self.min_air_temper_CB.grid(row=24, sticky="W", padx=200)
        self.max_air_temper_CB.grid(row=25, sticky="W", padx=200)

        self.time_above_temper_E = tk.Entry(tab4, width=5)
        self.time_above_temper_E.grid(row=24, sticky="W", padx=97)
        self.time_below_temper_E = tk.Entry(tab4, width=5)
        self.time_below_temper_E.grid(row=25, sticky="W", padx=97)

        # -----------------------------------------------------------------------------------------------------------
        # ----- Footer -----
        uark_path = str(self.master_dir_path / "misc_files" / "NIQ_Sups" / "uark.png")
        durant_path = str(self.master_dir_path / "misc_files" / "NIQ_Sups" / "durant.png")
        uark_logo = ImageTk.PhotoImage(Image.open(uark_path))
        durant_logo = ImageTk.PhotoImage(Image.open(durant_path))
        uark_logo_L = tk.Label(self.root, background="white", image=uark_logo)
        uark_logo_L.grid(row=29, sticky="W", padx=20)
        durant_logo_L = tk.Label(self.root, background="white", image=durant_logo)
        durant_logo_L.grid(row=29, sticky="W", padx=80)

        self.run = False
        self.run_B = tk.Button(self.root, text="Run", command=(lambda: self.trigger_run()))
        self.run_B.grid(row=29, sticky="NE", padx=10, pady=(10, 0))
        self.run_B.configure(bg="red4", fg="white", width=10, height=1)
        self.run_B["font"] = HEADER_FONT

        self.show_warns_BV = tk.BooleanVar()
        self.show_warns_CB = tk.Checkbutton(
            self.root, text="Show warnings", variable=self.show_warns_BV, background="white", activebackground="white", font=STANDARD_FONT
        )
        self.show_warns_CB.grid(row=29, sticky="SE", padx=10, pady=(10, 0))

        load_config(self, program_startup=True)

        # Call function to handle user closing GUI window
        self.root.protocol("WM_DELETE_WINDOW", lambda: self.close_niq())

        _ = None
        self.root.bind("<Return>", lambda _: self.trigger_run())

        self.root.bind("<`>", lambda _: testing.test_run(self))
        self.root.bind("<Control-`>", lambda _: testing.master_test(self))

        self.valid = True
        while self.valid and not self.run:
            self.run_loop()

    def run_loop(self):
        """
            Updates GUI and sets program clock

            Args:
                root (tk root widget): base widget of GUI
		"""

        self.root.update_idletasks()
        self.root.update()
        time.sleep(0.01)

    def help(self):
        """ Launches user manual. """

        subprocess.Popen(str(self.master_dir_path / "NIQ_manual.pdf"), shell=True)

    def toggle_col(self, column, command):
        """
            Selects or deselects entire columns of Stat Options tab

            Args:
                column (list): list of variables to be selected or deselected
                command (string)
		"""

        for option in column:
            option.select() if command == "select" else option.deselect()

    def get_input_file_name(self):
        """ Handles input file browsing and selection. """

        input_paths = list(filedialog.askopenfilename(initialdir=(self.master_dir_path / "input_files"), multiple=True))

        # Remove curley braces that are sometimes added automatically
        input_paths = [item.replace("{", "").replace("}", "") for item in input_paths]

        replace_entry(self.input_file_E, " | ".join(input_paths))

        if len(input_paths) == 1:
            # Update default output file names
            stem = Path(input_paths[0]).stem
            out_dir = self.master_dir_path / "output_files"
            set_unique_path(self.plot_file_E, out_dir / (stem + "_plot"), ".html")
            set_unique_path(self.stats_file_E, out_dir / (stem + "_stats"), ".csv")

    def get_plot_file(self, entry):
        """ Handles plot file browsing and selection """

        path_ = filedialog.askopenfilename()

        if path_ != "":
            replace_entry(entry, path_)

        niq_misc.remove_curly(entry)

    def handle_save_as(self, entry):
        """
            Allows the user to browse the file system and provide a path to 
            populate the entry box with.

            Args:
                entry (tk.Entry): Entry box to be populated
		"""

        if entry == self.plot_file_E:
            ext = ".html"
        elif entry == self.stats_file_E or entry == self.multi_in_stats_file_E:
            ext = ".csv"

        path = filedialog.asksaveasfilename(initialdir=(self.master_dir_path / "output_files"))
        
        if path != "":
            replace_entry(entry, str(Path(path).with_suffix(ext)))


    def reset_multi_file_var(self):
        """
            Resets variables used to store data across multiple input files.
		"""

        self.multi_file_off_durs = []
        self.multi_file_off_decs = []
        self.multi_file_on_durs = []
        self.multi_in_on_incs = []
        self.multi_in_day_tempers = []
        self.multi_in_night_tempers = []
        self.multi_in_air_tempers = []
        self.multi_in_full_day_count = 0

    def select_vertices(self):
        """
            Generates special plot for the user to select their ideal vertex locations. This plot can be
            saved and later used for supervised parameter acquisition or manual vertex modification.
		"""

        days_list = []
        
        in_file_paths = self.parse_input_file_entry()
        self.set_active_input(in_file_paths[0], replace_out=False)

        if not all((check_valid_plot_ops(self), check_valid_main(self, check_output=False), check_valid_adv(self))):
            return

        try:
            self.master_df = self.init_master_df(self.input_file_E.get())

            # Get days_list for plotting vertical lines
            days_list = niq_misc.split_days(self)[0]  # Indexing at end excludes nights_list
        except Exception:
            messagebox.showerror(("Input File Error (Advanced tab)"), "Input file could not be processed.")
            traceback.print_exc()
            return False

        path = self.master_dir_path / "misc_files" / "temp_plot.html"

        niq_misc.generate_plot(self, days_list, edit_mode=True, out_path=path)

    def parse_input_file_entry(self):
        """ Splits input file entry box into individual input paths if present. """

        paths = [Path(path) for path in self.input_file_E.get().split(" | ")]
        return paths

    def set_active_input(self, path, replace_out=False):
        """ Sets parameters based on single input file currently being analyzed. """

        replace_entry(self.input_file_E, str(path))
        self.active_input_path = path

        if replace_out:
            # Update default output file names
            out_dir = self.master_dir_path / "output_files"
            set_unique_path(self.plot_file_E, out_dir / (path.stem + "_plot"), ".html")
            set_unique_path(self.stats_file_E, out_dir / (path.stem + "_stats"), ".csv")


    # Ensure valid parameters and execute processing
    def trigger_run(self):
        """
            Ensure everything is in order and if so, initiate processing of the input file(s).

            Args:
                root (tk root widget): base widget of GUI
		"""

        run_start = time.time()

        try:
            print("-" * 100)
            print("Running NestIQ")

            in_file_paths = self.parse_input_file_entry()
            self.multi_file_stats = niq_classes.MultiFileStats(self)

            self.air_valid = True   

            for file_num, path in enumerate(in_file_paths, 1):
                self.set_active_input(path, replace_out=(len(in_file_paths) > 1))
                self.run = True

                self.run_B["text"] = f"Running {file_num}..."
                self.run_B.config(bg="gray", fg="white", width=15, height=1)
                self.root.update()

                if not (
                    check_valid_main(self, first_in=(file_num == 1))
                    and check_valid_adv(self)
                    and check_valid_plot_ops(self)
                    and check_valid_stat_ops(self)
                ):
                    break

                print("Active file:", path)


                self.master_df = self.init_master_df(path)

                if path.suffix == ".html":
                    custom_verts = niq_misc.get_verts_from_html(self, self.input_file_E.get())
                    self.master_df = self.add_states(verts=custom_verts)
                else:
                    self.master_hmm = niq_hmm.HMM()
                    self.master_hmm.build_model_from_entries(self)
                    self.master_hmm.normalize_params(self)
                    self.master_hmm.populate_hmm_entries(self)

                    # Adds state column to master_df of input file
                    results = self.master_hmm.decode(self.master_df)
                    self.master_df = self.add_states(states=results)

                try:
                    main(self)
                except:
                    traceback.print_exc()
                    break

            if self.multi_in_stats_BV.get():
                self.multi_file_stats.write(self)

            replace_entry(self.input_file_E, " | ".join([str(path) for path in in_file_paths]))

            self.run_B["text"] = "Run"
            self.run_B.config(bg="red4", fg="white", width=10, height=1)
            self.run = False
            print(colored("Done", "green"))

        except Exception:
            traceback.print_exc()
            messagebox.showerror(("Unidentified Error"), "An unknown error has occerred." + "Please report this error to wxhawkins@gmail.com")

        print(f"Run took {round(time.time() - run_start, 2)} seconds")

    def close_niq(self):
        """
            Cleanly terminates the program.

            Args:
               root (tk root widget): base of GUI
		"""

        self.valid = False
        self.root.quit()
        self.root.destroy()

    def erase_nighttime_state(self, master_df):
        """
            Sets state of nightime data points to "nonsense" value of 2. These points will be ignored for the
            majority of downstream statistical calculations.

            Args:
                nights_list (list of blocks): used to get boudaries for nightime data points
                master_df (DataFrame): master DataFrame which will have states column modified
		"""

        if self.restrict_search_BV.get():
            filt = master_df["is_daytime"] == False
            master_df.loc[filt, "bout_state"] = "None"

        return master_df

    def unsupervised_learning(self, auto_run=False):
        """
            Prepares master array from input data, runs the baum welch algorithm, and populates the GUI with
            resulting parameters.

            Args:
                auto_run (bool): False if this function call is from clicking button on the Advanced tab
		"""

        self.run_B["text"] = "Learning..."
        self.run_B.config(bg="gray", fg="white", width=10, height=1)
        self.root.update()

        in_file_paths = self.parse_input_file_entry()
        self.set_active_input(in_file_paths[0], replace_out=False)

        if len(in_file_paths) > 1:
            messagebox.showerror(
                ("Unsupervised Learning Error"), "Multiple input files provided. Unsupervised learning currently only supports single input files."
            )

            self.run_B["text"] = "Run"
            self.run_B.config(bg="red4", fg="white", width=10, height=1)
            self.run = False
            return False

        # If auto_run, check_valid_main will be called in trigger_run
        if not auto_run:
            if not check_valid_main(self, check_output=False):
                self.run_B["text"] = "Run"
                self.run_B.config(bg="red4", fg="white", width=10, height=1)
                self.run = False
                self.root.update()
                return False

        in_file = self.input_file_E.get()
        self.master_df = self.init_master_df(in_file)

        self.master_hmm = niq_hmm.HMM()
        emis_arr = self.master_df.loc[:, "delta_temper"].to_numpy()
        emis_arr = emis_arr.reshape(-1, 1)
        self.master_hmm.baum_welch(emis_arr)
        self.master_hmm.populate_hmm_entries(self)

        self.run_B["text"] = "Run"
        self.run_B.config(bg="red4", fg="white", width=10, height=1)
        self.run = False


    def supervised_learning(self):
        """
		    Calculates model parameters from user-provided vertex locations.
		"""

        in_file_paths = self.parse_input_file_entry()
        self.set_active_input(in_file_paths[0], replace_out=False)

        if len(in_file_paths) > 1:
            messagebox.showerror(
                ("Supervised Learning Error"), "Multiple input files provided. Please provide the single input file used to generate the vertex selection file."
            )

            return False

        if not check_valid_vertex_file(self) or not check_valid_main(self, check_output=False):
            return

        self.master_df = self.init_master_df(self.input_file_E.get())

        training_verts = niq_misc.get_verts_from_html(self, self.vertex_file_E.get())
        self.master_hmm = niq_hmm.HMM()
        self.master_df = self.add_states(verts=training_verts)
        reduced_df = self.master_df.iloc[training_verts[0].index:training_verts[-1].index + 1]
        self.master_hmm.extract_params_from_verts(reduced_df)
        self.master_hmm.normalize_params(self)
        self.master_hmm.populate_hmm_entries(self)

    def init_master_df(self, in_path):
        """
            Adds all columns barring bout_state

            Args:
                in_path (str or pathlib.Path): path to input file containing data to be analyzed

            columns:
                data_point = data point
                date_time = date and time of temperature recording
                egg_temper = egg temperature
                air_temper = ambient air temperature
                adj_temper = adjusted temperature (egg - air temperature)
                smoothed_egg_temper = egg_temper with rolling mean applied
                smoothed_adj_temper = adj_temper with rolling mean applied
                delta_temper = change in smoothed_adj_temper or smoothed_egg_temper
                is_daytime = True if datapoint falls in daytime time range
                bout_state = on, off or None for nighttime data points in a restricted analysis
        """
        def add_daytime(df):
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
            day_start = niq_misc.convert_to_datetime(f"01/01/2020 {str(self.day_start_E.get())}").time()
            night_start = niq_misc.convert_to_datetime(f"01/01/2020 {str(self.night_start_E.get())}").time()

            df["is_daytime"] = df["date_time"].apply(is_daytime)

            return df

        def html_to_df(path):
            with open(path, "r") as f:
                lines = f.readlines()

            i = lines.index("<!--NestIQ input data\n") + 1
            json_str = lines[i][:-1]
            input_dict = json.loads(json_str)
            size = len(input_dict["egg_temper"])

            # Restore data point column
            dp_start = int(input_dict["first_dp"])
            dp_stop = dp_start + size
            input_dict["data_point"] = list(range(dp_start, dp_stop))

            # Restore date/time column
            first_dt = niq_misc.convert_to_datetime(input_dict["first_dt"])
            time_d = datetime.timedelta(seconds=int(input_dict["dt_interval"]))
            input_dict["date_time"] = [first_dt + (x * time_d) for x in range(0, size)]

            df = pd.DataFrame({
                "data_point": input_dict["data_point"],
                "date_time": input_dict["date_time"],
                "egg_temper": input_dict["egg_temper"],
                "air_temper": input_dict["air_temper"]
                })
        
            return df


        def csv_to_df(path):
            try:
                df = pd.read_csv(path)
            except UnicodeDecodeError:
                # Attempt to convert file encoding to UTF-8
                temp_path = self.master_dir_path / "misc_files" / "temp_input.csv"
                with open(in_path, "r") as original_file, open(temp_path, "w", encoding="utf8") as mod_file:
                    mod_file.write(original_file.read())

                df = pd.read_csv(temp_path)

            return df

        def is_number(string):
            try:
                float(string)
            except ValueError:
                return False

            return True

        in_path = Path(in_path)
        if in_path.suffix == ".html":
            df = html_to_df(str(in_path))
        else:
            df = csv_to_df(str(in_path))

        # Set time interval
        delta_secs = (convert_to_datetime(df.iloc[-1, 1]) - convert_to_datetime(df.iloc[0, 1])).total_seconds()
        self.time_interval = round(delta_secs / len(df))
        print("interval =", self.time_interval)

        # Fill air_temper column with 0's if none provided
        if not self.air_valid:
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
        df["date_time"] = df["date_time"].apply(niq_misc.convert_to_datetime)
        df["egg_temper"] = df["egg_temper"].astype(float).round(4)
        df["air_temper"] = df["air_temper"].astype(float).round(4)

        # Reassign data_point column to be continuous
        start = int(df["data_point"].iloc[0])
        new_col = range(start, (start + len(df)))
        df["data_point"] = new_col
            

        # Add adjusted (egg - air temperature) temperatures column
        df["adj_temper"] = (df["egg_temper"] - df["air_temper"]).round(4)

        # Add smoothed temperatures columns
        radius = int(self.smoothing_radius_E.get())
        df["smoothed_egg_temper"] = niq_misc.smooth_series(radius, df["egg_temper"]).round(4)
        df["smoothed_adj_temper"] = niq_misc.smooth_series(radius, df["adj_temper"]).round(4)

        # Add column storing difference in adjusted temperature from previous entry to current
        df["delta_temper"] = np.zeros(df.shape[0])
        emission_source = "smoothed_adj_temper" if int(self.train_from_IV.get()) == 1 else "smoothed_egg_temper"
        df.iloc[1:, df.columns.get_loc("delta_temper")] = df[emission_source].diff()

        # Set first cell equal to second
        df.iloc[0, df.columns.get_loc("delta_temper")] = df.iloc[1, df.columns.get_loc("delta_temper")]

        df = add_daytime(df)

        return df.reset_index(drop=True)

    def add_states(self, verts=None, states=None):
        """
            Adds bout state column

            Args:   
                verts (list):
                states (numpy array):

            Flag: consider adding "partial_bout" argument that dictates if data at extremities of df is classified.
        """

        # Appends state values based on vertex locations
        if verts is not None:

            self.master_df["bout_state"] = "None"

            state = "off"  # Assume off-bout start -- is corrected by "swap_params_by_state" if necessary

            # Create list of vertex indices
            indices = [0]
            indices += [vert.index for vert in verts]
            indices.append(len(self.master_df))

            prev_i = indices[0]
            for next_i in indices[1:]:
                self.master_df.loc[prev_i : next_i - 1, "bout_state"] = state

                # Set up for next round
                prev_i = next_i
                state = "off" if state == "on" else "on"

        # If states are provided, simply append
        if states is not None:
            self.master_df.loc[:, "bout_state"] = states
            self.master_df.loc[:, "bout_state"].replace([0, 1, 2], ["off", "on", "None"], inplace=True)

        # Flip bout states if necessary
        on_bout_delta_temp = self.master_df.loc[self.master_df["bout_state"] == "on", "delta_temper"].mean()
        off_bout_delta_temp = self.master_df.loc[self.master_df["bout_state"] == "off", "delta_temper"].mean()
        if off_bout_delta_temp > on_bout_delta_temp:
            self.master_df.loc[:, "bout_state"].replace(["off", "on", "None"], ["on", "off", "None"], inplace=True)

        return self.master_df


def main(gui):
    """
        Pior to entering this function, master_df has be fully constructed including the annotation of bout_state,
        and daytime/nighttime status for the entiere dataset, regardless of daytime restriction. First, any data points
        corrisponding to nighttime have their bout_state set to None. A master block is constructed which covers the
        entire dataset. The vertices for this Block are acquired by searching for changes in bout state (e.g. "off" to 
        "on" or "on" to None). Bouts are subsequently extracted from these vertices. Statistics for this block represent
        the dataset as a whole. Later individual Blocks are created for each date represented in the input data. These 
        blocks have their bouts extracted from the pool of bouts already identified in the master_block.

        Args:
            gui (GUIClass)
	"""
    
    gui.master_df = gui.erase_nighttime_state(gui.master_df)

    # Store all vertices in master block object for later allocation
    gui.master_block = niq_classes.Block(gui, 0, len(gui.master_df) - 1, False)
    gui.master_block.vertices = niq_misc.get_verts_from_master_df(gui.master_df)
    gui.master_block.bouts = niq_misc.get_bouts_from_verts(gui, gui.master_block.vertices)

    gui.master_df, gui.bouts_dropped_locs = niq_misc.filter_by_dur(gui)

    # FLAG - need to figure out how to reduce this redundancy
    gui.master_block = niq_classes.Block(gui, 0, len(gui.master_df) - 1, False)
    gui.master_block.vertices = niq_misc.get_verts_from_master_df(gui.master_df)
    gui.master_block.bouts = niq_misc.get_bouts_from_verts(gui, gui.master_block.vertices)

    gui.master_block.get_stats(gui)
    file_bouts = gui.master_block.bouts

    gui.multi_file_stats.add_block(gui.master_block)

    if gui.air_valid:
        gui.multi_in_air_tempers += gui.master_block.air_tempers.tolist()

    # Create blocks each date represented in input file
    date_block_list = niq_misc.get_date_blocks(gui)
    for date_block in date_block_list:
        date_block.bouts = niq_misc.extract_bouts_in_range(gui, file_bouts, date_block.first, date_block.last)
        date_block.get_stats(gui)

    # Plot and write stats file if requested
    if gui.make_plot_BV.get():
        niq_misc.generate_plot(gui, date_block_list, edit_mode=gui.edit_mode_BV.get())
    if gui.get_stats_BV.get():
        niq_misc.write_stats(gui, date_block_list, gui.master_block)


if __name__ == "__main__":
    gui = GUIClass(root)
    root.mainloop()
