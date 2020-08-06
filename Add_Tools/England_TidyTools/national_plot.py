import geopandas as gpd
import os
import pandas as pd
from matplotlib import pyplot as plt
from glob import glob
from matplotlib import colors
from matplotlib import rc
from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
from matplotlib.lines import Line2D
from matplotlib import rcParams
import numpy as np


def main():
    root = os.path.abspath('D:/HG_Work/GB_Beaver_Data/ENGLAND_BDC_Tidy/BDC_RBD')
    save_img = os.path.abspath('D:/HG_Work/GB_Beaver_Data\ENGLAND_BDC_Tidy/Example_Maps/England_BDC.jpg')

    print('collecting features...')

    shp_list = glob(os.path.join(root, '*_BDC', '*_BDC.shp'))

    bdc_gdf = merge_bdc_gdf(feature_list=shp_list)

    plot_bdc_map(bdc_gdf, save_img)

    print('PAUSE...')

def plot_bdc_map(Nat_bdc_gdf, save_path):
    print('set up axis...')
    set_style()
    colmap, norms = create_col_map()

    fig, ax = plt.subplots()
    ax.set_yticklabels([])
    ax.set_xticklabels([])
    ax.tick_params(axis=u'both', which=u'both', length=0)
    ax.set_facecolor('white')
    ax.axis('off')

    print('creating geopandas plot...')
    Nat_bdc_gdf.plot(column='BDC', ax=ax, legend=False, linewidth=0.1, cmap=colmap, norm=norms)

    legend_elements = [Line2D([0], [0], color='black', lw=2),
                       Line2D([0], [0], color='#DC7011', lw=2),
                       Line2D([0], [0], color='#FEF30F', lw=2),
                       Line2D([0], [0], color='#5CE506', lw=2),
                       Line2D([0], [0], color='#1173F3', lw=2)]

    print('Adding map features: legend, N arrow, scalebar')

    ax.legend(handles=legend_elements,
              labels=['None: 0', 'Rare: 0-1', 'Occasional: 1-4','Frequent: 4-15', 'Pervasive: 15-30'],
              loc='upper left',
              title='Beaver Dam Capacity (dams/km)',
              framealpha=0,
              edgecolor=None,
              fontsize='x-small',
              title_fontsize=9)._legend_box.align='left'

    x, y, arrow_length = 0.95, 0.98, 0.15
    ax.annotate('N', xy=(x, y), xytext=(x, y - arrow_length),
                arrowprops=dict(facecolor='black', width=2, headwidth=7),
                ha='center', va='center', fontsize=15,
                xycoords=ax.transAxes)

    scalebar = AnchoredSizeBar(ax.transData, size=200000, label = '200 km', loc='lower center',
                               frameon=False)
    ax.add_artist(scalebar)

    print('show plot...')
    fig.tight_layout()
    fig.show()

    print('save plot...')
    fig.savefig(fname=save_path, dpi=600)

def create_col_map():
    print('defining color palette')

    cmap = colors.ListedColormap(['black', '#DC7011', '#FEF30F', '#5CE506', '#1173F3'])
    boundaries = [0, 0.001, 1, 4, 15, 30]
    norm = colors.BoundaryNorm(boundaries, cmap.N, clip=True)

    return cmap, norm

def set_style():

    font = {'family': 'Tahoma',
            'weight': 'ultralight',
            'size': 10}
    rc('font', **font)
    rcParams['figure.figsize'] = 5, 5.5


def merge_bdc_gdf(feature_list):
    """function to return merged gdf from list of shp file paths"""

    return pd.concat([gpd.read_file(shp)
                      for shp in feature_list],
                     sort=True).pipe(gpd.GeoDataFrame)





if __name__ == '__main__':
    main()
