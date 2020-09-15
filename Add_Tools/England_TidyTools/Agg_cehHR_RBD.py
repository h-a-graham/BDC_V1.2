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
        feature_list = glob(os.path.join(root, 'Op_Catch_*', 'BDC_OC*', 'Output_BDC_OC*.gpkg'))
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


        if len(clip_bdc.index) == 0:
            warn("The following row from supplied polygon does not intersect any river lines and will not be added:")
            print("{0}".format(row))
            continue

        Area_summ = poly_sumstat(clip_bdc, gdf_i)
        summ_poly_list.append(Area_summ)

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

        rbd_fold_path = os.path.join(save_folder, 'BeaverNetwork_' + rbd_name)

        if save_BDC is True:
            if os.path.isdir(rbd_fold_path):
                pass
            else:
                os.mkdir(rbd_fold_path)

            bdc_out_path = os.path.join(rbd_fold_path, 'BeaverNetwork_' + rbd_name + '.shp')
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


def poly_sumstat(riv_gdf, area_gdf):
    """column to get summary statistics from beaver network based on polyons typically river catchments/basins"""
    # print("summarising BDC stats for region and attaching to region polygon")
    area_gdf['Area_km2'] = area_gdf.geometry.area/1e+6

    dist_tot = riv_gdf['Length_m'].sum()

    riv_gdf['Actual_BDC'] = (riv_gdf['BDC']/1000) * riv_gdf['Length_m']

    area_gdf['BDC_TOT'] = riv_gdf['Actual_BDC'].sum()  #riv_gdf['Actual_BDC'].sum()
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
    path_root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_GB_v2_0')

    rbd_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_ENG/RBD_BeaverNetwork_Eng')
    mcat_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_ENG/ManCat_BeaverNetwork_Eng')
    opcat_save_folder = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_ENG/OpCat_BeaverNetwork_Eng')

    sumstat_root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_ENG/SummStats_BeaverNetwork_Eng')

    rbd_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/RivBasDis/England_RBDs.gpkg')
    mancat_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/ManCat.shp')
    opcat_RivBasDis = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/NE_OCs_MCs_Provided/OpCat.shp')

    bdc_gdf = main(root=path_root, save_folder=rbd_save_folder , RivBasDis=rbd_RivBasDis,
                   Area_Def='RiverBasinDistrict', save_BDC=True, sumstat_path=sumstat_root)
    main(root=path_root, save_folder=mcat_save_folder, RivBasDis=mancat_RivBasDis,
         Area_Def='ManagementCatchment', save_BDC=True, sumstat_path=sumstat_root, merged_bdc=bdc_gdf)
    main(root=path_root, save_folder=opcat_save_folder, RivBasDis=opcat_RivBasDis,
         Area_Def='OperationalCatchment', save_BDC=False, sumstat_path=sumstat_root, merged_bdc=bdc_gdf)
