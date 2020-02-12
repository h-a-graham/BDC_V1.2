# Script to Copy final 5m BHI and BVI files to Gdb.
import arcpy
import os
import glob
from datetime import datetime
startTime = datetime.now()
# exp_f = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Res_v2")
# epsg_code = str(27700)

def exports_main(exp_f):
    arcpy.env.compression = "LZW"
    arcpy.env.overwriteOutput = True
    print(startTime)
    export_fold = os.path.join(exp_f, "BHI_BVI_merged")

    gdb_option = False
    if gdb_option is True:
        fileExt = ".gdb"
    else:
        fileExt = ""

    if os.path.exists(export_fold):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(export_fold)

    BHI_gdb = os.path.join(export_fold, "BHI_5m" + fileExt)
    if BHI_gdb[-4:] == ".gdb":
        bhi_file_ext = ""
        if arcpy.Exists(BHI_gdb):
            arcpy.Delete_management(BHI_gdb)
            arcpy.CreateFileGDB_management(export_fold, "BHI_5m")
        else:
            arcpy.CreateFileGDB_management(export_fold, "BHI_5m")
    else:
        bhi_file_ext = ".tif"
        if arcpy.Exists(BHI_gdb):
            arcpy.Delete_management(BHI_gdb)
            arcpy.CreateFolder_management(export_fold, "BHI_5m")
        else:
            arcpy.CreateFolder_management(export_fold, "BHI_5m")

    BVI_gdb = os.path.join(export_fold, "BVI_5m" + fileExt)
    if BVI_gdb[-4:] == ".gdb":
        bvi_file_ext = ""
        if arcpy.Exists(BVI_gdb):
            arcpy.Delete_management(BVI_gdb)
            arcpy.CreateFileGDB_management(export_fold, "BVI_5m")
        else:
            arcpy.CreateFileGDB_management(export_fold, "BVI_5m")
    else:
        bvi_file_ext = ".tif"
        if arcpy.Exists(BVI_gdb):
            arcpy.Delete_management(BVI_gdb)
            arcpy.CreateFolder_management(export_fold, "BVI_5m")
        else:
            arcpy.CreateFolder_management(export_fold, "BVI_5m")
    BVI_exten = "**/*_GB_BVI.tif"
    BHI_exten = "**/*_GB_BHI.tif"
    # BVI_out1km = "BVI_merge1km.tif"
    # BHI_out1km = "BHI_merge1km.tif"

    collect_HR_data(exp_f, BHI_exten, BHI_gdb, bhi_file_ext)
    collect_HR_data(exp_f, BVI_exten, BVI_gdb, bvi_file_ext)

def collect_HR_data(exp_f, exten, file_gdb, fext):
    print("collecting all high res data in gdb")

    print("get glob")
    file_search = os.path.join(exp_f, exten)
    rasters = glob.glob(file_search, recursive=True)

    for file in rasters:
        name = file[-13:-4]
        print("Copying Raster for {0}".format(name))
        outName = os.path.join(file_gdb, name)
        try:
            arcpy.CopyRaster_management(file, outName + fext)
        except Exception as e:
            print(e)

#     arcpy_merge(km_out, export_fold, file_gdb)
#
#
#
# def arcpy_merge(out_ras, exp_fold, workspace):
#     print("merging rasters with arcpy")
#     arcpy.env.workspace = workspace
#
#     # Get and print a list of GRIDs from the workspace
#     rasters = arcpy.ListRasters("*", "ALL")
#
#     arcpy.MosaicToNewRaster_management(rasters, exp_fold, out_ras, number_of_bands=1,
#                                        cellsize=1000, mosaic_method="MEAN")

