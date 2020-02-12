# This Script Extracts a BHI for every feeding sign location using a 10m buffer to cater for GPS uncertainty and the
# survey methodology whereby a point was recorded every 10m where activity was idenitified.
import os
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.transform import from_origin
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.crs import CRS
from shapely.geometry import box
import sys
import json
import matplotlib.pyplot as plt
from rasterio.plot import show
from rasterio import features
import numpy as np

def main():
    otter_fp = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Feeding_Signs/RivOtter_FS.shp")
    otter_Area = os.path.abspath("D:/Work/GB_Beaver_Data/BDC_Process/Op_Catch_1002/OC1002_catchmentArea.shp")

    bhi_root = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Res_v2")
    osGrid_root = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp")

    bhiValHome = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/BHI_Validation")
    if os.path.exists(bhiValHome):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(bhiValHome)

    print("running BHI Validation prep script")

    sortOutOtter(otter_fp, bhi_path) # this is where i need to start

    getBHI(otter_Area, bhi_root, osGrid_root, bhiValHome, bhi_root)




    sortOutOtter(otter_fp)


def getBHI(Catch_Area, bhi_path, osGridPath, bhi_outF, bhi_parent):
    print("getting BHI area")
    work_area = gpd.read_file(Catch_Area)
    crs = str(work_area.crs)[-7:-2]
    AreaID = work_area['id'].iloc[0]

    coord, grid_lst = get_extents(work_area, osGridPath, crs)

    nCateg, bhi_rst = get_bvi(bhi_parent, crs, coord, bhi_outF, AreaID, grid_lst, work_area)

def sortOutOtter(points_path, bhi_path):
    pointsGDF = gpd.read_file(points_path)

    # id_listA = list(opCatch_gp['id'])
    # rst = rasterio.open(rst_fn, bhi_path)
    #
    # arr = np.random.randint(5, size=(100, 100)).astype(np.float)
    #
    # transform = from_origin(472137, 5015782, 0.5, 0.5)
    #
    # new_dataset = rasterio.open('test1.tif', 'w', driver='GTiff',
    #                             height=arr.shape[0], width=arr.shape[1],
    #                             count=1, dtype=str(arr.dtype),
    #                             crs='+proj=utm +zone=10 +ellps=GRS80 +datum=NAD83 +units=m +no_defs',
    #                             transform=transform)

    # new_dataset.write(arr,

def get_extents(work_hyd_area, os_grid, epsg):
    print("getting working extents for Op Catch hydrometic area")

    ordsurv_gp = gpd.read_file(os_grid, driver="ESRI Shapefile")

    os_grids = gpd.overlay(ordsurv_gp, work_hyd_area, how='intersection')
    print(os_grids)
    grid_list = list(os_grids['GRIDSQ'])

    print(grid_list)

    minx, miny, maxx, maxy = work_hyd_area.geometry.total_bounds
    bbox = box(minx, miny, maxx, maxy)
    geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0])
    coords = getFeatures(geo)

    geo.crs = ({'init': 'epsg:' + epsg})
    return coords, grid_list


def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    return [json.loads(gdf.to_json())['features'][0]['geometry']]


def get_bvi(root, epsg, coords, outfold, hyd_num, grid_list, work_hydAr):
    print("extracting Beaver Veg. Index within Op Catch")
    # We need to add a condition - if len(gridlist) < 1 then no need to merge - skip to mask.
    bvi_list = []


    for grid in grid_list:
        path = os.path.join(root, grid.lower())
        ras_test = os.listdir(path)
        for x in ras_test:
            if x[-10:] == 'GB_BHI.tif':
                ras_file = os.path.join(path, x)
                bvi_list.append(ras_file)

    if len(bvi_list) > 1:
        print(">1 OS grid masking and merging rasters")
        src_files_to_mosaic = []
        mx, my, Mx, My = work_hydAr.geometry.total_bounds
        for fp in bvi_list:
            src = rasterio.open(fp)
            # out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
            src_files_to_mosaic.append(src)
        mosaic, out_trans = merge(src_files_to_mosaic, bounds=[mx, my, Mx, My])

    elif len(bvi_list) == 0:
        print("eh what's going on? looks like you've got no BVI to merge?")
        sys.exit(1)

    else:
        print("just one OS Grid - masking now")
        for fp in bvi_list:
            src = rasterio.open(fp)
            mosaic, out_trans = mask(dataset=src, shapes=coords, crop=True)

    # out_img, out_transform = mask(dataset=mosaic, shapes=coords, crop=True)

    out_meta = src.meta.copy()

    out_meta.update(
        {"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
         "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    work_hydAr['BHI_Val'] = 1
    print("exporting output raster")
    out_ras = os.path.join(outfold, "OC{0}_BHI.tif".format(hyd_num))
    with rasterio.open(out_ras, "r+", **out_meta) as dest:
        dest.nodata = -99
        out_arr = dest.read(1)

        # this is where we create a generator of geom, value pairs to use in rasterizing
        shapes = ((geom, value) for geom, value in zip(work_hydAr.geometry, work_hydAr.BHI_Val))

        burned = rasterio.features.rasterize(shapes=shapes, fill=-99, out=out_arr, transform=dest.transform)
        burned = burned.reshape(1, burned.shape[0], burned.shape[1])
        # mosaic.shape = burned.shape
        mosaic[burned != 1] = burned[burned != 1]

        n0 = len(mosaic[mosaic == 0])
        n1 = len(mosaic[mosaic == 1])
        n2 = len(mosaic[mosaic == 2])
        n3 = len(mosaic[mosaic == 3])
        n4 = len(mosaic[mosaic == 4])
        n5 = len(mosaic[mosaic == 5])

        numlis = [n0, n1, n2, n3, n4, n5]

        # nNA = len(mosaic[mosaic == -99])
        # image_read_masked = np.ma.masked_array(mosaic, mask=(mosaic == -99))

        dest.write(mosaic)
    rst_bhi = rasterio.open(out_ras)
    show(rst_bhi)

    return numlis, rst_bhi



    out_img = None
    mosaic = None


if __name__ == '__main__':
    main()