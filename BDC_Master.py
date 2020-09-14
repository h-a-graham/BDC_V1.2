from Beaver_Dam_Cap import Dataset_Prep
from Beaver_Dam_Cap import SplitLinesGeoPand
from Beaver_Dam_Cap import BDC_Terrain_Processing
from Beaver_Dam_Cap import BDC_tab_GEoPand
from Beaver_Dam_Cap import Veg_FIS
from Beaver_Dam_Cap import iHyd
from Beaver_Dam_Cap import Comb_FIS
from Beaver_Dam_Cap import Add_Stats
from Beaver_Dam_Cap.CombineGpks import join_gpkg_layers
from tqdm import tqdm
import multiprocessing
from functools import partial
import os

from datetime import datetime


def set_vars():
    """ function to return all user defined variables"""
    # ------------- Don't edit:
    rivers_root = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml")

    dem_path = os.path.abspath("D:/HG_Work/GB_Beaver_Data/Data/Edina/exu-hg-t5dtm/terrain-5-dtm/asc")

    bvi_etc_root = os.path.abspath("D:/HG_Work/GB_Beaver_Data/GB_BVI_Res_v2")

    r_exe = os.path.abspath("C:/Program Files/R/R-3.6.3/bin/Rscript.exe")

    osgeo_path = os.path.abspath("C:/OSGeo4W64/OSGeo4W.bat")

    # ---------------- Edit:
    operCatch = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/"
                                "CEH_catchments/GB_CEH_HAs_V2.gpkg")
    outRoot = os.path.abspath("D:/HG_Work/GB_Beaver_Data/BeaverNetwork_GB_v2_0")

    # operCatch = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/"
    #                             "CEH_catchments/TestCase2.gpkg")
    #
    # operCatch = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/"
    #                             "EA_catchments/CH_OC_Test.gpkg")
    # #
    # outRoot = os.path.abspath("D:/HG_Work/GB_Beaver_Data/Test_CASE4")

    OutGpkgName = 'BeaverNetwork_GB'
    gpkg_layer_prefix = 'BeaverNetwork_CEH_HA'

    epsg_code = str(27700)

    run_prep = False

    run_terrain = False

    id_column = 'HA_NUM'  # Set as None where no id column exists - one will be created.

    return rivers_root, dem_path, bvi_etc_root, operCatch, outRoot, OutGpkgName, epsg_code, run_prep, id_column, \
        r_exe, osgeo_path, gpkg_layer_prefix, run_terrain



def bdc_data_prep(rivers_root, dem_path, bvi_etc_root, operCatch, outRoot, epsg_code,  run_prep, id_col):
    """function to call bdc prep script"""
    if run_prep is True:
        print("running data prep script to organise inputs for all target Dam Capacity Areas/ Catchments")
        Dataset_Prep.BDC_setup_main(rivers_root, dem_path, bvi_etc_root, operCatch, epsg_code, outRoot,
                                    id_column=id_col)
    else:
        print("skipping preperation script: run_prep arg set to False")
        pass


def terrain_processing(outRoot, epsg_code, osgeo, direc):
    """ function to run terrain processing """
    # ------ Define intermediate files --------
    ocNum = direc[-4:]
    home = os.path.join(outRoot, direc)
    split_lines = os.path.join(home, "BDC_reaches.gpkg")
    raw_lines = os.path.join(home, "OC{0}_MM_rivers.gpkg".format(ocNum))

    DEM_path = os.path.join(home, "OC{0}_DTM.tif".format(ocNum))

    gdb_name = "scratch_OC{0}".format(ocNum)
    scratch_gdb = os.path.join(home, gdb_name)
    spltLinesP2 = os.path.join(scratch_gdb, "seg_network_b.gpkg")

    if os.path.isfile(split_lines):
        # working reaches already exist, skip split lines
        pass
    else:
        # run line splitting tool
        SplitLinesGeoPand.main(home, raw_lines, epsg_code)

    if os.path.exists(scratch_gdb):
        # GRASS scratch folder already exists
        pass
    else:
        os.mkdir(scratch_gdb)

    # run Terrain processing module
    if os.path.isfile(spltLinesP2):
        # Reaches with terrain data already calculated - skip region.
        pass
    else:
        BDC_Terrain_Processing.main(home, scratch_gdb, split_lines, DEM_path, epsg_code, osgeo)

    return "terrain done..."


def bdc_processing(outRoot, r_exe, pbar, direc):
    """function to call bdc processing scripts"""
    # ------ Define intermediate files --------
    ocNum = direc[-4:]
    home = os.path.join(outRoot, direc)
    opCatchArea = os.path.join(home, "OC{0}_catchmentArea.gpkg".format(ocNum))

    in_waterArea = os.path.join(home, "OC{0}_OS_InWater.gpkg".format(ocNum))
    BVI_raster = os.path.join(home, "OC{0}_BVI.tif".format(ocNum))

    gdb_name = "scratch_OC{0}".format(ocNum)
    scratch_gdb = os.path.join(home, gdb_name)

    DEM_burn = os.path.join(home, "BDC_OC{0}strBurndDEm.tif".format(ocNum))
    DrAreaRas = os.path.join(home, "DrainArea_sqkm.tif")
    spltLinesP2 = os.path.join(scratch_gdb, "seg_network_b.gpkg")

    if os.path.isfile(os.path.join(outRoot, direc, "BDC_OC{0}/Output_BDC_OC{0}.gpkg".format(direc[-4:]))):
        print("Operational Catchment {0} already completed - pass".format(direc[-4:]))
    else:

        # run buffer creation/raster stats modeule
        bdc_gdf, bdc_net = BDC_tab_GEoPand.main(home, spltLinesP2, DEM_burn, in_waterArea, BVI_raster, DrAreaRas,
                                                progress_bar=pbar)  # current

        # run Vegetation Fuzzy Inference System
        bdc_gdf = Veg_FIS.main(bdc_gdf)

        # run Hydrological Fuzzy Inference System
        bdc_gdf = iHyd.main(bdc_gdf, opCatchArea, r_exe)

        # running Combined Fuzzy Inference System
        Comb_FIS.main(bdc_gdf)

        # run module to add probability and actual dam number stats to reaches
        Add_Stats.main(bdc_gdf, bdc_net)

    return "done..."  # perhaps not required but in case the parallrun needs something returned...


def parallel_terrain(root, crs, osgeo_p, run):
    """Function to run the line splitting and terrain processing on multiple cores"""
    """Note: the limitation here is RAM not CPU with 64GB of RAM 3 cores is fine."""

    if run is True:
        direc_list = next(os.walk(root))[1]

        num_cores = 3   # testing to find the ideal number... 8 possibly on the low side ~50% RAM
        n_split = len(direc_list)
        if n_split < num_cores:
            num_cores = n_split

        function = partial(terrain_processing, root, crs, osgeo_p)

        with multiprocessing.Pool(processes=num_cores) as p:
            max_ = len(direc_list)
            with tqdm(total=max_, desc='Terrain Processing - {0} cores'.format(num_cores)) as pbar:
                for i, _ in enumerate(p.imap_unordered(function, direc_list)):
                    pbar.update()
    else:
        print('Run terrain arg set to False - skipping terrain processing...')


def once_core_terrain(root, crs, osgeo_p, run):
    """Function to run the line splitting and terrain processing on a single core"""

    if run is True:
        direc_list = next(os.walk(root))[1]

        for d in tqdm(direc_list, desc='Terrain Processing - 1 core'):
            terrain_processing(outRoot=root, epsg_code=crs, osgeo=osgeo_p, direc=d)

    else:
        print('Run terrain arg set to False - skipping terrain processing...')


def parallel_bdc(root, gpkg_n, gpkg_pref, r_exe_p):
    """Function to run the bdc processing on multiple cores"""
    """Note: cpu is main limting factor so n cpus - 1 should work fine."""

    direc_list = next(os.walk(root))[1]

    num_cores = multiprocessing.cpu_count() - 1
    n_split = len(direc_list)
    if n_split < num_cores:
        num_cores = n_split

    function = partial(bdc_processing, root, r_exe_p, True)

    with multiprocessing.Pool(processes=num_cores) as p:
        max_ = len(direc_list)
        with tqdm(total=max_, desc='BDC processing') as pbar:
            for i, _ in enumerate(p.imap_unordered(function, direc_list)):
                pbar.update()

    print('join files to multi-layer gpkg')

    join_gpkg_layers(root=root, gpkg_name=gpkg_n, prefix=gpkg_pref)


def one_core_bdc(root, gpkg_n, gpkg_pref, r_exe_p):
    """ function to run bdc processing on a single core. progress bar is initiated in the bdc_tab_GeoPand.py"""

    direc_list = next(os.walk(root))[1]

    for d in direc_list:
        bdc_processing(root, r_exe_p, pbar=False, direc=d)

    print('join files to multi-layer gpkg')

    join_gpkg_layers(root=root, gpkg_name=gpkg_n, prefix=gpkg_pref)


if __name__ == '__main__':
    startTime = datetime.now()
    print(startTime)

    riv_root, dem_p, bvi_root, Catch, o_Root, o_GpkgName, crs_code, prep, id,\
        r_exec, osgeo_bat_p, gpkg_layer_pref, run_terr = set_vars()

    bdc_data_prep(rivers_root=riv_root, dem_path=dem_p, bvi_etc_root=bvi_root,
                  operCatch=Catch, outRoot=o_Root, epsg_code=crs_code,
                  run_prep=prep, id_col=id)

    parallel_terrain(root=o_Root, crs=crs_code, osgeo_p=osgeo_bat_p, run=run_terr)
    # once_core_terrain(root=o_Root, crs=crs_code, osgeo_p=osgeo_bat_p, run=run_terr)
    # one_core_bdc(root=o_Root, gpkg_n=o_GpkgName,gpkg_pref=gpkg_layer_pref, r_exe_p=r_exec)

    parallel_bdc(root=o_Root, gpkg_n=o_GpkgName, gpkg_pref=gpkg_layer_pref, r_exe_p=r_exec)

    finTime = datetime.now() - startTime
    print("Master Script Completed. \n"
          "Processing time = {0}".format(finTime))
