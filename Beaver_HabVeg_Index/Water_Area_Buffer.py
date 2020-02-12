# This script will buffer the OS MasterMap layer and the OS Water Area layer and then merge and rasterize to
# give us a BVI region around all freshwater bodies.

# Issues: So it looks like the only problem is that when there is only inland water
#         no buffer feature is being created...

import sys
import gdal
import os
import arcpy
import geopandas as gpd
import osr
import rasterio
from rasterio import features
import numpy as np
from datetime import datetime

#start timer
startTime = datetime.now()



def riv_area_main(buff_size, epsg_code, riv_line_fold, scratch, exports, OrdSurv_Grid):
    print(startTime)
    print("running water area buffer pre processing")
    # buff_size = 100  # Set this value up front therefore enabling adjustment later if required.
    # set up workspace
    # epsg_code = 27700  # this is OSGB should be no need ot change

    # riv_line_fold = os.path.abspath("D:/GB_Beaver_Data/Edina/exu-hg-vml-3/mastermap-water/2018_10/gml")


    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")

    # scratch = os.path.abspath(
    #     "C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.

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

    # exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OSVM_exports_test2")  # export location
    test = os.path.exists(exports)
    if test is False:
        raise ValueError("Export folder does not exists:"
                         "YOU MUST FIRST CREATE WATER AREA LAYER !!!!")
    else:
        print("export folder exists, Continue...")

    arcpy.env.overwriteOutput = True
    arcpy.env.scratchWorkspace = r"in_memory"
    arcpy.Delete_management(r"in_memory")
    ref = arcpy.SpatialReference(int(epsg_code))
    arcpy.env.outputCoordinateSystem = ref

    buff_water_area(exports, buff_size, riv_line_fold, scratch_gdb, OrdSurv_Grid, epsg_code)

    # buff_lines(OrdSurv_Grid, riv_line_fold, exports)

    print("reclassification done")
    arcpy.Delete_management(r"in_memory")

    print(datetime.now() - startTime)
    print("script finished")


def buff_water_area(exports, buff_size, riv_line_fold, scratch_gdb, OrdSurv_Grid, epsg_code):
    ordsurv_gp = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")
    ordsurv_gp.crs = ({'init': 'epsg:' + epsg_code})

    direc_list = next(os.walk(exports))[1]

    # print(direc_list)

    # iterate over top folder containing OS regions
    print("start looping folders")
    for folder in direc_list:
        # if folder == 'sx' or folder == 'sy': # Just for testing

        wa_path = os.path.join(exports, folder, folder + "_WaterArea.shp")
        if arcpy.Exists(wa_path):
            print("buffering water area for OS Grid {0}".format(folder))
            wa_buff_tmp = r"in_memory/wa_buff"
            arcpy.Buffer_analysis(wa_path, r"in_memory/wa_buff", buffer_distance_or_field=buff_size,
                                  line_side="FULL")

            line_buff = buff_lines(riv_line_fold, folder, buff_size, OrdSurv_Grid)

            buffer_out = os.path.join(scratch_gdb, folder + "water_buffer")

            if line_buff is None:
                print("no line features for {0}, using olys only".format(folder))
                arcpy.CopyFeatures_management(wa_buff_tmp, buffer_out)
            else:
                print("merging line and polygons for OS Grid {0}".format(folder))
                merge_list = [wa_buff_tmp, line_buff]
                arcpy.Merge_management(merge_list, buffer_out)

            water_gpd = gpd.read_file(scratch_gdb, driver='FileGDB')
            water_gpd['Wat_True'] = 1
            os_Area_gpd = ordsurv_gp[ordsurv_gp.GRIDSQ == folder.upper()]

            rasterise_that(water_gpd, os_Area_gpd, exports, epsg_code, folder.upper())
            arcpy.Delete_management(buffer_out)


        else:
            line_buff = buff_lines(riv_line_fold, folder, buff_size, OrdSurv_Grid)
            if line_buff is None:
                print("no rivers for OS GRID {0}".format(folder))
            else:
                buffer_out = os.path.join(scratch_gdb, folder + "water_buffer")
                arcpy.CopyFeatures_management(line_buff, buffer_out)
                water_gpd = gpd.read_file(scratch_gdb, driver='FileGDB')
                water_gpd['Wat_True'] = 1
                os_Area_gpd = ordsurv_gp[ordsurv_gp.GRIDSQ == folder.upper()]

                rasterise_that(water_gpd, os_Area_gpd, exports, epsg_code, folder.upper())
                arcpy.Delete_management(buffer_out)

        arcpy.Delete_management(r"in_memory")


def buff_lines(riv_line_fold, folder, buff_size, Ordnan_Grid):
    print("selecting the relevant area to clip")

    river_folders = next(os.walk(riv_line_fold))[1]

    # print(river_folders)

    # iterate over top folder containing OS regions
    print("start looping folders")
    for fold in river_folders:
        if fold == folder:
            print('importing and merging river lines for OS Grid {0}'.format(fold))

            root = os.path.join(riv_line_fold, fold)
            f_list = os.listdir(root)
            for x in f_list:
                if x[-4:] == '.shp':
                    river_lines = os.path.join(riv_line_fold, fold, x)  # riv_line_fold + "\\" + fold + "\\" + "*.gz"

                    print("copy features to in memory")
                    rivers_name = r"in_memory/rivers"
                    arcpy.CopyFeatures_management(river_lines, rivers_name)

                    rivers_buffer = r"in_memory/riversBuff"

                    print("buffering")

                    arcpy.Buffer_analysis(rivers_name, rivers_buffer, buff_size)

                    clip_zone = r"in_memory/clipZone"
                    expr = """{0} = '{1}'""".format('GRIDSQ', fold.upper())
                    arcpy.MakeFeatureLayer_management(Ordnan_Grid, clip_zone,)
                    arcpy.SelectLayerByAttribute_management(clip_zone, selection_type="NEW_SELECTION",
                                                            where_clause=expr) # Needs double checking
                    rivers_buffnclip = r"in_memory/rivBuff_n_clip"
                    arcpy.Clip_analysis(rivers_buffer,clip_zone,rivers_buffnclip)

            if arcpy.Exists(r"in_memory/rivBuff_n_clip"):
                pass
            else:
                rivers_buffnclip = None  # this is a bit lazy but I don't think this can occur anyway...

            return rivers_buffnclip

def rasterise_that(water_shp, grid_area, exports, epsg_code, grid_name):
    print("rasterising some rivers n stuff...")


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

    ras_exp_path = os.path.join(os_grid_fold, grid_name + "_Water_Buffer_ras.tif")
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

    raster = np.full((height, width), 0, dtype=np.int8, )
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
        shapes = ((geom, value) for geom, value in zip(water_shp.geometry, water_shp.Wat_True))

        burned = features.rasterize(shapes=shapes, fill=99, out=out_arr, transform=out.transform)
        out.write_band(1, burned)
    out = None
# if __name__ == '__main__':
#     riv_area_main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
