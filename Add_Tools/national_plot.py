import geopandas as gpd
import os
import pandas as pd
from matplotlib import pyplot as plt
from glob import glob

root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Out')
save_img = os.path.abspath('D:/GoogleDrive/Cool_Maps/England_StreamPower.jpg')


def main():
    print('collecting features...')

    feature_list = glob(os.path.join(root, 'Op_Catch_*', 'BDC_OC*', 'Output_BDC_OC*.shp'))

    Nat_bdc_gdf = pd.concat([
        gpd.read_file(shp)
        for shp in feature_list
    ], sort=True).pipe(gpd.GeoDataFrame)

    Nat_bdc_gdf['unit_SP'] = Nat_bdc_gdf.iHyd_SP2/Nat_bdc_gdf.iGeo_Width

    fig, ax = plt.subplots(1, 1)
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.set_facecolor('grey')
    Nat_bdc_gdf.plot(column='unit_SP', ax=ax, legend=False, linewidth=0.1, cmap='plasma', vmin=0, vmax=100)

    plt.show()

    fig.savefig(fname=save_img, dpi=600)


if __name__ == '__main__':
    main()
