import urllib.request
import os
import geopandas as gpd
import geojson
import pandas as pd
import json
# import arcpy
import matplotlib.pyplot as plt
import sys
import rtree

### ISSUES: crs for output is not in OSGB and I'm struggling to set up geopandas to allow it to change -  I have use arcpy?
def main():
    # EA selected Catchments
    # catchment_list = [3549, 3367, 3336, 3359, 3045, 3334, 3155, 3123, 3493,
    #                   3498, 3261, 3423, 3282, 3243, 3251, 3157, 3111, 3029]
    # selection for Alan
    # catchment_list = [3530]

    # Kent and Leven Demo Areas for Toolboxes
    # catchment_list = [3251, 3029, 3111, 3243]

    # Management Catchments for Alan
    # catchment_list = [3060]

    # Management Catchments for Alan Batch
    catchment_list = [3089, 3043, 3036, 3028, 3085, 3026, 3029]


    #pick one of the following
    catch_type = 'ManagementCatchment'
    # catch_type = 'OperationalCatchment'

    if catch_type == 'ManagementCatchment':
        ab = 'Ma'
    elif catch_type == 'OperationalCatchment':
        ab = 'Op'
    else:
        sys.exit("set the correct catch_type")

    # gjf = os.path.abspath("C:/Users/hughg/Desktop/Alan_BDC/MC3000and3004")
    # gjf = os.path.abspath("C:/Users/hughg/Desktop/Beaver_Workshop/BHI_BDC_Demo/Shp_Files")
    # gjf = os.path.abspath("C:/Users/hughg/Desktop/GB_Beaver_modelling/EA_catchments")
    gjf = os.path.abspath("C:/HG_Projects/Hugh_BDC_Files/Alan_BDC")
    epsg_code = 27700
    outfold = os.path.join(gjf, "Alan_Batch_gpkg")

    if os.path.isdir(outfold):
        print("output folder already exists")
    else:
        print("create output folder")
        os.makedirs(outfold)


    gpd_lis = []
    for catch in catchment_list:
        with urllib.request.urlopen("https://environment.data.gov.uk/"
                                    "catchment-planning/so/{0}/".format(catch_type) + str(catch) + "/polygon") as url:
            data = geojson.loads(url.read().decode())

            with urllib.request.urlopen("https://environment.data.gov.uk/"
                                        "catchment-planning/so/{0}/".format(catch_type) + str(catch) + ".json") as urlmet:
                metdata = json.loads(urlmet.read().decode())

                metpand = pd.DataFrame(metdata["items"])
                oc = metpand.label[0]
                print(oc)

            # print(data)

            out_file = os.path.join(outfold, "{0}_catch_{1}.gpkg".format(ab, catch))
            gp_df = gpd.read_file(str(data), driver="GeoJSON")
            gp_df['id'] = catch
            gp_df['opc_NAME'] = oc
            # print(gp_df.crs)
            # dest_CRS = str(pyproj.Proj('+init=' 'epsg:' + epsg_code))
            # gp_df.to_crs('+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +units=m +no_defs')
            # gp_df.to_crs({'init': 'epsg:' + epsg_code})
            # print(gp_df.crs)
            gpd_lis.append(gp_df)
            gp_df.crs = {'init': 'epsg:4326'}

            gp_df = gp_df.to_crs({'init': 'epsg:{}'.format(epsg_code)})
            gp_df.to_file(out_file, driver="GPKG")

    out_f = os.path.join(outfold, "{0}_catchments_All.gpkg".format(ab))
    print("merging all catchments")
    rdf = gpd.GeoDataFrame(pd.concat(gpd_lis, ignore_index=True),
                           crs=gpd_lis[0].crs)


    # print(rdf.crs)
    # print(rdf)


    print('.shp format selected - reproject to epsg: {}'.format(epsg_code))

    rdf.crs = {'init': 'epsg:4326'}

    rdf = rdf.to_crs({'init': 'epsg:{}'.format(epsg_code)})

    rdf.to_file(out_f, driver="GPKG")

    check_gdf = gpd.read_file(out_f, driver="GPKG")
    check_gdf.plot(column='opc_NAME')
    plt.show()
    print(check_gdf.crs)

if __name__ == '__main__':
    main()
