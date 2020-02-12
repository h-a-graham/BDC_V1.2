
import os
import arcpy
import multiprocessing
from arcpy.sa import *
from datetime import datetime

#start timer
startTime = datetime.now()
print(startTime)

def riv_area_main():
    print("running water area buffer pre processing")
    buff_size = 100  # Set this value up front therefore enabling adjustment later if required.
    # set up workspace
    epsg_code = 27700  # this is OSGB should be no need ot change

    riv_line_fold = os.path.abspath("D:/GB_Beaver_Data/Edina/exu-hg-vml-3/mastermap-water/2018_10/gml")


    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")

    scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace name no need to create.

    if os.path.exists(scratch):
        print("scratch folder already exists")
    else:
        print("create scratch folder")
        os.makedirs(scratch)

    exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/CEH_LWF_export")  # export location
    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    arcpy.env.overwriteOutput = True
    arcpy.env.scratchWorkspace = r"in_memory"
    arcpy.Delete_management(r"in_memory")
    ref = arcpy.SpatialReference(epsg_code)
    arcpy.env.outputCoordinateSystem = ref

    # buff_water_area(exports, buff_size)
    mphandler(OrdSurv_Grid, riv_line_fold, exports, scratch, buff_size)

    # buff_lines(OrdSurv_Grid, riv_line_fold, exports, scratch, buff_size)

    print("reclassification done")
    arcpy.Delete_management(r"in_memory")

    print(datetime.now() - startTime)
    print("script finished")

def sort_lines(riv_line_fold, scratch, buff_size,ranges, river_folders):

    print("selecting the relevant area to clip")

    river_folders = next(os.walk(riv_line_fold))[1]

    print(river_folders)

    # iterate over top folder containing OS regions
    print("start looping folders")
    for fold in river_folders:
        if fold == 'nn':
            print('importing and merging river lines for OS Grid {0}'.format(fold))

            gml_list = os.listdir(os.path.join(riv_line_fold, fold))
            gml_list_abs = [riv_line_fold + "\\" + fold + "\\" + s for s in gml_list]

            gml_files = riv_line_fold + "\\" + fold + "\\" + "*.gz"

            shapes_list = []

            # for gml in gml_list_abs:
            gml_gdb = arcpy.CreateFileGDB_management(scratch, "temp_rivers.gdb") # turned off for now TURN ON AFTER TESTING
            gml_gdb_path = os.path.join(scratch, "temp_rivers.gdb")
            # print(gml)
            print("running quick import")
            arcpy.QuickImport_interop(gml_files, gml_gdb)  # This works.

            print("skipped import use one created already")
            rivers_name = r"in_memory/rivers_" + fold

            river_lines = os.path.join(gml_gdb_path, "WatercourseLink")

            if arcpy.Exists(river_lines):
                print("copy features to in memory")

                arcpy.CopyFeatures_management(river_lines, rivers_name)

                rivers_buffer = os.path.join(gml_gdb_path, "testBuff_rivers") #change to in memory???

                print("buffering")

                arcpy.Buffer_analysis(rivers_name, rivers_buffer, buff_size)
            else:
                pass
            print(shapes_list)


def mphandler(OrdSurv_Grid, riv_line_fold, exports, scratch, buff_size):
    print ("new_home_folder")
    # if arcpy.Exists(home):
    #     arcpy.Delete_management(home)
    # arcpy.CreateFolder_management(path, home_name)

    # import arcpy
    # startTime = datetime.now()
    # print (startTime)
    #######
    # inFc1 = home + "/inFc.shp"
    # arcpy.CopyFeatures_management(seg_network_b, inFc1)
    #
    # network_fields = [f.name for f in arcpy.ListFields(inFc1)]
    # if "OBJECTID" in network_fields:
    #     arcpy.DeleteField_management(inFc1, "OBJECTID")
    # if "OID" in network_fields:
    #     arcpy.DeleteField_management(inFc1, "OID")

    river_folders = next(os.walk(riv_line_fold))[1]

    count = len(river_folders)

    print(river_folders)

    # result = arcpy.GetCount_management(inFc1)
    # count = int(result.getOutput(0))
    num_cores =  multiprocessing.cpu_count()  # this can be automated but the number of processes is also related to
    interval = int(round(count / num_cores))      # the size of the dataset and available RAM so change if errors occur

    #### 4 CORES #####
    if num_cores <= 4:
        ranges = [[0, int(interval)],
                  [int(interval) + 1, int(interval) * 2],
                  [(int(interval) * 2) + 1, int(interval) * 3],
                  [(int(interval) * 3) + 1, int(count)]]
    #### 5 CORES ####
    if num_cores == 5:
        ranges = [[0, int(interval)],
                  [int(interval) + 1, int(interval) * 2],
                  [(int(interval) * 2) + 1, int(interval) * 3],
                  [(int(interval) * 3) + 1, int(interval) * 4],
                  [(int(interval) * 4) + 1, int(count)]]
    #### 6 CORES ####
    if num_cores == 6:
        ranges = [[0, int(interval)],
                  [int(interval) + 1, int(interval) * 2],
                  [(int(interval) * 2) + 1, int(interval) * 3],
                  [(int(interval) * 3) + 1, int(interval) * 4],
                  [(int(interval) * 4) + 1, int(interval) * 5],
                  [(int(interval) * 5) + 1, int(count)]]

    #### 7 CORES ####
    if num_cores == 7:
        ranges = [[0, int(interval)],
                  [int(interval) + 1, int(interval) * 2],
                  [(int(interval) * 2) + 1, int(interval) * 3],
                  [(int(interval) * 3) + 1, int(interval) * 4],
                  [(int(interval) * 4) + 1, int(interval) * 5],
                  [(int(interval) * 5) + 1, int(interval) * 6],
                  [(int(interval) * 6) + 1, int(count)]]

    #### 8 CORES ####
    if num_cores >= 8:
        ranges = [[0, int(interval)],
                  [int(interval) + 1, int(interval) * 2],
                  [(int(interval) * 2) + 1, int(interval) * 3],
                  [(int(interval) * 3) + 1, int(interval) * 4],
                  [(int(interval) * 4) + 1, int(interval) * 5],
                  [(int(interval) * 5) + 1, int(interval) * 6],
                  [(int(interval) * 6) + 1, int(interval) * 7],
                  [(int(interval) * 7) + 1, int(count)]]
    else:
        ranges = None  # lazy but again not possible to reach
    print(ranges)

    pool = multiprocessing.Pool()

    pool.map(sort_lines, ranges)
    # pool.map(bratTableCreate, ranges)


    # Synchronize the main process with the job processes to
    # Ensure proper cleanup.
    pool.close()
    pool.join()



if __name__ == '__main__':
    riv_area_main()


# Geopandas version not working:


# for i in gml_list_abs:
#     # print(i)
#     try:
#         mm_riv_gp = gpd.read_file(i, driver='GML')
#         print(len(mm_riv_gp))
#         if mm_riv_gp.geom_type[0] == 'Point':
#             print("geom type is point")
#         else:
#             print("NOT A POINT")
#         river_lines.append(mm_riv_gp)
#     except ValueError:
#         print("Something went wrong NO WORRIES")
# # print(river_lines)
#
# merge = gpd.GeoDataFrame( pd.concat( river_lines, ignore_index=True) )
#
# export_path = os.path.join(scratch, "gp_tesp.shp")
# merge.to_file(export_path, driver="ESRI Shapefile")