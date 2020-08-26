from Beaver_Dam_Cap import Dataset_Prep
from Beaver_Dam_Cap import SplitLinesGeoPand
from Beaver_Dam_Cap import BDC_Terrain_Processing
from Beaver_Dam_Cap import BDC_tab_GEoPand
from Beaver_Dam_Cap import Veg_FIS
from Beaver_Dam_Cap import iHyd
from Beaver_Dam_Cap import Comb_FIS
from Beaver_Dam_Cap import Add_Stats
from Beaver_Dam_Cap.CombineGpks import join_gpkg_layers

import os

from datetime import datetime

def main():
    startTime = datetime.now()
    print(startTime)

    # ------------- Don't edit:
    rivers_root = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")

    dem_path = os.path.abspath("D:/HG_Work/GB_Beaver_Data/Data/Edina/exu-hg-t5dtm/terrain-5-dtm/asc")

    bvi_etc_root = os.path.abspath("D:/HG_Work/GB_Beaver_Data/GB_BVI_Res_v2")

    # ---------------- Edit:
    # operCatch = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/"
    #                             "CEH_catchments/GB_CEH_HAs_V2.gpkg")
    # outRoot = os.path.abspath("D:/HG_Work/GB_Beaver_Data/BeaverNetwork_GB")
    #
    # OutGpkgName = 'BeaverNetwork_GB'

    operCatch = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/"
                                "CEH_catchments/TEST_ExeGroup.gpkg")

    outRoot = os.path.abspath("D:/HG_Work/GB_Beaver_Data/Test_CASE")

    OutGpkgName = 'BeaverNetwork_ExeGroup'

    epsg_code = str(27700)

    prep_only = False
    skip_prep = False

    # ------------------- program begins:
    if skip_prep is False:
        print("running data prep script to organise inputs for all target Dam Capacity Areas/ Catchments")
        Dataset_Prep.BDC_setup_main(rivers_root, dem_path, bvi_etc_root, operCatch, epsg_code, outRoot,
                                    id_column='HA_NUM')
    else:
        print("skipping preperation script due to skip_prep setting...")
        pass

    if prep_only is True:  # OPtion to only run the above if prep only is true - mainly for very large runs...
        print("only running prep section for now.")
        pass

    else:

        direc_list = next(os.walk(outRoot))[1]

        for direc in direc_list:

            if os.path.isfile(os.path.join(outRoot, direc, "BDC_OC{0}/Output_BDC_OC{0}.gpkg".format(direc[-4:]))):
                print("Operational Catchment {0} already completed - pass".format(direc[-4:]))
            else:
                ocNum = direc[-4:]
                print("running BDC pipeline for Operational Catchment {0}".format(ocNum))
                home = os.path.join(outRoot, direc)
                raw_lines = os.path.join(home, "OC{0}_MM_rivers.gpkg".format(ocNum))

                split_lines = os.path.join(home, "BDC_reaches.gpkg")

                if os.path.isfile(split_lines):
                    print("working reaches already exist, skip split lines")
                else:
                    print("running line splitting tool")
                    SplitLinesGeoPand.main(home, raw_lines, epsg_code)


                DEM_path = os.path.join(home, "OC{0}_DTM.tif".format(ocNum))  # Below commented out for testing split lines
                in_waterArea = os.path.join(home, "OC{0}_OS_InWater.gpkg".format(ocNum))
                BVI_raster = os.path.join(home, "OC{0}_BVI.tif".format(ocNum))

                gdb_name = "scratch_OC{0}".format(ocNum)
                scratch_gdb = os.path.join(home, gdb_name)
                if os.path.exists(scratch_gdb):
                    print("scratch gdb exists")
                else:
                    # os.mkdir(scratch_gdb)
                    os.mkdir(os.path.join(home, gdb_name))
                #
                print("runnning BDC data extraction script")
                DEM_burn = os.path.join(home, "BDC_OC{0}strBurndDEm.tif".format(ocNum))
                DrAreaRas = os.path.join(home, "DrainArea_sqkm.tif")
                spltLinesP2 = os.path.join(scratch_gdb, "seg_network_b.gpkg")

                paramList = [DEM_burn, DrAreaRas, spltLinesP2]
                for p in paramList:
                    if os.path.exists(p) is False:
                        print()
                        BDC_Terrain_Processing.main(home, scratch_gdb, split_lines, DEM_path, epsg_code)
                    else:
                        print('{0} aready exitst! woop'.format(p))

                bdc_gdf, bdc_net = BDC_tab_GEoPand.main(home, spltLinesP2, DEM_burn, in_waterArea, BVI_raster, DrAreaRas) # current

                print("running Vegetation Fuzzy Inference System")
                bdc_gdf = Veg_FIS.main(bdc_gdf)

                opCatchArea = os.path.join(home, "OC{0}_catchmentArea.gpkg".format(ocNum))
                print("running Hydrological Fuzzy Inference System")
                bdc_gdf = iHyd.main(bdc_gdf, opCatchArea)

                print("running Combined Fuzzy Inference System")
                Comb_FIS.main(bdc_gdf)

                # bdc_net = os.path.join(home, "BDC_OC{0}".format(ocNum), "Output_BDC_OC{0}.gpkg".format(ocNum))

                Add_Stats.main(bdc_gdf, bdc_net)

        print('join files to multi-layer gpkg')

        join_gpkg_layers(root=outRoot, gpkg_name=OutGpkgName, prefix='BeaverNetwork_CEH_HA')


    finTime = datetime.now() - startTime
    print("Master Script Completed. \n"
          "Processing time = {0}".format(finTime))

if __name__ == '__main__':
    main()
