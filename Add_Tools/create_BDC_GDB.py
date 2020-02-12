import arcpy
from arcpy import env
import os
import sys
import glob


def main():
    print("running clean up script to create final BDC geodatabase")
    rename_for_HA = True
    # bdcParent = os.path.abspath("D:/Work/GB_Beaver_Data/EA_BDC")
    bdcParent = os.path.abspath("D:/HG_Work/GB_Beaver_Data/NRW_BDC_Out")
    # bdcParent = os.path.abspath("C:/Users/hughg/Desktop/Alan_BDC/BDC_Process")
    # ogdbName = "BDC_ALL_V2.gdb" # must include gdb extension if a gdb is required

    # ogdbName = "BDC_ALL_V3"

    ogdbName = "NRW_BDC_All_V2"

    symbologyLayer = os.path.join(bdcParent, "BDC_vis.lyrx")

    out_gdb = os.path.join(bdcParent, ogdbName)

    if ogdbName[-4:] == ".gdb":
        ext = ""
        if arcpy.Exists(out_gdb):
            print(" out geo database already exists... Delete")
            arcpy.Delete_management(out_gdb)
        else:
            arcpy.CreateFileGDB_management(bdcParent, ogdbName)
    else:
        ext = ".shp"

        if arcpy.Exists(out_gdb):
            print(" out file already exists... Do nothing for now")
            # arcpy.Delete_management(out_gdb)
        else:
            arcpy.CreateFolder_management(bdcParent, ogdbName)

    #
    #
    # if arcpy.Exists(out_gdb):
    #     print(" out geo database already exists... Do nothing for now")
    #     # arcpy.Delete_management(out_gdb)
    # else:
    #     arcpy.CreateFileGDB_management(bdcParent, ogdbName)

    file_search = os.path.join(bdcParent, "*/BDC_OC*/Output_BDC_OC*.shp")
    bdcs = glob.glob(file_search, recursive=True)

    print(bdcs)
    print(len(bdcs))

    print("copying all bdc files to new gdb")
    for file in bdcs:
        name = (file[-10:-4])
        outfc = os.path.join(out_gdb, name + ext)

        if arcpy.Exists(outfc):
            print("{0} bdc file exisits... pass".format(name))
            pass
        else:
            arcpy.CopyFeatures_management(file, outfc + ext)

    newbdc_list =[]
    walk = arcpy.da.Walk(out_gdb, datatype="FeatureClass", type="Polyline")
    for dirpath, dirnames, filenames in walk:
        for filename in filenames:
            newbdc_list.append(os.path.join(dirpath, filename))

    print(newbdc_list)

    keep_atts = ["BDC", "iHyd_SP2", "iHyd_SPLow", "iHyd_Q2", "iHyd_QLow", "oVC_EX", "reach_no", "iVeg_10EX",
                 "iVeg_100EX", "iGeo_DA", "iGeo_Width", "iGeo_Len", "iGeo_Slope", "Str_order", "catchmentN",
                 "watercou_1", "Shape_Length", "Shape", "OBJECTID", "FID"]

    for fc in newbdc_list:
        # field_list = arcpy.ListFields(fc)
        field_list = [f.name for f in arcpy.ListFields(fc)]
        print(field_list)
        for i in keep_atts:
            if i in field_list:
                field_list.remove(i)

        if len(field_list) >= 1:
            print("deleting unwanted fields")
            arcpy.DeleteField_management(fc, field_list)
        else:
            print("no fields to delete")

        checkFields = [f.name for f in arcpy.ListFields(fc)]
        print(checkFields)
        if rename_for_HA is True:
            newname = os.path.join(out_gdb, (os.path.basename(fc).replace('OC1', 'HA0')))

            arcpy.Rename_management(fc, newname)

        # arcpy.ApplySymbologyFromLayer_management(fc, symbologyLayer) # doesn't seem to do anything


if __name__ == '__main__':
    main()
