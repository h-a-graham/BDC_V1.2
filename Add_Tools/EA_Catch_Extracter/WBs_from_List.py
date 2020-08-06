import urllib.request
import os
import geopandas as gpd
import geojson
import pandas as pd
import json
import matplotlib.pyplot as plt
import sys
import requests
from warnings import warn
from tqdm import tqdm
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)


### ISSUES: crs for output is not in OSGB and I'm struggling to set up geopandas to allow it to change -  I have use arcpy?
def main(catchment_list, out_file, epsg_code, catch_type):
    # catch_type = 'WaterBody'
    filename, file_extension = os.path.splitext(out_file)
    if file_extension == '.json' or file_extension == '.geojson':
        format = 'GeoJSON'
    elif file_extension == '.shp':
        format = 'ESRI Shapefile'
    elif file_extension == '.gpkg':
        format = 'GPKG'
    else:
        print("can only export: GeoJSON, ESRI Shapefile, GPKG")
        sys.exit()


    gpd_lis = []
    for catch in tqdm(catchment_list):
        poly_url = "https://environment.data.gov.uk/catchment-planning/so/{0}/{1}/polygon".format(catch_type, catch)
        with urllib.request.urlopen(poly_url) as url:
            data = geojson.loads(url.read().decode())

            m_data_url = "https://environment.data.gov.uk/catchment-planning/so/{0}/{1}.json".format(catch_type, catch)
            with requests.get(m_data_url) as urlmet:
                try:
                    metdata = urlmet.json()



                    metpand = pd.DataFrame(metdata["items"])

                    if catch_type == 'WaterBody':
                        wb_number = metpand.currentVersion[0]['waterBodyCatchment']
                        wb_name = metpand.currentVersion[0]['label']
                        wb_area_km2 = metpand.characteristic[0][3]['characteristicValue']
                        wb_len_km = metpand.characteristic[0][1]['characteristicValue']
                        wb_op_catch = metpand.inOperationalCatchment[0]['operationalCatchmentNotation']
                        with urllib.request.urlopen(
                                metpand.inOperationalCatchment[0]['inManagementCatchment']['@id'] + ".json") as mgmturl:
                            wb_mgmt_catch = json.loads(mgmturl.read().decode())['items'][0]['managementCatchmentNotation']

                    elif catch_type == 'RiverBasinDistrict':
                        wb_number = metpand['riverBasinDistrictNotation'][0]
                        wb_name = metpand['label'][0]

                    elif catch_type == 'OperationalCatchment':
                        wb_number = metpand['notation'][0]
                        wb_name = metpand['label'][0]

                    else:
                        warn('A catchment type has been provided that is not yet supported...')
                        exit()

                except Exception as e:
                    print('API Error - likely that Metadata is not available - will return geometry only.')

                    wb_number = str(catch)
                    wb_name = ""

            gp_df = gpd.read_file(str(data), driver="GeoJSON")
            gp_df['WB_number'] = wb_number
            gp_df['WB_name'] = wb_name

            if catch_type == 'WaterBody':
                gp_df['WB_area_km2'] = wb_area_km2
            elif catch_type == 'RiverBasinDistrict':
                gp_df = gp_df.to_crs(crs='epsg:{}'.format(epsg_code))
                gp_df['WB_area_km2'] = gp_df.area
            elif catch_type == 'OperationalCatchment':
                gp_df = gp_df.to_crs(crs='epsg:{}'.format(epsg_code))
                gp_df['WB_area_km2'] = gp_df.area

            else:
                warn("Catchment type not recognised...")
                gp_df['WB_area_km2'] = gp_df.area

            if catch_type == 'WaterBody':
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
        rdf.crs = 'epsg:4326'
        rdf.to_file(out_file, driver="GeoJSON")
    else:
        print('{0} format selected - reproject to epsg: {1}'.format(file_extension, epsg_code))

        # rdf.crs = {'init': 'epsg:4326'}

        rdf = rdf.to_crs('epsg:{}'.format(epsg_code))

        print('features now in crs: {}'.format(rdf.crs))

        if file_extension == '.gpkg':
            rdf.to_file(out_file, driver="GPKG")
        elif file_extension == '.shp':
            rdf.to_file(out_file, driver="ESRI Shapefile")
        else:
            warn('Unknown format has got through... Not saving output')

    check_gdf = gpd.read_file(out_file)
    check_gdf.plot(column='WB_name')
    plt.show()

    print("done")

