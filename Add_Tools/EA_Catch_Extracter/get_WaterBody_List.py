import urllib.request
import os
import geopandas as gpd
import geojson
import pandas as pd
import json
import matplotlib.pyplot as plt
import sys


def getWaterBodies(catch_type, catch_num):
    with urllib.request.urlopen("https://environment.data.gov.uk/"
                                "catchment-planning/so/{0}/{1}/water-bodies".format(catch_type, str(catch_num)) + ".json") as urlmet:
        metdata = json.loads(urlmet.read().decode())

        metpand = pd.DataFrame(metdata["items"])

        wb_list = list(metpand['waterBodyNotation'])
        print(wb_list)
        return wb_list


# getWaterBodies('OperationalCatchment', '3536')
# getWaterBodies('ManagementCatchment', '3081')
# getWaterBodies('RiverBasinDistrict', '8')
