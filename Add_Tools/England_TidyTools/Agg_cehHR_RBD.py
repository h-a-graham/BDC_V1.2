import geopandas as gpd
import os
import pandas as pd
from glob import glob
from warnings import warn
import numpy as np
from tqdm import tqdm
from datetime import datetime
startTime = datetime.now()


def main(root, save_folder, RivBasDis, Area_Def, save_BDC, sumstat_path, **kwargs):
    """main function to call on all sub functions."""
    merged_bdc = kwargs.get('merged_bdc', None)  # option to reuse geodataframe to save time

    print('check save directory')
    if os.path.isdir(save_folder):
        print('root folder {} already exists'.format(save_folder))
    else:
        os.mkdir(save_folder)

    if merged_bdc is None:
        print('collecting features...')
        feature_list = glob(os.path.join(root, 'Op_Catch_*', 'BDC_OC*', 'Output_BDC_OC*.shp'))
        Nat_bdc_gdf = concat_gdf_list(feature_list)
    else:
        print('user provided geodatafrmae...')
        Nat_bdc_gdf = merged_bdc

    print('read in Split-Area geometries')

    rbd_gdf = gpd.read_file(RivBasDis)

    summ_poly_list = []

    print('iterating over geometries to extract BDC reaches... \n'
          'Save BDC areas is set as: {0}'.format(save_BDC))
    for idx, row in tqdm(rbd_gdf.iterrows(), total=rbd_gdf.shape[0]):
        gdf_i = gpd.GeoDataFrame(rbd_gdf.iloc[rbd_gdf.index == idx])

        clip_bdc = clip(Nat_bdc_gdf, gdf_i)

        clip_bdc = rename_BDC_cols(clip_bdc)
        clip_bdc = Add_Prob_Cols(clip_bdc)
        clip_bdc = predict_dam_nums(clip_bdc)

        if len(clip_bdc.index) == 0:
            warn("The following row from supplied polygon does not intersect any river lines and will not be added:")
            print("{0}".format(row))
            continue

        Area_summ = poly_sumstat(clip_bdc, gdf_i)
        summ_poly_list.append(Area_summ)

        #clean up final unwanted columns before output

        clip_bdc = BDC_finclean(clip_bdc)

        if Area_Def == 'RiverBasinDistrict':
            rbd_name = row['WB_name'].replace(' ', '_')

        elif Area_Def == 'ManagementCatchment':
            rbd_name = row['MANAGEMENT'] + '_' + str(row['MANCAT_ID'])

        elif Area_Def =='OperationalCatchment':
            rbd_name = row['OPERATIONA'] + '_' + str(row['OPCAT_ID'])

        else:
            warn("River Basin Classification not recognised... \n"
                 "Using generic catchment naming structure instead. ")
            rbd_name = 'Catchment_{0}'.format(idx)

        rbd_fold_path = os.path.join(save_folder, rbd_name + '_BDC')

        if save_BDC is True:
            if os.path.isdir(rbd_fold_path):
                pass
            else:
                os.mkdir(rbd_fold_path)

            bdc_out_path = os.path.join(rbd_fold_path, rbd_name + '_BDC.shp')
            clip_bdc.to_file(bdc_out_path, driver="ESRI Shapefile")


    # join plygon features
    print('BDC extraction complete - now saving summary stats polygons...')
    area_summary_gdf = pd.concat(summ_poly_list)
    area_summary_gdf = sumstat_finclean(area_summary_gdf)

    # save shp file
    if os.path.isdir(sumstat_path):
        pass

    else:
        os.mkdir(sumstat_path)

    summ_path_save = os.path.join(sumstat_path, Area_Def + '_SummStats.shp' )
    area_summary_gdf.to_file(summ_path_save, driver="ESRI Shapefile")

    finTime = datetime.now() - startTime
    print("Script Completed. \n"
          "Processing time = {0}".format(finTime))

    return Nat_bdc_gdf


def concat_gdf_list(f_list):
    """function to join a list of features to single GeoDataFrame"""
    print('merging features...')

    gdf_join = pd.concat([
        gpd.read_file(shp)
        for shp in f_list
    ], ignore_index=True)#.pipe(gpd.GeoDataFrame)

    gdf_join = gdf_join.reset_index(drop=True)

    print("NUmer of output features is:   {0}".format(len(gdf_join.index)))

    return gdf_join

def clip(to_clip, clip_shp):
    """Alternative clip function"""
    union = gpd.GeoDataFrame(
        gpd.GeoSeries([clip_shp.unary_union]),
        columns=['geometry'],
        crs=clip_shp.crs
    )

    clip_gdf = gpd.sjoin(to_clip, union, op='within')

    clip_gdf = clip_gdf.drop(columns=['index_right'])
    # clip_gdf = gpd.clip(to_clip, clip_shp, keep_geom_type=True)
    # print(clip_gdf.head())

    return clip_gdf


def sumstat_finclean(geo_df):
    """function to clean up badly named columns in RivBasDist polygon"""

    col_list = geo_df.columns.tolist()

    if 'WB_name' in col_list:
        geo_df = geo_df.rename(columns={'WB_name':'RBD'})

    if 'WB_number' in col_list:
        geo_df = geo_df.rename(columns={'WB_number': 'RBD_ID'})

    if 'WB_area_km2' in col_list:
        geo_df = geo_df.drop(['WB_area_km2'], axis=1)

    return geo_df


def BDC_finclean(geo_df):
    """function to drop irrelevant columns and appropriately order remaining columns..."""
    geo_df.drop(['Actual_BDC', 'Actual_BDC_b'], axis=1)

    col_list_order = ['BDC', 'BDC_cat', 'BFI_10m', 'BFI_40m', 'BFI_cat', 'V_BDC', 'Dam_Prob', 'Dam_ProbLC',
                      'Dam_ProbUC', 'For_Prob', 'For_ProbLC', 'For_ProbUC', 'Est_nDam', 'Est_nDamLC', 'Est_nDamUC',
                      'Length_m', 'Width_m', 'Slope_perc', 'Drain_Area', 'Str_order', 'Q2_Flow', 'Q80_Flow',
                      'Q2_StrPow', 'Q80_StrPow', 'reach_no', 'geometry']

    geo_df = geo_df[col_list_order]

    return geo_df

def rename_BDC_cols(geo_df):
    """function to rename columns to something more verbose..."""
    # print('renaming columns')

    #drop unwanted columns
    geo_df = geo_df.drop(['iGeo_Area', 'iGeo_ElMax', 'iGeo_ElMin'], axis=1)

    #rename columns to make more readable
    geo_df = geo_df.rename(columns={"iGeo_DA": "Drain_Area",
                                    "iGeo_Len": "Length_m",
                                    "iGeo_Slope": "Slope_perc",
                                    "iGeo_Width": "Width_m",
                                    "iHyd_Q2": "Q2_Flow",
                                    "iHyd_QLow": "Q80_Flow",
                                    "iHyd_SP2": "Q2_StrPow",
                                    "iHyd_SPLow": "Q80_StrPow",
                                    "iVeg_10": "BFI_10m",
                                    "iVeg_40": "BFI_40m",
                                    "oVC_EX": "V_BDC"})
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


def poly_sumstat(riv_gdf, area_gdf):
    """column to get summary statistics from beaver network based on polyons typically river catchments/basins"""
    # print("summarising BDC stats for region and attaching to region polygon")
    area_gdf['Area_km2'] = area_gdf.geometry.area/1e+6

    dist_tot = riv_gdf['Length_m'].sum()

    area_gdf['BDC_TOT'] = riv_gdf['Actual_BDC'].sum()
    area_gdf['BDC_W_AVG'] = riv_gdf['Actual_BDC'].sum()/(dist_tot/1000)
    area_gdf['BDC_MEAN'] = bdcmean = riv_gdf['BDC'].mean()
    area_gdf['BDC_MIN'] = riv_gdf['BDC'].min()
    area_gdf['BDC_MAX'] = riv_gdf['BDC'].max()
    area_gdf['BDC_W_STD'] = np.sqrt(np.average((riv_gdf['BDC'] - bdcmean) ** 2, weights=riv_gdf['Length_m']))
    area_gdf['BDC_STD'] = riv_gdf['BDC'].std()

    area_gdf['Est_nDam'] = riv_gdf['Est_nDam'].sum()
    area_gdf['Est_nDamLC'] = riv_gdf['Est_nDamLC'].sum()
    area_gdf['Est_nDamUC'] = riv_gdf['Est_nDamUC'].sum()

    area_gdf['Est_DamD'] = riv_gdf['Est_nDam'].sum()/(dist_tot/1000)
    area_gdf['Est_DamDLC'] = riv_gdf['Est_nDamLC'].sum()/(dist_tot/1000)
    area_gdf['Est_DamDUC'] = riv_gdf['Est_nDamUC'].sum()/(dist_tot/1000)

    dist_none = riv_gdf.loc[riv_gdf['BDC_cat'] == 'None', 'Length_m'].sum()
    dist_rare = riv_gdf.loc[riv_gdf['BDC_cat'] == 'Rare', 'Length_m'].sum()
    dist_occ = riv_gdf.loc[riv_gdf['BDC_cat'] == 'Occasional', 'Length_m'].sum()
    dist_freq = riv_gdf.loc[riv_gdf['BDC_cat'] == 'Frequent', 'Length_m'].sum()
    dist_perv = riv_gdf.loc[riv_gdf['BDC_cat'] == 'Pervasive', 'Length_m'].sum()

    area_gdf['BDC_P_NONE'] = dist_none/dist_tot * 100
    area_gdf['BDC_P_RARE'] = dist_rare/dist_tot * 100
    area_gdf['BDC_P_OCC'] = dist_occ/dist_tot * 100
    area_gdf['BDC_P_FREQ'] = dist_freq/dist_tot * 100
    area_gdf['BDC_P_PERV'] = dist_perv/dist_tot * 100

    area_gdf['BDCkm_NONE'] = dist_none/1000
    area_gdf['BDCkm_RARE'] = dist_rare/1000
    area_gdf['BDCkm_OCC'] = dist_occ/1000
    area_gdf['BDCkm_FREQ'] = dist_freq/1000
    area_gdf['BDCkm_PERV'] = dist_perv/1000

    dist_uns = riv_gdf.loc[riv_gdf['BFI_cat'] == 'Unsuitable', 'Length_m'].sum()
    dist_low = riv_gdf.loc[riv_gdf['BFI_cat'] == 'Low', 'Length_m'].sum()
    dist_mod = riv_gdf.loc[riv_gdf['BFI_cat'] == 'Moderate', 'Length_m'].sum()
    dist_high = riv_gdf.loc[riv_gdf['BFI_cat'] == 'High', 'Length_m'].sum()
    dist_pref = riv_gdf.loc[riv_gdf['BFI_cat'] == 'Preferred', 'Length_m'].sum()

    area_gdf['BFI40_P_UN'] = dist_uns/dist_tot * 100
    area_gdf['BFI40_P_LO'] = dist_low/dist_tot * 100
    area_gdf['BFI40_P_MO'] = dist_mod/dist_tot * 100
    area_gdf['BFI40_P_HI'] = dist_high/dist_tot * 100
    area_gdf['BFI40_P_PR'] = dist_pref/dist_tot * 100

    area_gdf['BFI40km_UN'] = dist_uns/1000
    area_gdf['BFI40km_LO'] = dist_low/1000
    area_gdf['BFI40km_MO'] = dist_mod/1000
    area_gdf['BFI40km_HI'] = dist_high/1000
    area_gdf['BFI40km_PR'] = dist_pref/1000

    area_gdf['TOT_km'] = dist_tot/1000

    area_gdf = area_gdf.round(3)

    return area_gdf


if __name__ == '__main__':
    """The call to the main function"""
    path_root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Out')

    rbd_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Tidy/BDC_RBD')
    mcat_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Tidy/BDC_ManCat')
    opcat_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Tidy/BDC_OpCat')

    sumstat_root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Tidy/Catch_SummStats')

    rbd_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/RivBasDis/England_RBDs.gpkg')
    mancat_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/ManCat.shp')
    opcat_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/OpCat.shp')

    bdc_gdf = main(root=path_root, save_folder=rbd_save_folder , RivBasDis=rbd_RivBasDis,
                   Area_Def='RiverBasinDistrict', save_BDC=True, sumstat_path=sumstat_root)
    main(root=path_root, save_folder=mcat_save_folder, RivBasDis=mancat_RivBasDis,
         Area_Def='ManagementCatchment', save_BDC=True, sumstat_path=sumstat_root, merged_bdc=bdc_gdf)
    main(root=path_root, save_folder=opcat_save_folder, RivBasDis=opcat_RivBasDis,
         Area_Def='OperationalCatchment', save_BDC=False, sumstat_path=sumstat_root, merged_bdc=bdc_gdf)
