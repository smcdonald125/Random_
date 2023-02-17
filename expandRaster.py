"""
Script: expandRaster.py
Author: Sarah McDonald, Geographer, U.S. Geological Survey
Purpose: This script utilizes the rasterio and numpy libraries to add rows and columns
    to a raster dataset.
"""

import os
import sys
import numpy as np 
import rasterio as rio 
from rasterio.transform import from_bounds as trans_fb

def add_rows_or_cols(ary, isRows, numToAdd, isEnd, fillVal, meta):
    """
    add_rows_or_cols: for a given array, add the specified number of rows
    or columns with the fill value in the location provided

    Parameters
    ----------
    ary : [np.array]
        [array to add to]
    isRows : bool
        [True if rows, False if cols]
    numToAdd : [int]
        [number of rows or cols to add]
    isEnd : [bool]
        [True if new row/col should be at the end of the array, False if it should be at the start]
    fillVal : [int or np.nan]
        [value to assign to the new rows or columns]

    Returns
    -------
    [np.array]
        [array of raster with added rows/cols]
    [dict]
        [raster metadata with updated extent]
    """
    # raster cell size
    cellSize = meta['transform'][0]
    xmin, ymax = meta['transform'][2], meta['transform'][5]
    xmax = xmin + (cellSize * meta['width'])
    ymin = ymax - (cellSize * meta['height'])

    # add n numbers of rows/cols
    for n in range(numToAdd):
        if isRows: # add a row of nulls
            vals = [fillVal for i in range(int(ary.shape[1]))]
            if isEnd: # add row to end of array (south)
                ary = np.insert(ary, int(ary.shape[0]), vals, axis=0) 
                ymin -= cellSize
            else: # add row to start of array (north)
                ary = np.insert(ary, 0, vals, axis=0) 
                ymax += cellSize
        else: # add column of nulls
            vals = [[fillVal] for i in range(int(ary.shape[0]))]
            if isEnd: # add col to end of array (east)
                ary = np.insert(ary, [int(ary.shape[1])], vals, axis=1) 
                xmax += cellSize
            else: # add col to start of array (west)
                ary = np.insert(ary, [0], vals, axis=1)  
                xmin -= cellSize      

    # update Affine with new raster extent
    aff = trans_fb(xmin, ymin, xmax, ymax, xmax-xmin, ymax-ymin)

    # replace cellSize (previous step reverts it to 1?)
    aff = rio.Affine(cellSize, aff[1], aff[2], aff[3], -1*cellSize, aff[5])

    # update metadata dictionary
    meta.update({
        "transform":aff,
        "height":int(ary.shape[0]),
        "width":int(ary.shape[1])
    })

    return ary, meta

def read_ras(path:str):
    """
    read_ras read raster into a numpy array and read metadata.

    Parameters
    ----------
    path : [str]
        [path of raster to read in]

    Returns
    -------
    [np.array]
        [array of raster]
    [dict]
        [raster metadata]
    """
    with rio.open(path) as src:
        ary = src.read(1)
        meta = src.meta.copy() # only need for test write

    if len(ary.shape) == 3:
        ary = ary[0]

    return ary, meta

def write_ras(path:str, meta:dict, ary):
    """
    write_ras write array to raster at specified path.

    Parameters
    ----------
    path : str
        [path to write the raster]
    meta : dict
        [raster metadata with updated extent]
    ary : [np.array]
        [array of raster values]
    """
    with rio.open(path, 'w', **meta, compress="LZW") as dst:
        dst.write(ary, 1)

def update_extent(inPath:str, outPath:str):
    """
    update_extent read raster and raster metadata and add rows/columns specified in dictionary. 
    write the results to new raster at specified path.

    Parameters
    ----------
    inPath : str
        [path to input raster]
    outPath : str
        [path to write resulting raster]
    """
    # build dictionary
    dimensions = get_user_input()
    if len(dimensions) == 0:
        print("No rows or columns to add. Exiting.")
        sys.exit()

    # print dicitonary
    for key in dimensions:
        if dimensions[key]['end']:
            print(f"Adding {dimensions[key]['toAdd']} {key} to end with value {dimensions[key]['fill']}")
        else:
            print(f"Adding {dimensions[key]['toAdd']} {key} to start with value {dimensions[key]['fill']}")

    # read raster as array
    print("Reading raster...")
    ary, meta = read_ras(inPath)
    shp = ary.shape

    # add rows
    if 'rows' in dimensions:
        print(f"Adding {dimensions['rows']['toAdd']} rows...")
        ary, meta = add_rows_or_cols(ary, True, dimensions['rows']['toAdd'], dimensions['rows']['end'], dimensions['rows']['fill'], meta)

    # add columns
    if 'columns' in dimensions:
        print(f"Adding {dimensions['columns']['toAdd']} columns...")
        ary, meta = add_rows_or_cols(ary, False, dimensions['columns']['toAdd'], dimensions['columns']['end'], dimensions['columns']['fill'], meta)

    # print starting dimensions
    if ary.shape[0] - shp[0] != dimensions['rows']['toAdd'] or ary.shape[1] - shp[1] != dimensions['columns']['toAdd']:
        print(f"Invalid dimensions\n Start: {shp}\nEnd: {ary.shape}")
        sys.exit()
    else:
        print(f"Valid dimensions\n\tStart: {shp}\n\tEnd: {ary.shape}")

    # validate datatype
    if meta['dtype'] != ary.dtype:
        if meta['dtype'] == 'int8':
            print(f"Converting dtype from {ary.dtype} to int8")
            ary = ary.astype(np.int8)
        elif meta['dtype'] == 'int16':
            print(f"Converting dtype from {ary.dtype} to int16")
            ary = ary.astype(np.int16)
        elif meta['dtype'] == 'int32':
            print(f"Converting dtype from {ary.dtype} to int32")
            ary = ary.astype(np.int32)
        else:
            print(f"Add line to convert to datatype {meta['dtype']}")
            sys.exit()

    # write results
    print("Writing results...")
    write_ras(outPath, meta, ary)

def get_user_input():
    """
    get_user_input builds the dictionary of rows and columns to be added, where to add them in the array,
    and the value to assign to the cells.

    Returns
    -------
    [dict]
        Example:
            dimensions = {
                'rows'  : { # exists if user enters data for rows
                    'toAdd' : 3, # number of rows to add
                    'end'   : False, # True if adding to the end of the array (bottom of array)
                    'fill'  : -128 # value to fill
                },
                'columns'  : { # exists if user enters data for columns
                    'toAdd' : 3, # number of rows to add
                    'end'   : False, # True if adding to the end of the array (to the right)
                    'fill'  : -128 # value to fill
                }
    }
    """
    dimensions = {}
    keys = ['rows', 'columns']

    # loop through keys and collect data from user
    for key in keys:
        v = input(f"Do you want to add {key} to the raster? (y or n): ")
        while v not in ['y', 'n']:
            v = input(f"Invalid entry: {v}\nDo you want to add rows to the raster? (y or n): ")
        if v == 'y':
            # create entry in dictionary to add either rows or columns
            dimensions[key] = {}

            # collect the number of rows/cols to add
            a = input(f"Enter the number of {key} to add: ")
            t = True
            while t:
                try:
                    a = int(a)
                    t = False
                except:
                    a = input(f"Invalid entry: {a}\nEnter the number of {key} to add: ")

            # add rows columns to the end or beginning?
            txt = f"Do you want to add {key} to the end"
            if key == 'rows':
                txt += " (south)"
            else:
                txt += " (east)"
            txt += ". Enter y or n: "
            e = input(txt)     
            while e not in ['y', 'n']:
                e = input(f"Invalid entry: {e}\n{txt}")
            if e == 'y':
                e = True
            else:
                e = False

            # enter fill value
            f = input(f"Enter the fill value for new {key}: ")
            t = True
            while t:
                try:
                    f = int(f)
                    t = False
                except:
                    f = input(f"Invalid entry: {f}\nEnter the fill value for new {key}: ")

            # update dictionary
            dimensions[key]['toAdd'] = a
            dimensions[key]['end'] = e
            dimensions[key]['fill'] = f

    print("\n")
    return dimensions

if __name__=="__main__":
    raspath = r"C:\Users\smcdonald\Documents\Data\ChangePaper\Analysis\data\input\hr\imp_10m_masked.tif"
    outPath = r'C:\Users\smcdonald\Documents\Data\ChangePaper\Analysis\data\input\hr\HR_IMP_10m_expanded.tif'

    update_extent(raspath, outPath)