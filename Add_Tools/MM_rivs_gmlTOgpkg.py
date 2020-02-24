import geopandas as gpd
import pandas as pd
import os
import glob
from tqdm import tqdm
# from matplotlib import pyplot as plt

data_path = os.path.abspath('C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/Raw_Data/mastermap-water/2018_10/gml')
epsg = 27700


def main():
    grid_fold_list = [os.path.abspath(x) for x in glob.glob(data_path + '/*/')]

    for folder in tqdm(grid_fold_list):
        gdf_list = []

        grid_name = os.path.basename(folder)

        os.chdir(folder)
        for file in glob.glob("*.gml.gz"):
            try:
                gdf = gpd.read_file(file, layer='WatercourseLink')
                gdf.crs = "EPSG:{}".format(epsg)
                gdf_list.append(gdf)

            except Exception as e:
                pass
                # print(e)

        if len(gdf_list) > 0:
            grid_gdf = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True), crs=gdf_list[0].crs)

            save_path = os.path.join(folder, '{0}_OSMM_Rivers.gpkg'.format(grid_name))
            if os.path.isfile(save_path):
                # print("{0} Geo Package exists - deleting...")
                os.remove(save_path)

            grid_gdf.to_file(save_path, driver='GPKG')

            # grid_gdf.plot()
            #
            # plt.show()
        else:
            pass


if __name__ == '__main__':
    main()

