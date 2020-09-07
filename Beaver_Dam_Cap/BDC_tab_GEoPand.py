# Notes:
# Add prefix to naming structure?
# parallel structure removed to allow for higher level of parallelism - should improve speed.
#
# from __future__ import division
# -------------------------------------------------------------------------------
# Name:
# Purpose:     Builds the initial table to run through the BRAT tools
#
# Author:      Hugh Graham
#
# -------------------------------------------------------------------------------


##############################################
########## IMPORTS ##########################
#############################################
import numpy as np
import os
import geopandas as gpd
import pandas as pd
import shutil
from shapely import errors
from shapely.geometry import Polygon, MultiPolygon, Point, mapping
import rasterio
from rasterio.mask import mask
from tqdm import tqdm
import warnings
# import matplotlib.pyplot as plt # leave for debugging

############# START TIME ##############


def main(path, seg_network_b, sb_DEM, in_water_vec, coded_vegIn, DrAreaPathIn, progress_bar):
    """main function to call all sub functions"""

    home_name = "BDC_OC{0}".format(path[-4:])  # REQUIRED - name of home working directory to be created
    home = os.path.join(path, home_name)  # Don't Edit
    if os.path.isdir(home):
        shutil.rmtree(home)
    os.mkdir(home)

    reaches_gdf, proj_crs, process_name, outName, out_network = PrepStrNet(seg_network_b, home, home_name)

    iw_area_merge = CreatInWatArea(reaches_gdf, in_water_vec, proj_crs)

    bdc_gdf = MainProcessing(iw_area_merge, sb_DEM, DrAreaPathIn, coded_vegIn, proj_crs, reaches_gdf, progress_bar)

    final_gdf = remove_dup_geoms(bdc_gdf)

    return final_gdf, out_network


def remove_dup_geoms(gdf):
    """function to remove any duplicates - prioritises duplicates with high stream orders"""
    gdf = gdf.sort_values(by=['Str_order'])
    gdf = gdf.reset_index(drop=True)

    gdf["geometry_wkb"] = gdf["geometry"].apply(lambda geom: geom.wkb)
    gdf = gdf.drop_duplicates(["geometry_wkb"], keep='last')
    gdf = gdf.drop(['geometry_wkb'], axis=1)

    gdf = gdf.sort_values(by=['reach_no'])
    gdf = gdf.reset_index(drop=True)

    return gdf


def PrepStrNet(seg_net_pathA, home, h_name):
    """ Simple function to prep the stream network for processing"""
    process_namep = "process_{0}_".format(h_name)
    outNamep = ("process_fold_{0}".format(h_name))

    # print("set up out network path")

    out_networkp = os.path.join(home, "Output_{0}.gpkg".format(h_name))

    seg_network = gpd.read_file(seg_net_pathA)
    project_crs = seg_network.crs

    # create sequential numbers for reaches
    seg_network['reach_no'] = np.arange(len(seg_network))

    return seg_network, project_crs, process_namep, outNamep, out_networkp

def CreatInWatArea(seg_network, in_water_vec_a, proj_crs):
    """ Function to combine inland water area polyons and river lines (buffered to 0.5 m) """

    # print("create limited inland water area with rivers")
    ndb = gpd.GeoDataFrame(seg_network.buffer(distance=0.5),columns=['geometry'])

    iwv_gdf = gpd.read_file(in_water_vec_a)
    iwv_gdf.geometry = convert_3D_2D(iwv_gdf.geometry)  # new geodf with 2D geometry series

    diff_wat_ditch = gpd.overlay(ndb, iwv_gdf, how='difference')

    # print("merging inland water ply and stream network poly")
    dataframesList = [diff_wat_ditch, iwv_gdf]
    iw_area_merge = gpd.GeoDataFrame(pd.concat(dataframesList, ignore_index=True))
    iw_area_merge = iw_area_merge[['geometry']]

    iw_area_merge.crs = proj_crs

    return iw_area_merge

def convert_3D_2D(geometry):
    """Takes a GeoSeries of 3D Multi/Polygons (has_z) and returns a list of 2D Multi/Polygons
    from: https://gist.github.com/rmania/8c88377a5c902dfbc134795a7af538d8"""

    new_geo = []
    for p in geometry:
        if p.has_z:
            if p.geom_type == 'Polygon':
                lines = [xy[:2] for xy in list(p.exterior.coords)]
                new_p = Polygon(lines)
                new_geo.append(new_p)
            elif p.geom_type == 'MultiPolygon':
                new_multi_p = []
                for ap in p:
                    lines = [xy[:2] for xy in list(ap.exterior.coords)]
                    new_p = Polygon(lines)
                    new_multi_p.append(new_p)
                new_geo.append(MultiPolygon(new_multi_p))
        else:
            new_geo.append(p)
    return new_geo



def MainProcessing(iw_area_merge, DEM_burn, DrArea, coded_veg, proj_crs, seg_network, prog_bar):
    """ function to run the main loop to collect all search area features and carry out raster stats."""

    iw_area_merge_si = iw_area_merge.sindex

    reach_dict_list = []

    with rasterio.open(DEM_burn) as demburn, rasterio.open(coded_veg) as vegras, rasterio.open(DrArea) as drainras:
        for row in tqdm(seg_network.itertuples(), total=seg_network.shape[0], disable=prog_bar):

            reach_gdf = gpd.GeoDataFrame(
                gpd.GeoSeries([row.geometry]),
                columns=['geometry'],
                crs=proj_crs
            )
            reach_gdf['reach_no'] = row.reach_no

            # ------ Generating points -----
            reach_start_gdf = Buff_PointsAlongLine(gdf_line=reach_gdf, p_dist=0, buff_dist=2.5)
            reach_mid_gdf = Buff_PointsAlongLine(gdf_line=reach_gdf, p_dist=0.5, buff_dist=10)
            reach_end_gdf = Buff_PointsAlongLine(gdf_line=reach_gdf, p_dist=1, buff_dist=2.5)

            # ------ Generating Buffer areas -----
            buff_10m_gdf = generate_reach_buffer(reach_shape=reach_gdf, inland_wat_SI=iw_area_merge_si,
                                                 inlandwatergdf=iw_area_merge, prebuff=90, postbuff=10)

            buff_40m_gdf = generate_reach_buffer(reach_shape=reach_gdf, inland_wat_SI=iw_area_merge_si,
                                                 inlandwatergdf=iw_area_merge, prebuff=60, postbuff=40)

            reach_areas_gdf = generate_reach_buffer(reach_shape=reach_gdf, inland_wat_SI=iw_area_merge_si,
                                                    inlandwatergdf=iw_area_merge, prebuff=20, postbuff=None)

            # ------ Run Raster Stats -------------
            start_p_min = zonal_ras_stat(gdf=reach_start_gdf, ras_obj=demburn, stat='min', touched=True)
            end_p_min = zonal_ras_stat(gdf=reach_end_gdf, ras_obj=demburn, stat='min', touched=True)
            mid_p_max = zonal_ras_stat(gdf=reach_mid_gdf, ras_obj=drainras, stat='max', touched=True)
            if mid_p_max <= 0:
                mid_p_max = 0.1

            buff10_th_mean = zonal_ras_stat(gdf=buff_10m_gdf, ras_obj=vegras, stat='th_mean', touched=True)
            buff40_th_mean = zonal_ras_stat(gdf=buff_40m_gdf, ras_obj=vegras, stat='th_mean', touched=True)

            # ------- Calc Reach Slope -----------
            if row.reach_leng == 0:
                reach_slope = 0  # incase of zero division
                print('reach length is ZERO???')
            else:
                reach_slope = (start_p_min - end_p_min)/row.reach_leng

            if reach_slope <= 0:
                reach_slope = 0.0001
            if reach_slope >= 1.0:
                # print('CRAZY REACH SLOPE REPORTED \n'
                #       'Reach Length = {0}'.format(row.reach_leng))
                reach_slope = 0.5

            # ------- Calc Reach Width -----------
            reach_area = reach_areas_gdf['geometry'].area.values[0]
            reach_width = reach_area / (row.reach_leng + 40)

            # ------ Build dictionary ---------------

            reach_dict = {'reach_no': row.reach_no, 'Length_m': row.reach_leng, 'Str_order': row.Str_order,
                          'Slope_perc': reach_slope, 'Width_m': reach_width, 'Drain_Area': mid_p_max,
                          'BFI_10m': buff10_th_mean, 'BFI_40m': buff40_th_mean, 'geometry': row.geometry}

            reach_dict_list.append(reach_dict)

    # --------- concat gdf lists ---------------
    pd_list = pd.DataFrame(reach_dict_list)

    out_network = gpd.GeoDataFrame(pd_list, geometry='geometry', crs=proj_crs)

    return out_network


def Buff_PointsAlongLine(gdf_line, p_dist, buff_dist):
    """ function to create lines x percent along line then buffer point to desired distance"""

    shapelyLine = gdf_line['geometry'][0]

    splitPoint = (shapelyLine.interpolate(p_dist, normalized=True))
    x, y = splitPoint.coords.xy
    coords = (float(x[0]), float(y[0]))

    gs_points = gpd.GeoSeries(Point(coords[0], coords[1]))
    gdf_points = gpd.GeoDataFrame()
    gdf_points['geometry'] = gs_points
    gdf_points['reach_no'] = gdf_line['reach_no'][0]
    gdf_points.crs = gdf_line.crs
    gdf_buff = gdf_points.buffer(buff_dist)

    return gdf_buff


def generate_reach_buffer(reach_shape, inland_wat_SI, inlandwatergdf, prebuff, postbuff):
    """ function to create reach areas that extend x distance up and downstream of target reach, then option to
    buffer this reach area to generate search areas for statistics"""

    reach_pre_buff = gpd.GeoDataFrame(reach_shape.buffer(prebuff), columns=['geometry'], crs=reach_shape.crs)

    possible_matches_index = list(inland_wat_SI.intersection(list(reach_pre_buff.bounds.values[0])))
    possible_matches = inlandwatergdf.iloc[possible_matches_index].reset_index(drop=True)
    clipped_gdf = gpd.overlay(possible_matches, reach_pre_buff, how="intersection")

    clipped_gdf['diss_key'] = 1
    clipped_gdf = clipped_gdf.dissolve(by='diss_key', as_index=False)
    clipped_gdf = clipped_gdf[['geometry']]
    clipped_gdf['reach_no'] = reach_shape['reach_no']
    clipped_gdf.crs = reach_shape.crs

    if clipped_gdf.geometry[0].geom_type == 'MultiPolygon':

        check_buff = gpd.GeoDataFrame(reach_shape.buffer(0.5), columns=['geometry'], crs=reach_shape.crs)
        gdf_explode = explode(clipped_gdf, crs=reach_shape.crs)
        gdf_sjoin = gpd.sjoin(gdf_explode, check_buff, op='intersects')

        if gdf_sjoin.shape[0] > 1:
            gdf_sjoin['diss_key'] = 1
            gdf_sjoin = gdf_sjoin.dissolve(by='diss_key')

        clipped_gdf['geometry'] = gdf_sjoin['geometry'].values
        # clipped_gdf.crs = reach_shape.crs

    if postbuff is None:
        final_buff = clipped_gdf.copy()
    else:
        buff_riv_area = gpd.GeoDataFrame(clipped_gdf.buffer(postbuff), columns=['geometry'], crs=reach_shape.crs)
        try:
            final_buff = gpd.overlay(buff_riv_area, possible_matches, how='difference')
        except errors.TopologicalError:
            try:
                possible_matches['diss_key'] = 1
                possible_matches = possible_matches.dissolve(by='diss_key')
                final_buff = gpd.overlay(buff_riv_area, possible_matches, how='difference')
            except errors.TopologicalError:
                try:
                    final_buff = gpd.overlay(buff_riv_area, clipped_gdf, how='difference') # last resort...
                except errors.TopologicalError as e:
                    raise e

    if len(final_buff) < 1:  # if the river area is wider than the buffer this is required to avoid NULL geometry
            # print("River wider than 40m")
            final_buff = reach_pre_buff.copy()


    return final_buff


def explode(indf, crs):
    """"Explode MultiPolygon geometry into individual Polygon geometries in a shapefile using GeoPandas and Shapely
     from: https://gist.github.com/mhweber/cf36bb4e09df9deee5eb54dc6be74d26"""

    outdf = gpd.GeoDataFrame(columns=indf.columns)
    for idx, row in indf.iterrows():
        if type(row.geometry) == Polygon:
            outdf = outdf.append(row,ignore_index=True)
        if type(row.geometry) == MultiPolygon:
            multdf = gpd.GeoDataFrame(columns=indf.columns)
            recs = len(row.geometry)
            multdf = multdf.append([row]*recs,ignore_index=True)
            for geom in range(recs):
                multdf.loc[geom,'geometry'] = row.geometry[geom]
            outdf = outdf.append(multdf,ignore_index=True)
    outdf.crs = crs
    return outdf

def zonal_ras_stat(gdf, ras_obj, stat, touched):
    """ Function to carry out Zonal statistics using Rasterio """
    # extract the geometry in GeoJSON format
    geoms = gdf.geometry.values  # list of shapely geometries
    try:
        geoms = [mapping(geoms[0])] # transform to GeJSON format
    except IndexError as e: # this error is raised when for some reason an empty geometry is provided here...
        print(gdf)
        print(stat)
        print(gdf.geometry.values)

        raise e

    # extract the raster values values within the polygon

    try:
        out_image, out_transform = mask(ras_obj, geoms, crop=True, all_touched=touched, nodata=-999)
    except ValueError:
        raise ValueError('A river feature lies outside the bounds of the rasters - '
                         'an error has occurred in Dataset_Prep.py')

    out_image = np.ma.masked_equal(out_image, -999)

    if stat == 'th_mean':
        stat_val = GetTopHalfMean(out_image) # this needs updating...
    elif stat == 'min':
        stat_val = np.nanmin(out_image)
    elif stat == 'max':
        stat_val = np.nanmax(out_image)
    else:
        raise ValueError('The statistic requested is not supported')

    return stat_val


def GetTopHalfMean(stat_df):
    """function to generate the mean of the top 50% of values in a numpy matrix"""
    unmasked = stat_df[stat_df.mask == False]
    Newdf = np.ma.sort(unmasked)
    lower, upper = np.array_split(Newdf, 2)

    # with warnings.catch_warnings():  # wrapped in with warnings.catchwarnings to fix empty slices.
    #     warnings.filterwarnings('error')
    #     try:
    #         statval = np.nanmean(upper)
    #     except Warning as e:
    #         statval = 0

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        statval = np.nanmean(upper)

    if np.isnan(statval):
        statval = 0

    return statval

