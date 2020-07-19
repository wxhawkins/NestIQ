from pathlib import Path
import re
from random import randint
import traceback

import colorama
from termcolor import colored

from niq_misc import replace_entry

from tkinter import filedialog


def test_run(gui):
    """ Load GUI entry boxes with test files. """

    test_dir_path = gui.master_dir_path / "testing"

    # Input file
    replace_entry(gui.input_file_E, test_dir_path / "input" / "test_input_long.csv")

    # Vertex plot
    replace_entry(gui.vertex_file_E, test_dir_path / "plots" / "vertex_selection.html")

    # Original plot
    replace_entry(gui.ori_plot_E, test_dir_path / "input" / "test_input_long.html")

    # Modified plot
    replace_entry(gui.mod_plot_E, test_dir_path / "input" / "mod_plot.html")


def master_test(gui):
    """
        Run automated tests for unrestricted plotting/statistics, restricted plotting/statistics,
        unsupervised learning and supervised learning.
    """

    def compare_stats(key, ref_path, test_path):
        """
            Compare two statistics files line by line and store discrepencies.

            Args:
                key (int): random number identifier for this test run
                ref_path (pathlib.Path): Path to reference statistics file
                test_path (pathlib.Path): Path to test statistics file
        """

        mismatches = dict()

        # Exctract important lines from files provided

        with open(ref_path, "r") as ref_file, open(test_path, "r") as test_file:
            ref_lines = ref_file.readlines()
            labels = ref_lines[1].strip().split(",")
            ref_vals = ref_lines[10].strip().split(",")
            # test_vals = test_file.readlines()[10].strip().split(",")
            test_vals = test_file.read().split("\n")[12].strip().split(",")

        # Compare values
        for i, label in enumerate(labels):
            if ref_vals[i].strip() != test_vals[i].strip():
                try:
                    if float(ref_vals[i]) != float(test_vals[i]):
                        mismatches[label] = (ref_vals[i], test_vals[i])
                except ValueError:
                    mismatches[label] = (ref_vals[i], "None")

        return mismatches

    def compare_configs(ref_path, test_path):
        """
            Compare two configuration files line by line and store discrepencies.

            Args:
                ref_path (pathlib.Path): Path to reference configuration file
                test_path (pathlib.Path): Path to test configuration file
        """

        with open(ref_path, "r") as ref_file, open(test_path, "r") as test_file:
            ref_lines = ref_file.readlines()
            test_lines = test_file.readlines()
        mismatches = dict()
        for ref_line, test_line in zip(ref_lines[2:], test_lines[2:]):
            if test_line.strip() != ref_line.strip():
                try:
                    # Get line label
                    label = re.search((r"[^=]*"), ref_line).group(0)
                    # Get reference and test values
                    ref_val = re.search((r"=(.*)"), ref_line).group(1).strip()
                    test_val = re.search((r"=(.*)"), test_line).group(1).strip()
                    # Try converting and comparing as floats
                    try:
                        if float(ref_val) != float(test_val):
                            mismatches[label] = (ref_val, test_val)
                    except:
                        if ref_val != test_val:
                            mismatches[label] = (ref_val, test_val)
                except:
                    mismatches[label] = (ref_val, "None")

        return mismatches

    # Initialization
    test_dir_path = gui.master_dir_path / "testing"
    test_out_dir = test_dir_path / "temp_output"

    in_file_path = test_dir_path / "input" / "test_input_long.csv"

    # Load config file
    ref_config_path = test_dir_path / "config" / "test_config.ini"
    gui.load_config(config_file_=ref_config_path)

    # Load testing input file
    replace_entry(gui.input_file_E, in_file_path)

    # Set up output
    rand_key = str(randint(1e6, 1e7))

    # ---------------------------------Statistics----------------------------------------
    # Declare paths
    unres_ref_stats_path = test_dir_path / "stats" / "ref_stats_unrestricted_long.csv"
    res_ref_stats_path = test_dir_path / "stats" / "ref_stats_restricted_long.csv"

    # Set up text coloring
    colorama.init()

    print(f"Key = {rand_key}")

    for test_type in ("unrestricted", "restricted"):
        # Test unrestricted statistics
        print(f"\n\nTesting statistics ({test_type})")
        if test_type == "restricted":
            gui.restrict_search_CB.select()
        else:
            gui.restrict_search_CB.deselect()

        ref_path = res_ref_stats_path if test_type == "restricted" else unres_ref_stats_path

        # Set up output file names
        test_stats_path = test_out_dir / f"{rand_key}_{test_type}.csv"
        test_plot_path = test_out_dir / f"{rand_key}_{test_type}.html"
        replace_entry(gui.stats_file_E, test_stats_path)
        replace_entry(gui.plot_file_E, test_plot_path)

        # Run statistical analysis
        gui.trigger_run()

        # Look for discrepencies in output files
        mismatches = dict()
        mismatches = compare_stats(rand_key, ref_path, test_stats_path)

        # Notify user of mismatched values if any
        if not mismatches:
            print(colored(f"{test_type.upper()} STATS PASSED".center(100, "-"), "green"))
        else:
            print(colored(f"{test_type.upper()} STATS FAILED".center(100, "-"), "red"))
            for key, values in mismatches.items():
                print(
                    colored(key, "yellow")
                    + ": test value of "
                    + colored(str(values[1]), "yellow")
                    + " did not match reference "
                    + colored(str(values[0]), "yellow")
                )

    # ---------------------------------Unsupervised learning--------------------------------------
    print(f"\n\nTesting unsupervised learning")

    gui.load_config(config_file_=ref_config_path)
    gui.unsupervised_learning()
    unsup_test_path = test_out_dir / f"{rand_key}_unsup_test_config.ini"
    unsup_ref_path = test_dir_path / "config" / "unsup_ref_config.ini"
    gui.save_config(out_file=str(unsup_test_path))

    # Search for config discrepencies
    mismatches = dict()
    mismatches = compare_configs(unsup_ref_path, unsup_test_path)

    if not mismatches:
        print(colored("UNSUP PASSED".center(100, "-"), "green"))
    else:
        print(colored("UNSUP FAILED".center(100, "-"), "red"))
        for key, values in mismatches.items():
            print(
                colored(key, "yellow")
                + ": test value of "
                + colored(str(values[1]), "yellow")
                + " did not match reference "
                + colored(str(values[0]), "yellow")
            )

    # ---------------------------------Supervised learning----------------------------------------
    print(f"\n\nTesting supervised learning")

    vertex_file_path = test_dir_path / "plots" / "vertex_selection.html"

    # Attempt to make vertex selection plot
    try:
        gui.select_vertices()
    except:
        print(colored("VERTEX SELECTION PLOT FAILED".center(100, "-"), "red"))
        traceback.print_exc()

    replace_entry(gui.vertex_file_E, vertex_file_path)

    gui.load_config(config_file_=ref_config_path)
    gui.supervised_learning()
    sup_test_path = test_out_dir / f"{rand_key}_sup_test_config.ini"
    sup_ref_path = test_dir_path / "config" / "sup_ref_config.ini"
    gui.save_config(out_file=str(sup_test_path))

    # Search for config discrepencies
    mismatches = dict()
    mismatches = compare_configs(sup_ref_path, sup_test_path)

    if not mismatches:
        print(colored("SUP PASSED".center(100, "-"), "green"))
    else:
        print(colored("SUP FAILED".center(100, "-"), "red"))
        for key, values in mismatches.items():
            print(
                colored(key, "yellow")
                + ": test value of "
                + colored(str(values[1]), "yellow")
                + " did not match reference "
                + colored(str(values[0]), "yellow")
            )

    # ---------------------------------Plot Editing----------------------------------------
    print(f"\n\nTesting plot editing")

    # Establish configuration
    ref_config_path = test_dir_path / "config" / "test_config.ini"
    gui.load_config(config_file_=ref_config_path)

    # Declare file paths
    mod_ref_path = test_dir_path / "stats" / "ref_mod_stats.csv"
    ori_plot_path = test_dir_path / "input" / "test_input_long.html"
    mod_plot_path = test_dir_path / "input" / "mod_plot.html"

    # Fill entry boxes
    replace_entry(gui.input_file_E, in_file_path)
    replace_entry(gui.ori_plot_E, ori_plot_path)
    replace_entry(gui.mod_plot_E, mod_plot_path)

    # Make modifiable plot
    gui.select_vertices(mod_plot=True)

    # Set up output file names
    test_mod_stats_path = test_out_dir / f"{rand_key}_modified.csv"
    test_mod_plot_path = test_out_dir / f"{rand_key}_modified.html"
    replace_entry(gui.stats_file_E, test_mod_stats_path)
    replace_entry(gui.plot_file_E, test_mod_plot_path)

    # Rerun with modified verticies
    gui.trigger_run(rerun=True)

    # Look for discrepencies in output files
    mismatches = dict()
    mismatches = compare_stats(rand_key, mod_ref_path, test_mod_stats_path)

    # Notify user of mismatched values if any
    if not mismatches:
        print(colored("PLOT EDITING PASSED".center(100, "-"), "green"))
    else:
        print(colored("PLOT EDITING FAILED".center(100, "-"), "red"))
        for key, values in mismatches.items():
            print(
                colored(key, "yellow")
                + ": test value of "
                + colored(str(values[1]), "yellow")
                + " did not match reference "
                + colored(str(values[0]), "yellow")
            )

    print(colored("TESTING COMPLETED".center(100, "-"), "blue"))
