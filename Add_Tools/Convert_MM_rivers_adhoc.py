import os
import sys
import glob
import arcpy
from datetime import datetime
import multiprocessing
# from itertools import product
from functools import partial
import traceback
import shutil

class LicenseError(Exception):
    pass
try:
    if arcpy.CheckExtension("DataInteroperability") == "Available":
        arcpy.CheckOutExtension("DataInteroperability")
    else:
        # Raise a custom exception
        #
        raise LicenseError

except LicenseError:
    print("DataInteroperability license is unavailable")

arcpy.env.overwriteOutput = True
arcpy.env.scratchWorkspace = r"in_memory"
# arcpy.Delete_management(r"in_memory")
epsg_code = 27700
ref = arcpy.SpatialReference(epsg_code)
arcpy.env.outputCoordinateSystem = ref



# def MM_conv_main():
#     # start timer
#     startTime = datetime.now()
#     print(startTime)
#
#     arcpy.Delete_management(r"in_memory")
#
#
#     # riv_line_fold = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/MM_Rivers_gml")
#     # scratch = os.path.abspath(
#     #         "C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")
#
#     mphandler(riv_line_fold)
#     # run_MM_conv(riv_line_fold, scratch)
#
#     print(datetime.now() - startTime)
#     print("script finished")

def run_MM_conv(riv_line_fold, scratch, river_folders, ranges):

    pnt = str(multiprocessing.current_process().name)
    pnt2 = pnt.replace("-", "_")
    pn = pnt2.replace(":", "_")
    print(pn)

    print(ranges)
    # print(river_folders)

    # iterate over top folder containing OS regions
    if ranges[0] == 0:
        sliceObj = slice(ranges[0], ranges[1])
    else:
        sliceObj = slice(ranges[0] - 1, ranges[1])

    grid_list = river_folders[sliceObj] # turned off for testing
    print(grid_list)

    # grid_list = ['tf']
    print(river_folders)

    print(pn + " starting to loop folders")
    for fold in grid_list:
        # if fold in grid_list:
        if fold == 'tf': # for testing
            root = os.path.join(riv_line_fold, fold)
            shp_test = os.listdir(root)
            if any(x[-4:] == '.shp' for x in shp_test):

                print("Shape file already exists for OS GRID: {0}".format(fold))

            else:
                os.chdir(root)
                gml_list = []
                for file in glob.glob("*.gz"):
                    gml_list.append(file)

                gml_list_abs = [riv_line_fold + "\\" + fold + "\\" + s for s in gml_list]
                # print(gml_list)
                arcpy.CreateFileGDB_management(scratch, pn + "_Main.gdb")
                fold_gdb_path = os.path.join(scratch, pn + "_Main.gdb")

                river_lines = []

                for i in gml_list_abs:
                    # print(i)
                    marker = i[-13:-7]
                    # print(marker)
                    gml_gdb = arcpy.CreateFileGDB_management(scratch,  pn + "_tr.gdb")

                    gml_gdb_path = os.path.join(scratch, pn + "_tr.gdb")
                    # print(gml)

                    try:
                        print("try import OS GRID {0}".format(marker))
                        arcpy.QuickImport_interop(i, gml_gdb)  # This works.
                        print("OS GRID {0} imported". format(marker))
                        rivers_name = os.path.join(fold_gdb_path, marker)
                        #
                        mm_riv_ap = os.path.join(gml_gdb_path, "WatercourseLink")

                        #
                        if arcpy.Exists(mm_riv_ap):
                            arcpy.CopyFeatures_management(mm_riv_ap, rivers_name)
                            desc = arcpy.Describe(rivers_name)
                            what_shp = desc.shapeType
                            if what_shp == 'Polyline':
                                river_lines.append(rivers_name)

                            print(marker + " features copied to gdb")
                        else:
                            print("no features for " + marker)

                    except Exception as ex:  # this is naughty but it saves hiccups if there is an unforseen error...
                        print("OS GRID {0} import failed".format(marker))
                        print(ex)

                    # arcpy.Delete_management(gml_gdb)


                export_path = os.path.join(root, fold + "_mm_rivers2.shp")

                try:
                    print("merging data for OS GRID {0}".format(fold))
                    arcpy.Merge_management(river_lines, export_path)
                    print("data merged for {0}".format(fold))
                    # for i in river_lines:
                    #     arcpy.Delete_management(i)
                    #     print(i + " deleted from memory")

                except Exception as ex:
                    traceback.print_exc()
                    # print(e)
    if os.path.isdir(os.path.join(scratch, pn + "_Main.gdb")):
        shutil.rmtree(os.path.join(scratch, pn + "_Main.gdb"))
    if os.path.isdir(os.path.join(scratch, pn + "_tr.gdb")):
        shutil.rmtree(os.path.join(scratch, pn + "_tr.gdb"))
def MM_conv_main():
    # print(arcpy.GetActivePortalURL())
    # arcpy.SignInToPortal(arcpy.GetActivePortalURL(), "hg340_uoe", "1Airblunt1")

    # riv_line_fold = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")
    riv_line_fold = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")
    scratch = os.path.abspath(
        "C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/BVI_scratch")


    print("running multiprocess handler")
    startTime = datetime.now()
    print(startTime)


    river_folders = next(os.walk(riv_line_fold))[1]

    count = len(river_folders)

    print(river_folders)

    # result = arcpy.GetCount_management(inFc1)
    # count = int(result.getOutput(0))
    num_cores = multiprocessing.cpu_count() - 1
    print(num_cores)
    interval = int(round(count / num_cores))      # the size of the dataset and available RAM so change if errors occur

    ranges = []
    core_list = range(1, num_cores+1)
    start = [0, int(interval)]
    for i in core_list:
        # print(i)
        if i == 1:
            values = start
        elif i > 1 and i < num_cores:
            values = [(int(interval) * (i-1)) + 1, int(interval) * i]
        else:
            values = [(int(interval) * (i - 1)) + 1, int(count)]
        ranges.append(values)
    print(ranges)

    pool = multiprocessing.Pool()

    # pool.starmap(run_MM_conv, product(ranges, riv_line_fold, scratch, river_folders))

    func = partial(run_MM_conv, riv_line_fold, scratch, river_folders)
    pool.map(func, ranges)


    # pool.map(bratTableCreate, ranges)
    # pool.starmap(merge_names, product(names, repeat=2))

    # Synchronize the main process with the job processes to
    # Ensure proper cleanup.
    pool.close()
    pool.join()

    print(datetime.now() - startTime)
    print("script finished")




if __name__ == '__main__':
    #MM_conv_main(sys.argv[0], sys.argv[1])
    MM_conv_main()

