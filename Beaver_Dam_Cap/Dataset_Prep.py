import json
import os
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.crs import CRS
from shapely.geometry import box
from datetime import datetime
from tqdm import tqdm
# from matplotlib import pyplot as plt


def BDC_setup_main(rivers_root, dem_path, bvi_etc_root, operCatch, epsg_code, outRoot, **kwargs):
    id_col = kwargs.get('id_column', None)

    os_gridPath = os.path.join(os.path.dirname(__file__), 'Data', 'OSGB_Grid_100km.gpkg')

    startTime = datetime.now()
    # print("running BDC setup script")
    # print("start time = {0}".format(startTime))

    if os.path.exists(outRoot):
        # print("export folder already exists")
        pass
    else:
        # print("create export folder")
        os.makedirs(outRoot)

    opCatch_gp = gpd.read_file(operCatch)
    opCatch_gp = opCatch_gp.to_crs(crs='epsg:{}'.format(epsg_code))
    # print(opCatch_gp.crs)


    # A better way of handling indexes would be nice but for now you must add manually.
    if id_col is None:
        print("id column not provided - adding default id numbers")
        opCatch_gp['id'] = opCatch_gp.index + 1000
        # print("id column exists - continue")
    else:
        try:
            opCatch_gp['id'] = opCatch_gp[id_col] + 1000
        except KeyError as e:
            raise KeyError('Supplied ID column does not exist in geo data frame: {0}'.format(id_col))


    id_listA = list(opCatch_gp['id'])
    id_list = [int(i) for i in id_listA]
    for area in tqdm(id_list, desc='Dataset Preparation'):

        outFolder = os.path.join(outRoot, "Op_Catch_{0}".format(area))
        if os.path.exists(outFolder):
            # print("OS Grid folder already exists")
            pass
        else:
            # print("create OS Grid folder folder")
            os.makedirs(outFolder)

        opCatSelec = opCatch_gp[opCatch_gp.id == area]
        opCatSelec.crs = ('epsg:{}'.format(epsg_code))
        exp_path = os.path.join(outFolder,
                                   "OC{0}_catchmentArea.gpkg".format(area))  # define the output shp file name
        opCatSelec.to_file(exp_path, driver='GPKG')

        coords, grid_List = get_extents(opCatSelec, os_gridPath, epsg_code)

        get_rivs(rivers_root, opCatSelec, grid_List, outFolder, area, epsg_code)
        get_inWatArea(bvi_etc_root, opCatSelec, epsg_code, grid_List, outFolder, area)
        get_bvi(bvi_etc_root, epsg_code, coords, outFolder, area, grid_List, opCatSelec)
        get_dem(dem_path, epsg_code, coords, outFolder, area, grid_List, opCatSelec)

        # if os.path.exists(scratch):
        #     shutil.rmtree(scratch)



    # print("script finished at {0}".format(datetime.now()))
    # print("Total Run Time = {0}".format(datetime.now() - startTime))


def get_extents(work_hyd_area, os_grid, epsg):
    # print("getting working extents for Op Catch hydrometic area")

    ordsurv_gp = gpd.read_file(os_grid)
    ordsurv_gp['GRIDSQ'] = ordsurv_gp['TILE_NAME']
    os_grids = gpd.overlay(ordsurv_gp, work_hyd_area, how='intersection')
    # print(os_grids)
    grid_list = list(os_grids['GRIDSQ'])

    # print(grid_list)

    minx, miny, maxx, maxy = work_hyd_area.geometry.total_bounds
    bbox = box(minx, miny, maxx, maxy)
    geo = gpd.GeoDataFrame({'geometry': bbox}, index=[0])
    coords = getFeatures(geo)

    geo.crs = ('epsg:{}'.format(epsg))
    return coords, grid_list


def getFeatures(gdf):
    """Function to parse features from GeoDataFrame in such a manner that rasterio wants them"""
    return [json.loads(gdf.to_json())['features'][0]['geometry']]


def get_rivs(riv_root, oc_shp, grid_list, outfold, hyd_num, epsg):
    # print("extracting detailed river network features with Op Catch")

    oc_area = oc_shp.loc[oc_shp.id == hyd_num].copy()
    oc_area = oc_area.reset_index()
    oc_area.crs = oc_shp.crs

    river_list = []
    count = 0
    for grid in grid_list:
        path = os.path.join(riv_root, grid.lower())
        shp_test = os.listdir(path)
        for x in shp_test:
            if x[-5:] == '.gpkg':
                count += 1
                shp_file = os.path.join(path, x)
                riv_gpd = gpd.read_file(shp_file)

                if oc_area.loc[0, 'geometry'].is_valid is False: # fixes catchment if geometery is invalid
                    oc_area.loc[0, 'geometry'] = oc_area.loc[0, 'geometry'].buffer(0)

                rivs_clipped = clip(riv_gpd, oc_area)

                river_list.append(rivs_clipped)


    if len(river_list) > 1:
        # temp_rivs = os.path.join(tempo_gdb, 'temp_rivs')
        # print("merging clipped features")
        riv_masked = gpd.GeoDataFrame(pd.concat(river_list, ignore_index=True))

        # riv_masked = pd.concat([
        #     gpd.read_file(shp)
        #     for shp in river_list], sort=True).pipe(gpd.GeoDataFrame)

    else:
        # print("copying features")

        riv_masked = river_list[0]

    riv_masked.crs = ('epsg:{}'.format(epsg))

    rivs_clipped = None
    river_list = None

    export_path = os.path.join(outfold, "OC{0}_MM_rivers.gpkg".format(hyd_num))

    riv_masked.to_file(export_path, driver='GPKG')

    # pd.set_option('display.max_rows', 500)
    # pd.set_option('display.max_columns', 500)
    # pd.set_option('display.width', 1000)
    # riv_masked.head()
    # ax = riv_masked.plot()
    # oc_area.plot(ax=ax, color='None', edgecolor='black')
    # plt.show()



def get_inWatArea(root, oc_ha, epsg, grid_list, outfold, hyd_num):
    # print("extracting inland water area features within OC HA")

    water_list = []

    for grid in grid_list:
        path = os.path.join(root, grid.lower())
        shp_test = os.listdir(path)
        for x in shp_test:
            if x[-13:] == 'WaterArea.shp':
                shp_file = os.path.join(path, x)
                water_list.append(shp_file)

    inwaterA_gp = pd.concat([
        gpd.read_file(shp)
        for shp in water_list
    ], sort=True).pipe(gpd.GeoDataFrame)

    water_list = None

    inwaterA_gp.crs = ('epsg:{}'.format(epsg))

    inwaterB_gp = gpd.overlay(inwaterA_gp, oc_ha, how='intersection')

    inwaterA_gp = None

    export_path = os.path.join(outfold, "OC{0}_OS_InWater.gpkg".format(hyd_num))  # define the output shp file name
    inwaterB_gp.to_file(export_path, driver='GPKG')

def get_bvi(root, epsg, coords, outfold, hyd_num, grid_list, work_hydAr):
    # print("extracting Beaver Veg. Index within Op Catch")
    # We need to add a condition - if len(gridlist) < 1 then no need to merge - skip to mask.
    bvi_list = []


    for grid in grid_list:
        path = os.path.join(root, grid.lower())
        ras_test = os.listdir(path)
        for x in ras_test:
            if x[-10:] == 'GB_BVI.tif':
                ras_file = os.path.join(path, x)
                bvi_list.append(ras_file)

    if len(bvi_list) > 1:
        # print(">1 OS grid masking and merging rasters")
        src_files_to_mosaic = []
        mx, my, Mx, My = work_hydAr.geometry.total_bounds
        for fp in bvi_list:
            src = rasterio.open(fp)
            # out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
            src_files_to_mosaic.append(src)
        mosaic, out_trans = merge(src_files_to_mosaic, bounds=[mx, my, Mx, My])

    elif len(bvi_list) == 0:
        raise ValueError("eh what's going on? looks like you've got no BVI to merge?")

    else:
        # print("just one OS Grid - masking now")
        for fp in bvi_list:
            src = rasterio.open(fp)
            mosaic, out_trans = mask(dataset=src, shapes=coords, crop=True)


    out_meta = src.meta.copy()

    out_meta.update(
        {"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
         "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    # print("exporting output raster")
    out_ras = os.path.join(outfold, "OC{0}_BVI.tif".format(hyd_num))
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)


def get_dem(dem_root,epsg, coords, outfold, hyd_num, grid_list, work_hydAr):
    # print("extracting DEM for Op Catch")

    dtm_list = []

    for grid in grid_list:
        path = os.path.join(dem_root, grid.lower())
        ras_test = os.listdir(path)
        for x in ras_test:
            if x[-10:] == 'DTM_5m.tif':
                ras_file = os.path.join(path, x)
                dtm_list.append(ras_file)

    # src_files_to_mosaic = []
    if len(dtm_list) > 1:
        # print(">1 OS grid masking and merging rasters")
        mx, my, Mx, My = work_hydAr.geometry.total_bounds
        src_files_to_mosaic = []
        for fp in dtm_list:
            src = rasterio.open(fp)
            # out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
            src_files_to_mosaic.append(src)
        mosaic, out_trans = merge(src_files_to_mosaic, bounds=[mx, my, Mx, My])

    elif len(dtm_list) == 0:
        raise ValueError("eh what's going on? looks like you've got no DTMs to merge?")
    else:
        # print("just one OS Grid - masking now")
        src = rasterio.open(dtm_list[0])
        mosaic, out_trans = mask(dataset=src, shapes=coords, crop=True)


    out_meta = src.meta.copy()

    out_meta.update(
        {"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
         "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    # print("exporting output raster")
    out_ras = os.path.join(outfold, "OC{0}_DTM.tif".format(hyd_num))
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)

    mosaic = None
    out_img = None
    src = None

    maskedRas = rasterio.open(out_ras)

    hydAr_gj = getFeatures(work_hydAr)
    mosaicb, otb = mask(dataset=maskedRas, shapes=hydAr_gj, crop=False, nodata=(-100), all_touched=False)

    maskedRas = None

    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaicb)

def clip(to_clip, clip_shp):
    """Alternative clip function"""
    union = gpd.GeoDataFrame(
        gpd.GeoSeries([clip_shp.unary_union]),
        columns=['geometry'],
        crs=clip_shp.crs
    )

    # clip_gdf1 = gpd.sjoin(to_clip, union, op='within')  # previously 'within': caused deletion of tidal reaches
    clip_gdf = gpd.overlay(to_clip, union, how="intersection")
    # clip_gdf = clip_gdf.drop(columns=['index_right'])

    return clip_gdf
