#  1) This script will pull in all the data sets
#  2) Transform all datasets to the same coordinate system
#  3) convert vector data (OS VectorMap Local and CEH LWF) to Raster
#  4) align all raster cells so that they overlap exactly.
#  5) Send Data to a new folder for processing in the next script.

#Import Modules
import gdal
import numpy as np
import os
from gdalnumeric import *
import geopandas as gpd
from geopandas import GeoDataFrame

from osgeo import ogr

import matplotlib.pyplot as plt

# Start Timer
from datetime import datetime
startTime = datetime.now()
print(startTime)


def main():

    # Set up working environment
    home = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Test_Data")  # the home folder containing your corrected data
    exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/GB_BVI_test_inputs")
    # scratch_name = "BVI_scratch"  # sctatch workspace name no need to create.
    # scratch = os.path.join(home, scratch_name)

    # not sure we need a scratch folder... Perhaps we will if we go down the chunking route...
    # if os.path.exists(scratch):
    #     print ("scratch folder already exists")
    # else:
    #     print ("create scratch folder")
    #     os.makedirs(scratch)

    # output file directories
    OS_landuse_o = os.path.join(exports, "OS_raster.tif")  # Rasterised version of OS vector data
    LWF_o = os.path.join(exports, "lwf_ras.tif") # Rasterised linear woody framework data
    TCD_20_o = os.path.join(exports, "tcd20_raster.tif")  # Copernicus Tree cover density data
    LCM_o = os.path.join(exports, "LCM_raster_V2.tif")  # rasterised land cover map data
    ceh_con_p = os.path.join(exports, "scot_ceh_con.tif")

    scratch_name = "BVI_scratch"  # sctatch workspace name no need to create.
    scratch = os.path.join(home, scratch_name)

    if os.path.exists(scratch):
        print("scratch folder already exists")
    else:
        print("create scratch folder")
        os.makedirs(scratch)

    # input files

    vecmap_shp = os.path.join(home, "OS_Poly_tay.shp")
    lcm_shp = os.path.join(home, "ceh_lcm.shp")
    lwf_shp = os.path.join(home, "ceh_lwf.shp")
    tcd_ras = os.path.join(home, "tcd.tiff")

    rasterise_shps(vecmap_shp, lcm_shp, lwf_shp, OS_landuse_o, scratch)

def rasterise_shps(vecmap_shp, lcm_shp, lwf_shp, OS_landuse_o, scratch):
    print("rasterizing shapefiles")

    vecmap_gp = gpd.read_file(vecmap_shp)  # the geopandas way - so slow!

    # extent = vecmap_ogr.GetExtent()
    #
    # print(extent)
    # rast_res = 5  # desired resolution of rasters
    # dist_width = extent[2] - extent[0]
    # width = round(dist_width)/5
    # print(width)
    #
    # dist_height = extent[4] - extent[1]
    # height = round(dist_height) / 5
    # print(height)
    #
    # format = "MEM"
    # driver = gdal.GetDriverByName(format)
    #
    # dst_ds = driver.Create("", width, height, 1, gdal.GDT_Float32)

    # print("file_loaded")
    # time_update = (datetime.now() - startTime)
    # print(time_update)
    #
    # fieldDefn = ogr.FieldDefn('BVI_Val_A', ogr.OFTReal)
    # fieldDefn.SetWidth(3)
    # fieldDefn.SetPrecision(0)
    # vecmap_ogr.CreateField(fieldDefn)
    #
    # # vecmap_ogr.SetAttributeFilter("'FeatDesc' = 'Broad-leafed woodland'")
    #

    # geopandas way - slow as shit!
    vecmap_gp['BVI_Val'] = None
    print("column added")

    print(vecmap_gp.head())


    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Boulders", 'BVI_Val'] = 0
    print("A")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Boulders and Sand", 'BVI_Val'] = 0
    print("B")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Boulders and Shingle", 'BVI_Val'] = 0
    print("C")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Broad-leafed woodland", 'BVI_Val'] = 5
    print("D")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Broad-leafed woodland and Shru", 'BVI_Val'] = 5
    print("E")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Building polygon", 'BVI_Val'] = 0
    print("F")
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Coniferous woodland", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Coniferous woodland and Shrub", 'BVI_Val'] = 5
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Custom landform polygon", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Glasshouse polygon", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Gravel Pit", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Heathland", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Heathland and Boulders", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Heathland and Marsh", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Heathland and Unimproved Grass", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Inland Rock", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Inland water polygon", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Marsh", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Marsh and Unimproved Grass", 'BVI_Val'] = 2
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Mixed woodland", 'BVI_Val'] = 5
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Mixed woodland and Shrub", 'BVI_Val'] = 5
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Mud", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Orchard", 'BVI_Val'] = 5
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Reeds", 'BVI_Val'] = 2
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Refuse or Slag Heap", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Sand", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Sand Pit", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Sea polygon", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shingle", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shingle and Mud", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shingle and Sand", 'BVI_Val'] = 0
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub", 'BVI_Val'] = 5
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and  Boulders", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Heathland", 'BVI_Val'] = 2
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Heathland and Boulde", 'BVI_Val'] = 2
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Heathland and Unimpr", 'BVI_Val'] = 2
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Marsh", 'BVI_Val'] = 4
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Marsh and Heath", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Marsh and Unimproved", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Shrub and Unimproved Grass", 'BVI_Val'] = 3
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Unimproved Grass", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Unimproved Grass and Sand", 'BVI_Val'] = 1
    vecmap_gp.loc[vecmap_gp['FeatDesc'] == "Grass and Shingle", 'BVI_Val'] = 1
    #
    # vecmap_gp.loc[vecmap_gp['BVI_Val'] == None, 'BVI_Val'] = 999
    # # Plot
    # vecmap_gp.plot(column="BVI_Val", linewidth=0, legend=True)
    # plt.show()
    # Use tight layout
    # plt.tight_layout()

    # OS_land_tmp = os.path.join(scratch, "OS_raster_tmp.shp")
    # GeoDataFrame.to_file(vecmap_gp, OS_land_tmp, driver="ESRI Shapefile")

    # gdal.RasterizeLayer(OS_landuse_o, [1], mb_l, options=["ATTRIBUTE=BVI_Val"])

    # for i in range(len(vecmap_gp)):
    #     landcov = vecmap_gp.at[i, 'FeatDesc']  # add in whatever OS call their land cover class
    #     if landcov == "Boulders":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Boulders and Sand":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Boulders and Shingle":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Broad-leafed woodland":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Broad-leafed woodland and Shru":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Building polygon":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Coniferous woodland":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Coniferous woodland and Shrub":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Custom landform polygon":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Glasshouse polygon":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Gravel Pit":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Heathland":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Heathland and Boulders":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Heathland and Marsh":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Heathland and Unimproved Grass":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Inland Rock":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Inland water polygon":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Marsh":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Marsh and Unimproved Grass":
    #         vecmap_gp['BVI_Val'] == 2
    #     elif landcov == "Mixed woodland":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Mixed woodland and Shrub":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Mud":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Orchard":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Reeds":
    #         vecmap_gp['BVI_Val'] == 2
    #     elif landcov == "Refuse or Slag Heap":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Sand":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Sand Pit":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Sea polygon":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Shingle":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Shingle and Mud":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Shingle and Sand":
    #         vecmap_gp['BVI_Val'] == 0
    #     elif landcov == "Shrub":
    #         vecmap_gp['BVI_Val'] == 5
    #     elif landcov == "Shrub and  Boulders":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Shrub and Heathland":
    #         vecmap_gp['BVI_Val'] == 2
    #     elif landcov == "Shrub and Heathland and Boulde":
    #         vecmap_gp['BVI_Val'] == 2
    #     elif landcov == "Shrub and Heathland and Unimpr":
    #         vecmap_gp['BVI_Val'] == 2
    #     elif landcov == "Shrub and Marsh":
    #         vecmap_gp['BVI_Val'] == 4
    #     elif landcov == "Shrub and Marsh and Heath":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Shrub and Marsh and Unimproved":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Shrub and Unimproved Grass":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Shrub and Unimproved Grass and":
    #         vecmap_gp['BVI_Val'] == 3
    #     elif landcov == "Unimproved Grass":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Unimproved Grass and Boulders":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Unimproved Grass and Sand":
    #         vecmap_gp['BVI_Val'] == 1
    #     elif landcov == "Unimproved Grass and Shingle":
    #         vecmap_gp['BVI_Val'] == 1
    #     else:
    #         vecmap_gp['BVI_Val'] == 999


    print("done")

if __name__ == '__main__':
    main()


