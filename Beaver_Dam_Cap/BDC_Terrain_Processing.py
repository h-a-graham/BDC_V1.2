# from arcpy.sa import *
# import arcpy
from datetime import datetime
import os
import sys



############# START TIME ##############
startTime = datetime.now()


def main(path, scratch_gdb, seg_network_a, DEM_orig):

    arcpy.env.overwriteOutput = True
    arcpy.CheckOutExtension("spatial")
    arcpy.env.scratchworkspace = r"in_memory" #scratch_gdb

    print(startTime)

    home_name = "BDC_OC{0}".format(path[-4:])  # REQUIRED - name of home working directory to be created
    home = os.path.join(path, home_name)  # Don't Edit
    outname = "Output_BDC_OC{0}.shp".format(path[-4:])  # REQUIRED - output file name -  must end in .shp


    print("Run Stream Burn Process")

    stream_burn_dem, net_raster, sb_DEM = streamBurning(DEM_orig, scratch_gdb, seg_network_a, path, home_name)

    print("Run Flow Accumulation / Drainage area raster Process")

    DrAreaPath, FlowDir = calc_drain_area(stream_burn_dem, scratch_gdb, DEM_orig)

    print("Run Stream Order Polygon Generation")

    if arcpy.Exists(scratch_gdb + "/seg_network_b"):
        print("stream ordering alredy done...")
        seg_network_b = scratch_gdb + "/seg_network_b"
    else:
        seg_network_b = get_stream_order(scratch_gdb, stream_burn_dem, seg_network_a, DEM_orig, FlowDir, net_raster)

    finTime = datetime.now() - startTime
    print("BDC table script completed. \n"
          "Processing time = {0}".format(finTime))

    return seg_network_b

################################################################################################
###################### NOW TIME FOR STREAM BURNING ###############################
################################################################################################

def streamBurning(DEM_orig, scratch_gdb, seg_network_a, home, home_name):
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

    sb_DEM = os.path.join(home, "{0}strBurndDEm.tif".format(home_name))

    arcpy.CopyRaster_management(scratch_gdb + "/raster_burn", sb_DEM)

    print("stream burning complete")
    return stream_burn_dem_a, network_raster, sb_DEM


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

    with arcpy.da.UpdateCursor(seg_network_b, ["Str_order", "gridcode"]) as cursor:
        for row in cursor:
            row[0] = row[1]
            cursor.updateRow(row)
    del row
    del cursor

    arcpy.DeleteField_management(seg_network_b, "gridcode")

    return seg_network_b

if __name__ == '__main__':
    main(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],)
