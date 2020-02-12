import rasterio
from rasterio.merge import merge
from rasterio.crs import CRS
import os
import glob
from datetime import datetime
startTime = datetime.now()


def dtm_combineMain():
    print("running script to combine DTM files into OS GRID tiles")
    print("start time = {0}".format(startTime))

    dtm_root = os.path.abspath("D:/Work/GB_Beaver_Data/Edina/exu-hg-t5dtm/terrain-5-dtm/asc")
    epsg_code = str(27700)

    os_tileList = next(os.walk(dtm_root))[1]

    for tile in os_tileList:
        # if tile == 'sy' or tile == 'ss' or tile == 'st'or tile == 'sw':
        print("combinings asc DTM files for OS Grid {0}".format(tile))

        file_search = os.path.join(dtm_root, tile, "*.asc")
        ascFiles = glob.glob(file_search, recursive=True)

        print(ascFiles)

        outRas = os.path.join(dtm_root, tile, "{0}_DTM_5m.tif".format(tile))

        run_merge(ascFiles, outRas, epsg_code)

    print("script finished at {0}".format(datetime.now()))
    print("Total Run Time = {0}".format(datetime.now() - startTime))


def run_merge(ascfiles, out_ras, epsg):

    print("running raster merge...")

    print("loading files into rasterio")
    src_files_to_mosaic = []
    for fp in ascfiles:
        src = rasterio.open(fp)
        src_files_to_mosaic.append(src)
    print("merging rasters")
    mosaic, out_trans = merge(src_files_to_mosaic)

    # show(mosaic, cmap='viridis')

    print("preparing output raster")
    out_meta = src.meta.copy()

    out_meta.update({"driver": "GTiff", "height": mosaic.shape[1], "width": mosaic.shape[2], "transform": out_trans,
                     "crs": CRS.from_epsg(epsg), "compress": "lzw"})

    print("exporting output raster")
    with rasterio.open(out_ras, "w", **out_meta) as dest:
        dest.write(mosaic)


if __name__ == '__main__':
    dtm_combineMain()