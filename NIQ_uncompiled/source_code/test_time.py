from tkinter import filedialog, font, messagebox, ttk
from dateutil.parser import parse
import re
from datetime import datetime


def check_time(time, DN):
			"""
							Checks if times provided for daytime start and nighttime start are valid.

							Args:
											time (string): string provided in the entry box
											DN (string): "day" or "night" depending on entry box being analyzed
			"""

			time_re = re.search(r"(\d+)(:)(\d+)", time)
			show_default_error = False

			# If time found, store hour and minute values
			if time_re:
				hour = int(time_re.group(1))
				minute = int(time_re.group(3))
			else:
				show_default_error = True

			# Detects non-numerical characters (possibly due to use of 12hr, am/pm format)
			if re.search("([^0-9:])", time):
				# messagebox.showerror("Start Time Error", (DN + " start time must be entered in 24 hr format."))
				return False
			elif hour < 0 or hour > 23:
				show_default_error = True
			elif minute < 0 or minute > 59:
				show_default_error = True

			if show_default_error:
				# messagebox.showerror("Start Time Error", ("Invalid " + DN + " start time."))
				return False

			return True


def check_time_new(string, fuzzy=True):
    """
    Return whether the string can be interpreted as a date.

    :param string: str, string to check for date
    :param fuzzy: bool, ignore unknown tokens in string if True
    """
    try:
        parse(string, fuzzy=fuzzy)
        dt = datetime.strptime(string, "%M:%S")
        print(dt.time)
        return True

    except ValueError:
        return False


tests = ["12:00", "13:00", "25:00", "4/21/2018 9:48", "4/21/2018 9:48 PM", "4/21/2018 232:48 PM", "4/21/2018 19:48 PM"]

for test in tests:
    print(test)
    print(f"Check Time Old: {check_time(test, 'day')}")
    print(f"Check Time New: {check_time_new(test)}")
