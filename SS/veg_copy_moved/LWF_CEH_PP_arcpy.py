## I think this finally works...

import os
import sys
import arcpy
from arcpy.sa import *
from datetime import datetime

#start timer
startTime = datetime.now()


def lwf_main(epsg_code, file_loc, OrdSurv_Grid, exports, scratch):
    print(startTime)
    print("running linear Woody Features pre processing")
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
    # set up workspace
    # epsg_code = 27700  # this is OSGB should be no need ot change

    # file_loc = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/GB_WLF_V1_0.gdb/GB_WLF_V1_0")

    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")


    # exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/CEH_LWF_export")  # export location
    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    arcpy.env.overwriteOutput = True
    arcpy.env.scratchWorkspace = scratch_gdb
    arcpy.Delete_management(r"in_memory")
    ref = arcpy.SpatialReference(int(epsg_code))
    arcpy.env.outputCoordinateSystem = ref
    arcpy.env.compression = "LZW"
    arcpy.env.parallelProcessingFactor = "150%"

    # lwf_check_proj(file_loc, exports, scratch_gdb, int(epsg_code))

    lwf_process(OrdSurv_Grid, file_loc, exports, scratch_gdb)

    print("reclassification done")
    arcpy.Delete_management(r"in_memory")
    # arcpy.Delete_management(scratch_gdb)
    print(datetime.now() - startTime)
    print("script finished")
# def lwf_check_proj(file_loc, exports, scratch_gdb, epsg):
#     print("checking coordinate system for LWF data")
#     orig_desc = arcpy.Describe(file_loc)
#     orig_ref = orig_desc.spatialReference.factoryCode
#     print(orig_ref)

def lwf_process(OrdSurv_Grid, file_loc, exports, scratch_gdb):

    print("selecting the relevant area to clip")



    ord_grid_fl = arcpy.MakeFeatureLayer_management(OrdSurv_Grid, "lay_selec", "", r"in_memory")


    with arcpy.da.SearchCursor(ord_grid_fl, ["GRIDSQ"]) as cursor:
        for row in cursor:
            # if row[0] == 'SX':
            arcpy.env.extent = 'MINOF'
            grid_area = row[0]
            print(grid_area)

            os_grid_fold = os.path.join(exports, grid_area.lower())
            if os.path.exists(os_grid_fold):
                print("OS Grid folder already exists")
            else:
                print("create OS Grid folder folder")
                os.makedirs(os_grid_fold)

            print('select features within Ordnance Survey grid area')
            # expr = ('GRIDSQ = {0}'.format(row[0]))
            expr = """{0} = '{1}'""".format('GRIDSQ', row[0])
            print(expr)

            arcpy.SelectLayerByAttribute_management(ord_grid_fl,
                                                    "NEW_SELECTION",
                                                    expr)
            temp_zone =  r"in_memory/OS_tempZone"
            OS_clip = arcpy.CopyFeatures_management(ord_grid_fl, temp_zone)

            work_area = arcpy.Describe(OS_clip)
            work_ext = work_area.extent
            arcpy.env.extent = work_ext

            # clip_file = r"in_memory/lwf_clip"
            clip_file = os.path.join(scratch_gdb, "lwf_clip")
            print("clipping features to Grid area")
            arcpy.Clip_analysis(file_loc, OS_clip, clip_file, cluster_tolerance=0)
            obj_len = int(str(arcpy.GetCount_management(clip_file)))
            # print(obj_len)
            if obj_len > 0:

                arcpy.AddField_management(clip_file, field_name='BVI_Val', field_type='SHORT')
                cursor2 = arcpy.da.UpdateCursor(clip_file, ['BVI_Val'])
                for row2 in cursor2:
                    row2[0] = 4
                    cursor2.updateRow(row2)

                print("creating snap raster")
                # temp_ras = r"in_memory/temp_ras"
                temp_ras = os.path.join(scratch_gdb, "temp_ras")
                arcpy.PolygonToRaster_conversion(in_features=OS_clip, value_field='GRIDSQ',
                                                 out_rasterdataset=temp_ras, cell_assignment="CELL_CENTER", cellsize=5)
                work_area = arcpy.Describe(temp_ras)
                work_ext = work_area.extent
                arcpy.env.extent = work_ext

                arcpy.env.cellsize = temp_ras
                arcpy.env.snapRaster = temp_ras

                # lwf_out_tmp = r"in_memory/lwf_ras_tmp"
                lwf_out_tmp = os.path.join(scratch_gdb, "lwf_ras_tmp")

                print("converting features to raster")
                arcpy.FeatureToRaster_conversion(clip_file, "BVI_Val", lwf_out_tmp, 5)

                lwf_out = os.path.join(os_grid_fold, grid_area + '_lwf_ras.tif')

                print("converting null to zero")
                # arcpy.env.extent = 'MAXOF'
                lwf_ras = Con(IsNull(lwf_out_tmp), 0, lwf_out_tmp)
                # lwf_ras = Con(IsNull(lwf_out_tmp),0,Con((Raster(lwf_out_tmp) > Raster(temp_ras)), Raster(lwf_out_tmp), 0)) # try this is might solve things...
                lwf_ras.save(lwf_out)

                arcpy.Delete_management(r"in_memory")
                arcpy.ClearEnvironment("extent")
                arcpy.ClearEnvironment("snapRaster")
                arcpy.ClearEnvironment("cellsize")
            else:
                print("no features in OS GRID {0}".format(grid_area))

# if __name__ == '__main__':
#     lwf_main(sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3])