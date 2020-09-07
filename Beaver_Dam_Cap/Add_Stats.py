import geopandas as gpd
import os
import pandas as pd
from glob import glob
from warnings import warn
import numpy as np
from tqdm import tqdm
from datetime import datetime
startTime = datetime.now()


def main(bdc_gdf, save_path):

    # bdc_gdf = rename_BDC_cols(bdc_gdf)

    bdc_gdf = Add_Prob_Cols(bdc_gdf)

    bdc_gdf = predict_dam_nums(bdc_gdf)

    bdc_gdf = BDC_finclean(bdc_gdf)

    bdc_gdf.to_file(save_path, driver="GPKG")


def BDC_finclean(geo_df):
    """function to drop irrelevant columns and appropriately order remaining columns..."""
    geo_df.drop(['Actual_BDC_b'], axis=1)

    col_list_order = ['BDC', 'BDC_cat', 'BFI_10m', 'BFI_40m', 'BFI_cat', 'V_BDC', 'Dam_Prob', 'Dam_ProbLC',
                      'Dam_ProbUC', 'For_Prob', 'For_ProbLC', 'For_ProbUC', 'Est_nDam', 'Est_nDamLC', 'Est_nDamUC',
                      'Length_m', 'Width_m', 'Slope_perc', 'Drain_Area', 'Str_order', 'Q2_Flow', 'Q80_Flow',
                      'Q2_StrPow', 'Q80_StrPow', 'reach_no', 'geometry']

    geo_df = geo_df[col_list_order]

    return geo_df


def Add_Prob_Cols(geo_df):
    """function to add probability estimates to reaches based on BDC and BFI categories"""
    # print('Adding Bayesian Probability estimates by BDC category')

    geo_df['BDC_cat'] = 'None'
    geo_df.loc[(geo_df.BDC > 0) & (geo_df.BDC <= 1), 'BDC_cat'] = 'Rare'
    geo_df.loc[(geo_df.BDC > 1) & (geo_df.BDC <= 4), 'BDC_cat'] = 'Occasional'
    geo_df.loc[(geo_df.BDC > 4) & (geo_df.BDC <= 15), 'BDC_cat'] = 'Frequent'
    geo_df.loc[geo_df.BDC > 15, 'BDC_cat'] = 'Pervasive'

    # set up a BFI category column
    geo_df['BFI_cat'] = 'Unsuitable'
    geo_df.loc[(geo_df.BFI_40m > 1) & (geo_df.BFI_40m <= 2), 'BFI_cat'] = 'Low'
    geo_df.loc[(geo_df.BFI_40m > 2) & (geo_df.BFI_40m <= 3), 'BFI_cat'] = 'Moderate'
    geo_df.loc[(geo_df.BFI_40m > 3) & (geo_df.BFI_40m <= 4), 'BFI_cat'] = 'High'
    geo_df.loc[geo_df.BFI_40m > 4, 'BFI_cat'] = 'Preferred'

    # Add Dam Probabilty Estimates
    geo_df['Dam_Prob'] = 0
    geo_df.loc[geo_df['BDC_cat'] == 'Rare', 'Dam_Prob'] = 0.032
    geo_df.loc[geo_df['BDC_cat'] == 'Occasional', 'Dam_Prob'] = 0.055
    geo_df.loc[geo_df['BDC_cat'] == 'Frequent', 'Dam_Prob'] = 0.075
    geo_df.loc[geo_df['BDC_cat'] == 'Pervasive', 'Dam_Prob'] = 0.133

    geo_df['Dam_ProbLC'] = 0
    geo_df.loc[geo_df['BDC_cat'] == 'Rare', 'Dam_ProbLC'] = 0.018
    geo_df.loc[geo_df['BDC_cat'] == 'Occasional', 'Dam_ProbLC'] = 0.031
    geo_df.loc[geo_df['BDC_cat'] == 'Frequent', 'Dam_ProbLC'] = 0.045
    geo_df.loc[geo_df['BDC_cat'] == 'Pervasive', 'Dam_ProbLC'] = 0.093

    geo_df['Dam_ProbUC'] = 0.003
    geo_df.loc[geo_df['BDC_cat'] == 'Rare', 'Dam_ProbUC'] = 0.061
    geo_df.loc[geo_df['BDC_cat'] == 'Occasional', 'Dam_ProbUC'] = 0.1
    geo_df.loc[geo_df['BDC_cat'] == 'Frequent', 'Dam_ProbUC'] = 0.125
    geo_df.loc[geo_df['BDC_cat'] == 'Pervasive', 'Dam_ProbUC'] = 0.189

    # Add Foraging Probabilty Estimates
    geo_df['For_Prob'] = 0.001
    geo_df.loc[geo_df['BFI_cat'] == 'Low', 'For_Prob'] = 0.015
    geo_df.loc[geo_df['BFI_cat'] == 'Moderate', 'For_Prob'] = 0.02
    geo_df.loc[geo_df['BFI_cat'] == 'High', 'For_Prob'] = 0.021
    geo_df.loc[geo_df['BFI_cat'] == 'Preferred', 'For_Prob'] = 0.035

    geo_df['For_ProbLC'] = 0.001
    geo_df.loc[geo_df['BFI_cat'] == 'Low', 'For_ProbLC'] = 0.014
    geo_df.loc[geo_df['BFI_cat'] == 'Moderate', 'For_ProbLC'] = 0.018
    geo_df.loc[geo_df['BFI_cat'] == 'High', 'For_ProbLC'] = 0.019
    geo_df.loc[geo_df['BFI_cat'] == 'Preferred', 'For_ProbLC'] = 0.033

    geo_df['For_ProbUC'] = 0.001
    geo_df.loc[geo_df['BFI_cat'] == 'Low', 'For_ProbUC'] = 0.017
    geo_df.loc[geo_df['BFI_cat'] == 'Moderate', 'For_ProbUC'] = 0.022
    geo_df.loc[geo_df['BFI_cat'] == 'High', 'For_ProbUC'] = 0.024
    geo_df.loc[geo_df['BFI_cat'] == 'Preferred', 'For_ProbUC'] = 0.037

    return geo_df


def predict_dam_nums(geo_df):
    """function to match Actual BDC values with those from the ZINB predicted values to estimate dam numbers"""

    check_length = len(geo_df.index)

    script_path = os.path.dirname(os.path.realpath(__file__))
    zinb_preds_path = os.path.join(script_path, 'Data', 'ZINB_Predictions.csv')

    zinb_pd = pd.read_csv(zinb_preds_path)
    zinb_pd = zinb_pd.rename(columns={'n_dams_mod': 'Actual_BDC'})

    geo_df['Actual_BDC'] = round((geo_df['BDC']/1000)*(geo_df['Length_m']), 3)*1000
    geo_df = geo_df.astype({'Actual_BDC': 'int32'})
    geo_df.loc[geo_df['Actual_BDC'] > 6000, 'Actual_BDC'] = 6000

    zinb_pd['Actual_BDC'] = zinb_pd['Actual_BDC']*1000
    zinb_pd = zinb_pd.astype({'Actual_BDC': 'int32'})
    geo_df = geo_df.reset_index()

    geo_df = geo_df.join(zinb_pd, on='Actual_BDC', how="left", rsuffix='_b')  # join dfs

    geo_df = geo_df.rename(columns={"Est.1": "Est_nDam"})
    geo_df = geo_df.rename(columns={"pLL": "Est_nDamLC"})
    geo_df = geo_df.rename(columns={"pUL": "Est_nDamUC"})

    if check_length!=len(geo_df.index):
        warn('{0} NaN values have occurred in the predicted dam numbers merge. Check and fix!')

    geo_df['Actual_BDC'] = geo_df['Actual_BDC']/1000  # convert back to Actual BDC for later calcs.

    return geo_df
