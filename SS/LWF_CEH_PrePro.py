# This script will do the pre processing of CEH's Linear Woody Framework (LWF) dataset


import osgeo
from osgeo import gdal
import numpy as np
import os
import geopandas as gpd
import osr
import rasterio
from rasterio import features
from datetime import datetime



#start timer
startTime = datetime.now()
print(startTime)


def lwf_main():
    print("running linear Woody Features pre processing")

    # set up workspace
    epsg_code = str(27700)  # this is OSGB should be no need ot change

    file_loc = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/Raw_Data/GB_WLF_V1_0.gdb")  # test

    # OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp") # all tiles
    OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/OS_Grid_test.shp")

    scratch = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/BVI_scratch")  # sctatch workspace
    if os.path.exists(scratch):
        print("scratch folder already exists")
    else:
        print("create scratch folder")
        os.makedirs(scratch)
    print("clearing out scratch space")
    for the_file in os.listdir(scratch):
        file_path = os.path.join(scratch, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            print(e)

    exports = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/CEH_LWF_export")  # export location
    if os.path.exists(exports):
        print("export folder already exists")
    else:
        print("create export folder")
        os.makedirs(exports)

    lwf_gp = lwfmapReclass(file_loc, scratch)
    print("reclassification done")

    # lwf_mapRas(lwf_gp, OrdSurv_Grid, exports, epsg_code)

    print(datetime.now() - startTime)
    print("script finished")

def lwfmapReclass(file_loc, scratch):
    print("classifying line data")

    lwf_gp = gpd.read_file(file_loc, driver='FileGDB')

    print(file_loc + " loaded")
    lwf_gp['BVI_Val'] = 4

    export_path = os.path.join(scratch + "_LWF_GB_reclass.shp")  # define the output shp file name
    lwf_gp.to_file(export_path, driver="ESRI Shapefile")

    return export_path

def lwf_mapRas(lwf_gp, OrdSurv_Grid, exports, epsg_code):
    print("convert linear woody features to raster for OS tile areas")

    ordsurv_gp = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")

    for feature, row in ordsurv_gp.iterrows():
        grid_name = row['GRIDSQ']
        print(grid_name)

        os_grid_fold = os.path.join(exports, grid_name.lower())
        if os.path.exists(os_grid_fold):
            print("OS Grid folder already exists")
        else:
            print("create OS Grid folder folder")
            os.makedirs(os_grid_fold)

        # grid_area = row['geometry']
        grid_area = gpd.GeoDataFrame(ordsurv_gp.loc[ordsurv_gp['GRIDSQ'] == grid_name],
                                     geometry='geometry', crs={'init': 'epsg:' + epsg_code})

        # lwf_selec = gpd.overlay(lwf_gp, grid_area, how='intersection')
        lwf_selec = gpd.sjoin(lwf_gp, grid_area, op='intersects')
        minx, miny, maxx, maxy = lwf_selec.geometry.total_bounds

        print(minx)
        print(miny)
        print(maxx)
        print(maxy)


        lwf_selec = lwf_gp.intersection(grid_area.unary_union)
        print(lwf_selec.geometry.total_bounds)
        export_path = os.path.join(os_grid_fold, grid_name + "_LWF_test.shp")  # define the output shp file name
        lwf_selec.to_file(export_path, driver="ESRI Shapefile")  # export OSGB feature to shp file - not required but can be useful for debugging
        print("creating template Raster file")
        # convert merged shp file to Raster
        minx, miny, maxx, maxy = lwf_selec.geometry.total_bounds  # get boundary of shapefile

        rast_res = 5  # desired resolution of rasters
        dist_width = maxx - minx
        width = int(round(dist_width) / rast_res)

        dist_height = maxy - miny
        height = int(round(dist_height) / rast_res)

        format = "GTiff"
        driver = gdal.GetDriverByName(format)

        ras_exp_path = os.path.join(os_grid_fold, grid_name + "_CEH_LCM_BVI_5m.tif")
        print(ras_exp_path)
        ras_template = driver.Create(ras_exp_path, width, height, 1, gdal.GDT_Int16, ['COMPRESS=LZW'])
        print("template created")
        geotransform = ([minx, rast_res, 0, maxy, 0, -rast_res])

        ras_template.SetGeoTransform(geotransform)
        print("geotransformed")

        srs = osr.SpatialReference()
        srs.ImportFromEPSG(int(epsg_code))
        ras_template.SetProjection(srs.ExportToWkt())
        print("projection set")

        raster = np.full((height, width), 99, dtype=np.int8, )
        print("numpy array created")
        # raster[...] = 99

        ras_template.GetRasterBand(1).WriteArray(raster)
        print("numpy array set to raster")

        ras_template = None

        # print("opening template in rasterio")
        # rst = rasterio.open(ras_exp_path)
        #
        # meta = rst.meta.copy()
        # meta.update(compress='lzw')
        #
        # rst = None
        #
        # print("rasterizing Features")
        #
        # with rasterio.open(ras_exp_path, 'r+', **meta) as out:
        #     out_arr = out.read(1)
        #
        #     # this is where we create a generator of geom, value pairs to use in rasterizing
        #     shapes = ((geom, value) for geom, value in zip(lwf_selec.geometry, lwf_selec.BVI_Val))
        #
        #     burned = features.rasterize(shapes=shapes, fill=0, out=out_arr, transform=out.transform)
        #     out.write_band(1, burned)
        # out = None

if __name__ == '__main__':
    lwf_main()
