# -------------------------------------------------------------------------------
# Name:        iHYD
# Purpose:     Adds the hydrologic attributes to the BRAT input table
#
# Author:      Jordan Gilbert + Hugh Graham
#
# Created:     10/2018
# Note: unlike the original iHyd script from Macfarlane, et al. (2017), this version uses SI units
# -------------------------------------------------------------------------------

import os
import subprocess
import geopandas as gpd

## NEED TO ADD A QUICK SUBSET FUNCTION TO DETERMINE OVERLAPPING CEH HYDROMETRIC AREAS!!!!


def main(DA, opcpath):



    print('Adding Qlow and Q2 to network')


    command = os.path.abspath("C:/Program Files/R/R-3.6.3/bin/Rscript.exe")
    scriptHome = os.path.dirname(__file__)
    print(scriptHome)
    myscript_loc = os.path.join(scriptHome, "Extracting_data_from_CEH_V2.R")

    # args = [46, 2, 3, 4, 66]
    # args = [str(region)]
    args = get_ceh_areas(opcpath)
    print(args)
    cmd = [command, myscript_loc] + args

    x = subprocess.check_output(cmd, universal_newlines=True)
    print(x)
    coefs = [float(i) for i in x.split()]

    Q2coef = coefs[0:2]
    print("Q2 coefs are {0} and {1}".format(Q2coef[0], Q2coef[1]))

    Q80coef = coefs[2:4]
    print("Q80 coefs are {0} and {1}".format(Q80coef[0], Q80coef[1]))

    DA['iHyd_QLow'] = Q80coef[0] * DA['iGeo_DA'] ** Q80coef[1]

    DA['iHyd_Q2'] = Q2coef[0] * DA['iGeo_DA'] ** Q2coef[1]

    DA.loc[DA['iHyd_Q2'] < DA['iHyd_QLow'], 'iHyd_Q2'] = DA['iHyd_QLow'] + 5

    DA['iHyd_SPLow'] = (1000 * 9.80665) * DA['iHyd_QLow'] * DA['iGeo_Slope']

    DA['iHyd_SP2'] = (1000 * 9.80665) * DA['iGeo_Slope'] * DA['iHyd_Q2']

    # DA.to_file(in_network, driver="GPKG")

    return DA


def get_ceh_areas(opc_path):
    rating_img_root = os.path.dirname(opc_path)

    print("retrieving CEH Hydrometric Area Values")
    ceh_path = os.path.join(os.path.dirname(__file__), 'Data', 'GB_CEH_HA.gpkg')

    ceh_gp = gpd.read_file(ceh_path)
    opc_gp = gpd.read_file(opc_path)

    if 'HA_NUM' in opc_gp.columns:
        opc_gp = opc_gp.drop('HA_NUM', axis=1)

    ceh_areas = gpd.overlay(ceh_gp, opc_gp, how='intersection')

    ceh_areas['area'] = ceh_areas['geometry'].area / 10**6

    if len(ceh_areas) > 1:
        topArea = ceh_areas.loc[ceh_areas.area.idxmax()]
        grid_list = [str(topArea[0]), rating_img_root]
    else:
        grid_list = list(map(str, (ceh_areas['HA_NUM']))) + [rating_img_root]

    return grid_list
