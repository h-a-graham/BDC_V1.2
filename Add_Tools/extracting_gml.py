import os
import geopandas as gpd
import matplotlib.pyplot as plt
home = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/mastermap_ext_reworking/tf")

file_list = os.listdir(home)

gml = file_list[0]
gml_dir = os.path.join(home,gml)
gdf = gpd.read_file(gml_dir)

gdf.plot()
plt.show()

import gzip
import shutil
with gzip.open(gml_dir, 'rb') as f_in:
    print(f_in)
    for i in f_in:
        gdf = gpd.read_file(i)
        print(gdf)
    for i in f_in:
        print(i)
    with open('file.txt', 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)