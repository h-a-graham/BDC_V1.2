import sys
import json
import os
import geopandas as gpd
import pandas as pd
import rasterio
from rasterio.merge import merge
from rasterio.mask import mask
from rasterio.crs import CRS
from shapely.geometry import box
from shapely.ops import cascaded_union
from datetime import datetime
import earthpy as et
import earthpy.clip as ec

startTime = datetime.now()


def BDC_setup_main(rivers_root, dem_path, bvi_etc_root, operCatch, os_gridPath, epsg_code, outRoot):

    print("running BDC setup script")
    print("start time = {0}".format(startTime))

    if os.path.exists(outRoot):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(outRoot)

    opCatch_gp = gpd.read_file(operCatch)
    opCatch_gp.to_crs = ({'init': 'epsg:' + epsg_code})
    print(opCatch_gp.crs)


    # A better way of handling indexes would be nice but for now you must add manually.
    if 'id' in opCatch_gp.columns:
        print("id column exists - continue")
    else:
        print("id column does not exists - add one")
        opCatch_gp['id'] = opCatch_gp.index + 1000


    id_listA = list(opCatch_gp['id'])
    id_list = [int(i) for i in id_listA]
    for area in id_list:

        outFolder = os.path.join(outRoot, "Op_Catch_{0}".format(area))
        if os.path.exists(outFolder):
            print("OS Grid folder already exists")
        else:
            print("create OS Grid folder folder")
            os.makedirs(outFolder)
        opCatSelec = opCatch_gp[opCatch_gp.id == area]
        opCatSelec.crs = ({'init': 'epsg:' + epsg_code})
        exp_path = os.path.join(outFolder,
                                   "OC{0}_catchmentArea.gpkg".format(area))  # define the output shp file name
        opCatSelec.to_file(exp_path)

        coords, grid_List = get_extents(opCatSelec, os_gridPath, epsg_code)

        get_rivs_arc(rivers_root, opCatSelec, grid_List, outFolder, area)
        get_inWatArea(bvi_etc_root, opCatSelec, epsg_code, grid_List, outFolder, area)
        get_bvi(bvi_etc_root, epsg_code, coords, outFolder, area, grid_List, opCatSelec)
        get_dem(dem_path, epsg_code, coords, outFolder, area, grid_List, opCatSelec)

    print("script finished at {0}".format(datetime.now()))
    print("Total Run Time = {0}".format(datetime.now() - startTime))


def get_extents(work_hyd_area, os_grid, epsg):
    print("getting working extents for Op Catch hydrometic area")

    ordsurv_gp = gpd.read_file(os_grid, driver="ESRI Shapefile")
    ordsurv_gp['GRIDSQ'] = ordsurv_gp['TILE_NAME']
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


def get_rivs_arc(riv_root, oc_shp, grid_list, outfold, hyd_num):
    print("extracting detailed river network features with Op Catch")

    # arcpy.env.overwriteOutput = True
    # # arcpy.Delete_management(r"in_memory")
    # gdb_name = 'tempo_GDB.gdb'
    # tempo_gdb = os.path.join(outfold, gdb_name)
    # if arcpy.Exists(tempo_gdb):
    #     arcpy.Delete_management(tempo_gdb)
    # arcpy.CreateFileGDB_management(outfold, gdb_name)

    # oc_area = gpd.read_file(oc_shp)
    oc_area = oc_shp.loc[oc_shp.id == hyd_num].copy()
    oc_area.crs = oc_shp.crs
    # oc_area = arcpy.MakeFeatureLayer_management(oc_shp, "oc_selec", "", tempo_gdb)
    # with arcpy.da.SearchCursor(oc_area, ["id"]) as cursor:
    #     for row in cursor:
    #         if row[0] == hyd_num:
    #             print(row[0])
    #             expr = """{0} = {1}""".format('id', row[0])
    #             print(expr)
    #
    #             arcpy.SelectLayerByAttribute_management(oc_area,
    #                                                     "NEW_SELECTION",
    #                                                     expr)
    #             temp_zone = os.path.join(tempo_gdb, 'OS_tempZone')
    #             oc_clip = arcpy.CopyFeatures_management(oc_area, temp_zone)

    river_list = []
    count = 0
    for grid in grid_list:
        path = os.path.join(riv_root, grid.lower())
        shp_test = os.listdir(path)
        for x in shp_test:
            # count += 1
            if x[-4:] == '.shp':
                count += 1
                shp_file = os.path.join(path, x)
                riv_gpd = gpd.read_file(shp_file)
                # temp_rivs = os.path.join(tempo_gdb, 'temp_rivs{0}'.format(count)

                if oc_area.loc[0, 'geometry'].is_valid is False: # fixes catchment if geometery is invalid
                    oc_area.loc[0, 'geometry'] = oc_area.loc[0, 'geometry'].buffer(0)
                rivs_clipped = ec.clip_shp(riv_gpd, oc_area)
                # Remove empty geometries
                rivs_clipped = rivs_clipped[~rivs_clipped.is_empty]

                river_list.append(rivs_clipped)

    # export_path = os.path.join(outfold, "OC{0}_MM_rivers.shp".format(hyd_num))



    if len(river_list) > 1:
        # temp_rivs = os.path.join(tempo_gdb, 'temp_rivs')
        print("merging clipped features")
        riv_masked = gpd.GeoDataFrame(pd.concat(river_list, ignore_index=True))

        # print("clipping features")
        # arcpy.Clip_analysis(temp_rivs, oc_clip, export_path)
    else:
        print("copying features")

        riv_masked = river_list[0]
        # arcpy.CopyFeatures_management(river_list[0], export_path)
        # arcpy.Clip_analysis(river_list[0], oc_clip, export_path)
    export_path = os.path.join(outfold, "OC{0}_MM_rivers.gpkg".format(hyd_num))

    riv_masked.to_file(export_path)



def get_inWatArea(root, oc_ha, epsg, grid_list, outfold, hyd_num):
    print("extracting inland water area features within OC HA")

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
    inwaterA_gp.crs = ({'init': 'epsg:' + epsg})

    inwaterB_gp = gpd.overlay(inwaterA_gp, oc_ha, how='intersection')

    export_path = os.path.join(outfold, "OC{0}_OS_InWater.gpkg".format(hyd_num))  # define the output shp file name
    inwaterB_gp.to_file(export_path)

def get_bvi(root, epsg, coords, outfold, hyd_num, grid_list, work_hydAr):
    print("extracting Beaver Veg. Index within Op Catch")
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

    print("exporting output raster")
    out_ras = os.path.join(outfold, "OC{0}_BVI.tif".format(hyd_num))
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)

    out_img = None
    mosaic = None


def get_dem(dem_root,epsg, coords, outfold, hyd_num, grid_list, work_hydAr):
    print("extracting DEM for Op Catch")

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
        print(">1 OS grid masking and merging rasters")
        mx, my, Mx, My = work_hydAr.geometry.total_bounds
        src_files_to_mosaic = []
        for fp in dtm_list:
            src = rasterio.open(fp)
            # out_img, out_transform = mask(dataset=src, shapes=coords, crop=True)
            src_files_to_mosaic.append(src)
        mosaic, out_trans = merge(src_files_to_mosaic, bounds=[mx, my, Mx, My])

    elif len(dtm_list) == 0:
        print("eh what's going on? looks like you've got no DTMs to merge?")
        sys.exit(1)
    else:
        print("just one OS Grid - masking now")
        src = rasterio.open(dtm_list[0])
        mosaic, out_trans = mask(dataset=src, shapes=coords, crop=True)



    # out_img, out_transform = mask(dataset=mosaic, shapes=coords, crop=True)

    out_meta = src.meta.copy()

    out_meta.update(
        {"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
         "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    print("exporting output raster")
    out_ras = os.path.join(outfold, "OC{0}_DTM.tif".format(hyd_num))
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)

    mosaic = None
    out_img = None

    maskedRas = rasterio.open(out_ras)

    # hydAr_gj = gpd.GeoSeries([work_hydAr]).__geo_interface__
    hydAr_gj = getFeatures(work_hydAr)
    mosaicb, otb = mask(dataset=maskedRas, shapes=hydAr_gj, crop=False, nodata=(-100), all_touched=False)

    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaicb)



if __name__ == '__main__':
     BDC_setup_main(sys.argv[1],
                    sys.argv[2],
                    sys.argv[3],
                    sys.argv[4],
                    sys.argv[5],
                    sys.argv[6],
                    sys.argv[7])
