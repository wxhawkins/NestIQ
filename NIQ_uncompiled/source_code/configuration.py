import configparser
import traceback
from pathlib import Path
from shutil import copyfile
from tkinter import filedialog, messagebox

from niq_misc import replace_entry


def save_config(gui, out_file=None):
    """
        Prompts user to provide a save file name and location then generates a configuration file from
        the current GUI settings and statuses.

    """

    if out_file is None:
        try:
            out_file = Path(filedialog.asksaveasfilename()).with_suffix(".ini")
        except ValueError: 
            return

    # Copy over defualt_backup as template
    copyfile(gui.master_dir_path / "config_files" / "backup_config.ini", out_file)
    update_config(gui, out_file)

def load_config(gui, program_startup=False, config_file_=None):
    """
        Updates all GUI settings and statuses according to a configuration file. If this file is not immediately
        provided to the function, the user is prompted to select a file from a dialog box.

        Args:
            program_startup (bool): True if is the initial call used to populate GUI upon program startup
            config_file_ (pathlib.Path): Path to configuration file to be loaded
    """

    # Load config button clicked
    if not program_startup and config_file_ is None:
        config_file = filedialog.askopenfilename()

        if config_file == "":
            return False

        config_file = Path(config_file)
        if not config_file.exists():
            messagebox.showerror(("Config File Loading Error"), "Configuration file could not be found.")
            return False

        try:
            gui.config.read(str(config_file))
        except:
            messagebox.showerror(("Config File Loading Error"), "Configuration file appears invalid.  Please try a differnt file.")

    if config_file_ is not None:
        config_file = config_file_
        gui.config.read(str(config_file))

    try:
        gui.time_interval = gui.config.get("Main Settings", "data_time_interval")
        gui.show_warns_CB.select() if gui.config.get("Main Settings", "show_warnings").lower() == "true" else gui.show_warns_CB.deselect()
        gui.restrict_search_CB.select() if gui.config.get("Main Settings", "restrict_bout_search").lower() == "true" else gui.restrict_search_CB.deselect()
        replace_entry(gui.day_start_E, gui.config.get("Main Settings", "day_Start_Time"))
        replace_entry(gui.night_start_E, gui.config.get("Main Settings", "night_Start_Time"))
        replace_entry(gui.smoothing_radius_E, gui.config.get("Main Settings", "smoothing_radius"))
        replace_entry(gui.dur_thresh_E, gui.config.get("Main Settings", "duration_threshold"))
        gui.train_from_IV.set(0) if gui.config.get("Advanced Settings", "train_from").lower() == "0" else gui.train_from_IV.set(1)
        replace_entry(gui.init_off_E, gui.config.get("Advanced Settings", "off_bout_initial"))
        replace_entry(gui.init_on_E, gui.config.get("Advanced Settings", "on_bout_initial"))
        replace_entry(gui.off_off_trans_E, gui.config.get("Advanced Settings", "off_off_trans"))
        replace_entry(gui.off_on_trans_E, gui.config.get("Advanced Settings", "off_on_trans"))
        replace_entry(gui.on_on_trans_E, gui.config.get("Advanced Settings", "on_on_trans"))
        replace_entry(gui.on_off_trans_E, gui.config.get("Advanced Settings", "on_off_trans"))
        replace_entry(gui.off_mean_E, gui.config.get("Advanced Settings", "off_bout_emis_mean"))
        replace_entry(gui.off_stdev_E, gui.config.get("Advanced Settings", "off_bout_emis_stdev"))
        replace_entry(gui.on_mean_E, gui.config.get("Advanced Settings", "on_bout_emis_mean"))
        replace_entry(gui.on_stdev_E, gui.config.get("Advanced Settings", "on_bout_emis_stdev"))
        gui.manual_plot_dims.set(0) if gui.config.get("Plot Options", "manual_plot_dimensions").lower() == "false" else gui.manual_plot_dims.set(1)
        replace_entry(gui.plot_dim_x_E, gui.config.get("Plot Options", "plot_x_dim"))
        replace_entry(gui.plot_dim_y_E, gui.config.get("Plot Options", "plot_y_dim"))
        replace_entry(gui.title_font_size_E, gui.config.get("Plot Options", "title_font_size"))
        replace_entry(gui.axis_title_font_size_E, gui.config.get("Plot Options", "axis_title_font_size"))
        replace_entry(gui.axis_label_font_size_E, gui.config.get("Plot Options", "axis_label_font_size"))
        replace_entry(gui.axis_tick_size_E, gui.config.get("Plot Options", "axis_tick_size"))
        replace_entry(gui.legend_font_size_E, gui.config.get("Plot Options", "legend_font_size"))
        gui.plot_egg_CB.select() if gui.config.get("Plot Options", "plot_egg_tempers").lower() == "true" else gui.plot_egg_CB.deselect()
        gui.plot_air_CB.select() if gui.config.get("Plot Options", "plot_air_tempers").lower() == "true" else gui.plot_air_CB.deselect()
        gui.plot_adj_CB.select() if gui.config.get("Plot Options", "plot_egg_minus_air").lower() == "true" else gui.plot_adj_CB.deselect()
        gui.smooth_status_IV.set(0) if gui.config.get("Plot Options", "plot_smoothed").lower() == "false" else gui.smooth_status_IV.set(1)
        gui.legend_loc.set(gui.config.get("Plot Options", "legend_location"))
        gui.on_point_color.set(gui.config.get("Plot Options", "on_point_color"))
        gui.off_point_color.set(gui.config.get("Plot Options", "off_point_color"))
        gui.bout_line_color.set(gui.config.get("Plot Options", "bout_line_color"))
        gui.air_line_color.set(gui.config.get("Plot Options", "air_line_color"))
        gui.day_marker_color.set(gui.config.get("Plot Options", "day_marker_color"))
        replace_entry(gui.on_point_size_E, gui.config.get("Plot Options", "on_point_size"))
        replace_entry(gui.bout_line_width_E, gui.config.get("Plot Options", "bout_line_width"))
        replace_entry(gui.air_line_width_E, gui.config.get("Plot Options", "air_line_width"))
        replace_entry(gui.day_marker_width_E, gui.config.get("Plot Options", "day_marker_width"))
        gui.show_day_markers_CB.select() if gui.config.get("Plot Options", "show_day_marker").lower() == "true" else gui.show_day_markers_CB.deselect()
        gui.show_grid_CB.select() if gui.config.get("Plot Options", "show_grid").lower() == "true" else gui.show_grid_CB.deselect()
        gui.day_num_CB.select() if gui.config.get("Stats Options", "day_Number").lower() == "true" else gui.day_num_CB.deselect()
        gui.date_CB.select() if gui.config.get("Stats Options", "date").lower() == "true" else gui.date_CB.deselect()
        gui.off_count_CB.select() if gui.config.get("Stats Options", "off_Bout_Count").lower() == "true" else gui.off_count_CB.deselect()
        gui.off_dur_CB.select() if gui.config.get("Stats Options", "mean_Off_Bout_Duration").lower() == "true" else gui.off_dur_CB.deselect()
        gui.off_dur_sd_CB.select() if gui.config.get("Stats Options", "off_Bout_Duration_StDev").lower() == "true" else gui.off_dur_sd_CB.deselect()
        gui.off_dec_CB.select() if gui.config.get("Stats Options", "mean_Off_Bout_Temp_Drop").lower() == "true" else gui.off_dec_CB.deselect()
        gui.off_dec_sd_CB.select() if gui.config.get("Stats Options", "off_Bout_Temp_Drop_StDev").lower() == "true" else gui.off_dec_sd_CB.deselect()
        gui.mean_off_temper_CB.select() if gui.config.get("Stats Options", "mean_Off_Bout_Temp").lower() == "true" else gui.mean_off_temper_CB.deselect()
        gui.off_time_sum_CB.select() if gui.config.get("Stats Options", "off_bout_time_sum").lower() == "true" else gui.off_time_sum_CB.deselect()
        gui.on_count_CB.select() if gui.config.get("Stats Options", "on_Bout_Count").lower() == "true" else gui.on_count_CB.deselect()
        gui.on_dur_CB.select() if gui.config.get("Stats Options", "mean_On_Bout_Duration").lower() == "true" else gui.on_dur_CB.deselect()
        gui.on_dur_sd_CB.select() if gui.config.get("Stats Options", "on_Bout_Duration_StDev").lower() == "true" else gui.on_dur_sd_CB.deselect()
        gui.on_inc_CB.select() if gui.config.get("Stats Options", "mean_On_Bout_Temp_Rise").lower() == "true" else gui.on_inc_CB.deselect()
        gui.on_inc_sd_CB.select() if gui.config.get("Stats Options", "on_Bout_Temp_Rise_StDev").lower() == "true" else gui.on_inc_sd_CB.deselect()
        gui.mean_on_temper_CB.select() if gui.config.get("Stats Options", "mean_On_Bout_Temp").lower() == "true" else gui.mean_on_temper_CB.deselect()
        gui.on_time_sum_CB.select() if gui.config.get("Stats Options", "on_bout_time_sum").lower() == "true" else gui.on_time_sum_CB.deselect()
        gui.bouts_dropped_CB.select() if gui.config.get("Stats Options", "bouts_Dropped").lower() == "true" else gui.bouts_dropped_CB.deselect()
        gui.time_above_temper_CB.select() if gui.config.get(
            "Stats Options", "time_above_critical"
        ).lower() == "true" else gui.time_above_temper_CB.deselect()
        gui.time_below_temper_CB.select() if gui.config.get(
            "Stats Options", "time_below_critical"
        ).lower() == "true" else gui.time_below_temper_CB.deselect()
        gui.mean_temper_d_CB.select() if gui.config.get(
            "Stats Options", "mean_Daytime_Temperature"
        ).lower() == "true" else gui.mean_temper_d_CB.deselect()
        gui.mean_temper_d_sd_CB.select() if gui.config.get(
            "Stats Options", "daytime_Temp_StDev"
        ).lower() == "true" else gui.mean_temper_d_sd_CB.deselect()
        gui.median_temper_d_CB.select() if gui.config.get(
            "Stats Options", "median_Daytime_Temp"
        ).lower() == "true" else gui.median_temper_d_CB.deselect()
        gui.min_temper_d_CB.select() if gui.config.get("Stats Options", "min_Daytime_Temp").lower() == "true" else gui.min_temper_d_CB.deselect()
        gui.max_temper_d_CB.select() if gui.config.get("Stats Options", "max_Daytime_Temp").lower() == "true" else gui.max_temper_d_CB.deselect()
        gui.mean_temper_n_CB.select() if gui.config.get("Stats Options", "mean_Nighttime_Temp").lower() == "true" else gui.mean_temper_n_CB.deselect()
        gui.mean_temper_n_sd_CB.select() if gui.config.get(
            "Stats Options", "nighttime_Temp_StDev"
        ).lower() == "true" else gui.mean_temper_n_sd_CB.deselect()
        gui.median_temper_n_CB.select() if gui.config.get(
            "Stats Options", "median_Nighttime_Temp"
        ).lower() == "true" else gui.median_temper_n_CB.deselect()
        gui.min_temper_n_CB.select() if gui.config.get("Stats Options", "min_Nighttime_Temp").lower() == "true" else gui.min_temper_n_CB.deselect()
        gui.max_temper_n_CB.select() if gui.config.get("Stats Options", "max_Nighttime_Temp").lower() == "true" else gui.max_temper_n_CB.deselect()
        gui.mean_temper_dn_CB.select() if gui.config.get("Stats Options", "mean_DayNight_Temp").lower() == "true" else gui.mean_temper_dn_CB.deselect()
        gui.mean_temper_dn_sd_CB.select() if gui.config.get(
            "Stats Options", "dayNight_Temp_StDev"
        ).lower() == "true" else gui.mean_temper_dn_sd_CB.deselect()
        gui.median_temper_db_CB.select() if gui.config.get(
            "Stats Options", "median_DayNight_Temp"
        ).lower() == "true" else gui.median_temper_db_CB.deselect()
        gui.min_temper_dn_CB.select() if gui.config.get("Stats Options", "min_DayNight_Temp").lower() == "true" else gui.min_temper_dn_CB.deselect()
        gui.max_temper_dn_CB.select() if gui.config.get("Stats Options", "max_DayNight_Temp").lower() == "true" else gui.max_temper_dn_CB.deselect()
        gui.mean_air_temper_CB.select() if gui.config.get("Stats Options", "mean_air_temp").lower() == "true" else gui.mean_air_temper_CB.deselect()
        gui.mean_air_temper_sd_CB.select() if gui.config.get(
            "Stats Options", "mean_air_temp_stdev"
        ).lower() == "true" else gui.mean_air_temper_sd_CB.deselect()
        gui.min_air_temper_CB.select() if gui.config.get("Stats Options", "min_air_temp").lower() == "true" else gui.min_air_temper_CB.deselect()
        gui.max_air_temper_CB.select() if gui.config.get("Stats Options", "max_air_temp").lower() == "true" else gui.max_air_temper_CB.deselect()
        replace_entry(gui.time_above_temper_E, gui.config.get("Stats Options", "custom_time_above_temperature"))
        replace_entry(gui.time_below_temper_E, gui.config.get("Stats Options", "custom_time_below_temperature"))

    except:
        if program_startup:
            messagebox.showerror(("Config File Loading Error"), "default_config.ini could not be read, reverting to backup config file.")
            traceback.print_exc()

            # If an error is encountered, try loading "backup_config.ini"
            copyfile(gui.master_dir_path / "config_files" / "backup_config.ini", gui.master_dir_path / "config_files" / "default_config.ini")

            gui.config.read(gui.master_dir_path / "config_files" / "default_config.ini")
            load_config(gui, program_startup=True)
        else:
            messagebox.showerror(("Config File Loading Error"), str(config_file) + " could not be read.")
            traceback.print_exc()

def set_defaults(gui):
    """
        Updates default configureation file with current GUI status.
    """

    try:
        update_config(gui)
        messagebox.showinfo("Default Parameters Saved", "default_config.ini has been updated.")
    except:
        messagebox.showerror(
            ("Default Settings Error"), "An error was encountered while updating default parameters.  Check if provided parameters are valid."
        )


def init_config(gui):
    """
        Initializes GUI from backup_config.ini.  backup_config.ini is used as a backup if anything goes wrong.
    """

    gui.config = configparser.RawConfigParser()

    config_default_path = Path(gui.master_dir_path / "config_files" / "default_config.ini")
    backup_config_path = Path(gui.master_dir_path / "config_files" / "backup_config.ini")

    try:
        gui.config.read(str(config_default_path))
    except configparser.ParsingError:
        copyfile(backup_config_path, config_default_path)
        gui.config.read(str(config_default_path))

def update_config(gui, config_file=None):
    """
        Generates a configuration file from the current GUI parameters. If no file name if provided,
        this function saves to default_config.ini, resetting the default parameters for NestIQ.

        Args:
            config_file (string): path to and name of file to be saved
    """

    if config_file is None:
        config_file = Path(gui.master_dir_path / "config_files" / "default_config.ini")

    gui.config.set("Main Settings", "show_warnings", gui.show_warns_BV.get())
    gui.config.set("Main Settings", "day_start_time", gui.day_start_E.get())
    gui.config.set("Main Settings", "night_start_time", gui.night_start_E.get())
    gui.config.set("Main Settings", "restrict_bout_search", gui.restrict_search_BV.get())

    gui.config.set("Main Settings", "smoothing_radius", gui.smoothing_radius_E.get())
    gui.config.set("Main Settings", "duration_threshold", gui.dur_thresh_E.get())
    
    gui.config.set("Advanced Settings", "train_from", int(gui.train_from_IV.get()))
    gui.config.set("Advanced Settings", "off_bout_initial", gui.init_off_E.get())
    gui.config.set("Advanced Settings", "on_bout_initial", gui.init_on_E.get())
    gui.config.set("Advanced Settings", "off_off_trans", gui.off_off_trans_E.get())
    gui.config.set("Advanced Settings", "off_on_trans", gui.off_on_trans_E.get())
    gui.config.set("Advanced Settings", "on_on_trans", gui.on_on_trans_E.get())
    gui.config.set("Advanced Settings", "on_off_trans", gui.on_off_trans_E.get())
    gui.config.set("Advanced Settings", "off_bout_emis_mean", gui.off_mean_E.get())
    gui.config.set("Advanced Settings", "off_bout_emis_stdev", gui.off_stdev_E.get())
    gui.config.set("Advanced Settings", "on_bout_emis_mean", gui.on_mean_E.get())
    gui.config.set("Advanced Settings", "on_bout_emis_stdev", gui.on_stdev_E.get())

    gui.config.set("Plot Options", "manual_plot_dimensions", bool(gui.manual_plot_dims.get()))
    gui.config.set("Plot Options", "plot_x_dim", gui.plot_dim_x_E.get())
    gui.config.set("Plot Options", "plot_y_dim", gui.plot_dim_y_E.get())
    gui.config.set("Plot Options", "title_font_size", gui.title_font_size_E.get())
    gui.config.set("Plot Options", "axis_title_font_size", gui.axis_title_font_size_E.get())
    gui.config.set("Plot Options", "axis_label_font_size", gui.axis_label_font_size_E.get())
    gui.config.set("Plot Options", "axis_tick_size", gui.axis_tick_size_E.get())
    gui.config.set("Plot Options", "legend_font_size", gui.legend_font_size_E.get())

    gui.config.set("Plot Options", "plot_egg_tempers", gui.plot_egg_BV.get())
    gui.config.set("Plot Options", "plot_air_tempers", gui.plot_air_BV.get())
    gui.config.set("Plot Options", "plot_egg_minus_air", gui.plot_adj_BV.get())
    gui.config.set("Plot Options", "plot_smoothed", bool(gui.smooth_status_IV.get()))
    gui.config.set("Plot Options", "legend_location", gui.legend_loc.get())

    gui.config.set("Plot Options", "on_point_color", gui.on_point_color.get())
    gui.config.set("Plot Options", "off_point_color", gui.off_point_color.get())
    gui.config.set("Plot Options", "bout_line_color", gui.bout_line_color.get())
    gui.config.set("Plot Options", "air_line_color", gui.air_line_color.get())
    gui.config.set("Plot Options", "day_marker_color", gui.day_marker_color.get())

    gui.config.set("Plot Options", "on_point_size", gui.on_point_size_E.get())
    gui.config.set("Plot Options", "bout_line_width", gui.bout_line_width_E.get())
    gui.config.set("Plot Options", "air_line_width", gui.air_line_width_E.get())
    gui.config.set("Plot Options", "day_marker_width", gui.day_marker_width_E.get())

    gui.config.set("Plot Options", "show_day_marker", gui.show_day_markers_BV.get())
    gui.config.set("Plot Options", "show_grid", gui.show_grid_BV.get())

    gui.config.set("Stats Options", "day_number", gui.day_num_BV.get())
    gui.config.set("Stats Options", "date", gui.date_BV.get())
    gui.config.set("Stats Options", "off_bout_count", gui.off_count_BV.get())
    gui.config.set("Stats Options", "mean_off_bout_duration", gui.off_dur_BV.get())
    gui.config.set("Stats Options", "off_bout_duration_stdev", gui.off_dur_sd_BV.get())
    gui.config.set("Stats Options", "mean_off_bout_temp_drop", gui.off_dec_BV.get())
    gui.config.set("Stats Options", "off_bout_temp_drop_stdev", gui.off_dec_sd_BV.get())
    gui.config.set("Stats Options", "mean_off_bout_temp", gui.mean_off_temper_BV.get())
    gui.config.set("Stats Options", "off_bout_time_sum", gui.off_time_sum_BV.get())
    gui.config.set("Stats Options", "on_bout_count", gui.on_count_BV.get())
    gui.config.set("Stats Options", "mean_on_bout_duration", gui.on_dur_BV.get())
    gui.config.set("Stats Options", "on_bout_duration_stdev", gui.on_dur_sd_BV.get())
    gui.config.set("Stats Options", "mean_on_bout_temp_rise", gui.on_inc_BV.get())
    gui.config.set("Stats Options", "on_bout_temp_rise_stdev", gui.on_inc_sd_BV.get())
    gui.config.set("Stats Options", "mean_on_bout_temp", gui.mean_on_temper_BV.get())
    gui.config.set("Stats Options", "on_bout_time_sum", gui.on_time_sum_BV.get())
    gui.config.set("Stats Options", "time_above_critical", gui.time_above_temper_BV.get())
    gui.config.set("Stats Options", "time_below_critical", gui.time_below_temper_BV.get())
    gui.config.set("Stats Options", "bouts_dropped", gui.bouts_dropped_BV.get())
    gui.config.set("Stats Options", "mean_daytime_temperature", gui.mean_temper_d_BV.get())
    gui.config.set("Stats Options", "daytime_temp_stdev", gui.mean_temper_d_sd_BV.get())
    gui.config.set("Stats Options", "median_daytime_temp", gui.median_temper_d_BV.get())
    gui.config.set("Stats Options", "min_daytime_temp", gui.min_temper_d_BV.get())
    gui.config.set("Stats Options", "max_daytime_temp", gui.max_temper_d_BV.get())
    gui.config.set("Stats Options", "mean_nighttime_temp", gui.mean_temper_n_BV.get())
    gui.config.set("Stats Options", "nighttime_temp_stdev", gui.mean_temper_n_sd_BV.get())
    gui.config.set("Stats Options", "median_nighttime_temp", gui.median_temper_n_BV.get())
    gui.config.set("Stats Options", "min_nighttime_temp", gui.min_temper_n_BV.get())
    gui.config.set("Stats Options", "max_nighttime_temp", gui.max_temper_n_BV.get())
    gui.config.set("Stats Options", "mean_daynight_temp", gui.mean_temper_dn_BV.get())
    gui.config.set("Stats Options", "daynight_temp_stdev", gui.mean_temper_dn_sd_BV.get())
    gui.config.set("Stats Options", "median_daynight_temp", gui.median_temper_dn_BV.get())
    gui.config.set("Stats Options", "min_daynight_temp", gui.min_temper_dn_BV.get())
    gui.config.set("Stats Options", "max_daynight_temp", gui.max_temper_dn_BV.get())
    gui.config.set("Stats Options", "mean_air_temp", gui.mean_air_temper_BV.get())
    gui.config.set("Stats Options", "mean_air_temp_stdev", gui.mean_air_temper_sd_BV.get())
    gui.config.set("Stats Options", "min_air_temp", gui.min_air_temper_BV.get())
    gui.config.set("Stats Options", "max_air_temp", gui.max_air_temper_BV.get())
    gui.config.set("Stats Options", "custom_time_over_bool", gui.time_above_temper_BV.get())
    gui.config.set("Stats Options", "custom_time_below_bool", gui.time_below_temper_BV.get())

    gui.config.set("Stats Options", "custom_time_above_temperature", gui.time_above_temper_E.get())
    gui.config.set("Stats Options", "custom_time_below_temperature", gui.time_below_temper_E.get())

    with open(config_file, "w") as out_file:
        gui.config.write(out_file)
