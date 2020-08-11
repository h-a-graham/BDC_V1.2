import geopandas as gpd
from glob import glob
import os
import re


def join_gpkg_layers(root, gpkg_name, prefix):
    print('joining GPKG layers')

    feature_list = glob(os.path.join(root, 'Op_Catch_*', 'BDC_OC*', 'Output_BDC_OC*.gpkg'))

    if gpkg_name.endswith('.gpkg'):
        pass
    else:
        gpkg_name = gpkg_name + '.gpkg'

    gpkg_save = os.path.join(root, gpkg_name)

    try:
        os.remove(gpkg_save)
    except OSError:
        pass

    for i in feature_list:
        id = int(re.search('Output_BDC_OC(.+?).gpkg', i).group(1)) - 1000
        lyr_name = prefix + '_' + str(id)

        gdf = gpd.read_file(i)
        gdf.to_file(gpkg_save, driver='GPKG', layer=lyr_name)


