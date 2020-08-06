import sys
import os
import arcpy
# from arcpy.sa import *
from datetime import datetime

#start timer
startTime = datetime.now()
print(startTime)


def riv_merge_main():
    print("running water area buffer pre processing")

    # set up workspace
    epsg_code = 27700  # this is OSGB should be no need ot change

    out_root = os.path.abspath(
        "C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data")
    out_gdbName = "GB_rivers.gdb"
    outgdb = os.path.join(out_root, out_gdbName)
    out_fileName = "GB_rivers"
    out_file = os.path.join(outgdb, out_fileName)

    riv_line_fold = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")

    # root = os.path.abspath(
    #     "C:/Users/hughg/Desktop/GB_Beaver_modelling")
    # scratch_gdb = os.path.abspath(
    #     "C:/Users/hughg/Desktop/GB_Beaver_modelling/merge_rivs.gdb")  # sctatch workspace name no need to create.

    if arcpy.Exists(outgdb):
        print("scratch folder already exists..."
              "Delete folder manually - let's not accidentally delete stuff")
        sys.exit(1)
    else:
        print("create scratch folder")
        arcpy.CreateFileGDB_management(out_root, out_gdbName)


    #
    # if arcpy.Exists(scratch_gdb):
    #     print("scratch folder already exists")
    # else:
    #     print("create scratch folder")
    #     arcpy.CreateFileGDB_management(root, scratch_gdb[len(root):])


    arcpy.env.overwriteOutput = True
    arcpy.env.scratchWorkspace = outgdb
    # arcpy.Delete_management(r"in_memory")
    ref = arcpy.SpatialReference(epsg_code)
    arcpy.env.outputCoordinateSystem = ref

    merge_rivers(riv_line_fold, out_file)
    # arcpy.Delete_management(r"in_memory")

    print(datetime.now() - startTime)
    print("script finished")


def merge_rivers(riv_line_fold, out_file):
    print("begin file detection")
    direc_list = next(os.walk(riv_line_fold))[1]

    file_list = [riv_line_fold + "\\" + f for f in direc_list]
    print(file_list)

    merge_list = []

    for root in file_list:
        shp_test = os.listdir(root)
        for x in shp_test:
            if x[-4:] == '.shp':
                shp_file = os.path.join(root, x)
                merge_list.append(shp_file)

    # print(merge_list)
    merge_list_b = []
    for i in merge_list:
        desc = arcpy.Describe(i)
        what_shp = desc.shapeType
        if what_shp == 'Polyline':
            merge_list_b.append(i)

    # out_shp = os.path.join(scratch_gdb, "rivs_sofar2")
    print("running merge")
    print(merge_list_b)
    print(out_file)
    arcpy.Merge_management(merge_list_b, out_file)


if __name__ == '__main__':
    riv_merge_main()
