
from datetime import datetime
import os
import sys
import rasterio
import geopandas as gpd
from rasterio import features
import subprocess
import numpy as np
import shutil
from matplotlib import pyplot as plt
import pandas as pd

############# START TIME ##############
startTime = datetime.now()


def main(path, scratch_gdb, seg_network_a, DEM_orig, epsg):

    print(startTime)

    home_name = "BDC_OC{0}".format(path[-4:])  # REQUIRED - name of home working directory to be created
    home = os.path.join(path, home_name)  # Don't Edit
    outname = "Output_BDC_OC{0}.shp".format(path[-4:])  # REQUIRED - output file name -  must end in .shp


    print("Run Stream Burn Process")

    stream_burn_dem, net_raster, ras_meta, riv_gdf = streamBurning(DEM_orig, scratch_gdb, seg_network_a, path, home_name)

    print("Run Flow Accumulation / Drainage area raster Process")
    flowacc, strord_lines, grass_dir = run_grass(scratch_gdb, stream_burn_dem)

    acc_to_contarea(DEM_orig, flowacc)


    print("Run Stream Order Polygon Generation")

    reaches_out = os.path.join(scratch_gdb, "seg_network_b.gpkg")

    if os.path.isfile(reaches_out):
        print("stream ordering alredy done...")

    else:
        seg_net_gdf =join_str_order(riv_gdf, strord_lines)
        seg_net_gdf.crs = ({'init': 'epsg:' + epsg})
        seg_net_gdf.to_file(reaches_out)

    if os.path.isdir(grass_dir):
        try:
            shutil.rmtree(grass_dir)
        except PermissionError as e:
            print(e)

    finTime = datetime.now() - startTime
    print("BDC Terrain completed. \n"
          "Processing time = {0}".format(finTime))

    return reaches_out

################################################################################################
###################### NOW TIME FOR STREAM BURNING ###############################
################################################################################################

def streamBurning(DEM_orig, scratch_gdb, seg_network_a, home, home_name):
    print ("stream burning process")

    riv_vec = gpd.read_file(seg_network_a)

    with rasterio.open(DEM_orig) as dem:
        meta = dem.meta.copy()
        meta.update(compress='lzw')
        dem_arr = dem.read(1)

    riv_ras = os.path.join(scratch_gdb, "{0}Riv_Ras.tif".format(home_name))

    with rasterio.open(riv_ras, 'w+', **meta) as out:
        out_arr = out.read(1)


        # this is where we create a generator of geom, value pairs to use in rasterizing
        shapes = (geom for geom in riv_vec.geometry)

        features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform,
                                    all_touched=True)
        print(np.max(out_arr))
        print(np.min(out_arr))

        out.write_band(1, out_arr)


    sb_DEM = os.path.join(home, "{0}strBurndDEm.tif".format(home_name))

    with rasterio.open(sb_DEM, 'w+', **meta) as out:
        dem_arr[out_arr == 1] = dem_arr[out_arr == 1] - 50
        out.write_band(1, dem_arr)

    return sb_DEM, riv_ras, meta, riv_vec

def run_grass(scratch_gdb, burn_dem):
    print("set up to run terrain processing in GRASS GIS")
    scriptHome = os.path.dirname(__file__)

    wrkdir = os.path.join(scriptHome, 'grass_processing')
    if os.path.isdir(wrkdir):
        try:
            shutil.rmtree(wrkdir)
        except PermissionError as e:
            print(e)

    out_lines = os.path.join(scratch_gdb, "st_ord_line.gpkg")
    out_flwacc = os.path.join(scratch_gdb, "flwacc.tif")
    command = os.path.abspath("C:/OSGeo4W64/OSGeo4W.bat")


    init_script = os.path.join(scriptHome, 'grass_scripts', 'grass_initiate.bat')
    run_script = os.path.join(scriptHome, 'grass_scripts', 'grass_streamorder.bat')
    # print(scriptHome)
    # myscript_loc = os.path.join(scriptHome, "Stream_Order_Sub.py")

    args = [wrkdir, run_script, burn_dem, out_lines, out_flwacc]
    # print(args)
    cmd = [command, init_script] + args

    subprocess.call(cmd, universal_newlines=True)

    return out_flwacc, out_lines, wrkdir

def acc_to_contarea(DEM_orig, flwacc_path):
    print("converting n cells to contributing area")

    with rasterio.open(flwacc_path, 'r') as flw:
        flowacc = flw.read(1)
        meta = flw.meta

    meta.update(dtype="float32")
    res = abs(meta.get('transform')[0])
    drain_area = (flowacc * (res*res) / 1000000).astype(dtype='float32')

    DEM_dirname = os.path.dirname(DEM_orig)
    DrArea_path = os.path.join(DEM_dirname, "DrainArea_sqkm.tif")
    with rasterio.open(DrArea_path, 'w', **meta) as cont:
        cont.write_band(1, drain_area)


def join_str_order(streams_gdf, str_ord_lines):

    so_gdf = gpd.read_file(str_ord_lines)


    riv_centroids = streams_gdf.copy()
    riv_centroids['join_key'] = riv_centroids.index
    riv_centroids['geometry'] = riv_centroids['geometry'].centroid
    riv_centroids['geometry'] = riv_centroids['geometry'].buffer(15)

    streams_so_join = gpd.sjoin(riv_centroids, so_gdf, how='left', op='intersects', lsuffix='left',
                             rsuffix='right')
    print(streams_so_join)
    streams_gdf['join_key'] = streams_gdf.index
    streams_so_join = streams_gdf.merge(streams_so_join, on='join_key', how='left')

    streams_so_join = gpd.GeoDataFrame(streams_so_join[['reach_leng_x', 'strahler']],
                                       geometry=gpd.GeoSeries(streams_so_join['geometry_x']))

    streams_so_join = streams_so_join.rename(columns={"strahler": "Str_order"})
    streams_so_join = streams_so_join.rename(columns={"reach_leng_x": "reach_leng"})
    streams_so_join["Str_order"] = streams_so_join["Str_order"].fillna(value=1)

    return streams_so_join


if __name__ == '__main__':
        main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        sys.argv[5])


