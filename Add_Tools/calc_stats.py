import geopandas as gpd
import os
import pandas as pd
from glob import glob

from datetime import datetime
startTime = datetime.now()


def concat_gdf_list(f_list):
    """function to join a list of features to single GeoDataFrame"""
    print('merging features...')

    gdf_join = pd.concat([
        gpd.read_file(shp)
        for shp in f_list
    ], ignore_index=True)

    gdf_join = gdf_join.reset_index(drop=True)

    # Add stats calculation here as needed...
    ndams = round(gdf_join['Est_nDam'].sum(), 2)
    ndamsll = round(gdf_join['Est_nDamLC'].sum(), 2)
    ndamsul = round(gdf_join['Est_nDamUC'].sum(), 2)

    print("NUmer of output features is:   {0} \n".format(len(gdf_join.index)))

    print('Total Number of GB dams is: \n'
          '{0} 95% CI [{1}, {2}]'.format(ndams, ndamsll, ndamsul))

    return gdf_join

if __name__ == '__main__':
    """The call to the main function"""
    path_root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/BeaverNetwork_GB_v2_0')

    feature_list = glob(os.path.join(path_root, 'Op_Catch_*', 'BDC_OC*', 'Output_BDC_OC*.gpkg'))

    concat_gdf_list(feature_list)