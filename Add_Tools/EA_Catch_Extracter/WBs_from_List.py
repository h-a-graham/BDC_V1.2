import urllib.request
import os
import geopandas as gpd
import geojson
import pandas as pd
import json
import matplotlib.pyplot as plt
import sys

# pd.set_option('display.max_rows', 500)
# pd.set_option('display.max_columns', 500)
# pd.set_option('display.width', 1000)


### ISSUES: crs for output is not in OSGB and I'm struggling to set up geopandas to allow it to change -  I have use arcpy?
def main(catchment_list, out_file, epsg_code):
    catch_type = 'WaterBody'
    filename, file_extension = os.path.splitext(out_file)
    if file_extension == '.json' or file_extension == '.geojson':
        format = 'GeoJSON'
    elif file_extension == '.shp':
        format = 'ESRI Shapefile'
    else:
        print("can only export: GeoJSON, ESRI Shapefile")
        sys.exit()


    gpd_lis = []
    for catch in catchment_list:
        with urllib.request.urlopen("https://environment.data.gov.uk/"
                                    "catchment-planning/so/{0}/".format(catch_type) + str(catch) + "/polygon") as url:
            data = geojson.loads(url.read().decode())

            with urllib.request.urlopen("https://environment.data.gov.uk/"
                                        "catchment-planning/so/{0}/".format(catch_type) + str(catch) + ".json") as urlmet:
                metdata = json.loads(urlmet.read().decode())

                metpand = pd.DataFrame(metdata["items"])

                wb_number = metpand.currentVersion[0]['waterBodyCatchment']
                wb_name = metpand.currentVersion[0]['label']
                wb_area_km2 = metpand.characteristic[0][3]['characteristicValue']
                wb_len_km = metpand.characteristic[0][1]['characteristicValue']
                wb_op_catch = metpand.inOperationalCatchment[0]['operationalCatchmentNotation']

                with urllib.request.urlopen(metpand.inOperationalCatchment[0]['inManagementCatchment']['@id'] + ".json") as mgmturl:
                    wb_mgmt_catch = json.loads(mgmturl.read().decode())['items'][0]['managementCatchmentNotation']

                # print(oc)

            # print(data)

            # out_file = os.path.join(outfold, "{0}_{1}.geojson".format(catch_type, catch))
            gp_df = gpd.read_file(str(data), driver="GeoJSON")
            gp_df['WB_number'] = wb_number
            gp_df['WB_name'] = wb_name
            gp_df['WB_area_km2'] = wb_area_km2
            try:
                gp_df['WB_length_km'] = wb_len_km
            except ValueError:
                print("################################################################"
                      "\n Warning - an error exists in the EA Json for Water Body {0} \n"
                      "         Taking first given value for channel length \n"
                      "################################################################".format(wb_number))
                gp_df['WB_length_km'] = wb_len_km[0]
            gp_df['OC_number'] = wb_op_catch
            gp_df['MC_number'] = wb_mgmt_catch

            gpd_lis.append(gp_df)

            # gp_df.to_file(out_file, driver="GeoJSON")

    print("merging all catchments")
    if len(gpd_lis) > 1:
        rdf = gpd.GeoDataFrame(pd.concat(gpd_lis, axis=0))
    else:
        rdf = gpd_lis[0]


    # print(rdf.crs)
    # print(rdf)

    if format == 'GeoJSON':
        rdf.crs = {'init': 'epsg:4326'}
        rdf.to_file(out_file, driver="GeoJSON")
    else:
        print('.shp format selected - reproject to epsg: {}'.format(epsg_code))

        rdf.crs = {'init': 'epsg:4326'}

        rdf = rdf.to_crs({'init': 'epsg:{}'.format(epsg_code)})

        rdf.to_file(out_file, driver="ESRI Shapefile")


    check_gdf = gpd.read_file(out_file, driver="ESRI Shapefile")
    check_gdf.plot(column='WB_name')
    plt.show()

    print("done")

