
# Issues:

#Import Modules
import gdal
import numpy as np
import os
from gdalnumeric import *

# Start Timer
from datetime import datetime
startTime = datetime.now()



def main(home):
    print(startTime)
    setup_vars(home)
    print(datetime.now() - startTime)
    print("script finished")
    # Set up working environment
    # home = "D:/Work/GB_Beaver_Data/GB_BVI_Results"  # the home folder containing your corrected data
    # exports = "C:/Users/hughg/Desktop/GB_Beaver_modelling/GB_Beaver_Exports"
    # scratch_name = "BVI_scratch"  # sctatch workspace name no need to create.
    # scratch = os.path.join(home, scratch_name)

    # not sure we need a scratch folder... Perhaps we will if we go down the chunking route...
    # if os.path.exists(scratch):
    #     print ("scratch folder already exists")
    # else:
    #     print ("create scratch folder")
    #     os.makedirs(scratch)

    # Set up outputs

def setup_vars(home):
    print("defining all variables")
    direc_list = next(os.walk(home))[1]
    for folder in direc_list:
        # if folder == 'sx':  # for testing st looks to be the right size...
        #     print("testing mode for 'st'")
        root = os.path.join(home, folder)
        #define exports
        ukveg_o = os.path.join(root, folder.upper() + "_GB_BVI.tif")  # Output file name
        ukveg_c = os.path.join(root, folder.upper() + "_GB_BHI.tif")
        # input file directories
        OS_landuse_p = os.path.join(root, folder + "_OS_vec_5m.tif")  # Rasterised version of OS vector data
        LWF_p = os.path.join(root, folder.upper() + "_lwf_ras.tif")  # Rasterised linear woody framework data
        TCD_20_p = os.path.join(root, folder.upper() + "_TCD.tif")  # Copernicus Tree cover density data
        LCM_p = os.path.join(root, folder.upper() + "_CEH_LCM_BVI_5m.tif")  # rasterised land cover map data
        ceh_con_p = os.path.join(root, folder.upper() + "_CEH_Con.tif")  # Coniferous area from LCM
        water_buff_p = os.path.join(root, folder.upper() + "_Water_Buffer_ras.tif")  # need to check this path

        gbbvi(OS_landuse_p, LWF_p, TCD_20_p, LCM_p, ceh_con_p, ukveg_o, ukveg_c, water_buff_p, folder)


def gbbvi(OS_landuse_path, LWF_path, TCD_20_path, LCM_path, ceh_con_path, ukveg_out, ukveg_clip, water_buff_path,folder):

    print("importing data and converting to arrays")
    # convert all rasters to numpy arrays with Gdal
    if os.path.isfile(OS_landuse_path):
        OS_landuse = gdal.Open(OS_landuse_path)
        OS_landuse_Band = OS_landuse.GetRasterBand(1)  # This is here to allow for the export at the end
        OS_landuse_Arr = BandReadAsArray(OS_landuse_Band)
        OS_landuse_Arr[OS_landuse_Arr > 5] = 999
    else:
        print("No OS Vector data for Grid {0} - Skip grid".format(folder))
        return
    if os.path.isfile(LWF_path):
        LWF = gdal.Open(LWF_path)
        LWF_Arr = np.array(LWF.GetRasterBand(1).ReadAsArray())
        LWF_Arr[LWF_Arr > 5] = 999
    else:
        print("No LWFs for Grid {0}".format(folder))

    if os.path.isfile(TCD_20_path):
        TCD_20 = gdal.Open(TCD_20_path)
        TCD_20_Arr = np.array(TCD_20.GetRasterBand(1).ReadAsArray())
        TCD_20_Arr[TCD_20_Arr > 100] = 999
    else:
        print("No Tree Cover Density data for Grid {0} - Skip grid".format(folder))
        return

    if os.path.isfile(LCM_path):
        LCM = gdal.Open(LCM_path)
        LCM_Arr = np.array(LCM.GetRasterBand(1).ReadAsArray())
        LCM_Arr[LCM_Arr > 5] = 999
    else:
        print("No Land Cover data for Grid {0} - Skip grid".format(folder))
        return
    if os.path.isfile(ceh_con_path):
        ceh_con = gdal.Open(ceh_con_path)
        ceh_con_Arr = np.array(ceh_con.GetRasterBand(1).ReadAsArray())
        ceh_con_Arr[ceh_con_Arr != 3] = 999
    else:
        print("No Conifers for Grid {0}".format(folder))

    if os.path.isfile(water_buff_path):
        wat_buf = gdal.Open(water_buff_path)
        wat_buf_Arr = np.array(wat_buf.GetRasterBand(1).ReadAsArray())
        wat_buf_Arr[wat_buf_Arr != 1] = 0
    else:
        print("No Water for Grid {0}".format(folder))
        return

    print("running Tree Cover Density recalculation")

    TCD_20_Arr[np.isnan(TCD_20_Arr)] = 0
    TCD_20_Arr[TCD_20_Arr == 0] = 0
    TCD_20_Arr[TCD_20_Arr > 100] = 0
    TCD_20_Arr[(TCD_20_Arr > 0) & (TCD_20_Arr < 3)] = 1
    TCD_20_Arr[(TCD_20_Arr >= 3) & (TCD_20_Arr < 10)] = 2
    TCD_20_Arr[(TCD_20_Arr >= 10) & (TCD_20_Arr < 50)] = 3
    TCD_20_Arr[(TCD_20_Arr >= 50) & (TCD_20_Arr <= 100)] = 4 # Consider upping this to 5 now that we have the conif layer
    # tcd_a = TCD_20_Arr

    print("running primary BVI")

    vegval = np.zeros_like(OS_landuse_Arr)  # create a new np array of equal size to rasters

    vegval[TCD_20_Arr == 0] = LCM_Arr[TCD_20_Arr == 0]
    vegval[(TCD_20_Arr > 0) & (TCD_20_Arr <= 5)] = TCD_20_Arr[(TCD_20_Arr > 0) & (TCD_20_Arr <= 5)]
    if os.path.isfile(LWF_path):
        vegval[(LWF_Arr > 0) & (LWF_Arr <= 5)] = LWF_Arr[(LWF_Arr > 0) & (LWF_Arr <= 5)]
    vegval[OS_landuse_Arr <= 5] = OS_landuse_Arr[OS_landuse_Arr <= 5]

    print("running secondary BVI")
    vegval[(vegval < LCM_Arr)] = LCM_Arr[(vegval < LCM_Arr)] # This is a problem
    vegval[LCM_Arr > 5] = 0
    if os.path.isfile(LWF_path):
        vegval[vegval < LWF_Arr] = LWF_Arr[vegval < LWF_Arr]
    if os.path.isfile(ceh_con_path):
        vegval[(vegval <= TCD_20_Arr) & (ceh_con_Arr != 3)] = TCD_20_Arr[(vegval <= TCD_20_Arr) & (ceh_con_Arr != 3)] # be aware that if we don't make cehcon 3 in prior script this will fail
    vegval[OS_landuse_Arr < 1] = OS_landuse_Arr[OS_landuse_Arr < 1]

    print("exporting BVI Raster to " + str(ukveg_out))
    driver = gdal.GetDriverByName("GTiff")
    gb_bvi = driver.Create(ukveg_out, OS_landuse.RasterXSize, OS_landuse.RasterYSize, 1, OS_landuse_Band.DataType)
    CopyDatasetInfo(OS_landuse, gb_bvi)
    bandOut = gb_bvi.GetRasterBand(1)
    BandWriteArray(bandOut, vegval)

    print("BVI Raster for OS GRID {0} exported".format(folder))

    # Here we need to clip the BVI to the buffered area
    print("cropping area outside buffer for OS {0}".format(folder))
    vegval[wat_buf_Arr != 1] = 0

    print("exporting BHI Raster to " + str(ukveg_clip))
    driverc = gdal.GetDriverByName("GTiff")
    gb_bvic = driverc.Create(ukveg_clip, OS_landuse.RasterXSize, OS_landuse.RasterYSize, 1, OS_landuse_Band.DataType)
    CopyDatasetInfo(OS_landuse, gb_bvic)
    bandOutc = gb_bvic.GetRasterBand(1)
    BandWriteArray(bandOutc, vegval)

    print("BHI Raster for OS GRID {0} exported".format(folder))


    # Close the data sets
    OS_landuse_Band = None
    OS_landuse = None
    LWF = None
    TCD_20 = None
    LCM = None
    ceh_con = None
    bandOut = None
    gb_bvi = None
    bandOutc = None
    gb_bvic = None
    wat_buf = None

    print(datetime.now() - startTime)
    print("output created in: " + str(ukveg_out))

# if __name__ == '__main__':
#     main()

