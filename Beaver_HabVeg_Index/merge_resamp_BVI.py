import rasterio
from rasterio.merge import merge
from rasterio.crs import CRS
from rasterio import Affine
from rasterio.warp import reproject, Resampling
import numpy as np
import arcpy

# from rasterio.plot import show
import os
import glob
from datetime import datetime
startTime = datetime.now()
# exp_f = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Res_v2")
# epsg_code = str(27700)

def mer_res_main(exp_f, epsg_code):
    arcpy.env.compression = "LZW"
    arcpy.env.overwriteOutput = True
    print(startTime)
    export_fold = os.path.join(exp_f, "A_BVI_merged")
    if os.path.exists(export_fold):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(export_fold)

    print("creating merged datasets")
    BVI_exten = "**/*_GB_BVI.tif"
    BHI_exten = "**/*_GB_BHI.tif"
    BHI200_exten = "**/*_BHI_200mQ3.tif"
    BVI200_exten = "**/*_BVI_200mQ3.tif"

    # BVI_out = os.path.join(export_fold, "BVI_merge.TIFF")
    # BHI_out = os.path.join(export_fold, "BHI_merge.TIFF")
    # BHI_out = "BHI_merge.tif"

    # BVI_out100m = os.path.join(export_fold, "BVI_merge100m.TIFF")
    bhi_200name = "BHI_200mQ3.tif"
    bvi_200name = "BVI_200mQ3.tif"
    # BHI_out200m = os.path.join(export_fold, bhi_200name)

    # BHI_out100m = os.path.join(export_fold, "BHI_merge100m.TIFF")
    bhi_1kmname = "BHI_1kmQ3.tif"
    BHI_out1km = os.path.join(export_fold, "BHI_1kmQ3V4.tif")
    bvi_1kmname = "BVI_1kmQ3.tif"
    BVI_out1km = os.path.join(export_fold, "BVI_1kmQ3V4.tif")

    twohun = 0.025
    onekm = 0.2

    print("resampling BHI to 200m 3rd Quartile")
    method1 = "Q3"
    # reproj_ras(twohun, int(epsg_code), exp_f, BHI_exten, bhi_200name, method1)  # for BHI turn off for testing
    print("resampling BVI to 200m 3rd Quartile")
    # reproj_ras(twohun, int(epsg_code), exp_f, BVI_exten, bvi_200name, method1)  # for BVI

    print("resampling BHI to 1km average value")
    method2 = "Average"
    # reproj_ras(onekm, int(epsg_code), exp_f, BHI200_exten, bhi_1kmname, method2)  # turn off for testing
    print("resampling BVI to 1km average value")
    # reproj_ras(onekm, int(epsg_code), exp_f, BVI200_exten, bvi_1kmname, method2)

    BVI_extenKM = "**/*" + bvi_1kmname
    BHI_extenKM = "**/*" + bhi_1kmname

    # print("merging BVI rasters")
    # run_merge(exp_f, BVI_extenKM, BVI_out1km, int(epsg_code))

    print("merging BHI rasters")
    # run_merge(exp_f, BHI_extenKM, BHI_out1km, int(epsg_code))
    print("merging BVI rasters")
    run_merge(exp_f, BVI_extenKM, BVI_out1km, int(epsg_code))

    # arcpy_merge(exp_f, BHI_exten, BHI_out, int(epsg_code), export_fold)

    # print("resampling BVI to 100m")
    # reproj_ras(BVI_out, onehun, int(epsg_code), BVI_out100m)


    # print("resampling BHI to 100m")
    # reproj_ras(BHI_out, onehun, int(epsg_code), BHI_out100m)


    print(datetime.now() - startTime)
    print("script finished")
# def arcpy_merge(exp_f, exten, out_ras, epsg, exp_fold):
#     print("merging rasters with arcpy")
#
#     print("get glob for BVI")
#     file_search = os.path.join(exp_f, exten)
#     rasters = glob.glob(file_search, recursive=True)
#
#     arcpy.MosaicToNewRaster_management(rasters, exp_fold, out_ras, number_of_bands=1)

def run_merge(exp_f, exten, out_ras, epsg):

    print("running raster merge...")

    print("get glob for BVI")
    file_search = os.path.join(exp_f, exten)
    rasters = glob.glob(file_search, recursive=True)

    print("loading files into rasterio")
    src_files_to_mosaic = []
    for fp in rasters:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)
    print("merging rasters")
    mosaic, out_trans = merge(src_files_to_mosaic)

    # show(mosaic, cmap='viridis')

    print("preparing output raster")
    out_meta = src.meta.copy()

    out_meta.update({"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
                     "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    print("exporting output raster")
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)


def reproj_ras(size, epsg, data_folder, extens, fname, method):

    print("get glob for BVI")
    file_search = os.path.join(data_folder, extens)
    rasters = glob.glob(file_search, recursive=True)

    for data in rasters:

        grid = data[(len(data_folder)+1):(len(data_folder)+3)]
        # print(grid)
        print("resampling {0}".format(grid))
        src = rasterio.open(data)
        arr = src.read()
        newarr = np.empty(shape=(arr.shape[0],  # same number of bands
                                 round(arr.shape[1] * size),  #
                                 round(arr.shape[2] * size)), dtype="float32")

        # adjust the new affine transform to the 150% smaller cell size
        aff = src.transform
        newaff = Affine(aff.a / size, aff.b, aff.c,
                        aff.d, aff.e / size, aff.f)

        if method == "Q3":
            reproject(
                arr, newarr,
                src_transform=aff,
                dst_transform=newaff,
                src_crs=src.crs,
                dst_crs=src.crs,
                resampling=Resampling.q3)
        else:
            reproject(
                arr, newarr,
                src_transform=aff,
                dst_transform=newaff,
                src_crs=src.crs,
                dst_crs=src.crs,
                resampling=Resampling.average)

        out_meta = src.meta.copy()

        out_meta.update({"driver": "GTiff", "height": newarr.shape[1], "width": newarr.shape[2], "transform": newaff,
                         "crs": CRS.from_epsg(epsg), "compress": "lzw", "dtype": "float32"})

        re_out_ras = os.path.join(data_folder, grid, grid + "_" + fname)
        print(re_out_ras)
        with rasterio.open(re_out_ras, "w", **out_meta) as dest:
            dest.write(newarr)


# if __name__ == '__main__':
#     mer_res_main(exp_f, epsg_code)