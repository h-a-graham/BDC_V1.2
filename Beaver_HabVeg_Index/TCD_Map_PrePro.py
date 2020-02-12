

# align with other rasters 9this could be the challenging bit...
from osgeo.gdalnumeric import *
import arcpy
import numpy as np
import os
import geopandas as gpd
import osr
import rasterio
from rasterio import Affine
from rasterio.warp import reproject, Resampling
from datetime import datetime


#start timer
startTime = datetime.now()


def tcd_main(scratch, exports, tcd_cop_fold, OrdSurv_Grid, epsg_code):
    print(startTime)

    # scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.

    if os.path.exists(scratch):
        print("scratch folder already exists")
    else:
        print("create scratch folder")
        os.makedirs(scratch)
    print("clearing out scratch space")
    for the_file in os.listdir(scratch):
        file_path = os.path.join(scratch, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)

    # exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/TCD_exports")  # sctatch workspace name no need to create.
    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    # tcd_cop_fold = "C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/TCD_Data"
    #
    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    #
    # epsg_code = str(27700)

    tcd_cop = merge_tcd_ras(tcd_cop_fold, OrdSurv_Grid, scratch, epsg_code) # this one works with arcpy (trying not to use it)

    build_frame_raster(OrdSurv_Grid, epsg_code, exports, tcd_cop, scratch)

    print(datetime.now() - startTime)
    print("script finished")


def merge_tcd_ras(tcd_cop_fold, OrdSurv_Grid, scratch, epsg_code):
    print("merging rasters in arcpy")

    tcd_3030_cop = os.path.join(tcd_cop_fold, r"TCD_2015_020m_eu_03035_d05_E30N30",
                                r"TCD_2015_020m_eu_03035_d05_E30N30.TIF")
    tcd_3040_cop = os.path.join(tcd_cop_fold, r"TCD_2015_020m_eu_03035_d05_E30N40",
                                r"TCD_2015_020m_eu_03035_d05_E30N40.TIF")
    # scratch_sub = os.path.join(scratch, "tcd_temp")
    tcd_name = "TCD_GB_merge.TIF"
    tcd_crop = os.path.join(tcd_cop_fold, tcd_name)

    spatial_ref = arcpy.Describe(tcd_3030_cop).spatialReference

    if arcpy.Exists(tcd_crop):
        print("merged raster exists - SKIPPING RASTER MERGE!")
        # tcd_merge = (scratch, tcd_name)
    else:
        tcd_merge = arcpy.MosaicToNewRaster_management([tcd_3030_cop, tcd_3040_cop],
                                                       scratch, tcd_name, spatial_ref, number_of_bands=1)

        os_a_copy = (os.path.join(scratch, "OS_Grid_copy.shp"))
        if arcpy.Exists(os_a_copy):
            arcpy.Delete_management(os_a_copy)

        os_area_copy = arcpy.Project_management(OrdSurv_Grid, os_a_copy, spatial_ref)

        extent = arcpy.Describe(os_area_copy).extent
        xmin = extent.XMin
        ymin = extent.YMin
        xmax = extent.XMax
        ymax = extent.YMax

        corners = (str(xmin) + " " + str(ymin) + " " + str(xmax) + " " + str(ymax))

        if arcpy.Exists(tcd_crop):
            arcpy.Delete_management(tcd_crop)

        arcpy.Clip_management(tcd_merge, corners, tcd_crop)

        print("raster_clipped")

        # clear out scratch space
        print("clearing out scratch space")
        for the_file in os.listdir(scratch):
            file_path = os.path.join(scratch, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)

    return tcd_crop


def build_frame_raster(OrdSurv_Grid, epsg_code, exports, tcd_cop, scratch):
    print("building raster frame for transformation")
    ordsurv_gp = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")

    grid_area = None
    grid_name = None

    for feature, row in ordsurv_gp.iterrows():
        grid_name = row['GRIDSQ']
        print(grid_name)

        # if grid_name == 'NO' or grid_name == 'NN':  # This is just for testing
        os_grid_fold = os.path.join(exports, grid_name.lower())
        if os.path.exists(os_grid_fold):
            print("OS Grid folder already exists")
        else:
            print("create OS Grid folder folder")
            os.makedirs(os_grid_fold)

        grid_area = gpd.GeoDataFrame(ordsurv_gp.loc[ordsurv_gp['GRIDSQ'] == grid_name],
                                    geometry='geometry', crs={'init': 'epsg:' + epsg_code})

        print("creating template Raster file")
        # convert merged shp file to Raster
        minx, miny, maxx, maxy = grid_area.geometry.total_bounds  # get boundary of shapefile

        rast_res = 20  # desired resolution of rasters
        dist_width = maxx - minx
        width = int(round(dist_width) / rast_res)

        dist_height = maxy - miny
        height = int(round(dist_height) / rast_res)

        format = "GTiff"
        driver = gdal.GetDriverByName(format)

        ras_exp_path = os.path.join(scratch, grid_name + "_TCD.tif")  # change from b for real run
        print(ras_exp_path)

        ras_template = driver.Create(ras_exp_path, width, height, 1, gdal.GDT_Int32,
                                     ['COMPRESS=LZW'])   # ['COMPRESS=DEFLATE', 'PREDICTOR=2','ZLEVEL=9'])
        print("template created")
        geotransform = ([minx, rast_res, 0, maxy, 0, -rast_res])

        ras_template.SetGeoTransform(geotransform)
        print("geotransformed")

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        ras_template.SetProjection(srs.ExportToWkt())
        print("projection set")

        osgrid20_tcd = os.path.join(scratch, grid_name + "_TCD20.tif")
        osgrid5_tcd = os.path.join(os_grid_fold, grid_name + "_TCD.tif")

        del ras_template # Flush var
        transform_raster(tcd_cop, ras_exp_path, osgrid20_tcd, scratch, grid_name)
        resample_raster(osgrid20_tcd, osgrid5_tcd)

        # clear out scratch space
        print("clearing out scratch space")
        for the_file in os.listdir(scratch):
            file_path = os.path.join(scratch, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(e)


def transform_raster(tcd_cop, ras_exp_path, osgrid20_tcd, scratch, grid_name):
    print("Start transforming Raster")

    # Source
    print("retrieving vars for source file")
    src_filename = tcd_cop
    src = gdal.Open(src_filename, gdalconst.GA_ReadOnly)
    # src_proj = src.GetProjection()

    print("reclassifying TCD values > 100 as zero")
    src_band = src.GetRasterBand(1)
    src_data = BandReadAsArray(src_band)

    src_data[src_data > 100] = 0

    src_fix = os.path.join(scratch, grid_name + "_fix_tcd.tif")
    driver = gdal.GetDriverByName("GTiff")
    srcOut = driver.Create(src_fix, src.RasterXSize, src.RasterYSize, 1, src_band.DataType)

    CopyDatasetInfo(src, srcOut)
    bandOut = srcOut.GetRasterBand(1)
    BandWriteArray(bandOut, src_data)

    src_proj = srcOut.GetProjection()
    # Close the datasets
    src_band = None
    src_data = None
    bandOut = None
    src = None
    # src_dataOut = None


    # We want a section of source that matches this:
    print("retrieving vars for match file")
    match_filename = ras_exp_path
    match_ds = gdal.Open(match_filename, gdalconst.GA_ReadOnly)
    match_proj = match_ds.GetProjection()
    match_geotrans = match_ds.GetGeoTransform()
    wide = match_ds.RasterXSize
    high = match_ds.RasterYSize

    # Output / destination
    print("creating output raster driver")
    dst_filename = osgrid20_tcd
    dst = gdal.GetDriverByName('GTiff').Create(dst_filename, wide, high, 1, gdal.GDT_Int32, ['COMPRESS=LZW'])
    dst.SetGeoTransform(match_geotrans)
    dst.SetProjection(match_proj)

    # Do the work
    print("running raster transformation")
    gdal.ReprojectImage(srcOut, dst, src_proj, match_proj, gdalconst.GRA_Bilinear)

    del dst  # Flush
    del match_ds
    del srcOut


def resample_raster(osgrid20_tcd, osgrid5_tcd):
    print("resampling raster")
    with rasterio.open(osgrid20_tcd) as src:

        # adjust the new affine transform to the 150% smaller cell size
        aff = src.transform

        pixelSizeX = int(round(aff[0]))
        dst_cell_size = 5
        resize = pixelSizeX / dst_cell_size

        arr = src.read(1)
        print("setting up new array")
        newarr = np.empty(shape=(round(arr.shape[0] * resize),  # 400% resolution
                                 round(arr.shape[1] * resize)))

        print("setting up new affine params")
        newaff = Affine(aff.a / resize, aff.b, aff.c,
                        aff.d, aff.e / resize, aff.f)

        print("running reprojection with new cell size")
        reproject(arr,
                  newarr,
                  src_transform=aff,
                  dst_transform=newaff,
                  src_crs=src.crs,
                  dst_crs=src.crs,
                  resampling=Resampling.bilinear)

        # Assert that the destination is only partly filled.
        # assert newarr.any()
        # assert not newarr.all()

        newarr = newarr.astype(int)

        print("writing results to raster")
        with rasterio.open(
                osgrid5_tcd,
                'w',
                driver='GTiff',
                width=newarr.shape[0],
                height=newarr.shape[1],
                count=1,
                dtype=np.int32,
                #nodata=255,
                transform=newaff,
                crs=src.crs,
                compress='lzw') as dst:
            dst.write(newarr, indexes=1)

        src = None
        dst = None

# if __name__ == '__main__':
#     tcd_main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
