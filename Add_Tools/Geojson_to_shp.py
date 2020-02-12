import geopandas as gpd
import os
import glob


def main():
    gjf = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/GB_Beaver_modelling/OS_Grids")
    outfold = os.path.join(gjf, "shps_out")
    if os.path.isdir(outfold):
        print("output folder already exists")
    else:
        print("create output folder")
        os.makedirs(outfold)

    print("get glob")
    file_search = os.path.join(gjf, "*.geojson")
    gjs = glob.glob(file_search, recursive=True)

    for file in gjs:
        fname = file[-22:-8]
        print(fname)
        out_file = os.path.join(outfold, fname + ".shp")
        gp_df = gpd.read_file(file, driver="GeoJSON")

        gp_df.to_file(out_file, driver = "ESRI Shapefile")

    print("converting Geojson to ESRI shp file")


if __name__ == '__main__':
    main()
