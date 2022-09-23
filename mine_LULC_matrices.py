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
transition_flag: "ALL" if the user wants every transition for the specified schema (transition_dict will be created for you)
                 "" if user wants to define the transition dict themselves
transition_dict: dictionary of field_name: [from classes (T1)], [to classes (T2)]
        Example:
            'IMP_TC'    : ['ROAD', 'IMPS', 'IMPO'], ['FORE', 'TCOT'],
            'IMP_AG'    : ['ROAD', 'IMPS', 'IMPO'], ['CROP', 'PAST'],
schema: matrix schema to mine: 13, 18, or 54
bp_flag: True if bay portion of counties and False if full county
output_path: set the full path to the CSV you wish to write the results to
planimetrics_folder: path to the planimetrics folder/landuse/version2
"""
transition_flag = 'ALL'
transition_dict = {
}
schema = 18
bp_flag = False
out_path = r'PATH/LULC_county_18x18-transitions.csv'
planimetrics_folder = r"PATH"

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

def build_transition_dict():
    """
    Method: build_transition_dict()
    Purpose: If the transition_flag variable is set to ALL, this method will be executed. This method builds the 
             transition_dict for all possible transitions for the selected schema.
    Params: N/A
    Returns: N/A
    """
    # define list of classes for schema
    if schema == 18:
        classes = [
            "CROP",
            "EXTR",
            "FORE",
            "HARF",
            "IMPO",
            "IMPS",
            "NATS",
            "PAST",
            "PDEV",
            "RIVW",
            "ROAD",
            "TCIS",
            "TCOT",
            "TCTG",
            "TDLW",
            "TERW",
            "TURF",
            "WATR",
        ]
    elif schema == 13:
        classes = [
            "IR"  ,
            "INR" ,
            "TCI" ,
            "TG"  ,
            "TCT" ,
            "FORE",
            "MO"  ,
            "CRP" ,
            "PAS" ,
            "WLT" ,
            "WLO" ,
            "WLF" ,
            "WAT" ,
        ]
    elif schema == 54: # TODO: build 54 class list
        raise TypeError(f"Need to build 54-class list in build_transition_dict()")
    else:
        raise TypeError(f"Invalid schema {schema}: Expected 13, 18, or 54")

    # build transition dict
    global transition_dict
    transition_dict = {} # make sure it starts empty
    # build all possible transitions
    for t1 in classes:
        for t2 in classes:
            if t1 == t2:
                continue
            transition_dict[f"{t1}_{t2}"] = [t1], [t2]


if __name__=="__main__":
    # get list of cofips
    cfs = [x for x in os.listdir(planimetrics_folder) if os.path.isdir(f"{planimetrics_folder}/{x}") and 'backup' not in x]
    if len (cfs) != 206:
        raise TypeError(f"Incorrect number of counties: {len(cfs)}")

    # build transition dict if use wants all possible
    if transition_flag == "ALL":
        build_transition_dict()

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
    change_df.to_csv(out_path, index=False)