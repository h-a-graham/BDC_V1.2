########################################################################################################################
# --------------------- Converts CEH Land Cover Map Vector to a BVI input raster 5m resolution -------------------------
########################################################################################################################

import gdal
import numpy as np
import os
import geopandas as gpd
import osr
import rasterio
from rasterio import features
from datetime import datetime
import arcpy
import sys

#start timer
startTime = datetime.now()



def lcm_main(epsg_code, file_loc, OrdSurv_Grid, scratch, exports):
    print(startTime)
    # set up workspace
    # epsg_code = str(27700)  # this is OSGB should be no need ot change

    # file_loc = os.path.abspath("D:/UK_BVI_workflow_Data/Data/lcm-2015-vec_1904131/LCM2015_GB.gdb")  # full dataset
    # file_loc = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Arc_pro_inspect/GB_BVI_test.gdb")  #test

    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")

    # scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.
    arcpy.env.overwriteOutput = True
    gdb_name = "BVIscratch"
    scratch_gdb = os.path.join(scratch, gdb_name + ".gdb")
    if os.path.exists(scratch):
        print("scratch folder already exists")
        if arcpy.Exists(scratch_gdb):
            arcpy.Delete_management(scratch_gdb)
            arcpy.CreateFileGDB_management(scratch, gdb_name)
        else:
            arcpy.CreateFileGDB_management(scratch, gdb_name)

    else:
        print("create scratch folder")
        os.makedirs(scratch)
        arcpy.CreateFileGDB_management(scratch, gdb_name)
    arcpy.env.scratchWorkspace = scratch_gdb

    # exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/CEH_LCM_export")  # sctatch workspace name no need to create.
    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    cut_that_sucker(file_loc, OrdSurv_Grid, scratch_gdb, epsg_code, exports)
    # lcm_map_gp = lcmmapReclass(epsg_code, file_loc, scratch, exports)
    print("reclassification done")

    # lcm_mapRas(lcm_map_gp, OrdSurv_Grid, exports, epsg_code)

    print(datetime.now() - startTime)
    print("script finished")

def cut_that_sucker(file_loc, OrdSurv_Grid, scratch_gdb, epsg_code, exports):
    print("cutting up the shp file with arcpy becuase...I suck...")
    ordsurv_gp = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")
    ordsurv_gp.crs = ({'init': 'epsg:' + epsg_code})
    ord_grid_fl = arcpy.MakeFeatureLayer_management(OrdSurv_Grid, "lay_selec", "", r"in_memory")

    with arcpy.da.SearchCursor(ord_grid_fl, ["GRIDSQ"]) as cursor:
        for row in cursor:
            # if row[0] == 'SX':  # JUST FOR TESTING!!!
            grid_area = row[0]
            print(grid_area)

            print('select features within Ordnance Survey grid area')

            expr = """{0} = '{1}'""".format('GRIDSQ', row[0])
            print(expr)

            arcpy.SelectLayerByAttribute_management(ord_grid_fl,
                                                    "NEW_SELECTION",
                                                    expr)
            temp_zone = r"in_memory/OS_tempZone"
            OS_clip = arcpy.CopyFeatures_management(ord_grid_fl, temp_zone)

            clip_file = os.path.join(scratch_gdb, "lcm_clip")
            print("clipping features to Grid area")
            arcpy.Clip_analysis(file_loc, OS_clip, clip_file)
            obj_len = int(str(arcpy.GetCount_management(clip_file)))
            # print(obj_len)
            if obj_len > 0:
                print("run the next bit")
                lcm_gpd = lcmmapReclass(scratch_gdb, epsg_code)

                gpd_wa = ordsurv_gp[ordsurv_gp.GRIDSQ == grid_area]

                lcm_exp_code = "_CEH_LCM_BVI_5m.tif"

                lcm_mapRas(lcm_gpd, gpd_wa, exports, epsg_code, grid_area, lcm_exp_code)

                conif_gpd = lcm_gpd[lcm_gpd.bhab == "Coniferous woodland"]
                if conif_gpd.empty:
                    print("no conifer area in OS Grid {0}".format(grid_area))
                else:
                    con_exp_code = "_CEH_Con.tif"
                    lcm_mapRas(conif_gpd, gpd_wa, exports, epsg_code, grid_area, con_exp_code)

                arcpy.Delete_management(clip_file)

            else:
                print("no feautes in OS GRID {0}".format(grid_area))


def lcmmapReclass(file_loc, epsg_code):
    print("LCM reclassification")

    lcm_map_gp = gpd.read_file(file_loc, driver='FileGDB')
    lcm_map_gp.crs = ({'init': 'epsg:' + epsg_code})
    print(file_loc + " loaded")
    lcm_map_gp['BVI_Val'] = None

    print("running inference system")

    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Acid grassland", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Arable and horticulture", 'BVI_Val'] = 2
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Broadleaf woodland", 'BVI_Val'] = 5
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Bog", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Calcareous grassland", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Coniferous woodland", 'BVI_Val'] = 3
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Fen, marsh and swamp", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Freshwater", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Heather", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Heather grassland", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Improved grassland", 'BVI_Val'] = 1
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Inland rock", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Littoral rock", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Littoral sediment", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Neutral grassland", 'BVI_Val'] = 2
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Saltmarsh", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Saltwater", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Suburban", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Supralittoral rock", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Supralittoral sediment", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['bhab'] == "Urban", 'BVI_Val'] = 0
    lcm_map_gp.loc[lcm_map_gp['BVI_Val'].isnull(), 'BVI_Val'] = 98  # A flag for issues

    return lcm_map_gp

    # export_path = os.path.join(exports, "LCM_CEH_test_Area.shp")  # define the output shp file name
    # lcm_map_gp.to_file(export_path, driver="ESRI Shapefile")


def lcm_mapRas(lcm_selec, grid_area, exports, epsg_code, grid_name, name_code):
    print("converting to raster")

    print(grid_name)

    os_grid_fold = os.path.join(exports, grid_name.lower())
    if os.path.exists(os_grid_fold):
        print("OS Grid folder already exists")
    else:
        print("create OS Grid folder folder")
        os.makedirs(os_grid_fold)

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

    ras_exp_path = os.path.join(os_grid_fold, grid_name + name_code)
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

    raster = np.full((height, width), 99, dtype=np.int8,)
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
        shapes = ((geom, value) for geom, value in zip(lcm_selec.geometry, lcm_selec.BVI_Val))

        burned = features.rasterize(shapes=shapes, fill=99, out=out_arr, transform=out.transform)
        out.write_band(1, burned)
    out = None

# if __name__ == '__main__':
#     lcm_main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
