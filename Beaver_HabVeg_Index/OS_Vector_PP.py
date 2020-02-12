########################################################################################################################
# ------- Converts OS VectorMap Local layers (Landform Area, Water Area and Buildings) to a BVI input raster -----------
########################################################################################################################
#Issues... Looks like some classifiers are still not yet defined.

import gdal
import numpy as np
import os
# from pathlib import Path
import geopandas as gpd
import pandas
import osr
import rasterio
from rasterio import features
from datetime import datetime
import glob
import traceback
import sys
#start timer
startTime = datetime.now()
# print(startTime)


def OS_Vec_main(epsg_code, home, exports, OrdSurv_Grid): #epsg_code, home, scratch, exports

    print(startTime)
    # set up workspace
    # epsg_code = str(27700) # this is OSGB should be no need ot change
    # home = os.path.abspath("D:/Work/GB_Beaver_Data/Edina/OS_Vector")

    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")

    # scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.
    #
    # if os.path.exists(scratch):
    #     print("scratch folder already exists")
    # else:
    #     print("create scratch folder")
    #     os.makedirs(scratch)

    # exports = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Results")  # sctatch workspace name no need to create.

    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    osvecmapRas(epsg_code, home, exports, OrdSurv_Grid)

    print(datetime.now() - startTime)
    print("script finished")


def osvecmapRas(epsg_code, home, exports, OSgrid):

    direc_list = next(os.walk(home))[1]
    check_list = next(os.walk(exports))[1] # Turned off for testing
    print(direc_list)
    # check_list = ['sx']
    # iterate over top folder containing OS regions
    print("start looping folders")
    for osg in direc_list:
        if osg in check_list:
        # if osg == 'sx':  # for testing only
            print("{0} grid already processed - skip it.".format(osg))
        else:

            print("get glob for {0}".format(osg))
            file_search = os.path.join(home, osg, "**/Area.shp")
            shapefiles = glob.glob(file_search, recursive=True)

            print("merging glob")
            vecmap_gp = pandas.concat([
                gpd.read_file(shp)
                for shp in shapefiles
            ], sort=True).pipe(gpd.GeoDataFrame)
            vecmap_gp.crs = ({'init': 'epsg:' + epsg_code})

            print("geopandas merge completed - begin reclass")

            vecmap_gp = vecmap_gp[vecmap_gp.featureDes != 'Urban Extent']
            vecmap_gp['BVI_Val'] = None
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders And Sand", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders And Shingle", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Broad-leafed Woodland", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Broad-leafed Woodland And Shrub", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Building Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Coniferous Woodland", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Coniferous Woodland And Shrub", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Custom Landform Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Glasshouse Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Gravel Pit", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland And Boulders", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland And Marsh", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland And Unimproved Grass", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland And Unimproved Grass And Boulders", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Inland Rock", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Inland Water Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Marsh", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Marsh And Unimproved Grass", 'BVI_Val'] = 2
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Mixed Woodland", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Mixed Woodland And Shrub", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Mud", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Orchard", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Railway Bridge", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Reeds", 'BVI_Val'] = 2
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Refuse Or Slag Heap", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Sand", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Sand Pit", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Sea Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle And Mud", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle And Sand", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub", 'BVI_Val'] = 5
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Boulders", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Heathland", 'BVI_Val'] = 2
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Heathland And Boulders", 'BVI_Val'] = 2
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Heathland And Unimproved Grass", 'BVI_Val'] = 2
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Marsh", 'BVI_Val'] = 4
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Marsh And Heath", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Marsh And Unimproved Grass", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Unimproved Grass", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub And Unimproved Grass And Boulders", 'BVI_Val'] = 3
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass And Sand", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass And Boulders", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass And Shingle", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Grass And Shingle", 'BVI_Val'] = 1
            vecmap_gp.loc[vecmap_gp['featureDes'] == "Building Polygon", 'BVI_Val'] = 0
            vecmap_gp.loc[vecmap_gp['BVI_Val'].isnull(), 'BVI_Val'] = 98


            # print("exporting shapefiles for {0}".format(osg))

            # export_path = os.path.join(os_grid_fold, osg + "_OSVec_Area.shp")  # define the output shp file name
            # vecmap_gp.to_file(export_path,
            #                 driver="ESRI Shapefile")  # export OSGB feature to shp file - not required but can be useful for debugging

            # gdf_wat = vecmap_gp[vecmap_gp.featureDes == "Inland Water Polygon"]
            # print(gdf_wat)
            # gdf_wat = gpd.GeoDataFrame(vecmap_gp.loc[vecmap_gp['featureDes'] == "Inland Water Polygon"],
            #                  geometry='geometry', crs={'init': 'epsg:' + epsg_code})

            # export_path = os.path.join(os_grid_fold, osg + "_WaterArea.shp")  # define the output shp file name
            # gdf_wat.to_file(export_path,
            #                 driver="ESRI Shapefile")  # export OSGB feature to shp file - not required but can be useful for debugging

            print("OS Grid {0} completed".format(osg))

            split_up_gp(vecmap_gp, OSgrid, epsg_code, exports, osg)


            print("OS Grid {0} completed".format(osg))

    print("reclass complete")
    # return vecmap_gp


def split_up_gp(vecmap_GP, OSgrid, epsg_code, exports, osg):
    os_grid_fold = os.path.join(exports, osg)
    if os.path.exists(os_grid_fold):
        print("OS Grid folder already exists")
    else:
        print("create OS Grid folder folder")
        os.makedirs(os_grid_fold)

    print("begin splitting up geo data frame")
    ordsurv_gp = gpd.read_file(OSgrid, driver="ESRI Shapefile")

    print(osg.upper())

    # grid_area = ordsurv_gp[ordsurv_gp.GRIDSQ == osg.upper()]
    #
    grid_area = gpd.GeoDataFrame(ordsurv_gp.loc[ordsurv_gp['GRIDSQ'] == osg.upper()],
                                 geometry='geometry', crs={'init': 'epsg:' + epsg_code})
    print(grid_area)

    print("clip vector for OS {0}".format(osg))
    try:
        if vecmap_GP.empty:
            print("OS {0} has no features".format(osg))
        else:
            osv_selec = gpd.overlay(vecmap_GP, grid_area, how='intersection')

            wat_area = osv_selec[osv_selec.featureDes == 'Inland Water Polygon']
            if wat_area.empty:
                print("OS {0} has no water features".format(osg))

            else:
                print("Exporting Water Area shp file for OS GRID {0}".format(osg))
                export_path = os.path.join(os_grid_fold, osg + "_WaterArea.shp")  # define the output shp file name
                wat_area.to_file(export_path,
                                 driver="ESRI Shapefile")
    except Exception as ex:
        traceback.print_exc()

    wat_area = None
    vecmap_GP = None
    try:
        print("creating template Raster file")
        # convert merged shp file to Raster
        minx, miny, maxx, maxy = grid_area.geometry.total_bounds  # get boundary of shapefile

        rast_res = 5  # desired resolution of rasters
        dist_width = maxx - minx
        width = int(round(dist_width) / rast_res)

        dist_height = maxy - miny
        height = int(round(dist_height) / rast_res)

        format = "GTiff"
        driver = gdal.GetDriverByName(format)

        ras_exp_path = os.path.join(os_grid_fold, osg + "_OS_vec_5m.tif")
        print(ras_exp_path)
        ras_template = driver.Create(ras_exp_path, width, height, 1, gdal.GDT_Int16, ['COMPRESS=LZW'])
        print("template created")
        geotransform = ([minx, rast_res, 0, maxy, 0, -rast_res])

        ras_template.SetGeoTransform(geotransform)
        print("geotransformed")

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        ras_template.SetProjection(srs.ExportToWkt())
        print("projection set")

        raster = np.full((height, width), 99, dtype=np.int8, )
        print("numpy array created")
        # raster[...] = 99

        ras_template.GetRasterBand(1).WriteArray(raster)
        print("numpy array set to raster")

        ras_template = None

        print("opening template in rasterio")
        rst = rasterio.open(ras_exp_path)

        meta = rst.meta.copy()
        meta.update(compress='lzw')

        rst = None

        print("rasterizing Features")

        with rasterio.open(ras_exp_path, 'r+', **meta) as out:
            out_arr = out.read(1)

            # this is where we create a generator of geom, value pairs to use in rasterizing
            shapes = ((geom, value) for geom, value in zip(osv_selec.geometry, osv_selec.BVI_Val))

            burned = features.rasterize(shapes=shapes, fill=99, out=out_arr, transform=out.transform)
            out.write_band(1, burned)
        out = None
        osv_selec = None


    except Exception as ex:
        traceback.print_exc()

# if __name__ == '__main__':
#     OS_Vec_main() #sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3]
#
