# Prior to running this script I manually deleted the Southern Firth area as no beaver ativity was present there at the
# time of survey.

import os
import pandas as pd
import geopandas as gpd

Tay = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                      "ValidationAreas/Op_Catch_1005/BDC_OC1005/Output_BDC_OC1005.shp")
Earn = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                       "ValidationAreas/Op_Catch_1004/BDC_OC1004/Output_BDC_OC1004.shp")
FirthN = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                         "ValidationAreas/Op_Catch_1006/BDC_OC1006/Output_BDC_OC1006.shp")

TayWideOut = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                             "ValidationAreas/Op_Catch_1003/BDC_OC1003/Output_BDC_OC1003.shp")

def MergeyMerge():
    print("Merging Hyd Areas for Tay")
    Firth = gpd.read_file(FirthN)  # just because it's the smallest
    crs = Firth.crs
    Firth = None

    Catch_list = [Tay, Earn, FirthN]

    Tay_wider = pd.concat([
        gpd.read_file(shp)
        for shp in Catch_list
    ], sort=True).pipe(gpd.GeoDataFrame)

    Tay_wider.crs = crs

    Tay_wider.to_file(TayWideOut, driver="ESRI Shapefile")

if __name__ == '__main__':
    MergeyMerge()
