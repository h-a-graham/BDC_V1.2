# -------------------------------------------------------------------------------
# Name:        Parallel Split river/stream network into reaches
# Purpose:     Creates discrete reaches from a river network with a max length of x
#
# Author:      Hugh Graham
#
# -------------------------------------------------------------------------------
import glob
import multiprocessing
import arcpy, os
from arcpy import env
import time
from datetime import datetime
import sys
from functools import partial
import gc
import shutil

env.overwriteOutput = True

#################################################################
#################### START SPLIT FUNCTION ######################
################################################################


def Split_function(home, dist, ranges):

    gc.enable()

    inFc1 = home + "/inFc.shp"

    process_name = multiprocessing.current_process().name
    print (process_name)
    process_name2 = str(process_name)
    process_name3 = process_name2.replace("-", "_")
    outPath = home
    outName = ("pro_f_" + process_name3)

    # new_folder1 = arcpy.CreateFolder_management(outPath, outName)
    new_folder1 = arcpy.CreateFileGDB_management(outPath, outName)
    new_folder2 = str(new_folder1)
    new_folder = new_folder2.replace("\\","/")
    print(new_folder)

    time.sleep(5)

    arcpy.env.workspace = new_folder

    i, j = ranges[0], ranges[1]

    # print (i, j)

    # print ("A")
    flayer = arcpy.MakeFeatureLayer_management(inFc1, "fl")
    # print ("B")
    arcpy.SelectLayerByAttribute_management(flayer, "NEW_SELECTION", '"FID" >={0} AND "FID" <={1}'.format(i,j))
    # print ("C")

    inFl = arcpy.MakeFeatureLayer_management(flayer,'layer{0}'.format(i))

    # print ("E")
    arcpy.CopyFeatures_management(inFl, new_folder + "/work_area")

    inFc = new_folder + "/work_area"

    # print ("F")

    # arcpy.DeleteFeatures_management(flayer)
    # print ("G")

    num_rows = arcpy.GetCount_management(inFc)
    row_count = int(num_rows.getOutput(0))
    print(row_count)


    print ("determining spatial reference info")
    # Get spatial reference object
    sr = arcpy.Describe(inFc).spatialReference
    # meters conversion
    metersPerUnit = sr.metersPerUnit
    # Distance in feature class units
    checkDistance = dist / metersPerUnit
    print ("max distance:", checkDistance)


    print ("creating output feature class")
    # Create out feature class
    outPath = new_folder
    # outName = process_name3 +"out_fc.shp"
    outName = process_name3 + "out_fc"
    # try:
    outFc = arcpy.CreateFeatureclass_management(outPath, outName, "POLYLINE", inFc, spatial_reference=sr)


    # except Exception:
    #     e = sys.exc_info()[1]
    #     print(e.args[0])
    #     pass
    # set workspace
    arcpy.env.workspace = outPath
    # arcpy.env.scratchworkspace = r"in_memory"

    # list with geometry field
    fields = ["SHAPE@"]

    # Add feature class fields to list
    fields += [f.name for f in arcpy.ListFields(inFc)]

    # Get objectid field name
    oidFld = arcpy.Describe(inFc).OIDFieldName

    # Remove oid field from fields list
    fields.remove(oidFld)

    # empty list to have rows appended to
    rows = []

    print("iterating", arcpy.GetCount_management(inFc).getOutput(0), "rows")
    i = 0
    # cursor to iterate feature class
    with arcpy.da.SearchCursor(inFc, fields) as cursor:
        # iterate rows
        # try:  #####TESTING THIS AS A FAILSAFE...
        for row in cursor:
            # arcpy.Delete_management(r"in_memory")
            i += 1
            # get geometry object
            geometry = row[0]

            # get length
            length = geometry.length

            # check if length longer than limit
            if length > checkDistance:
                print("row", i)
                print("line length:", length)

                # empty list for intermediate data to be deleted
                garbage = []

                # create empty line fc for single feature
                # split = arcpy.CreateUniqueName("split_.shp")
                split = arcpy.CreateUniqueName("split_")
                outPath = os.path.dirname(split)
                outName = os.path.basename(split)
                arcpy.CreateFeatureclass_management(outPath, outName, "POLYLINE", inFc, spatial_reference=sr)

                # insert feature in new fc
                with arcpy.da.InsertCursor(split, fields) as cur1:
                    cur1.insertRow(row)
                # del cur
                # add new fc to garbage
                garbage += [split]

                # create empty point fc for single feature
                # midPnt = arcpy.CreateUniqueName("point_.shp")
                midPnt = arcpy.CreateUniqueName("point_")
                outPath = os.path.dirname(midPnt)
                outName = os.path.basename(midPnt)
                arcpy.CreateFeatureclass_management(outPath, outName, "POINT", spatial_reference=sr)
                # Get midpoint
                pnt = geometry.positionAlongLine(.5, True)
                # insert point into new feature class
                with arcpy.da.InsertCursor(midPnt, "SHAPE@") as cur2:
                    cur2.insertRow((pnt,))
                # del cur
                # add new fc to garbage
                garbage += [midPnt]


                # loop while length is greater than limit
                while length > checkDistance:

                    # Split line at (mid)point
                    # newSplit = arcpy.CreateUniqueName("split_.shp")
                    newSplit = arcpy.CreateUniqueName("split_")
                    garbage += [newSplit]
                    arcpy.SplitLineAtPoint_management(split, midPnt, newSplit)

                    # Create new mid points
                    # midPnt = arcpy.CreateUniqueName("point_.shp")
                    midPnt = arcpy.CreateUniqueName("point_")
                    garbage += [midPnt]
                    outPath = os.path.dirname(midPnt)
                    outName = os.path.basename(midPnt)
                    arcpy.CreateFeatureclass_management(outPath, outName, "POINT", spatial_reference=sr)

                    # empty list for new points
                    pnts = []

                    # iterate split line and get midpoints
                    with arcpy.da.SearchCursor(newSplit, "SHAPE@") as cur3:
                        for geom, in cur3:
                            pnt = geom.positionAlongLine(.5, True)
                            pnts += [pnt]
                    # del cur

                    # add midpoints to midpoint feature class
                    with arcpy.da.InsertCursor(midPnt, "SHAPE@") as cur4:
                        for pnt in pnts:
                            cur4.insertRow((pnt,))
                    # del cur

                    # divide length variable by two
                    length = length / 2
                    print("line length:", length)

                    split = newSplit
                # rows = []
                with arcpy.da.SearchCursor(split, fields) as cursorb: # testing this with statement rather than the below
                    for rowb in cursorb:
                        rows += [rowb]
                # rows += [row for row in arcpy.da.SearchCursor(split, fields)] # could this be the source of the mem leak?

                # clean up intermediate data
                for trash in garbage:
                    arcpy.Delete_management(trash)
                # del garbage



            else:
                rows += [row]

        # except Exception as e:  # PART OF FAILSAFE
        #     print(e)

    # del cursor variable
    # del cursor

    print ("inserting rows into new feature class")
    # insert cursor new feature class with rows
    with arcpy.da.InsertCursor(outFc, fields) as cursor2:
        for r in rows:
            cursor2.insertRow(r)

    obj_list = ('garbage', 'trash', 'rows', 'row', 'split', 'newSplit', 'midPnt', 'cur1', 'cur2', 'cur3', 'cur4',
                'cursor', 'cursor2', 'pnts', 'pnt', 'cursorb', 'rowb')
    for obj in obj_list:
        if obj in locals() or obj in globals():
            del obj
    gc.collect()
    # del cursor


    print("created:", outFc)

    fin_fc = home + "/" + process_name3 + "_out.shp"
    arcpy.CopyFeatures_management(outFc, fin_fc)
    print("done")


def mphandler(home, main_Fc):
    # consider adding something to check for old chunk_x.shp files
    dist = 200    # Defines the maximum allowable reach length in meters
    num_cores = multiprocessing.cpu_count()  # this is automated but consider reducing/increasing if errors occur
    print("number of cores = {0}".format(num_cores))
    # import arcpy
    startTime = datetime.now()
    # print (startTime)
    #######
    inFc1 = home + "/inFc.shp"


    if arcpy.Exists(inFc1):
        print("copy of original already exists")
    else:
        print("making copy of original features")
        arcpy.CopyFeatures_management(main_Fc, inFc1)

    network_fields = [f.name for f in arcpy.ListFields(inFc1)]
    if "OBJECTID" in network_fields:
        arcpy.DeleteField_management(inFc1, "OBJECTID")
    if "OID" in network_fields:
        arcpy.DeleteField_management(inFc1, "OID")

    n_feat = int(arcpy.GetCount_management(inFc1)[0])
    # n_feat = int(n_feat.getOutput(0))
    lim = 500
    if n_feat > lim:
        print("large river network submitted ({0} rows) - run chunked workflow".format(n_feat))

        n_chunks = round(n_feat/lim)
        chunk_size = round(n_feat/n_chunks)

        chunk_ranges = []
        chunk_list = range(1, n_chunks + 1)
        start = [0, int(chunk_size)]
        for i in chunk_list:
            # print(i)
            if i == 1:
                values = start
            # elif i > 1 and i < n_chunks:
            elif n_chunks > i > 1:
                values = [(int(chunk_size) * (i - 1)) + 1, int(chunk_size) * i]
            else:
                values = [(int(chunk_size) * (i - 1)) + 1, int(n_feat)]
            chunk_ranges.append(values)

        print(chunk_ranges)

        counter = 0
        for i in chunk_ranges:
            gc.collect()
            arcpy.Delete_management("in_memory")
            counter += 1
            print("Running line split tool for chunk {0}/{1}".format(counter, n_chunks))

            chunk_folder = os.path.join(home, "chunk_{0}".format(counter))
            if os.path.isdir(chunk_folder):
                try:
                    shutil.rmtree(chunk_folder)
                except Exception as e:
                    print(e)
            os.makedirs(chunk_folder)

            s, e = i[0], i[1]

            # print(s,e)

            cflayer = arcpy.MakeFeatureLayer_management(inFc1, "fl")

            arcpy.SelectLayerByAttribute_management(cflayer, "NEW_SELECTION",
                                                    '"FID" >={0} AND "FID" <={1}'.format(s, e))

            inCFl = arcpy.MakeFeatureLayer_management(cflayer, r'in_memory/chunk{0}'.format(counter))

            arcpy.CopyFeatures_management(inCFl, chunk_folder + "/inFc.shp")

            inCFc = os.path.join(chunk_folder, "inFc.shp")

            try:
                arcpy.Delete_management(inCFl)
            except Exception as e:
                print(e)

            chunk_n = int(arcpy.GetCount_management(inCFc)[0])
            interval = int(
                round(chunk_n / num_cores))  # the size of the dataset and available RAM so change if errors occur

            ranges = []
            core_list = range(1, num_cores + 1)
            start = [0, int(interval)]
            for x in core_list:
                # print(i)
                if x == 1:
                    values = start
                elif num_cores > x > 1:
                    values = [(int(interval) * (x - 1)) + 1, int(interval) * x]
                else:
                    values = [(int(interval) * (x - 1)) + 1, int(chunk_n)]
                ranges.append(values)

            print(ranges)

            pool = multiprocessing.Pool()

            func = partial(Split_function, chunk_folder, dist)
            pool.map(func, ranges)

            # Synchronize the main process with the job processes to
            # Ensure proper cleanup.
            pool.close()
            pool.join()

            file_search = os.path.join(chunk_folder, "*out.shp")
            shp_list = glob.glob(file_search)

            # fc_list = arcpy.ListFeatureClasses()

            merged_lines = chunk_folder + "/BDC_reaches.shp"

            arcpy.Merge_management(shp_list, merged_lines)

            chunk_out = os.path.join(home, "chunk_{0}_out.shp".format(counter))

            arcpy.CopyFeatures_management(merged_lines, chunk_out)

            if os.path.isdir(chunk_folder):
                try:
                    shutil.rmtree(chunk_folder)
                except Exception as e:
                    print(e)





    else:
        print("small river network submitted ({0} rows) - run single chunk".format(n_feat[0]))

        interval = int(round(n_feat / num_cores))  # the size of the dataset and available RAM so change if errors occur

        ranges = []
        core_list = range(1, num_cores + 1)
        start = [0, int(interval)]
        for i in core_list:
            # print(i)
            if i == 1:
                values = start
            elif num_cores > i > 1:
                values = [(int(interval) * (i - 1)) + 1, int(interval) * i]
            else:
                values = [(int(interval) * (i - 1)) + 1, int(n_feat)]
            ranges.append(values)

        print(ranges)

        pool = multiprocessing.Pool()

        func = partial(Split_function, home, dist)
        pool.map(func, ranges)


        # Synchronize the main process with the job processes to
        # Ensure proper cleanup.
        pool.close()
        pool.join()

    arcpy.Delete_management(inFc1)
    arcpy.env.workspace = home
    gdb_list = arcpy.ListWorkspaces(workspace_type="FileGDB")
    for gdb in gdb_list:
        if arcpy.Exists(gdb):
            arcpy.Delete_management(gdb)



    file_search = os.path.join(home, "*out.shp")
    shp_list = glob.glob(file_search)

    # fc_list = arcpy.ListFeatureClasses()

    merged_lines = home + "/BDC_reaches.shp"

    arcpy.Merge_management(shp_list, merged_lines)

    for fc in shp_list:
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)


    print("running reach length check.")
    ml_fields = [f.name for f in arcpy.ListFields(merged_lines)]

    if "reach_len" in ml_fields:
        print("field reach_len already exists - deleting")
        arcpy.DeleteField_management(merged_lines, 'reach_len')
    arcpy.AddField_management(merged_lines, 'reach_len', "DOUBLE")
    with arcpy.da.UpdateCursor(merged_lines, ["SHAPE@", "reach_len"]) as cursor:
        for row in cursor:
            row[1] = row[0].getLength('PLANAR', 'METERS')
            cursor.updateRow(row)

    with arcpy.da.SearchCursor(merged_lines, ["reach_len"]) as cursor:
        max_len = (max(cursor))[0]
        if max_len > dist:
            print("some lines still > target - running with new lines")
            mphandler(home, merged_lines)
        else:
            print("All reaches < than target value! Woop!")


    print(datetime.now() - startTime)
    print("output is ready")
    # End main


if __name__ == '__main__':
    mphandler(sys.argv[1],
              sys.argv[2])

