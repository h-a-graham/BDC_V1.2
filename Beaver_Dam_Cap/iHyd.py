# -------------------------------------------------------------------------------
# Name:        iHYD
# Purpose:     Adds the hydrologic attributes to the BRAT input table
#
# Author:      Jordan Gilbert + Hugh Graham
#
# Created:     10/2018
# Note: unlike the original iHyd script from Macfarlane, et al. (2017), this version uses SI units
# -------------------------------------------------------------------------------

# import arcpy
# import numpy as np
import os
import sys
import subprocess
import geopandas as gpd

## NEED TO ADD A QUICK SUBSET FUNCTION TO DETERMINE OVERLAPPING CEH HYDROMETRIC AREAS!!!!

def main(in_network, scratch, cehpath, opcpath):

    # bdc_fields = [f.name for f in arcpy.ListFields(in_network)]
    #
    # if "iHyd_QLow" in bdc_fields:
    #     print("field iHyd_QLow already exists - deleting")
    #     arcpy.DeleteField_management(in_network, 'iHyd_QLow')
    # if "iHyd_Q2" in bdc_fields:
    #     print("field iHyd_Q2 already exists - deleting")
    #     arcpy.DeleteField_management(in_network, 'iHyd_Q2')
    # if "iHyd_SP2" in bdc_fields:
    #     print("field iHyd_SP2 already exists - deleting")
    #     arcpy.DeleteField_management(in_network, 'iHyd_SP2')
    # if "iHyd_SPLow" in bdc_fields:
    #     print("field iHyd_SPLow already exists - deleting")
    #     arcpy.DeleteField_management(in_network, 'iHyd_SPLow')
    #
    # arcpy.env.overwriteOutput = True

    # DA_array = arcpy.da.FeatureClassToNumPyArray(in_network, "iGeo_DA")
    # DA = np.asarray(DA_array, np.float32)

    DA = gpd.read_file(in_network, driver="ESRI Shapefile")
    # Qlow = np.zeros_like(DA)
    # Q2 = np.zeros_like(DA)

    print('Adding Qlow and Q2 to network')
    # # # Add in regional curve equations here # # #

    command = os.path.abspath("C:/Program Files/R/R-3.6.1/bin/Rscript.exe")
    scriptHome = os.path.dirname(__file__)
    print(scriptHome)
    myscript_loc = os.path.join(scriptHome, "Extacting_data_from_CEH.R")

    # args = [46, 2, 3, 4, 66]
    # args = [str(region)]
    args = get_ceh_areas(cehpath, opcpath)
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
    # Q2 = Q2coef[0] * DA ** Q2coef[1]
    DA['iHyd_Q2'] = Q2coef[0] * DA['iGeo_DA'] ** Q2coef[1]

    DA.loc[DA['iHyd_Q2'] < DA['iHyd_QLow'], 'iHyd_Q2'] = DA['iHyd_QLow'] + 5

    # reach_no = np.arange(1, len(DA) + 1, 1)
    # columns = np.column_stack((reach_no, Qlow))
    # columns2 = np.column_stack((columns, Q2))
    # out_table = os.path.dirname(in_network) + "/ihyd_Q_Table.txt"
    # np.savetxt(out_table, columns2, delimiter=',', header='reach_no, iHyd_QLow, iHyd_Q2', comments='')
    #
    # ihyd_q_table = scratch + '/ihyd_q_table'  #
    # arcpy.CopyRows_management(out_table, ihyd_q_table)
    # arcpy.JoinField_management(in_network, 'reach_no', ihyd_q_table, 'reach_no', ['iHyd_QLow', 'iHyd_Q2'])
    # arcpy.Delete_management(out_table)

    # make sure Q2 is greater than Qlow
    # cursor = arcpy.da.UpdateCursor(in_network, ["iHyd_QLow", "iHyd_Q2"])
    # for row in cursor:
    #     if row[1] < row[0]:
    #         row[1] = row[0] + 5
    #     else:
    #         pass
    #     cursor.updateRow(row)
    # del row
    # del cursor
    DA['iHyd_SPLow'] = (1000 * 9.80665)  * DA['iHyd_QLow'] * DA['iGeo_Slope']

    DA['iHyd_SP2'] = (1000 * 9.80665) * DA['iGeo_Slope'] * DA['iHyd_Q2']

    DA.to_file(in_network, driver="ESRI Shapefile")

    # arcpy.AddMessage('Adding stream power to network')
    # # calculate Qlow stream power
    # arcpy.AddField_management(in_network, "iHyd_SPLow", "DOUBLE")
    # cursor = arcpy.da.UpdateCursor(in_network, ["iGeo_Slope", "iHyd_QLow", "iHyd_SPLow"])
    # for row in cursor:
    #     index = (1000 * 9.80665) * row[0] * row[1]
    #     row[2] = index
    #     cursor.updateRow(row)
    # del row
    # del cursor
    #
    # #calculate Q2 stream power
    # arcpy.AddField_management(in_network, "iHyd_SP2", "DOUBLE")
    # cursor = arcpy.da.UpdateCursor(in_network, ["iGeo_Slope", "iHyd_Q2", "iHyd_SP2"])
    # for row in cursor:
    #     index = (1000 * 9.80665) * row[0] * row[1]
    #     row[2] = index
    #     cursor.updateRow(row)
    # del row
    # del cursor



def get_ceh_areas(ceh_path, opc_path):
    print("retrieving CEH Hydrometric Area Values")

    ceh_gp = gpd.read_file(ceh_path, driver="ESRI Shapefile")
    opc_gp = gpd.read_file(opc_path, driver="ESRI Shapefile")

    if 'HA_NUM' in opc_gp.columns:
        opc_gp = opc_gp.drop('HA_NUM', axis=1)

    ceh_areas = gpd.overlay(ceh_gp, opc_gp, how='intersection')

    ceh_areas['area'] = ceh_areas['geometry'].area / 10**6

    if len(ceh_areas)>1:
        topArea = ceh_areas.loc[ceh_areas.area.idxmax()]
        grid_list = [str(topArea[0])]
    else:
        grid_list = list(map(str, (ceh_areas['HA_NUM'])))

    return grid_list


if __name__ == '__main__':
    main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4])
