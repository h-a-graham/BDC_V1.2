# -------------------------------------------------------------------------------
# Name:        Veg FIS
# Purpose:     Runs the vegetation FIS for the BRAT input table
#
# Author:      Jordan Gilbert + Hugh Graham
#
# Created:     10/2018
# -------------------------------------------------------------------------------

# import arcpy
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import numpy as np
import os
import sys
import geopandas as gpd


def main(in_network, scratch):

    net_gpd = gpd.read_file(in_network, driver="ESRI Shapefile")

    net_gpd.loc[net_gpd['iVeg_40'] < 0, 'iVeg_40'] = 0
    net_gpd.loc[net_gpd['iVeg_10'] < 0, 'iVeg_10'] = 0
    net_gpd.loc[net_gpd['iVeg_40'] > 5, 'iVeg_40'] = 5
    net_gpd.loc[net_gpd['iVeg_10'] > 5, 'iVeg_10'] = 5

    # arcpy.env.overwriteOutput = True

    # #elif fis_type == "EX":
    # cursor = arcpy.da.UpdateCursor(in_network, ["iVeg_100EX", "iVeg_10EX"])
    # for row in cursor:
    #     if row[0] < 0:
    #         row[0] = 0
    #         if row[1] < 0:
    #             row[1] = 0
    #         elif row[1] > 4.9:
    #             row[1] = 4.9
    #     elif row[0] > 4.9:  # updated by HG - now considers values up to 5
    #         row[0] = 4.9
    #         if row[1] < 0:
    #             row[1] = 0
    #         elif row[1] > 4.9:
    #             row[1] = 4.9
    #
    #     elif row[1] < 0:
    #         row[1] = 0
    #
    #     elif row[1] > 4.9:
    #         row[1] = 4.9
    #
    #     else:
    #         pass
    #     cursor.updateRow(row)
    # del row
    # del cursor

    # get arrays for fields of interest
    # riparian_area_a = arcpy.da.FeatureClassToNumPyArray(in_network, "iVeg_100EX")
    # streamside_a = arcpy.da.FeatureClassToNumPyArray(in_network, "iVeg_10EX")
    riparian_array = net_gpd['iVeg_40'].values
    streamside_array = net_gpd['iVeg_10'].values


    # riparian_array = np.asarray(riparian_area_a, np.float64)
    # streamside_array = np.asarray(streamside_a, np.float64)

    # del riparian_area_a, streamside_a

    # set up input and output ranges

    riparian = ctrl.Antecedent(np.arange(0, 5, 0.001), 'input1')
    streamside = ctrl.Antecedent(np.arange(0, 5, 0.001), 'input2')
    density = ctrl.Consequent(np.arange(0, 45, 0.5), 'result')

    riparian['unsuitablea'] = fuzz.trapmf(streamside.universe, [0, 0, 1, 1.5])
    riparian['barelya'] = fuzz.trapmf(streamside.universe, [1, 1.5, 2, 2.25])
    riparian['moderatelya'] = fuzz.trapmf(streamside.universe, [2, 2.25, 3.5, 4])
    riparian['suitablea'] = fuzz.trapmf(streamside.universe, [3.5, 4, 4.75, 5])
    riparian['preferreda'] = fuzz.trimf(riparian.universe, [4.5, 5, 5])

    streamside['unsuitable'] = fuzz.trapmf(streamside.universe, [0, 0, 1, 1.5])
    streamside['barely'] = fuzz.trapmf(streamside.universe, [1, 1.5, 2, 2.25])
    streamside['moderately'] = fuzz.trapmf(streamside.universe, [2, 2.25, 3.5, 4])
    streamside['suitable'] = fuzz.trapmf(streamside.universe, [3.5, 4, 4.75, 5])
    streamside['preferred'] = fuzz.trimf(riparian.universe, [4.5, 5, 5])

    density['none'] = fuzz.trimf(density.universe, [0, 0, 0])
    density['rare'] = fuzz.trapmf(density.universe, [0, 0, 1.0, 1.5])
    density['occasional'] = fuzz.trapmf(density.universe, [1, 1.5, 4, 8])
    density['frequent'] = fuzz.trapmf(density.universe, [4, 8, 12, 25])
    density['pervasive'] = fuzz.trapmf(density.universe, [12, 25, 45, 45])

    # rules
    rule1 = ctrl.Rule(riparian['unsuitablea'] & streamside['unsuitable'], density['none'])
    rule2 = ctrl.Rule(riparian['barelya'] & streamside['unsuitable'], density['none'])
    rule3 = ctrl.Rule(riparian['moderatelya'] & streamside['unsuitable'], density['rare'])
    rule4 = ctrl.Rule(riparian['suitablea'] & streamside['unsuitable'], density['occasional'])
    rule5 = ctrl.Rule(riparian['preferreda'] & streamside['unsuitable'], density['frequent'])
    rule6 = ctrl.Rule(riparian['unsuitablea'] & streamside['barely'], density['rare'])
    rule7 = ctrl.Rule(riparian['barelya'] & streamside['barely'], density['rare'])
    rule8 = ctrl.Rule(riparian['moderatelya'] & streamside['barely'], density['occasional'])
    rule9 = ctrl.Rule(riparian['suitablea'] & streamside['barely'], density['frequent'])
    rule10 = ctrl.Rule(riparian['preferreda'] & streamside['barely'], density['frequent'])
    rule11 = ctrl.Rule(riparian['unsuitablea'] & streamside['moderately'], density['occasional']) #
    rule12 = ctrl.Rule(riparian['barelya'] & streamside['moderately'], density['occasional'])
    rule13 = ctrl.Rule(riparian['moderatelya'] & streamside['moderately'], density['occasional'])
    rule14 = ctrl.Rule(riparian['suitablea'] & streamside['moderately'], density['frequent'])
    rule15 = ctrl.Rule(riparian['preferreda'] & streamside['moderately'], density['frequent'])
    rule16 = ctrl.Rule(riparian['unsuitablea'] & streamside['suitable'], density['occasional'])
    rule17 = ctrl.Rule(riparian['barelya'] & streamside['suitable'], density['frequent'])
    rule18 = ctrl.Rule(riparian['moderatelya'] & streamside['suitable'], density['frequent'])
    rule19 = ctrl.Rule(riparian['suitablea'] & streamside['suitable'], density['frequent'])
    rule20 = ctrl.Rule(riparian['preferreda'] & streamside['suitable'], density['pervasive'])
    rule21 = ctrl.Rule(riparian['unsuitablea'] & streamside['preferred'], density['frequent'])
    rule22 = ctrl.Rule(riparian['barelya'] & streamside['preferred'], density['frequent'])
    rule23 = ctrl.Rule(riparian['moderatelya'] & streamside['preferred'], density['frequent'])
    rule24 = ctrl.Rule(riparian['suitablea'] & streamside['preferred'], density['pervasive'])
    rule25 = ctrl.Rule(riparian['preferreda'] & streamside['preferred'], density['pervasive'])

    # FIS
    veg_ctrl = ctrl.ControlSystem([rule1, rule2, rule3, rule4, rule5, rule6, rule7, rule8, rule9, rule10, rule11,
                                   rule12, rule13, rule14, rule15, rule16, rule17, rule18, rule19, rule20, rule21,
                                   rule22, rule23, rule24, rule25])
    veg_fis = ctrl.ControlSystemSimulation(veg_ctrl)

    out = np.zeros(len(riparian_array))
    for i in range(len(out)):
        veg_fis.input['input1'] = riparian_array[i]
        veg_fis.input['input2'] = streamside_array[i]
        veg_fis.compute()
        out[i] = veg_fis.output['result']

    net_gpd['oVC_EX'] = out

    net_gpd.to_file(in_network, driver="ESRI Shapefile")
    # # save the output text file then merge to shapefile
    # reach_no = np.arange(1, len(out) + 1, 1)
    # columns = np.column_stack((reach_no, out))
    # out_table = os.path.dirname(in_network) + '/oVC_EX_Table.txt'
    # np.savetxt(out_table, columns, delimiter=',', header='reach_no, oVC_EX', comments='')
    #
    # bvi_fields = [f.name for f in arcpy.ListFields(in_network)]
    # if "oVC_EX" in bvi_fields:
    #     print("field oVC_EX already exists - deleting")
    #     arcpy.DeleteField_management(in_network, 'oVC_EX')
    #
    # ovc_table = scratch + '/ovc_ex_table'
    # arcpy.CopyRows_management(out_table, ovc_table)
    # arcpy.JoinField_management(in_network, 'reach_no', ovc_table, 'reach_no', 'oVC_EX')
    #
    # if arcpy.Exists(out_table):
    #     arcpy.Delete_management(out_table)
    # if arcpy.Exists(ovc_table):
    #     arcpy.Delete_management(ovc_table)
    #
    # del out, reach_no, columns


    return in_network

if __name__ == '__main__':
    main(
        sys.argv[1],
        sys.argv[2])
