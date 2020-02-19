import arcpy
from arcpy.sa import *
import sys
import os
arcpy.env.overwriteOutput = True

def get_stream_order(scratch_gdb, FlowDir, net_raster, out_poly):

    orderMethod = "STRAHLER"

    # print("running Stream order")
    outStreamOrder = StreamOrder(net_raster, FlowDir, orderMethod)

    strord_path = os.path.join(scratch_gdb, "streamord_out.tif")
    outStreamOrder.save(strord_path)

    # print("fixing dodgy first order streams")
    str_ras = Raster(strord_path)
    Cor_Str_Ord_b = Con(str_ras == 1, 1, str_ras - 1)

    Cor_Str_Ord = os.path.join(scratch_gdb, "Cor_Str_Ord.tif")
    Cor_Str_Ord_b.save(Cor_Str_Ord)

    max_val = arcpy.GetRasterProperties_management(Cor_Str_Ord, "MAXIMUM")
    int_max_val = int(max_val.getOutput(0)) + 1
    val_range = list(range(2, int_max_val))

    # print("expand values to remove 1st order errors")
    str_ord_exp = Expand(Cor_Str_Ord, 1, val_range)

    str_ord_exp_path = os.path.join(scratch_gdb, "str_ord_exp.tif")
    str_ord_exp.save(str_ord_exp_path)

    # print("convert Raster to Polygon")
    str_ord_exp_poly = os.path.join(scratch_gdb, "st_or_ex_poly.shp")
    arcpy.RasterToPolygon_conversion(str_ord_exp_path, str_ord_exp_poly, "NO_SIMPLIFY", "Value")

    return(str_ord_exp_poly)


if __name__ == '__main__':
    stream_order_strems = get_stream_order(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4])

    print(stream_order_strems)
