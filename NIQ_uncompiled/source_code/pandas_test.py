from pathlib import Path
import pandas as pd
import numpy as np
import re


class GUI:
    def __init__(self, air_valid_):
        self.air_valid = air_valid_


def get_master_df(gui, source_path):
    def smooth_col(radius, col):
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

        # Create empty Series
        smoothed_col = pd.Series(np.zeros(col.size, dtype=float))
        window_size = (radius * 2) + 1

        # Fill in with averaged temperatures
        for i in range(radius, col.size - radius):
            sum_ = sum(val for val in col.iloc[(i - radius):(i + radius + 1)])
            smoothed_col.iloc[i] = sum_ / window_size

        # Fill in ends
        for i in range(radius):
            smoothed_col.iloc[i] = col.iloc[i]
            smoothed_col.iloc[-(i + 1)] = col.iloc[-(i + 1)]

        return smoothed_col

    def is_number(string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    df = pd.read_csv(source_path)

    # Fill air_temper column with 0's if none provided
    if not gui.air_valid:
        df.iloc[:, 3] = np.zeros(df.shape[0])

    # Remove any "extra" columns
    if len(df.columns) > 4:
        for col in df.columns[3:]:
            df.drop(columns=col, inplace=True)

    # Rename columns
    old_col_names = list(df.columns)
    col_names = ["data_point", "date_time", "egg_temper", "air_temper"]
    col_rename_dict = {old: new for old, new in zip(old_col_names, col_names)}
    df.rename(columns=col_rename_dict, inplace=True)

    # Set any data_point, egg_temper or air_temper cells with non-number values to NaN
    numeric_cols = col_names[0:1] + col_names[2:]
    for col in numeric_cols:
        filt = df[col].astype(str).apply(is_number)
        df.loc[~filt, col] = np.NaN

    # Delete any rows containing NaN value
    df.dropna(inplace=True)

    # Convert column object types
    df["data_point"] = df["data_point"].astype(int)
    df["date_time"] = df["date_time"].astype(str)
    df["egg_temper"] = df["egg_temper"].astype(float)
    if gui.air_valid:
        df["air_temper"] = df["air_temper"].astype(float)

    # Reassign data_point column to be continuous
    start = int(df["data_point"].iloc[0])
    new_col = range(start, df.shape[0] + 1)
    df["data_point"] = new_col

    # Set indices to data_point column
    # df.set_index("data_point", inplace=True)

    # Add adjusted (egg - air temperature) temperatures column
    df["adj_temper"] = df["egg_temper"] - df["air_temper"]

    # Add smoothed, adjusted temperatures column
    # FLAG radius = int(gui.smoothing_radius_E.get())
    radius = 1
    df["smoothed_adj_temper"] = smooth_col(radius, df["adj_temper"])

    # Add column storing difference in adjusted temperature from previous entry to current
    df["delta_temper"] = np.zeros(df.shape[0])
    df.iloc[1:, df.columns.get_loc("delta_temper")] = df["smoothed_adj_temper"].diff()
    # Set first cell equal to second
    df.iloc[0, df.columns.get_loc("delta_temper")] = df.iloc[1, df.columns.get_loc("delta_temper")]
    return df


gui = GUI(True)
path = Path(r"C:\Users\wxhaw\OneDrive\Desktop\Github\NestIQ\NIQ_uncompiled\testing\input\test_input_long.csv")
df = get_master_df(gui, path)
print(len(df))
print(df.shape)
