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


def main(in_network):

    net_gpd = in_network.reset_index(drop=True)

    net_gpd.loc[net_gpd['BFI_40m'] < 0, 'BFI_40m'] = 0
    net_gpd.loc[net_gpd['BFI_10m'] < 0, 'BFI_10m'] = 0
    net_gpd.loc[net_gpd['BFI_40m'] > 5, 'BFI_40m'] = 5
    net_gpd.loc[net_gpd['BFI_10m'] > 5, 'BFI_10m'] = 5

    riparian_array = net_gpd['BFI_40m'].values
    streamside_array = net_gpd['BFI_10m'].values

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

    net_gpd['V_BDC'] = out

    # net_gpd.to_file(in_network, driver="GPKG")

    return net_gpd
