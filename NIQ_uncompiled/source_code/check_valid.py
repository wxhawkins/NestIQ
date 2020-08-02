import time
import datetime as dt
from pathlib import Path
from tkinter import messagebox
import re
import niq_misc
import math
import traceback

from niq_misc import replace_entry


def check_valid_vertex_file(gui):
    """
        Checks user-provided vertex selection file (HTML) for issues that could cause errors with
        downstream processes.

        Returns:
            True if file passes all tests, else displays error message and returns False
    """

    niq_misc.remove_curly(gui.vertex_file_E)
    vertex_path = Path(gui.vertex_file_E.get())

    # Check if path is empty
    if vertex_path.name == "":
        messagebox.showerror("Vertex File Error", "Please provide a vertex file.")
        return False

    # Check if path has invalid path
    if vertex_path.suffix not in (".html", ""):
        messagebox.showerror("Vertex Selection Error", r'Vertex selection file must have ".html" extension.')
        return False

    # Check if path exists
    if not vertex_path.exists():
        messagebox.showerror("Vertex Selection Error", "Provided vertex selection file not found.")
        return False

    with open(vertex_path, "r") as original_file:
        original_lines = original_file.readlines()

    # Remove extra table data lines if present
    cleaned_content = str()
    found = False
    for line in original_lines:
        if "<div class" in line:
            found = True
        if found:
            cleaned_content += line

    # Get datapoints
    tokens = re.finditer(r">([\d\.-]+)</span>", cleaned_content)

    try:
        # Every other value in tokens will be temperature and so is ignored
        for counter, match in enumerate(tokens):
            token_num = counter
            if not (counter % 2) == 0:
                round(float(match.group(1)))
    except:
        messagebox.showerror(("Vertex File Error"), "Vertex file is unreadable. Please try another.")
        return False

    if token_num < 2:
        messagebox.showerror(("Vertex File Error"), "No vertices detected in vertex file.")
        return False

    return True


def check_valid_main(gui, first_in=True, check_output=True):
    """
        Checks for valid configuration of all parameters housed on the Main tab.  This includes extensive
        review of the input file provided.

        Args:
            first_in (bool): False if current file is second or later in a queue of multiple input files
            check_output (bool): if False, output file names are not examined
    """

    def check_input_file(gui):
        """
            Checks several aspects of the input file to ensure it is compatable with all downstream processing.
            Also displays warnings for less severe format violations.
        """

        def check_datetime_intervals():
            """ Sets time interval between temperature readings and checks for gaps in date/time column. """

            delta_secs = (datetimes[-1] - datetimes[0]).total_seconds()
            interval = dt.timedelta(seconds=round(delta_secs / len(master_list)))

            if not gui.show_warns_BV.get():
                return True

            # If interval is greater than or equal to one minute
            if interval.seconds >= 60:
                i = 1
                while i < len(datetimes):
                    if datetimes[i - 1] + interval != datetimes[i]:
                        messagebox.showwarning(
                            "Date/time Warning",
                            f"{file_name_appendage}Discontinuous date/time found for data point {master_list[i][0]}." +
                            "The run will continue, but this could cause inaccurate statistical output.",
                        )
                    i += 1
                
                return True

            # If interval is less than one minute
            # Identify first change in date/time
            i = 0
            while datetimes[i] == datetimes[0]:
                i += 1

            # Find least common denominator with one minute
            LCD = abs(interval.seconds*60) // math.gcd(interval.seconds, 60)
            dp_leap = int(LCD / interval.seconds) # There should be a whole number minute change after this many data points
            min_leap = dt.timedelta(minutes=int(LCD / 60)) # That whole number of minutes is this

            i += dp_leap
            while i < len(datetimes):
                if datetimes[i - dp_leap] + min_leap != datetimes[i]:
                    messagebox.showwarning(
                    "Date/time Warning",
                    f"{file_name_appendage}Discontinuous date/time found for data point {master_list[i][0]}." +
                    "The run will continue, but this could cause inaccurate statistical output.",
                )
                i += dp_leap

            return True


        in_file_path = gui.active_input_path
        file_name_appendage = f"For file: {in_file_path.name} \n\n"
        datetimes = []

        if in_file_path.name == "":
            messagebox.showerror("Input error (Main tab)", "No input file provided.")
            return False

        if not in_file_path.exists():
            messagebox.showerror("Input File Error", "".join((file_name_appendage, "File with provided path could not be found.")))
            return False 

        if in_file_path.suffix not in (".csv", ".html"):
            messagebox.showerror("Input File Error", f'{file_name_appendage} Input file must have "csv" or "html" extension.')
            return False   

        try:

            # In the case of an HTML input, simply check for the presence of input file data
            if in_file_path.suffix == ".html":
                with open(in_file_path, "r") as f:
                    content = f.read()

                if "NestIQ input data" in content:
                    return True
                else:
                    messagebox.showerror("Input File Error", f'{file_name_appendage} HTML file does not contain the necessary information for processing.')
                    return False
            
            with open(in_file_path, "r") as f:
                lines = f.readlines()

            master_list = [line.strip().rstrip(",").split(",") for line in lines]

            pop_indices = []
            # Remove lines not conforming to expected format (such as headers)
            for i in range(len(master_list[:-1])):
                # Cells in data point column must contain only numbers
                if not str(master_list[i][0]).isnumeric():
                    pop_indices.append(i)

            for pop_count, index in enumerate(pop_indices):
                master_list.pop(index - pop_count)

            master_list.pop(len(master_list) - 1)

            prev_line = master_list[0]

            if len(prev_line) < 3:
                gui.air_valid = False

            for line in master_list[1:]:
                line = line[:4] if gui.air_valid else line[:3]

                # Check if data points are continuous and sequential
                try:
                    if not int(line[0]) == (int(prev_line[0]) + 1):
                        raise ValueError
                except:
                    messagebox.showerror(
                        "Data Point Error",
                        f"{file_name_appendage}Error after data point "
                        + f"{prev_line[0]}. Data point number is not sequential with regard to previous data point.",
                    )
                    return False

                # Test conversion of date/time string to datetime object
                try:
                    datetimes.append(niq_misc.convert_to_datetime(line[1]))
                except ValueError:
                    messagebox.showerror(
                        "Date/Time Error", f"{file_name_appendage}Invalid date/time found for data point {line[0]}.  Date/Time should be in MM/DD/YYYY HH:MM (:SS) format."
                    )
                    return False

                # Check egg temperatures column
                try:
                    float(line[2])
                except:
                    messagebox.showerror("Temperature Error", f"{file_name_appendage}Invalid temperature given for data point {line[0]}.")
                    return False

                # Check air temperatures column if appropriate
                if gui.air_valid:
                    try:
                        float(line[3])
                    except (IndexError, ValueError):
                        gui.air_valid = False
                        if gui.show_warns_BV.get():
                            messagebox.showwarning(
                                "Air Temperature Warning",
                                f"{file_name_appendage}Invalid air temperature detected for data point "
                                + f"{line[0]}. Air temperatures will not be plotted or included in statistical output.",
                            )
                prev_line = line

            # Lastly, check if date/times are continuous
            return check_datetime_intervals()

        except Exception as e:
            print(e)
            traceback.print_exc()
            messagebox.showerror(
                "Unknown Error",
                f"{file_name_appendage}There was an unidentifiable error with the provided input file. "
                + "This is sometimes the result of 'extra' cells in the input file.\n\n"
                + "Please reference the NestIQ manual for details regarding proper input file format."
                + " This can be accessed by clicking 'Help' in the top right.",
            )
            return False

    def check_out_file(gui, entry, title):
        """
            Checks if the name provided for a given output file is valid.  This includes asking the user if
            they want to override if a file with the same name already exists.

            Args:
                entry (tk.Entry): entry box being examined
                title (string): how to reference the current entry box if error messeage is triggered
        """

        if entry.get() == "":
            messagebox.showerror(f"{title} Error", "File name is empty.")
            return False

        entry_path = Path(entry.get())

        if entry_path.is_dir():
            messagebox.showerror(f"{title} Error", "Directory provided but no file name.")
            return False

        # Add extension if not present
        if entry == gui.plot_file_E:
            ext = ".html"
        elif entry == gui.stats_file_E or entry == gui.multi_in_stats_file_E:
            ext = ".csv"

        entry_path = Path(entry.get()).with_suffix(ext)

        # Default to "output_files" directory if only filename (no dir) provided
        if str(entry_path.parent) == ".":
            entry_path = gui.master_dir_path / "output_files" / entry_path

        replace_entry(entry, str(entry_path))

        # Check if plot file already exists and if so, ask to override
        if entry_path.exists():
            if gui.show_warns_BV.get():
                if not messagebox.askyesno("Override?", f"The file '{entry.get()}' already exists.  Do you want to override?"):
                    return False
            try:
                entry_path.unlink()
            except PermissionError:
                messagebox.showerror(f"{title} Error", "File could not be overridden. Please ensure files are closed before overriding.")

        return True

    # Check time entry boxes
    for time_str in (gui.day_start_E.get(), gui.night_start_E.get()):
        try:
            time.strptime(time_str, "%H:%M")
        except ValueError:
            messagebox.showerror("Daytime Start/End Error", f"Provided value of {time_str} is invalid. Please provide times in 24 hr HH:MM (:SS) format.")
            return False

    # Check data smoothing box
    try:
        if not float(gui.smoothing_radius_E.get()).is_integer():
            raise ValueError

        if int(gui.smoothing_radius_E.get()) < 0:
            messagebox.showerror("Data Smoothing Radius Error", "Data smoothing radius must be greater than or equal to zero.")
            return False
    except ValueError:
        messagebox.showerror("Data Smoothing Radius Error", "Data smoothing radius must be an integer.")
        return False

    # Check duration threshold box
    try:
        if int(float(gui.dur_thresh_E.get())) < 0:
            messagebox.showerror("Duration Threshold Error", "Duration threshold cannot be less than zero.")
            return False
    except ValueError:
        messagebox.showerror("Duration Threshold Error", "Invalid duration threshold (could not convert to integer).")
        return False

    if not check_input_file(gui):
        return False

    if check_output:
        if gui.make_plot_BV.get():
            if not check_out_file(gui, gui.plot_file_E, "Plot File"):
                return False

        if gui.get_stats_BV.get():
            if not check_out_file(gui, gui.stats_file_E, "Stats Output File"):
                return False

        if gui.multi_in_stats_BV.get() and first_in:
            if not check_out_file(gui, gui.multi_in_stats_file_E, "Compile Summary"):
                return False

    return True

def check_valid_adv(gui):
    """
                    Checks for valid configuration of all parameters housed on the Advanced tab.
    """

    def try_autofill():
        """
                        Checks if all Markov model parameter boxes are empty and runs unsupervised learning if so.
        """

        for entry in (
            gui.init_off_E,
            gui.init_on_E,
            gui.off_off_trans_E,
            gui.off_on_trans_E,
            gui.on_on_trans_E,
            gui.on_off_trans_E,
            gui.off_mean_E,
            gui.on_mean_E,
            gui.off_stdev_E,
            gui.on_stdev_E,
        ):
            if entry.get() != "":
                return False

        gui.unsupervised_learning(auto_run=True)
        return True

    try:
        entries = (gui.init_off_E, gui.init_on_E, gui.off_off_trans_E, gui.off_on_trans_E, gui.on_on_trans_E, gui.on_off_trans_E)

        for entry in entries:
            if float(entry.get()) < 0:
                raise ValueError("Probability less than 0 provided.")
    except ValueError:
        if gui.UL_default_BV.get():
            if try_autofill():
                return True

        messagebox.showerror("Parameter Error (Advanced tab)", "Probabilities must be real numbers greater than 0.")

        return False

    try:
        (float(mean) for mean in (gui.off_mean_E.get(), gui.on_mean_E.get()))

    except TypeError:
        messagebox.showerror("Parameter Error (Advanced tab)", "Means must be real numbers.")
        return False
    try:
        for stdev in (gui.off_stdev_E.get(), gui.on_stdev_E.get()):
            if float(stdev) <= 0:
                raise ValueError("Standard deviation less than 0 provided.")
    except:
        messagebox.showerror("Parameter Error (Advanced tab)", "Standard deviations must be real numbers greater than 0.")
        return False

    return True

def check_valid_plot_ops(gui):
    """
                    Checks for valid configuration of all parameters housed on the Plot Options tab.
    """

    # Check plot dimensions
    if gui.manual_plot_dims.get():
        valid = True
        try:
            if int(gui.plot_dim_x_E.get()) < 1 or int(gui.plot_dim_y_E.get()) < 1:
                valid = False
        except:
            valid = False

        if not valid:
            messagebox.showwarning(
                "Plot Dimensions Warning",
                ("Provided plot dimensions are not valid; please provide positive integers. Automatic resolution detection will be used."),
            )
            gui.manual_plot_dims.set(0)

    try:
        if float(gui.title_font_size_E.get()) < 0:
            raise ValueError("Provided plot title font size is less than 0")
    except ValueError:
        messagebox.showerror("Plot title Font Size Error (Plot Options tab)", "Invalid plot title font size was provided.")
        return False

    try:
        if float(gui.axis_title_font_size_E.get()) < 0:
            raise ValueError("Provided axis title font size is less than 0")
    except ValueError:
        messagebox.showerror("Axis Title Font Size Error (Plot Options tab)", "Invalid axis title font size was provided.")
        return False

    try:
        if float(gui.axis_label_font_size_E.get()) < 0:
            raise ValueError("Provided axis label font size is less than 0")
    except ValueError:
        messagebox.showerror("Axis Label Font Size Error (Plot Options tab)", "Invalid axis label font size was provided.")
        return False

    try:
        if int(gui.axis_tick_size_E.get()) < 0:
            raise ValueError("Provided axis tick size is less than 0")
    except ValueError:
        messagebox.showerror("Axis Tick Size Error (Plot Options tab)", "Invalid axis tick size was provided.")
        return False

    try:
        if float(gui.legend_font_size_E.get()) < 0:
            raise ValueError("Provided legend font size is less than 0")
    except ValueError:
        messagebox.showerror("Legend Font Size Error (Plot Options tab)", "Invalid legend font size was provided.")
        return False

    # Check plot element sizes/widths
    try:
        if float(gui.on_point_size_E.get()) < 0:
            raise ValueError("Provided on-bout point size is less than 0")
    except ValueError:
        messagebox.showerror("Point Size Error (Plot Options tab)", "Invalid on-bout point size was provided.")
        return False

    try:
        if float(gui.bout_line_width_E.get()) < 0:
            raise ValueError("Provided bout line width is less than 0")
    except ValueError:
        messagebox.showerror("Line Width Error (Plot Options tab)", "Invalid bout line width was provided.")
        return False

    try:
        if float(gui.air_line_width_E.get()) < 0:
            raise ValueError("Provided air line width is less than 0")
    except ValueError:
        messagebox.showerror("Line Width Error (Plot Options tab)", "Invalid air temperature line width was provided.")
        return False

    if gui.show_day_markers_BV.get():
        try:
            if float(gui.day_marker_width_E.get()) < 0:
                raise ValueError("Provided day marker size is less than 0")
        except ValueError:
            messagebox.showerror("Day Marker Size Error (Plot Options tab)", "Invalid day marker size was provided.")
            return False

    return True

def check_valid_stat_ops(gui):
    """
                    Checks for valid configuration of all parameters housed on the Stat Options tab.
    """

    try:
        float(gui.time_above_temper_E.get())
    except:
        messagebox.showerror("Custom Temperature Error (Stat Options tab)", 'Invalid "Time above" temperature.')
        return False

    try:
        float(gui.time_below_temper_E.get())
    except:
        messagebox.showerror("Custom Temperature Error (Stat Options tab)", 'Invalid "Time below" temperature.')
        return False

    return True
