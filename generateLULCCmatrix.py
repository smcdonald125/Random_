"""
Script: generateLULCmatrix.py
Purpose: This script summarizes the 1-meter, 54-class, LULC change raster data by user defined zones and converts the results
          to change matrices (1 per zone).
Author: Sarah McDonald, Geographer, U.S. Geological Survey
Contact: smcdonald@chesapeakebay.net
"""

import os
import sys
import pandas as pd 
import numpy as np
from pathlib import Path

import arcpy
from arcpy.sa import (
    TabulateArea,
    Raster
)

"""
USER-DEFINED VARIABLES
----------------------
1. in_zone_data - path to the vector or raster layer containing the zones
2. zone_field - the name of the field with the unique zone ID
3. in_LULC - path to the LULC change raster
4. out_matrix_path - path to the new csv or excel document to write the matrix to
    - if only 1 geometry, recommend a csv.
    - if you have multiple zones, use xlsx. The unique zone ID will be the sheet name.
5. master_crosswalk - path to the master table that relates the 2-digit land use classes to their general land use name.
"""
in_zone_data = r""
zone_field = ""
in_LULC = r""
out_matrix_path = r""
master_crosswalk = r""

# 1. Run tabulate area on 1-meter LULC and the zone data
print(f"Running Tabulate Area...")
arcpy.env.extent = in_zone_data
p = Path(out_matrix_path)
ta_dbf = f"{p.stem}_TA.dbf"
TabulateArea(
                in_zone_data,
                zone_field,
                in_LULC,
                "Value",
                f"{p.parent}/{ta_dbf}",
                processing_cell_size=1,
            )

# # 2. Convert the dbf to CSV
ta_name = f"{p.parent}/{p.stem}_TA.csv"
print(f"Writing Tabulate Area results to {ta_name}...")
arcpy.conversion.ExportTable(
                                f"{p.parent}/{ta_dbf}",
                                ta_name
                            )

# 3. create dict of raster value and to/from 18-class
rollup = {}
cw = pd.read_csv(master_crosswalk)
for idx1, row1 in cw.iterrows():
    for idx2, row2 in cw.iterrows():
        if idx1 == idx2:
            continue

        # produce change value
        change_value = (row1['Value'] * 100) + row2['Value']

        # record the to/from general land use (18-class)
        rollup[str(change_value)] = [row1['GenAbbrev'], row2['GenAbbrev']]

lu_order = ["ROAD", "IMPS", "IMPO", "TCIS", "TURF", "TCTG", "PDEV", "FORE", "TCOT", "HARF", "NATS", "CROP", "PAST", "EXTR", "TDLW", "RIVW", "TERW", "WATR"] 

# 4. Read the TA results as a pandas dataframe
print(f"Creating matrices...")
ta_df = pd.read_csv(f"{ta_name}")
matrices = {}
uniqueID = zone_field.upper()
for idx, row in ta_df.iterrows():
    # create 18x18 matrix filled with zeros
    matrix = pd.DataFrame(columns=lu_order)
    matrix.loc[:, '2013/14-2017/18'] = lu_order
    matrix = matrix.set_index('2013/14-2017/18')
    matrix = matrix.fillna(0.0) # assign 0 to all transitions

    # loop through change values and add to matrix
    for val in row.index:
        val_ru = val.split('_')[-1]
        if val_ru in rollup:
            f, t = rollup[val_ru]
            matrix.loc[f, t] += (row[val] / 4046.86) # add value to matrix, converted to acres
        else:
            print(f"WARNING: {val} not in rollup")

    # create totals
    matrix.loc[:, "Decrease"] = matrix[lu_order].sum(axis=1)
    matrix.loc["Increase"] = matrix[lu_order].sum(axis=0)
    matrix.loc["Totals"] = [np.nan for i in range(len(matrix))]
    matrix.loc["Total Increase"] = matrix.loc["Increase"]
    matrix.loc["Total Decrease"] = list(matrix["Decrease"])[0:len(lu_order)] + [np.nan]
    matrix.loc["Net Change"] = matrix.loc["Total Increase"] - matrix.loc["Total Decrease"]
    matrix.loc["Increase", "Decrease"] = sum(list(matrix["Decrease"][0:len(lu_order)]))

    # add matrix for zone into the dictionary
    matrices[row[uniqueID]] = matrix.copy()

# write results
print(f"Writing matrices to {out_matrix_path}...")
if len(matrices) > 1 or Path(out_matrix_path).suffix == '.xlsx':
    if Path(out_matrix_path).suffix != '.xlsx':
        print("Multiple zones, changing output file to excel document")
        out_matrix_path = out_matrix_path.replace('.csv', '.xlsx')

    # iterate through matrices and write sheets, named with zone field
    with pd.ExcelWriter(out_matrix_path) as writer:
        for m in matrices:
            matrices[m].to_excel(writer, sheet_name=m)
elif len(matrices) == 1 and Path(out_matrix_path).suffix == '.csv':
    for m in matrices:
        matrices[m].to_csv(out_matrix_path, index=True)  
else:
    print(f"ERROR: the number of matrices and extension do not work. Either need CSV for one zone or Excel.")
    print(f"{len(matrices)} unique matrices and {Path(out_matrix_path).suffix} extension")
        