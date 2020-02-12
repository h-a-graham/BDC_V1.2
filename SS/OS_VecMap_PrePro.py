########################################################################################################################
# ------- Converts OS VectorMap Local layers (Landform Area, Water Area and Buildings) to a BVI input raster -----------
########################################################################################################################
#Issues... So the problem is that the data I HAve is not laid out like the stuff from digimap so..
#... Going to need to rethink the project structure and looping over which folders etc...
#... ball bags

import gdal
import numpy as np
import os
from pathlib import Path
import geopandas as gpd
import pandas
import osr
import rasterio
from rasterio import features
from datetime import datetime
import sys
#start timer
startTime = datetime.now()
# print(startTime)


def OS_Vec_main(epsg_code, home, scratch, exports):

    print(startTime)
    # set up workspace
    # epsg_code = str(27700) # this is OSGB should be no need ot change
    # home = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Test_OSVM")

    # scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.

    if os.path.exists(scratch):
        print("scratch folder already exists")
    else:
        print("create scratch folder")
        os.makedirs(scratch)

    # exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OSVM_exports")  # sctatch workspace name no need to create.

    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    osvecmapRas(epsg_code, home, scratch, exports)
    # water_area(epsg_code, home, exports)

    print(datetime.now() - startTime)
    print("script finished")


def osvecmapRas(epsg_code, home, scratch, exports):

    direc_list = next(os.walk(home))[1]

    print(direc_list)

    # iterate over top folder containing OS regions
    print("start looping folders")
    for osg in direc_list:

        print("folder name = " + str(osg))
        folder_list = next(os.walk(os.path.join(home, osg)))[1]
        for folder in folder_list:
            file_list = os.listdir(os.path.join(home, osg, folder))
        # print (file_list)

            # then iterate over the shp files ending with landform Area
            for shp in file_list:
                if shp[-8:] == 'Area.shp':  #if shp[-17:] == 'Landform_Area.shp':
                    shp_name = folder

                    shp_path = os.path.join(home, osg, folder, shp)
                    # print(shp_path)

                    vecmap_gp = gpd.read_file(shp_path)
                    print(shp_name + " loaded")
                    vecmap_gp['BVI_Val'] = None

                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders and Sand", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Boulders and Shingle", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Broad-leafed woodland", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Broad-leafed woodland and Shru", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Building polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Coniferous woodland", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Coniferous woodland and Shrub", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Custom landform polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Glasshouse polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Gravel Pit", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland and Boulders", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland and Marsh", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Heathland and Unimproved Grass", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Inland Rock", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Inland Water Polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Marsh", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Marsh and Unimproved Grass", 'BVI_Val'] = 2
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Mixed woodland", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Mixed woodland and Shrub", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Mud", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Orchard", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Reeds", 'BVI_Val'] = 2
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Refuse or Slag Heap", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Sand", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Sand Pit", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Sea polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle and Mud", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shingle and Sand", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub", 'BVI_Val'] = 5
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and  Boulders", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Heathland", 'BVI_Val'] = 2
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Heathland and Boulde", 'BVI_Val'] = 2
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Heathland and Unimpr", 'BVI_Val'] = 2
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Marsh", 'BVI_Val'] = 4
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Marsh and Heath", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Marsh and Unimproved", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Unimproved Grass", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Shrub and Unimproved Grass and", 'BVI_Val'] = 3
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass and Sand", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Unimproved Grass and Boulders", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Grass and Shingle", 'BVI_Val'] = 1
                    vecmap_gp.loc[vecmap_gp['featureDes'] == "Building Polygon", 'BVI_Val'] = 0
                    vecmap_gp.loc[vecmap_gp['BVI_Val'].isnull(), 'BVI_Val'] = 98

                    vecmap_gp_out = os.path.join(scratch, shp_name + ".shp")

                    vecmap_gp.to_file(vecmap_gp_out, driver="ESRI Shapefile")

                    vecmap_gp = None

                # elif shp[-14:] == 'Water_Area.shp' or shp[-12:] == 'Building.shp':
                #     shp_name = shp[:12]
                #
                #     shp_path = os.path.join(home, folder, shp)
                #     # print(shp_path)
                #
                #     vecmap_gp = gpd.read_file(shp_path)
                #     print(shp + " loaded")
                #     vecmap_gp['BVI_Val'] = 0
                #
                #     vecmap_gp_out = os.path.join(scratch, shp_name + "." + "shp")
                #
                #     vecmap_gp.to_file(vecmap_gp_out, driver="ESRI Shapefile")
                #
                #     vecmap_gp = None

            # here we merge all the shapefiles for a given OSGB tile
        print("merging shapefiles for tile: " + osg)
        fold = Path(scratch)
        shapefiles = fold.glob("*.shp")
        gdf = pandas.concat([
            gpd.read_file(shp)
            for shp in shapefiles
        ], sort=True).pipe(gpd.GeoDataFrame)
        gdf.crs = ({'init': 'epsg:' + epsg_code})


        #clear out scratch space
        print("clearing out scratch space")
        for the_file in os.listdir(scratch):
            file_path = os.path.join(scratch, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)

        # create folder for OS grid region
        os_grid_fold = os.path.join(exports, osg.lower())
        if os.path.exists(os_grid_fold):
            print("OS Grid folder already exists")
        else:
            print("create OS Grid folder folder")
            os.makedirs(os_grid_fold)

        print("exporting water area")
        gdf_wat = gdf[gdf.featureDes == "Inland Water Polygon"]
        export_path = os.path.join(os_grid_fold, osg + "_WaterArea.shp")  # define the output shp file name
        gdf_wat.to_file(export_path, driver="ESRI Shapefile")  # export OSGB feature to shp file - not required but can be useful for debugging

        print("creating Raster file")
        # convert merged shp file to Raster
        minx, miny, maxx, maxy = gdf.geometry.total_bounds  # get boundary of shapefile

        rast_res = 5  # desired resolution of rasters
        dist_width = maxx - minx
        width = int(round(dist_width) / rast_res)

        dist_height = maxy - miny
        height = int(round(dist_height) / rast_res)

        format = "GTiff"
        driver = gdal.GetDriverByName(format)

        ras_exp_path = os.path.join(os_grid_fold, osg + "_OS_LA.tif")
        ras_template = driver.Create(ras_exp_path, width, height, 1, gdal.GDT_Int16)
        geotransform = ([minx, rast_res, 0, maxy, 0, -rast_res])
        ras_template.SetGeoTransform(geotransform)

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        ras_template.SetProjection(srs.ExportToWkt())

        raster = np.full((height, width), 99, dtype=np.int8, )

        ras_template.GetRasterBand(1).WriteArray(raster)

        ras_template = None

        rst = rasterio.open(ras_exp_path)

        meta = rst.meta.copy()
        meta.update(compress='lzw')

        rst = None

        with rasterio.open(ras_exp_path, 'r+', **meta) as out:
            out_arr = out.read(1)

            # this is where we create a generator of geom, value pairs to use in rasterizing
            shapes = ((geom, value) for geom, value in zip(gdf.geometry, gdf.BVI_Val))

            burned = features.rasterize(shapes=shapes, fill=99, out=out_arr, transform=out.transform)
            out.write_band(1, burned)
        out = None


# def water_area(epsg_code, home, exports):
#     direc_list = next(os.walk(home))[1]
#
#     print(direc_list)
#
#     # iterate over top folder containing OS regions
#     print("start looping folders")
#     for osg in direc_list:
#
#         folder_list = next(os.walk(os.path.join(home, osg)))[1]
#         for folder in folder_list:
#             file_list = os.listdir(os.path.join(home, osg, folder))
#             # print (file_list)
#
#             for shp in file_list:
#
#                 print("folder name = " + str(osg))
#
#                 src_fold = os.path.join(home, osg, folder)
#                 os_grid_fold = os.path.join(exports, osg.lower())
#
#                 print("joining water areas for OSGB " + str(folder))
#                 fold = Path(src_fold)
#                 shapefiles = fold.glob("*Water_Area.shp")
#                 gdf = pandas.concat([
#                     gpd.read_file(shp)
#                     for shp in shapefiles
#                 ]).pipe(gpd.GeoDataFrame)
#                 gdf.crs = ({'init': 'epsg:' + epsg_code})
#
#                 print("exporting water areas for OSGB " + str(folder))
#                 export_path = os.path.join(os_grid_fold, folder + "_WaterArea.shp")  # define the output shp file name
#                 gdf.to_file(export_path, driver="ESRI Shapefile")  # export OSGB feature to shp file - not required but can be useful for debugging
#
#                 gdf = None

if __name__ == '__main__':
    OS_Vec_main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3])







