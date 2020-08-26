#Notes:
# This works well - running all steps in parallel - where rivre nets are very large they are broken into chunks of 1000
# reaches. upload to GitHub.



from __future__ import division
# -------------------------------------------------------------------------------
# Name:        Parallel Beaver Dam Capacity Table
# Purpose:     Builds the initial table to run through the BRAT tools
#
# Author:      Hugh Graham
#
# -------------------------------------------------------------------------------


##############################################
########## IMPORTS ##########################
#############################################
# from arcpy.sa import *
import multiprocessing
from functools import partial
from datetime import datetime
import numpy as np
import os
from rasterstats import zonal_stats, point_query
import geopandas as gpd
# import matplotlib.pyplot as plt
import pandas as pd
import shutil
from shapely.geometry import Point
from shapely.wkb import loads
from shapely.geometry.multipolygon import MultiPolygon


############# START TIME ##############
startTime = datetime.now()


def main(path, seg_network_b, sb_DEM, in_water_vec, coded_vegIn, DrAreaPathIn):

    print(startTime)

    home_name = "BDC_OC{0}".format(path[-4:])  # REQUIRED - name of home working directory to be created
    home = os.path.join(path, home_name)  # Don't Edit
    if os.path.isdir(home):
        shutil.rmtree(home)
    os.mkdir(home)

    reaches_gdf, proj_crs, process_name, outName, out_network = PrepStrNet(seg_network_b, home, home_name)

    iw_area_merge = CreatInWatArea(reaches_gdf, in_water_vec, proj_crs)

    bdc_gdf = paralellProcess(reaches_gdf, iw_area_merge, sb_DEM, DrAreaPathIn, coded_vegIn, proj_crs )

    final_gdf = remove_dup_geoms(bdc_gdf)

    # final_gdf.to_file(out_network, driver="GPKG")

    # if os.path.isdir(scratchy):
    #     print("scratch folder exists")
    #     try:
    #         shutil.rmtree(scratchy)
    #     except Exception as e:
    #         print(e)

    finTime = datetime.now() - startTime
    print("BDC table script completed. \n"
          "Processing time = {0}".format(finTime))

    return final_gdf, out_network


def remove_dup_geoms(gdf):
    """function to remove any duplicates - prioritises duplicates with high stream orders"""
    gdf = gdf.sort_values(by=['Str_order'])
    gdf = gdf.reset_index(drop=True)

    gdf["geometry_wkb"] = gdf["geometry"].apply(lambda geom: geom.wkb)
    gdf = gdf.drop_duplicates(["geometry_wkb"], keep='last')
    gdf = gdf.drop(['geometry_wkb'], axis=1)
    # gdf["geometry_wkb"] = gdf["geometry"].apply(lambda geom: loads(geom))

    gdf = gdf.sort_values(by=['reach_no'])
    gdf = gdf.reset_index(drop=True)

    return gdf


def PrepStrNet(seg_net_pathA, home, h_name):

    process_namep = "process_{0}_".format(h_name)
    outNamep = ("process_fold_{0}".format(h_name))

    #### create working gdb
    # fgb_name = ("process_fold_{0}_scratch".format(h_name))
    # scratch = os.path.join(home, fgb_name)
    # if os.path.isdir(scratch):
    #     shutil.rmtree(scratch)
    # os.mkdir(scratch)

    # ##################################################
    print("set up out network path")

    out_networkp = os.path.join(home, "Output_{0}.gpkg".format(h_name))

    print("let's get started")

    seg_network = gpd.read_file(seg_net_pathA)
    project_crs = seg_network.crs

    # create sequential numbers for reaches
    seg_network['reach_no'] = np.arange(len(seg_network))

    return seg_network, project_crs, process_namep, outNamep, out_networkp

def CreatInWatArea(seg_network, in_water_vec_a, proj_crs):
    print("create limited inland water area with rivers")

    ndb = gpd.GeoDataFrame()
    ndb['geometry'] = seg_network.buffer(distance=0.5)
    ndb.crs = proj_crs

    iwv_gdf = gpd.read_file(in_water_vec_a)
    iwv_gdf = iwv_gdf[['geometry']]
    iwv_gdf.crs = proj_crs

    print("merging inland water ply and stream network poly")

    dataframesList = [ndb, iwv_gdf]
    iw_area_merge = gpd.GeoDataFrame(pd.concat(dataframesList, ignore_index=True))

    iw_area_merge.crs = proj_crs
    nbd = None
    iwv_gdf = None

    return iw_area_merge


def MainProcessing(iw_area_merge, DEM_orig, DrArea, coded_vega, proj_crs, full_net, seg_network):
    # set buffers for analyses
    proc_name = multiprocessing.current_process().name

    # seg_network.set_index('reach_no')

    print("vertices to points")
    print("create mid points")
    midpoints_gdf = PointsAlongLine(gdf_line=seg_network, p_dist=0.5, process_name=proc_name)
    midpoints_gdf.crs = proj_crs
    # midpoints_gdf.to_file(scratch + "/midpoints.shp", driver="ESRI Shapefile") # not required just for checking.

    print("create start points")

    startpoints_gdf = PointsAlongLine(gdf_line=seg_network, p_dist=0, process_name=proc_name)
    startpoints_gdf.crs = proj_crs
    # startpoints_gdf.to_file(scratch + "/startpoints.shp", driver="ESRI Shapefile")  # not required just for checking.

    print("create end points")

    endpoints_gdf = PointsAlongLine(gdf_line=seg_network, p_dist=1, process_name=proc_name)
    endpoints_gdf.crs = proj_crs
    # endpoints_gdf.to_file(scratch + "/endpoints.shp", driver="ESRI Shapefile")  # not required just for checking.
    print ("create midpoint buffer")
    midpoint_buffer = gpd.GeoDataFrame()
    midpoint_buffer['geometry'] = midpoints_gdf.buffer(distance=10)
    midpoint_buffer['reach_no'] = midpoints_gdf['reach_no']
    midpoint_buffer.crs = proj_crs
    print("create start point buffer")
    startpoint_buf = gpd.GeoDataFrame()
    startpoint_buf['geometry'] = startpoints_gdf.buffer(distance=6)
    startpoint_buf['reach_no'] = startpoints_gdf['reach_no']
    startpoint_buf.crs = proj_crs
    print("create end point buffer")
    endpoint_buff = gpd.GeoDataFrame()
    endpoint_buff['geometry'] = endpoints_gdf.buffer(distance=6)
    endpoint_buff['reach_no'] = endpoints_gdf['reach_no']
    endpoint_buff.crs = proj_crs
    midpoints_gdf = None
    startpoints_gdf = None
    endpoints_gdf = None


    print ("creating pre process buffer for reach areas")
    pre_area_buff = gpd.GeoDataFrame()
    pre_area_buff['geometry'] = seg_network.buffer(distance=60)
    pre_area_buff['reach_no'] = seg_network['reach_no']
    pre_area_buff.crs = proj_crs

    pre_area_buffb = gpd.GeoDataFrame()
    pre_area_buffb['geometry'] = seg_network.buffer(distance=90)
    pre_area_buffb['reach_no'] = seg_network['reach_no']
    pre_area_buffb.crs = proj_crs

    pre_area_buffc = gpd.GeoDataFrame()
    pre_area_buffc['geometry'] = seg_network.buffer(distance=20)
    pre_area_buffc['reach_no'] = seg_network['reach_no']
    pre_area_buffc.crs = proj_crs

    print("creating clip geometries...")
    clipgeoms = CreateOverlayGeoms(strNet_gdf=seg_network, inWatArea_gdf=iw_area_merge,
                                   crs=proj_crs, process_name=proc_name)


    print("clipping the reach areas")
    # TestTime = datetime.now()
    reach_areas = ClipAreasbyWater(mainShape=pre_area_buff, ClipShape=clipgeoms, crs=proj_crs, process_name=proc_name)
    reach_areasb = ClipAreasbyWater(mainShape=pre_area_buffb, ClipShape=clipgeoms, crs=proj_crs, process_name=proc_name)
    reach_areasc = ClipAreasbyWater(mainShape=pre_area_buffc, ClipShape=clipgeoms, crs=proj_crs, process_name=proc_name)

    pre_area_buff = None
    pre_area_buffb = None
    pre_area_buffc = None

    print ("create streamside buffer")
    #
    buf_10m = gpd.GeoDataFrame()
    buf_10m['geometry'] = reach_areasb.buffer(distance=10)
    buf_10m['reach_no'] = reach_areasb['reach_no']
    buf_10m.crs = proj_crs

    buf_10m = EraseAreasbyWater(mainShape=buf_10m, ClipShape=clipgeoms, crs=proj_crs, process_name=proc_name)

    print ("create foraging buffer")
    buf_40m = gpd.GeoDataFrame()
    buf_40m['geometry'] = reach_areas.buffer(distance=40)
    buf_40m['reach_no'] = reach_areas['reach_no']
    buf_40m.crs = proj_crs
    buf_40m = EraseAreasbyWater(mainShape=buf_40m, ClipShape=clipgeoms, crs=proj_crs, process_name=proc_name)

    # print("getting start elevation values")

    stats = LoopRasStats(shape=startpoint_buf, Raster=DEM_orig, stat='min', cat=False, process_name=proc_name)
    seg_network.loc[seg_network['reach_no'] == stats['reach_no'], "iGeo_ElMax"] = stats['min']


    print ("start elevations done for " + proc_name)

    # get end elevation values
    # print("getting end elevation values")


    ##### new end elevation value zs

    stats = LoopRasStats(shape=endpoint_buff, Raster=DEM_orig, stat='min', cat=False, process_name=proc_name)
    seg_network.loc[seg_network['reach_no'] == stats['reach_no'], "iGeo_ElMin"] = stats['min']


    print ("end elevations done for " + proc_name)

    # add slope
    print("calculating slope")

    seg_network["iGeo_Len"] = seg_network['geometry'].length.values

    seg_network["iGeo_Slope"] = (seg_network["iGeo_ElMax"] - seg_network["iGeo_ElMin"])/seg_network["iGeo_Len"]

    seg_network.loc[seg_network["iGeo_Slope"] <= 0, "iGeo_Slope"] = 0.0001
    seg_network.loc[seg_network["iGeo_Slope"] >= 1.0, "iGeo_Slope"] = 0.5

    # Get reach widths
    print("calculating reach widths")

    # gpd_reachAreas = gpd.read_file(reach_areasc, driver="ESRI Shapefile")
    seg_network["iGeo_Area"] = reach_areasc['geometry'].area.values
    seg_network["iGeo_Width"] = seg_network["iGeo_Area"]/(seg_network["iGeo_Len"] + 40)

    ##### new end Drain Area value zs

    stats = LoopRasStats(shape=midpoint_buffer, Raster=DrArea, stat='max', cat=False, process_name=proc_name)
    seg_network.loc[seg_network['reach_no'] == stats['reach_no'], "iGeo_DA"] = stats['max']



    seg_network.loc[seg_network["iGeo_DA"] <= 0, "iGeo_DA"] = 0.1

    print("drainage areas done for " + proc_name)

    stats = LoopRasStats(shape=buf_40m, Raster=coded_vega, stat=None, cat=True, process_name=proc_name)

    thm_pd = GetTopHalfMean(stats, process_name=proc_name)

    seg_network = pd.merge(seg_network, thm_pd, on='reach_no', how='left')
    seg_network = seg_network.rename(index=str, columns={"thMean": "iVeg_40"})
    # seg_network.loc[seg_network['reach_no'] == thm_pd['reach_no'], 'iVeg_40'] = thm_pd['thMean']

    print ("foraging veg done for " + proc_name)

    stats = LoopRasStats(shape=buf_10m, Raster=coded_vega, stat=None, cat=True, process_name=proc_name)

    thm_pd = GetTopHalfMean(stats, process_name=proc_name)
    seg_network = pd.merge(seg_network, thm_pd, on='reach_no', how='left')
    seg_network = seg_network.rename(index=str, columns={"thMean": "iVeg_10"})


    print("riparian veg done for " + proc_name)

    cols_list = list(seg_network)
    keep_list = ['Str_order', 'reach_no', 'geometry', 'iGeo_Area', 'iGeo_ElMax', 'iGeo_ElMin', 'iGeo_Len', 'iGeo_Slope',
                 'iGeo_Width', 'iGeo_DA', 'iVeg_40', 'iVeg_10', 'catchmentN', 'watercou_1']

    remove_list = [i for i in cols_list if i not in keep_list]

    for i in remove_list:
        if i in cols_list:
            seg_network = seg_network.drop(i, axis=1)
    # print(list(seg_network))

    print(proc_name + " done")
    # print(seg_network.head())

    return seg_network


def CreateOverlayGeoms(strNet_gdf, inWatArea_gdf, crs, process_name):
    # print('POINT_A: {0}'.format(process_name))
    boundsgeom = gpd.GeoDataFrame()
    boundsgeom['geometry'] = strNet_gdf.buffer(distance=100)
    boundsgeom['reach_no'] = strNet_gdf['reach_no']
    spatial_index = inWatArea_gdf.sindex
    # print('POINT_B: {0}'.format(process_name))
    gdfList = []
    shpLen = len(boundsgeom)
    # counter = 0
    for i, shp in boundsgeom.iterrows():

        gdf = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry']), columns=['geometry'])

        bound_matches_index = list(spatial_index.intersection(gdf.bounds.iloc[0]))

        matches = inWatArea_gdf.loc[bound_matches_index]

        out_gdf = gpd.GeoDataFrame()

        matches['merge'] = 'merge'
        matches_diss = matches.dissolve(by='merge')
        out_gdf['geometry'] = gpd.GeoSeries(matches_diss['geometry'])

        gdfList.append(out_gdf)


    clipping_gdf = gpd.GeoDataFrame(pd.concat(gdfList, ignore_index=True))
    clipping_gdf.crs = crs
    clipping_gdf['merge'] = 'merge'
    # print('POINT_D: {0}'.format(process_name))
    m_poly = clipping_gdf.dissolve(by='merge')
    m_poly = m_poly.reset_index()
    m_poly = m_poly.drop(columns='merge')

    print('Overlay Geoms - {0}: Completed'.format(process_name))
    return m_poly

def PointsAlongLine(gdf_line, p_dist, process_name):
    if p_dist == 0:
        name = 'start'
    elif p_dist == 1:
        name = 'end'
    else:
        name = 'mid'

    geom_list = []
    reachno_list = []
    nr = len(gdf_line)
    counter = 0
    for index, row in gdf_line.iterrows():
        counter += 1
        shapelyLine = row['geometry']

        splitPoint = (shapelyLine.interpolate(p_dist, normalized=True))
        x, y = splitPoint.coords.xy
        geom_list.append((float(x[0]), float(y[0])))
        reachno_list.append(row['reach_no'])

        # print_progress(counter, nr, prefix='{0} Points - {1}:'.format(name, process_name), suffix='Complete')

    gs_points = gpd.GeoSeries(Point(pnt[0], pnt[1]) for pnt in geom_list)
    gdf_points = gpd.GeoDataFrame()
    gdf_points['geometry'] = gs_points
    gdf_points['reach_no'] = reachno_list

    print('{0} Points - {1}: Completed'.format(name, process_name))

    return gdf_points

def LoopRasStats(shape, Raster, stat, cat, process_name):
    shpLen = len(shape)
    dfList = []
    counter = 0
    for i, shp in shape.iterrows():
        counter += 1
        gs = gpd.GeoSeries(shp['geometry'])
        try:
            stats = zonal_stats(gs, Raster, all_touched=True,
                            stats=stat, categorical=cat, nodata=-999)
        except Exception as e:
            print(e)
            print(shp)
            if cat == True:
                stats = {0: [0], 1: [0], 2: [0], 3: [0], 4: [0], 5: [0]}
            else:
                loz = [0] * shpLen
                stats = {stat: loz}

        df = pd.DataFrame(stats)
        df['reach_no'] = shp['reach_no']

        dfList.append(df)

        # print_progress(counter, shpLen, prefix='RasStats - {0}:'.format(process_name), suffix='Complete')

    dframe = pd.concat(dfList, sort=False)
    # dframe = dframe.reset_index(drop=True)
    dframe = dframe.set_index('reach_no', drop=False)
    dframe.index.name = None

    # dframe = dframe.sort_index(inplace=True)
    print('RasStats - {0}: Completed'.format(process_name))
    return dframe



def GetTopHalfMean(stat_df, process_name):

    nr = len(stat_df)
    stat_list = []
    counter = 0
    for i, row in stat_df.iterrows():
        counter += 1

        rnum = int(row['reach_no'])
        mod_arr = pd.DataFrame(row)
        mod_arr.columns = ['ncells']
        mod_arr = mod_arr.drop('reach_no')
        mod_arr = mod_arr.fillna(0)
        mod_arr['ncells'] = mod_arr['ncells'].astype(int)
        mod_arr['value'] = mod_arr.index
        Newdf = mod_arr.reindex(mod_arr.index.repeat(mod_arr.ncells))
        Newdf['position'] = Newdf.groupby(level=0).cumcount() + 1
        lower, upper = np.array_split(Newdf, 2)

        top_avg = upper['value'].mean()

        out_df = pd.DataFrame({'thMean': [top_avg],
                               'reach_no': [rnum]})

        stat_list.append(out_df)

    dframe = pd.concat(stat_list, sort=False)
    dframe = dframe.set_index('reach_no', drop=False)
    dframe.index.name = None
    print('TopHalfMean -{0}: Completed'.format(process_name))
    return dframe


def ClipAreasbyWater(mainShape, ClipShape, crs, process_name):

    count = 0
    geom_list = []
    rn_list = []

    for i, row in mainShape.iterrows():
        count += 1

        reachNum = row.loc['reach_no']
        main_so = row.loc['geometry']

        try:
            if main_so.geom_type != 'MultiPolygon':
                main_so = MultiPolygon([main_so])
        except AttributeError as e:
            print(e)
            main_so = MultiPolygon([main_so])

        try:
            newgeom = main_so.intersection(ClipShape['geometry'].values[0])

            # if newgeom.geom_type != 'MultiPolygon':
            #     newgeom = MultiPolygon([newgeom])

            if newgeom.is_empty:
                print("EMPTY GEOM!!!")
                newgeom = main_so
        except Exception as e:
            print(e)
            print('clip failed - returning non altered buffer for {0}'.format(reachNum))
            newgeom = main_so

        try:
            geom_list.append(newgeom)
            rn_list.append(reachNum)
        except Exception as e:
            print(e)
            print("BREAK_{}!".format(count))

    print('Clip Water Areas - {0}: Completed'.format(process_name))
    out_shape = gpd.GeoDataFrame(geometry=gpd.GeoSeries(geom_list))
    out_shape['reach_no'] = rn_list
    out_shape.crs = crs
    # print(out_shape)
    return out_shape


def EraseAreasbyWater(mainShape, ClipShape, crs, process_name):
    geom_list = []
    rn_list=[]
    count = 0
    for i, row in mainShape.iterrows():
        count += 1

        reachNum = row.loc['reach_no']
        main_so = row.loc['geometry']
        # workArea = ClipShape.loc[ClipShape['reach_no'] == reachNum]
        # if main_so.geom_type != 'MultiPolygon':
        #     main_so = MultiPolygon([main_so])
        try:
            newgeom = main_so.difference(ClipShape['geometry'].values[0])

            if newgeom.is_empty:
                print("EMPTY_ERASE_GEOM")
                newgeom = main_so
        except Exception as e:
            print(e)
            print('erase failed - returning non altered buffer for {0}'.format(reachNum))
            newgeom = main_so

        try:
            geom_list.append(newgeom)
            rn_list.append(reachNum)
        except Exception as e:
            print(e)
            print("BREAK_{}!".format(count))

    print('Erase Water Areas - {0}: Completed'.format(process_name))
    out_shape = gpd.GeoDataFrame(geometry=gpd.GeoSeries(geom_list))
    out_shape['reach_no'] = rn_list
    out_shape.crs = crs
    # print(out_shape)
    return out_shape


def paralellProcess(net_gdf, iw_area_shp, sb_DEM, DrAreaPathIn, coded_vegIn, proj_crs ):
    # gdf = MainProcessing(iw_area_shp, sb_DEM, DrAreaPathIn, coded_vegIn, proj_crs, net_gdf.copy(), net_gdf)

    n_feat = len(net_gdf)
    rowlim  = 1000
    num_cores = multiprocessing.cpu_count()
    n_split = int(n_feat/rowlim)
    if n_split < num_cores:
        n_chunks = num_cores
    else:
        n_chunks = n_split

    df_split = np.array_split(net_gdf, n_chunks)

    pool = multiprocessing.Pool(num_cores)

    function = partial(MainProcessing, iw_area_shp, sb_DEM, DrAreaPathIn, coded_vegIn, proj_crs, net_gdf.copy())
    results = pool.map(function, df_split)
    pool.close()
    pool.join()
    print('pools closed/joined...')

    print('joining outputs...')
    gdf = pd.concat(results)
    gdf = gdf.reset_index(drop=True)
    gdf['reach_no'] = gdf.index

    # gdf.plot(column='Str_order')
    # plt.show()

    return gdf


