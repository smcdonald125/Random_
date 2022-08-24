"""
Script: mine_LULC_matrices.py
Author: Sarah McDonald, Geographer, U.S. Geological Survey: Lower Mississippi-Gulf Water Science Center
Purpose: This script allows a user to select the matrix schema (full 54, general 18, or Phase 6 13) and mine each
         counties' change matrix of that schema for specified transitions. The data will be written to a single csv,
         containing the acres of the specified transitions (columns) and a row per county.
How to run:
    1. Set the USER DEFINED VARIABLES below
    2. Save the script
    3. Open conda prompt (search for Anaconda in Windows search bar and open "Anaconda Prompt (Miniconda)")
    4. Activate environment that has pandas library. Enter: conda activate environment_name
        a. if you do not have pandas installed, create environment and install it. You can install pandas in your base
            by not creating an environment and entering: conda install pandas
    5. Run the script. Type in the prompt: python /full/path/to/mine_LULC_matrices.py and hit enter
    6. Check the output where you defined the output CSV to go!
"""
import pandas as pd
import os

"""
----------------------
USER DEFINED VARIABLES
----------------------
transition_dict: dictionary of field_name: [from classes], [to classes]
schema: matrix schema to mine: 13, 18, or 54
bp_flag: True if bay portion of counties and False if full county
output_path: set the full path to the CSV you wish to write the results to
planimetrics_folder: path to the planimetrics folder/landuse/version2
"""
transition_dict = {
    'IMP_TC'    : [ ['ROAD', 'IMPS', 'IMPO'], ['FORE', 'TCOT'] ],
    'IMP_AG'    : [ ['ROAD', 'IMPS', 'IMPO'], ['CROP', 'PAST'] ],
}
schema = 18
bp_flag = False
output_file = r'G:\ImageryServer\usgs_sc\smcdonald\Scripts\Testing\LULC_18x18_IMPLoss.csv'
planimetrics_folder = r"X:/landuse/version2"

def validate_input():
    # validate transition dict
    if len(transition_dict) == 0:
        raise TypeError("Error: no transitions defined in transition_dict")
    for t in transition_dict:
        e_msg = "Error: transition dict expects \n\tstring variable name: followed by a list containing 2 lists"
        if type(transition_dict[t]) != list or len(transition_dict[t]) != 2:
            raise TypeError(e_msg)
        if type(transition_dict[t][0]) != list or type(transition_dict[t][0]) != list:
            raise TypeError(e_msg)

    # validate paths
    if not os.path.isdir(planimetrics_folder):
        raise TypeError(f"Planimetrics folder path does not exist: {planimetrics_folder}")

    if not os.path.isdir(os.path.dirname(output_file)):
        raise TypeError(f"Output file folder does not exist: {os.path.dirname(output_file)}")

    if os.path.isfile(output_file):
        raise TypeError(f"Output file already exists: {output_file}")

    # validate schema
    if schema not in [13, 18, 54]:
        raise TypeError(f"Invalid schema value, expected 13, 18 or 54")

    # validate bay portion flag
    if type(bp_flag) != bool:
        raise TypeError(f"Invalid bp_flag type, expected True or False of boolean type")

    # print validation passed
    out_msg = f"Mining {schema}x{schema} matrices for "
    if bp_flag:
        out_msg += f"bay portion of counties\n"
    else:
        out_msg += f"full extent of counties\n"

    for t in transition_dict:
        out_msg += f"\tCreating {t} field: from "
        for i in range(len(transition_dict[t][0])):
            if i == len(transition_dict[t][0]) - 1:
                out_msg += f"{transition_dict[t][0][i]} to "
            else:
                out_msg += f"{transition_dict[t][0][i]}, "
        for i in range(len(transition_dict[t][1])):
            if i == len(transition_dict[t][1]) - 1:
                out_msg += f"{transition_dict[t][1][i]}\n"
            else:
                out_msg += f"{transition_dict[t][1][i]}, "
    print(out_msg)


def sum_classes(from_classes, to_classes, df):
    val = 0
    for f in from_classes:
        for t in to_classes:
            val += df.loc[f, t]

    return val

def get_change(planimetrics_folder, cfs):
    """
    Method: get_change()
    Purpose: Calculate metrics for each specified transition
    Params: folder - path to version2 folder
            cfs - list of cofips
    Returns: df - dataframe of change metrics
    """
    df = pd.DataFrame(columns=['cf']+list(transition_dict.keys()))
    for cf in cfs:
        output = f"{planimetrics_folder}/{cf}/output"
        if bp_flag: # bay portion only
            matrix = [x for x in os.listdir(output) if f"{schema}x{schema}" in x and 'cbw' in x][0]
        else: # full county
            matrix = [x for x in os.listdir(output) if f"{schema}x{schema}" in x and 'cbw' not in x][0]

        # read in county matrix
        tmp = pd.read_csv(f"{output}/{matrix}")

        # set index on T2-T2 column
        col = [x for x in list(tmp) if '2013' in x or '2014' in x][0]
        tmp = tmp.set_index(col)

        #loop through the transition matrix
        data = [cf]
        for transition in transition_dict:
            d = sum_classes(transition_dict[transition][0], transition_dict[transition][1], tmp)
            data.append(d)

        # add county info to df
        df.loc[len(df)] = data.copy()
        del data

    # return data
    return df

if __name__=="__main__":
    validate_input()

    # get list of cofips
    cfs = [x for x in os.listdir(planimetrics_folder) if os.path.isdir(f"{planimetrics_folder}/{x}") and 'backup' not in x]
    if len (cfs) != 206:
        raise TypeError(f"Incorrect number of counties: {len(cfs)}")
    else:
        print("Analyzing 206 Counties...")

    # create change metric
    change_df = get_change(planimetrics_folder, cfs)

    # create a fips column
    t = change_df['cf'].str.split('_', n=1, expand=True)
    cols = list(change_df)
    change_df.loc[:, 'FIPS'] = t[1]
    cols.remove('cf')
    cols = ['cf', 'FIPS'] + cols
    change_df = change_df[cols]

    # write out results
    print(f"Writing Results to {output_file}")
    change_df.to_csv(output_file, index=False)
    print("Complete")