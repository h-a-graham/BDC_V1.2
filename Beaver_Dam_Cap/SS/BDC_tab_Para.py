# -------------------------------------------------------------------------------
# Name:        Parallel Beaver Dam Capacity Table
# Purpose:     Builds the initial table to run through the BRAT tools
#
# Author:      Hugh Graham & Jordan Gilbert
#
# -------------------------------------------------------------------------------

##############################################
########## IMPORTS ##########################
#############################################
from arcpy.sa import *
import multiprocessing
from functools import partial
import arcpy
import time
from datetime import datetime
import numpy as np
import os
import sys

############# START TIME ##############
startTime = datetime.now()

##### Otter ######

def main(path, scratch_gdb, seg_network_a, DEM_orig, in_water_vec_a, coded_vega):

    arcpy.env.overwriteOutput = True
    arcpy.CheckOutExtension("spatial")
    arcpy.env.scratchworkspace = r"in_memory" #scratch_gdb

    print(startTime)

    home_name = "BDC_OC{0}".format(path[-4:])  # REQUIRED - name of home working directory to be created
    home = os.path.join(path, home_name)  # Don't Edit
    outname = "Output_BDC_OC{0}.shp".format(path[-4:])  # REQUIRED - output file name -  must end in .shp


    print("Run Stream Burn Process")

    stream_burn_dem, net_raster = streamBurning(DEM_orig, scratch_gdb, seg_network_a)

    print("Run Flow Accumulation / Drainage area raster Process")

    DrAreaPath, FlowDir = calc_drain_area(stream_burn_dem, scratch_gdb, DEM_orig)

    print("Run Stream Order Polygon Generation")

    seg_network_b = get_stream_order(scratch_gdb, stream_burn_dem, seg_network_a, DEM_orig, FlowDir, net_raster)

    print("Run BDC variable extraction process (in parallel)")
    mphandler(home, in_water_vec_a, DEM_orig, DrAreaPath, coded_vega, path, home_name, seg_network_b, outname)

    finTime = datetime.now() - startTime
    print("BDC table script completed. \n"
          "Processing time = {0}".format(finTime))


################################################################################################
###################### NOW TIME FOR STREAM BURNING ###############################
################################################################################################

def streamBurning(DEM_orig, scratch_gdb, seg_network_a):
    print ("stream burning process")
    arcpy.CalculateStatistics_management(DEM_orig)

    dem_orig_b = Con(IsNull(DEM_orig), 0, DEM_orig)
    dem_orig_b.save(scratch_gdb + "/DEM_square")

    # set up river network raster
    network_raster = scratch_gdb + "/network_raster"

    arcpy.env.extent = dem_orig_b
    arcpy.env.cellsize = dem_orig_b
    arcpy.env.snapRaster = dem_orig_b
    arcpy.env.outputCoordinateSystem = dem_orig_b

    print('convert network to raster')
    net_fields = [f.name for f in arcpy.ListFields(seg_network_a)]
    if "burn_val" in net_fields:
        arcpy.DeleteField_management(seg_network_a, "burn_val")
    del net_fields
    arcpy.AddField_management(seg_network_a, "burn_val", "SHORT")
    arcpy.CalculateField_management(seg_network_a, "burn_val", "10") #

    arcpy.FeatureToRaster_conversion(seg_network_a, "burn_val", network_raster,
                                     dem_orig_b)  # THINK IT IS WORTH CHANGING THE ATTRIBUTE VALUE

    network_raster_a = Con(IsNull(network_raster), 0, 30)  # changed to 30 to see if it improves stream ordering
    network_raster_a.save(scratch_gdb + "/net_ras_fin")
    arcpy.ResetEnvironments()

    # This is just a map algebra thing to replace the stuff above that uses numpy (the numpy stuff works but is
    # limited in terms of how much it can process.
    print("stream burning DEM")
    rivers_ting = Raster(scratch_gdb + "/net_ras_fin")
    dem_ting = Raster(scratch_gdb + "/DEM_square")

    stream_burn_dem_a = dem_ting - rivers_ting
    stream_burn_dem_a.save(scratch_gdb + "/raster_burn")

    print("stream burning complete")
    return stream_burn_dem_a, network_raster


############################################################################################
###################### Drainage area calcs ##################################################
############################################################################################

def calc_drain_area(stream_burn_dem, scratch_gdb, DEM_orig):

    print("running drainage area calc process")
    DEMdesc = arcpy.Describe(stream_burn_dem)
    height = DEMdesc.meanCellHeight
    width = DEMdesc.meanCellWidth
    res = height * width
    resolution = int(res)

    # derive a flow accumulation raster from input DEM and covert to units of square kilometers
    print ("filling sinks in DEM")
    filled_DEM = Fill(stream_burn_dem, "")
    filled_DEM.save(scratch_gdb + "/fill_dem")
    print ("running flow direction raster")
    flow_direction = FlowDirection(filled_DEM, "NORMAL", "")
    flow_direction.save(scratch_gdb + "/flow_dir")
    print ("running flow accumulation raster")
    flow_accumulation = FlowAccumulation(flow_direction, "", "FLOAT")
    print("convert flow accumulation to drainage area")
    DrainArea = flow_accumulation * resolution / 1000000

    DEM_dirname = os.path.dirname(DEM_orig)

    if os.path.exists(DEM_dirname + "/DrainArea_sqkm.tif"):
        arcpy.Delete_management(DEM_dirname + "/DrainArea_sqkm.tif")
        DrArea_path = DEM_dirname + "/DrainArea_sqkm.tif"
        DrainArea.save(DrArea_path)
    else:
        DrArea_path = DEM_dirname + "/DrainArea_sqkm.tif"
        DrainArea.save(DrArea_path)

    print("drainage area Raster completed")
    return DrArea_path, flow_direction


###############################################################################
################# STREAM ORDERING ############################################
###############################################################################
def get_stream_order(scratch_gdb, stream_burn_dem, seg_network_a, DEM_orig, FlowDir, net_raster):

    orderMethod = "STRAHLER"

    print("running Stream order")
    outStreamOrder = StreamOrder(net_raster, FlowDir, orderMethod)

    strord_path = scratch_gdb + "/streamord_out"
    outStreamOrder.save(strord_path)

    print("fixing dodgy first order streams")
    str_ras = Raster(strord_path)
    Cor_Str_Ord_b = Con(str_ras == 1, 1, str_ras - 1)

    Cor_Str_Ord = scratch_gdb + "/Cor_Str_Ord"
    Cor_Str_Ord_b.save(Cor_Str_Ord)

    max_val = arcpy.GetRasterProperties_management(Cor_Str_Ord, "MAXIMUM")
    int_max_val = int(max_val.getOutput(0)) + 1
    val_range = list(range(2, int_max_val))

    print("expand values to remove 1st order errors")
    str_ord_exp = Expand(Cor_Str_Ord, 1, val_range)

    str_ord_exp_path = (scratch_gdb + "/str_ord_exp")
    str_ord_exp.save(str_ord_exp_path)

    print("convert Raster to Polygon")
    str_ord_exp_poly = scratch_gdb + "/st_or_ex_poly"
    arcpy.RasterToPolygon_conversion(str_ord_exp_path, str_ord_exp_poly, "NO_SIMPLIFY", "Value")

    net_fields = [f.name for f in arcpy.ListFields(seg_network_a)]
    if "Str_order" in net_fields:
        arcpy.DeleteField_management(seg_network_a, "Str_order")
    if "gridcode" in net_fields:
        arcpy.DeleteField_management(seg_network_a, "gridcode")
    del net_fields

    print ("join network and StrOrd Polygon fields")
    seg_network_b = scratch_gdb + "/seg_network_b"

    arcpy.SpatialJoin_analysis(seg_network_a, str_ord_exp_poly, seg_network_b, "JOIN_ONE_TO_ONE", "KEEP_ALL", "",
                               "HAVE_THEIR_CENTER_IN")

    arcpy.AddField_management(seg_network_b, "Str_order", "SHORT")

    cursor = arcpy.da.UpdateCursor(seg_network_b, ["Str_order", "gridcode"])
    for row in cursor:
        row[0] = row[1]
        cursor.updateRow(row)
    del row
    del cursor

    arcpy.DeleteField_management(seg_network_b, "gridcode")

    return seg_network_b


#################################################################################
################### BRAT TABLE FUNCTION ##########################################
#################################################################################
def bratTableCreate(home, in_water_vec_a, DEM_orig, DrArea, coded_vega, ranges):

    ############PARALLEL BIT ##########################
    inFc1 = home + "/inFc.shp"

    process_name = multiprocessing.current_process().name
    print (process_name)
    process_name2 = str(process_name)
    process_name3 = process_name2.replace("-", "_")
    outPath = home
    outName = ("process_fold_" + process_name3)

   ###create working folder
    new_folder1 = arcpy.CreateFolder_management(outPath, outName)
    new_folder2 = str(new_folder1)
    new_folder = new_folder2.replace("\\","/")
    print(new_folder)

    #### create working gdb
    fgb_name = ("process_fold_" + process_name3 + ".gdb")
    arcpy.CreateFileGDB_management(home, fgb_name)
    scratch = home + "/process_fold_" + process_name3 + ".gdb"

    time.sleep(5)

    arcpy.env.workspace = r"in_memory"
    arcpy.env.scratchworkspace = r"in_memory"

    i, j = ranges[0], ranges[1]

    print (i, j)

    flayer = arcpy.MakeFeatureLayer_management(inFc1, "fl")

    arcpy.SelectLayerByAttribute_management(flayer, "NEW_SELECTION", '"FID" >={0} AND "FID" <={1}'.format(i, j))

    inFl = arcpy.MakeFeatureLayer_management(flayer, 'layer{0}'.format(i))

    arcpy.CopyFeatures_management(inFl, new_folder + "/work_area.shp")

    inFc = new_folder + "/work_area.shp"

    num_rows = arcpy.GetCount_management(inFc)
    row_count = int(num_rows.getOutput(0))
    print(process_name + " reach count = " + str(row_count))

    seg_network = inFc
    ##################################################
    print ("creating out network")

    out_network = new_folder + "/" + process_name3 + "_net.shp"

    print("let's get started")
    # check that inputs are projected here
    networkSR = arcpy.Describe(seg_network).spatialReference
    if networkSR.type == "Projected":
        pass
    else:
        raise Exception("Input stream network must have a projected coordinate system")

    # check that input network is shapefile
    if seg_network.endswith(".shp"):
        pass
    else:
        raise Exception("Input network must be a shapefile (.shp)")

    # check that input network doesn't have field "objectid" already
    seg_network_fields = [f.name for f in arcpy.ListFields(seg_network)]
    if "OBJECTID" in seg_network_fields:
        raise Exception("Input network cannot have field 'OBJECTID', delete this field")
    if "reach_no" in seg_network_fields:
        arcpy.DeleteField_management(seg_network, "reach_no")

    # create sequential numbers for reaches
    inTable = seg_network
    fieldName = "reach_no"
    expression = "autoIncrement()"
    codeblock = """
rec = 0
def autoIncrement():
    global rec
    pStart = 1
    pInterval = 1
    if (rec == 0): 
        rec = pStart 
    else:
        rec = rec + pInterval 
    return rec"""

    # Execute AddField

    try:
        arcpy.AddField_management(inTable, fieldName, "LONG",)
    except Exception:
        print ("trying again")
        arcpy.AddField_management(inTable, fieldName, "LONG", )

    # Execute CalculateField
    arcpy.CalculateField_management(inTable, fieldName, expression, "PYTHON_9.3", codeblock)

    # set buffers for analyses
    print ("vertices to points")
    midpoints = scratch + "/midpoints"
    arcpy.FeatureVerticesToPoints_management(seg_network, midpoints, "MID")
    midpoint_fields = [f.name for f in arcpy.ListFields(midpoints)]
    midpoint_fields.remove("OBJECTID")
    midpoint_fields.remove("Shape")
    midpoint_fields.remove("reach_no")  ###
    arcpy.DeleteField_management(midpoints, midpoint_fields)


    print ("create limited inland water area with rivers")
    ndb = scratch + "/ndb"
    arcpy.Buffer_analysis(seg_network, ndb, "0.5 Meters", "", "", "NONE")  # changed to seg network


    iwv_copy = scratch + "/iwv_copy"
    arcpy.CopyFeatures_management(in_water_vec_a, iwv_copy)

    merge_list = [ndb, iwv_copy]
    iw_area_merge = scratch + "/iw_area_mer"

    print("merging inland water ply and stream network poly")
    arcpy.Merge_management(merge_list, iw_area_merge)

    print ("dissolving inland poly and stream network poly")
    iw_area_a = scratch + "/iw_area_a"
    arcpy.Dissolve_management(iw_area_merge, iw_area_a)


    print ("creating pre process buffer for reach areass")
    pre_area_buff = scratch + "/pre_area_buff"
    arcpy.Buffer_analysis(seg_network, pre_area_buff, "60 Meters", "", "ROUND",
                          "NONE")  # tried using flat end but causes error in the clip later - using 60m results in a 100m extension into adjacent reaches and 40m into riparian area

    pre_area_buffb = scratch + "/pre_area_buffb"
    arcpy.Buffer_analysis(seg_network, pre_area_buffb, "90 Meters", "", "ROUND",  # this buffer is added to make the bank length the same in both streamside and foraging areas
                          "NONE")

    pre_area_buffc = scratch + "/pre_area_buffc"
    arcpy.Buffer_analysis(seg_network, pre_area_buffc, "20 Meters", "", "ROUND", # to get more accurate width estimate (less than 40m)
                          "NONE") # this buffer is added to make the bank length the same in both streamside and foraging areas

    print ("clipping the reach areas")

    reach_areas = scratch + "/reach_areas"
    arcpy.Clip_analysis(pre_area_buff, iw_area_a, reach_areas, "")

    reach_areasb = scratch + "/reach_areasb"
    arcpy.Clip_analysis(pre_area_buffb, iw_area_a, reach_areasb, "")

    reach_areasc = scratch + "/reach_areasc"
    arcpy.Clip_analysis(pre_area_buffc, iw_area_a, reach_areasc, "")

    print ("create streamside buffer")
    #
    buf_10ma = scratch + "/buf_10ma"
    arcpy.Buffer_analysis(reach_areasb, buf_10ma, "10 Meters", "", "ROUND", "NONE")  #####10m buffer changed to 30 # now back to 10

    buf_10m = scratch + "/buf_10m"
    arcpy.Erase_analysis(buf_10ma, iw_area_a, buf_10m)

    print ("create foraging buffer")
    buf_100ma = scratch + "/buf_100ma"
    arcpy.Buffer_analysis(reach_areas, buf_100ma, "40 Meters", "", "ROUND", "NONE") ## changed to 40m based on Parker et al., 1999/2001 and Haarberg and Rosell 2006

    buf_100m = scratch + "/buf_100m"
    arcpy.Erase_analysis(buf_100ma, iw_area_a, buf_100m)

    print ("create elevation buffer")
    # elevation buffer
    elevation_buff = scratch + "/elevation_buff"
    arcpy.Buffer_analysis(seg_network, elevation_buff, "5 Meters", "", "ROUND", "NONE") # size reduced from 6 - 5 I think it is finding lower vals in some places


    print ("create midpoint buffer")
    midpoint_buffer = scratch + "/midpoint_buffer"
    arcpy.Buffer_analysis(midpoints, midpoint_buffer, "10 Meters", "", "", "NONE")  ##

    arcpy.CopyFeatures_management(seg_network, out_network)


    ###
    print ("Adding iGeo attributes to network")
    # if fields already exist, delete them
    network_fields = [f.name for f in arcpy.ListFields(out_network)]
    if "iGeo_ElMax" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_ElMax")
    if "iGeo_ElMin" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_ElMin")
    if "iGeo_Len" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_Len")
    if "iGeo_Slope" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_Slope")
    if "iGeo_DA" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_DA")
    if "iGeo_Area" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_Area")
    if "iGeo_Width" in network_fields:
        arcpy.DeleteField_management(out_network, "iGeo_Width")

        # get start elevation values
    print("getting start elevation values")
    print("where all the zonal statistics starts")
    startpoints = scratch + "/startpoints"
    arcpy.FeatureVerticesToPoints_management(out_network, startpoints, "START")
    startpoint_fields = [f.name for f in arcpy.ListFields(startpoints)]
    startpoint_fields.remove("OBJECTID")
    startpoint_fields.remove("Shape")  ## This needs changing - must join with reach no not orig_fid
    startpoint_fields.remove("reach_no")  ## changed
    arcpy.DeleteField_management(startpoints, startpoint_fields)
    startpoint_buf = scratch + "/startpoint_buf"
    arcpy.Buffer_analysis(startpoints, startpoint_buf, "6 Meters", "", "", "LIST", "reach_no")

    arcpy.env.extent = "MAXOF"

    arcpy.AddField_management(startpoint_buf, "iGeo_ElMax", "DOUBLE")
    fl_name = "sp_buf_FL_" + process_name3
    sp_buf_FL1 = arcpy.MakeFeatureLayer_management(startpoint_buf, fl_name, "", r"in_memory")

    table = r"in_memory/temp_table_" + process_name3

    with arcpy.da.SearchCursor(sp_buf_FL1, ["reach_no", "SHAPE@"]) as cursor:
        for row in cursor:
            reach_no = row[0]
            # print (process_name3 + " row:" + str(reach_no))

            row_extent = row[1].extent
            arcpy.env.extent = row_extent

            arcpy.SelectLayerByAttribute_management(sp_buf_FL1,
                                                    "NEW_SELECTION",
                                                    "reach_no = {0}".format(row[0]))

            # try:
            arcpy.sa.ZonalStatisticsAsTable(sp_buf_FL1, "reach_no", Raster(DEM_orig), table, "DATA", "MINIMUM")


            arcpy.JoinField_management(sp_buf_FL1, "reach_no", table, "reach_no", "MIN")
            #
            fl_name2 = "sp_buf_FLB_" + process_name3
            sp_buf_FL2 = arcpy.MakeFeatureLayer_management(sp_buf_FL1, fl_name2, "", r"in_memory")
            cursor2 = arcpy.da.UpdateCursor(sp_buf_FL2, ["reach_no", "iGeo_ElMax", "MIN"])
            for ro in cursor2:
                if ro[0] == reach_no:
                    ro[1] = ro[2]
                    cursor2.updateRow(ro)
            #print ("row updated")

            arcpy.DeleteField_management(sp_buf_FL1, "MIN")

            del cursor2

    del cursor

    arcpy.env.extent = "MAXOF"
    arcpy.SelectLayerByAttribute_management(sp_buf_FL1,"CLEAR_SELECTION")

    arcpy.JoinField_management(out_network, "reach_no", sp_buf_FL1, "reach_no", "iGeo_ElMax")

    arcpy.Delete_management(sp_buf_FL1)
    arcpy.Delete_management(table)

    print ("start elevations done for " + process_name3)

    # get end elevation values
    print("getting end elevation values")

    ##### new end elevation value zs

    arcpy.AddField_management(elevation_buff, "iGeo_ElMin", "DOUBLE")
    fl_name = "ep_buf_FL_" + process_name3
    ep_buf_FL1 = arcpy.MakeFeatureLayer_management(elevation_buff, fl_name, "", r"in_memory")

    table = r"in_memory/temp_table_" + process_name3

    with arcpy.da.SearchCursor(ep_buf_FL1, ["reach_no", "SHAPE@"]) as cursor:
        for row in cursor:
            reach_no = row[0]
            row_extent = row[1].extent
            arcpy.env.extent = row_extent

            arcpy.SelectLayerByAttribute_management(ep_buf_FL1,
                                                    "NEW_SELECTION",
                                                    "reach_no = {0}".format(row[0]))
            # try:
            arcpy.sa.ZonalStatisticsAsTable(ep_buf_FL1, "reach_no", Raster(DEM_orig), table, "DATA", "MINIMUM")

            arcpy.JoinField_management(ep_buf_FL1, "reach_no", table, "reach_no", "MIN")
            #
            fl_name2 = "ep_buf_FLB_" + process_name3
            sp_buf_FL2 = arcpy.MakeFeatureLayer_management(ep_buf_FL1, fl_name2, "", r"in_memory")
            cursor2 = arcpy.da.UpdateCursor(sp_buf_FL2, ["reach_no", "iGeo_ElMin", "MIN"])
            for ro in cursor2:
                if ro[0] == reach_no:
                    ro[1] = ro[2]
                    cursor2.updateRow(ro)
            #print ("row updated")

            arcpy.DeleteField_management(ep_buf_FL1, "MIN")

            del cursor2

    del cursor

    arcpy.env.extent = "MAXOF"

    arcpy.SelectLayerByAttribute_management(ep_buf_FL1, "CLEAR_SELECTION")

    arcpy.JoinField_management(out_network, "reach_no", ep_buf_FL1, "reach_no", "iGeo_ElMin")

    arcpy.Delete_management(ep_buf_FL1)
    arcpy.Delete_management(table)
    # arcpy.Delete_management(DEM_IM)
    print ("end elevations done for " + process_name3)

    # add slope
    print("calculating slope")
    arcpy.AddField_management(out_network, "iGeo_Len", "DOUBLE")
    arcpy.CalculateField_management(out_network, "iGeo_Len", '!shape.length@meters!', "PYTHON_9.3")
    arcpy.AddField_management(out_network, "iGeo_Slope", "DOUBLE")
    cursor = arcpy.da.UpdateCursor(out_network, ["iGeo_ElMax", "iGeo_ElMin", "iGeo_Len", "iGeo_Slope"])
    for row in cursor:
        index = (abs(row[0] - row[1])) / row[2]
        row[3] = index
        cursor.updateRow(row)
    del row
    del cursor
    cursor = arcpy.da.UpdateCursor(out_network, "iGeo_Slope")  # fix slope values of 0
    for row in cursor:
        if row[0] == 0.0:
            row[0] = 0.0001
        elif row[0] > 1.0:
            row[0] = 0.5
        else:
            pass
        cursor.updateRow(row)
    del row
    del cursor

    # Get reach widths
    print("calculating reach widths")

    arcpy.AddField_management(reach_areasc, "iGeo_Area", "DOUBLE") # now calacualtes width on area shp file than transfers this to network

    cursor = arcpy.da.UpdateCursor(reach_areasc, ["Shape_Area", "iGeo_Area"])
    for row in cursor:
        row[1] = row[0]
        cursor.updateRow(row)
    del row
    del cursor

    arcpy.JoinField_management(out_network, "reach_no", reach_areasc, "reach_no", "iGeo_Area")
    arcpy.AddField_management(out_network, "iGeo_Width", "DOUBLE")
    cursor = arcpy.da.UpdateCursor(out_network, ["iGeo_Area", "iGeo_len", "iGeo_Width"])
    for row in cursor:
        row[2] = row[0] / (row[1] + 40)
        cursor.updateRow(row)
    del row
    del cursor

    arcpy.DeleteField_management(out_network, "iGeo_Area")


    print("zonal statistics for drainage area")


    ##### new end Drain Area value zs
    print("create process Drainage Area")


    arcpy.AddField_management(midpoint_buffer, "iGeo_DA", "DOUBLE")
    fl_name = "DR_FL_" + process_name3
    dr_FL1 = arcpy.MakeFeatureLayer_management(midpoint_buffer, fl_name, "", r"in_memory")

    table = r"in_memory/temp_table_" + process_name3

    with arcpy.da.SearchCursor(dr_FL1, ["reach_no", "SHAPE@"]) as cursor:
        for row in cursor:
            reach_no = row[0]
            row_extent = row[1].extent
            arcpy.env.extent = row_extent

            arcpy.SelectLayerByAttribute_management(dr_FL1,
                                                    "NEW_SELECTION",
                                                    "reach_no = {0}".format(row[0]))
            # try:
            arcpy.sa.ZonalStatisticsAsTable(dr_FL1, "reach_no", DrArea, table, "DATA", "MAXIMUM")

            arcpy.JoinField_management(dr_FL1, "reach_no", table, "reach_no", "MAX")
            #
            fl_name2 = "dr_FLB_" + process_name3
            dr_FL2 = arcpy.MakeFeatureLayer_management(dr_FL1, fl_name2, "", r"in_memory")
            cursor2 = arcpy.da.UpdateCursor(dr_FL2, ["reach_no", "iGeo_DA", "MAX"])
            for ro in cursor2:
                if ro[0] == reach_no:
                    ro[1] = ro[2]
                    cursor2.updateRow(ro)
            #print ("row updated")

            arcpy.DeleteField_management(dr_FL1, "MAX")

            del cursor2

    del cursor

    arcpy.env.extent = "MAXOF"

    arcpy.SelectLayerByAttribute_management(dr_FL1, "CLEAR_SELECTION")

    arcpy.JoinField_management(out_network, "reach_no", dr_FL1, "reach_no", "iGeo_DA")

    arcpy.Delete_management(dr_FL1)
    arcpy.Delete_management(table)


    print ("drainage areas done for " + process_name3)

    #######
    with arcpy.da.UpdateCursor(out_network, ["iGeo_DA"]) as cursor:
        for row in cursor:
            if row[0] == 0:
                row[0] = 0.1
                cursor.updateRow(row)

            else:
                pass
    del cursor

    # arcpy.DeleteField_management(out_network, "MAX")
    # del drarea_zs

    print('Adding "iVeg" attributes to network')

    coded_veg = Raster(coded_vega)

# def iveg_attributes(coded_veg, buf_100m, buf_10m, out_network, scratch):
    # if fields already exist, delete them

    network_fields = [f.name for f in arcpy.ListFields(out_network)]
    if "iVeg_100EX" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_100EX")
    if "iVeg_10EX" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_10EX")
    if "iVeg_10EX_SD" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_10EX_SD")
    if "iVeg_100EX_SD" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_100EX_SD")
    if "iVeg_10EX_AVG" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_10EX_AVG")
    if "iVeg_100EX_AVG" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_100EX_AVG")
    if "iVeg_10p75" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_10p75")
    if "iVeg_100p75" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_100p75")
    if "iVeg_10p80" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_10p80")
    if "iVeg_100p80" in network_fields:
        arcpy.DeleteField_management(out_network, "iVeg_100p80")

    # get iVeg_VT100EX
    # veg_lookup = Lookup(coded_veg, "Value")
    print("calculating foraging vegetation value")


    arcpy.AddField_management(buf_100m, "iVeg_100EX", "DOUBLE")
    # arcpy.AddField_management(buf_100m, "iVeg_100SD", "DOUBLE") # trying out SD
    # arcpy.AddField_management(buf_100m, "iVeg_100AV", "DOUBLE")
    arcpy.AddField_management(buf_100m, "iVeg_100p75", "DOUBLE")
    arcpy.AddField_management(buf_100m, "iVeg_100p80", "DOUBLE")

    print("fields added")
    fl_name = "FV_FL_" + process_name3
    fv_FL1 = arcpy.MakeFeatureLayer_management(buf_100m, fl_name, "", r"in_memory")
    print("feature layer made")

    table = r"in_memory/temp_table_" + process_name3
    # table = scratch + "/temp_table_" + process_name3

    with arcpy.da.SearchCursor(fv_FL1, ["reach_no", "SHAPE@"]) as cursor:
        for row in cursor:
            reach_no = row[0]
            # print reach_no
            row_extent = row[1].extent
            arcpy.env.extent = row_extent

            arcpy.SelectLayerByAttribute_management(fv_FL1,
                                                    "NEW_SELECTION",
                                                    "reach_no = {0}".format(row[0]))
            temp_shp = r"in_memory/temp_shp_" + process_name3
            arcpy.CopyFeatures_management(fv_FL1, temp_shp)

            try:
                TabulateArea(coded_veg, "Value", temp_shp, "reach_no", table)

                field_names = [f.name for f in arcpy.ListFields(table)]
                field_names.pop(0)  # removes OID from field names
                # print field_names
                np1 = arcpy.da.TableToNumPyArray(table, field_names)

                G = np.asarray([list(t) for t in zip(*np1)])
                H = G.astype(int)

                # print H

                K, L = np.vsplit(H, 2)
                K = K.flatten()
                L = L.flatten()
                I = np.repeat(K, L)


                p80 = np.nanpercentile(I, 80) #

                p75 = np.nanpercentile(I, 75)

                low, high = np.array_split(I, 2)  #

                top_avg = np.mean(high)

                fl_name2 = "fv_FLB_" + process_name3

                fv_FL2 = arcpy.MakeFeatureLayer_management(fv_FL1, fl_name2, "", r"in_memory")
                cursor2 = arcpy.da.UpdateCursor(fv_FL2, ["reach_no", "iVeg_100EX", "iVeg_100p75", "iVeg_100p80"])

                for ro in cursor2:
                    if ro[0] == reach_no:
                        ro[1] = top_avg
                        ro[2] = p75
                        ro[3] = p80
                        cursor2.updateRow(ro)
                del cursor2
            except Exception as e:
                print(e)
                print("error on foraging buffer - reach " + str(reach_no) + ", " + process_name3)

                fl_name2 = "rv_FLB_" + process_name3
                fv_FL2 = arcpy.MakeFeatureLayer_management(fv_FL1, fl_name2, "", r"in_memory")
                cursor2 = arcpy.da.UpdateCursor(fv_FL2, ["reach_no", "iVeg_100EX", "iVeg_100p75", "iVeg_100p80"])
                for ro in cursor2:
                    if ro[0] == reach_no:
                        ro[1] = 0
                        ro[2] = 1000
                        ro[3] = 1000
                        cursor2.updateRow(ro)

                print ("error - temporarily fixed Foraging!! look for values with iVeg_100p75 and iVeg_100p80 of 1000 to check manually")

                del cursor2

    del cursor

    arcpy.env.extent = "MAXOF"

    arcpy.SelectLayerByAttribute_management(fv_FL1, "CLEAR_SELECTION")

    arcpy.JoinField_management(out_network, "reach_no", fv_FL1, "reach_no",
                               ["iVeg_100EX", "iVeg_100p75", "iVeg_100p80"])

    arcpy.Delete_management(fv_FL1)
    arcpy.Delete_management(table)
    arcpy.Delete_management(temp_shp)
    print ("foraging veg done for " + process_name3)
    ###
    # get iVeg_10EX
    print("calculating riparian vegetation value")

    ##### new riparian veg value zs

    arcpy.AddField_management(buf_10m, "iVeg_10EX", "DOUBLE")
    # arcpy.AddField_management(buf_10m, "iVeg_10SD", "DOUBLE")  # trying out SD
    # arcpy.AddField_management(buf_10m, "iVeg_10AV", "DOUBLE")
    arcpy.AddField_management(buf_10m, "iVeg_10p75", "DOUBLE")
    arcpy.AddField_management(buf_10m, "iVeg_10p80", "DOUBLE")

    fl_name = "RV_FL_" + process_name3
    rv_FL1 = arcpy.MakeFeatureLayer_management(buf_10m, fl_name, "", r"in_memory")

    table = r"in_memory/temp_table_" + process_name3

    with arcpy.da.SearchCursor(rv_FL1, ["reach_no", "SHAPE@"]) as cursor:
        for row in cursor:
            reach_no = row[0]
            row_extent = row[1].extent
            arcpy.env.extent = row_extent

            arcpy.SelectLayerByAttribute_management(rv_FL1,
                                                    "NEW_SELECTION",
                                                    "reach_no = {0}".format(row[0]))

            temp_shp = r"in_memory/temp_shp_" + process_name3
            arcpy.CopyFeatures_management(rv_FL1, temp_shp)

            try:
                TabulateArea(coded_veg, "Value", temp_shp, "reach_no", table)

                field_names = [f.name for f in arcpy.ListFields(table)]
                field_names.pop(0) # removes OID from field names

                np1 = arcpy.da.TableToNumPyArray(table, field_names)
                # print np1
                G = np.asarray([list(t) for t in zip(*np1)])

                H = G.astype(int)

                K, L = np.vsplit(H, 2)
                K = K.flatten()
                # K = np.sort(K, axis=None)
                L = L.flatten()
                # L = np.sort(L, axis=None)
                I = np.repeat(K, L)


                p80 = np.nanpercentile(I, 80) # changed to 80 but still called 95 in column - will change later if needed
                # p90 = np.nanpercentile(I, 90)
                p75 = np.nanpercentile(I, 75)

                # I_copy = np.copy(I)
                low, high = np.array_split(I, 2)  #

                top_avg = np.mean(high)

                fl_name2 = "fv_FLB_" + process_name3

                rv_FL2 = arcpy.MakeFeatureLayer_management(rv_FL1, fl_name2, "", r"in_memory")
                cursor2 = arcpy.da.UpdateCursor(rv_FL2, ["reach_no", "iVeg_10EX", "iVeg_10p75", "iVeg_10p80"])
                # print("begin cursor")
                for ro in cursor2:
                    if ro[0] == reach_no:
                        ro[1] = top_avg
                        ro[2] = p75
                        ro[3] = p80
                        cursor2.updateRow(ro)
                del cursor2
            except Exception:
                print ("error on riparian buffer - reach " + str(reach_no) + ", " + process_name3)

                fl_name2 = "rv_FLB_" + process_name3
                rv_FL2 = arcpy.MakeFeatureLayer_management(rv_FL1, fl_name2, "", r"in_memory")
                cursor2 = arcpy.da.UpdateCursor(rv_FL2, ["reach_no", "iVeg_10EX", "iVeg_10p75", "iVeg_10p80"])
                for ro in cursor2:
                    if ro[0] == reach_no:
                        ro[1] = 0
                        ro[2] = 1000
                        ro[3] = 1000
                        cursor2.updateRow(ro)

                print ("error - temporarily  fixed riparian veg!! look for values with iVeg_10p75 and iVeg_10p80 of 1000 to check manually")

                del cursor2

    del cursor

    arcpy.env.extent = "MAXOF"

    arcpy.SelectLayerByAttribute_management(rv_FL1, "CLEAR_SELECTION")

    arcpy.JoinField_management(out_network, "reach_no", rv_FL1, "reach_no",
                               ["iVeg_10EX", "iVeg_10p75", "iVeg_10p80"])

    arcpy.Delete_management(rv_FL1)
    arcpy.Delete_management(table)
    arcpy.Delete_management(temp_shp)

    print ("riparian veg done for " + process_name3)

#######
    print (process_name3 + " done")

    ### Copy out network to home location
    process_out = home + "/" + process_name3 + "_net.shp"
    arcpy.CopyFeatures_management(out_network, process_out)

    return


def mphandler(home, in_water_vec_a, DEM_orig, DrAreaPath, coded_vega, path, home_name, seg_network_b, outname):
    print ("new_home_folder")
    if arcpy.Exists(home):
        arcpy.Delete_management(home)
    arcpy.CreateFolder_management(path, home_name)

    # import arcpy
    startTime = datetime.now()
    print (startTime)
    #######
    inFc1 = home + "/inFc.shp"
    arcpy.CopyFeatures_management(seg_network_b, inFc1)

    network_fields = [f.name for f in arcpy.ListFields(inFc1)]
    if "OBJECTID" in network_fields:
        arcpy.DeleteField_management(inFc1, "OBJECTID")
    if "OID" in network_fields:
        arcpy.DeleteField_management(inFc1, "OID")


    result = arcpy.GetCount_management(inFc1)
    count = int(result.getOutput(0))
    num_cores = multiprocessing.cpu_count() - 1  # this can be automated but the number of processes is also related to
    print("number of cores = {0}".format(num_cores))
    interval = int(round(count / num_cores))  # the size of the dataset and available RAM so change if errors occur

    ranges = []
    core_list = range(1, num_cores + 1)
    start = [0, int(interval)]
    for i in core_list:
        # print(i)
        if i == 1:
            values = start
        elif i > 1 and i < num_cores:
            values = [(int(interval) * (i - 1)) + 1, int(interval) * i]
        else:
            values = [(int(interval) * (i - 1)) + 1, int(count)]
        ranges.append(values)

    print(ranges)

    pool = multiprocessing.Pool()

    func = partial(bratTableCreate, home, in_water_vec_a, DEM_orig, DrAreaPath, coded_vega)
    pool.map(func, ranges)

    # Synchronize the main process with the job processes to
    # Ensure proper cleanup.
    pool.close()
    pool.join()

    arcpy.env.extent = "MAXOF"

    print("merging network sections from cores")
    arcpy.Delete_management(inFc1)
    arcpy.env.workspace = home
    fc_list = arcpy.ListFeatureClasses()

    merged_lines = home + "/" + outname


    arcpy.Merge_management(fc_list, merged_lines)

    for fc in fc_list:
        if arcpy.Exists(fc):
            arcpy.Delete_management(fc)

    ##ADD REACH NO COLUMN AGAIN AND RECALC THE NUMBER
    brat_fields = [f.name for f in arcpy.ListFields(merged_lines)]
    if "reach_no" in brat_fields:
        arcpy.DeleteField_management(merged_lines, "reach_no")

    # create sequential numbers for reaches
    inTable_b = merged_lines
    fieldName = "reach_no"
    expression = "autoIncrement()"
    codeblock = """
rec = 0
def autoIncrement():
    global rec
    pStart = 1
    pInterval = 1
    if (rec == 0): 
        rec = pStart 
    else:
        rec = rec + pInterval 
    return rec"""

    # Execute AddField
    arcpy.AddField_management(inTable_b, fieldName, "LONG")

    # Execute CalculateField
    arcpy.CalculateField_management(inTable_b, fieldName, expression, "PYTHON_9.3", codeblock)

    arcpy.env.workspace = home

    # List all file geodatabases in the current workspace
    workspaces = arcpy.ListWorkspaces("*", "All")
    for w in workspaces:
        arcpy.Delete_management(w)

    print(datetime.now() - startTime)
    print("output is ready")
    # End main


if __name__ == '__main__':
    main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        sys.argv[5],
        sys.argv[6])
