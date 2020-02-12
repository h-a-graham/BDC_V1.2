# import numpy as np
import os
# from pathlib import Path
import geopandas as gpd
import pandas as pd
# import osr
# import rasterio
# from rasterio import features
# from datetime import datetime
import shapely
from shapely.geometry import Polygon
from io import StringIO

OrdSurv_Grid = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/OS_Grids/100km_grid_region.shp")

ordsurv_gp = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")

for index, row in ordsurv_gp.iterrows():

    grid_name = row['GRIDSQ']
    # print(index)
    # print(row['GRIDSQ'])

    # row['geometry'] = row['geometry'].apply(Polygon)

    # newdata = pd.Series.to_frame(row)
    # newshape = Polygon(newdata['geometry'])
    # print(newdata)
    # print(newshape)
    other_df = gpd.GeoDataFrame(ordsurv_gp.loc[ordsurv_gp['GRIDSQ'] == grid_name], geometry='geometry')
    print(other_df)
    # newdata['geometry'] = newdata['geometry'].apply(Polygon)
    # print(newdata)
    # grid_area = gpd.GeoDataFrame(newdata, geometry='geometry')
    # print(grid_area)

    # lcm_selec = gpd.overlay(lcm_map_gp, feature, how='intersection')