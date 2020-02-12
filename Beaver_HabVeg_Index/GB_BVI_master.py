# This script will run all necessary commands to generate BVI for GB from raw data inputs.
import os
import OS_Vector_PP
import TCD_Map_PrePro
import CEH_LCM_PrePro
import LWF_CEH_PP_arcpy
# import Convert_MM_rivers
import Water_Area_Buffer
import merge_resamp_BVI
import BHI_Exports
import GB_BVI

def main():
    #working directories
    scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")
    exports = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Res_v2")

    # data directories
    OrdSurv_fold = os.path.abspath("D:/Work/GB_Beaver_Data/Edina/OS_Vector")
    Ordnan_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp")
    tcd_cop_fold = "C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/TCD_Data"
    LCM_data = os.path.abspath("D:/Work/GB_Beaver_Data/Data/lcm-2015-vec_1904131/LCM2015_GB.gdb/LCM2015GBvector")
    LWF_data = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/GB_WLF_V1_0.gdb/GB_WLF_V1_0")
    rivers_folder = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")

    #project variables
    epsg_code = str(27700)
    buff_size = 100

    # OS_Vector_PP.OS_Vec_main(epsg_code, OrdSurv_fold, exports, Ordnan_Grid)
    #
    # TCD_Map_PrePro.tcd_main(scratch, exports, tcd_cop_fold, Ordnan_Grid, epsg_code)
    #
    # CEH_LCM_PrePro.lcm_main(epsg_code, LCM_data, Ordnan_Grid, scratch, exports) # Now working.
    #
    # LWF_CEH_PP_arcpy.lwf_main(epsg_code, LWF_data, Ordnan_Grid, exports, scratch)

    # Convert_MM_rivers.MM_conv_main(riv_line_fold, scratch) # bit complex and long best to run in advance...

    # Water_Area_Buffer.riv_area_main(buff_size, epsg_code, rivers_folder, scratch, exports, Ordnan_Grid)

    # GB_BVI.main(exports)   #
    # merge_resamp_BVI.mer_res_main(exports, epsg_code)
    BHI_Exports.exports_main(exports)


if __name__ == '__main__':
    main()

