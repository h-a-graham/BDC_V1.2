# Idea of this script is to automate the preprocessing needed before doing the validation in R.
# Main things are to snap dam locations to rivers and spatial join. Then need to calculate the dam n dams per reach and
# density of dams per reach.

import os
import pandas as pd
import geopandas as gpd
from shapely.ops import snap
import matplotlib.pyplot as plt

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

OutFold = os.path.abspath('C:/Users/hughg/Desktop/GB_Beaver_modelling/BDC_Validation')


Comb = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                      "ValidationAreas/Op_Catch_1001/BDC_OC1001/Output_BDC_OC1001.shp")
CombDams = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Dam_Locs/Comb_Damsrp.shp")
CombFeed = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Feeding_Signs/ComHead_FS.shp")

Otter = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                       "ValidationAreas/Op_Catch_1002/BDC_OC1002/Output_BDC_OC1002.shp")
OttDams = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Dam_Locs/Otter_Damsrp.shp")
OttFeed = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Feeding_Signs/RivOtter_FS.shp")


Tay = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/"
                         "ValidationAreas/Op_Catch_1003/BDC_OC1003/Output_BDC_OC1003.shp")
# TayDams = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Dam_Locs/Tay_Damsrp.shp")
TayDams = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Dam_Locs/Tay_DamsrpNoBamff.shp") # No Bamff
# TayFeed = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Feeding_Signs/Tay_FSrp.shp")
TayFeed = os.path.abspath("C:/Users/hughg/Desktop/ReRun_BHI_BDC_Analysis/Feeding_Signs/Tay_FSrpNoBamff.shp") # No Bamff

# order of next line is important - do not change
CatchList = [(Comb, CombDams, 'ComHead', CombFeed),
             (Otter, OttDams, 'Otter', OttFeed),
             (Tay, TayDams, 'Tay', TayFeed)]


def main():
    print("running Prep Script for Stats and BDC validation")

    damList = []
    reachList = []
    counter = 0
    for i in CatchList:
        counter += 1

        damsOut, network_ndams = ProcDamLocs(i[1], i[0])

        damsOut['Catchment'] = i[2]
        network_ndams['Catchment'] = i[2]

        damList.append(damsOut)
        # reachList.append(network_ndams)

        actReachNet = ProcActReaches(network_ndams, i[3])

        reachList.append(actReachNet)

    allDams = pd.concat(damList, sort=False)
    allReaches = pd.concat(reachList, sort=False)



    DsaveLoc = os.path.join(OutFold, "AllDams_noBamff.csv")
    RsaveLoc = os.path.join(OutFold, "AllReaches_noBamff.csv")

    allDams.to_csv(path_or_buf=DsaveLoc, index=False)
    allReaches.to_csv(path_or_buf=RsaveLoc, index=False)


def ProcDamLocs(points, lines):

    lnsgdf = gpd.read_file(lines)
    lnsgdf['reach_no'] = lnsgdf.index + +1
    crs = lnsgdf.crs
    pntsgdf = gpd.read_file(points)
    pntsgdf.to_crs = crs

    spatial_index = lnsgdf.sindex

    snapDamLocs = snapPointsToLines(pntsgdf, lnsgdf, spatial_index)

    snapDamLocs['dam_num'] = snapDamLocs.index + 1

    snapDamLocs.crs = crs

    plt.show()

    sjoinList = []

    for index, shp in snapDamLocs.iterrows():
        pntgdf = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry']), columns=['geometry'])
        pntgdf['dam_num'] = shp['dam_num']
        pntgdf.crs = crs
        buffer = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry'].buffer(50)), columns=['geometry'])
        buffer['dam_num'] = shp['dam_num']
        buffer.crs = crs

        sbuffer = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry'].buffer(0.1)), columns=['geometry'])
        sbuffer['dam_num'] = shp['dam_num']
        sbuffer.crs = crs

        possible_matches_index = list(spatial_index.intersection(buffer.bounds.iloc[0]))
        possible_matches = lnsgdf.loc[possible_matches_index]
        possible_matches.crs = crs
        possible_matches.intersects(buffer.geometry)
        # print(sbuffer.intersects(possible_matches.geometry).values[0])
        for i, row in possible_matches.iterrows():

            gdf = gpd.GeoDataFrame(possible_matches.iloc[possible_matches.index == i])

            if sbuffer.intersects(row.geometry).values[0]:
                # print("Yeah")
                sJoin = gdf.drop(['geometry'], axis=1)
                sJoin['dam_num'] = shp['dam_num']
                pntgdf = sJoin.merge(pntgdf, on='dam_num')
                break

        sjoinList.append(pntgdf)

    damLoc_Sjoin = gpd.GeoDataFrame(pd.concat(sjoinList), geometry='geometry', crs=crs)
    damLoc_Sjoin = damLoc_Sjoin.reset_index(drop=True)

    buckets = [0, 0.001, 1, 4, 15, 35]
    buckets_name = ['None', 'Rare', 'Mod', 'Freq', 'Perv']

    damLoc_Sjoin['Categ'] = pd.cut(damLoc_Sjoin['BDC'], buckets, labels=buckets_name)


    base = lnsgdf.plot(color='grey', linewidth=0.5)

    damLoc_Sjoin.plot(ax=base, marker='o', column='reach_no', markersize=2)
    plt.show()

    fig, ax = plt.subplots()
    damLoc_Sjoin['Categ'].value_counts().plot(ax=ax, kind='bar')
    plt.show()

    reaches_ndams = nDamsPerReach(damLoc_Sjoin, lnsgdf)

    return damLoc_Sjoin, reaches_ndams


def ProcActReaches(riv_net, feedlocs):
    print("defining active reaches")
    feedpoints = gpd.read_file(feedlocs)
    riv_net['Active'] = 0

    spatial_index = riv_net.sindex

    fs_snap = snapPointsToLines(feedpoints, riv_net, spatial_index)

    # sjoinList = []

    for index, shp in fs_snap.iterrows():
        pntgdf = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry']), columns=['geometry'])
        # pntgdf['reach_no'] = shp['reach_no']
        pntgdf.crs = riv_net.crs
        buffer = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry'].buffer(50)), columns=['geometry'])
        # buffer['reach_no'] = shp['reach_no']
        buffer.crs = riv_net.crs

        sbuffer = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry'].buffer(0.1)), columns=['geometry'])
        # sbuffer['reach_no'] = shp['reach_no']
        sbuffer.crs = riv_net.crs

        possible_matches_index = list(spatial_index.intersection(buffer.bounds.iloc[0]))
        possible_matches = riv_net.loc[possible_matches_index]
        possible_matches.crs = riv_net.crs
        possible_matches.intersects(buffer.geometry)
        # print(sbuffer.intersects(possible_matches.geometry).values[0])
        for i, row in possible_matches.iterrows():

            # gdf = gpd.GeoDataFrame(possible_matches.iloc[possible_matches.index == i])

            if sbuffer.intersects(row.geometry).values[0]:
                # print("Yeah")

                riv_net.iloc[i, riv_net.columns.get_loc('Active')] = 1

                # sJoin = gdf.drop(['geometry'], axis=1)
                # sJoin['dam_num'] = shp['dam_num']
                # pntgdf = sJoin.merge(pntgdf, on='dam_num')
                # break

        # sjoinList.append(pntgdf)
        # rivnet_Act = gpd.GeoDataFrame(pd.concat(sjoinList), geometry='geometry', crs=riv_net.crs)

    riv_net.plot(column='Active')
    plt.show()
    print("endthing")

    return riv_net


def nDamsPerReach(dams_gdf, reaches_gdf):

    group_dams = pd.DataFrame()
    group_dams['n_dams'] = dams_gdf['reach_no'].value_counts()
    group_dams['reach_no'] = group_dams.index


    newdf = gpd.GeoDataFrame(pd.merge(reaches_gdf, group_dams, how='left', left_index=True,
                                      right_index=False, on='reach_no'), geometry='geometry', crs=reaches_gdf.crs)

    newdf['n_dams'] = newdf['n_dams'].fillna(value=0).astype('int64')
    newdf = newdf.reset_index(drop=True)

    return newdf


def snapPointsToLines(pointsgdf, linesgdf, spat_index):
    # spatial_index = linesgdf.sindex
    snaplocList = []

    for index, shp in pointsgdf.iterrows():

        pntgdf = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry']), columns=['geometry'])
        buffer = gpd.GeoDataFrame(gpd.GeoSeries(shp['geometry'].buffer(50)), columns=['geometry'])

        try:
            possible_matches_index = list(spat_index.intersection(buffer.bounds.iloc[0]))
            possible_matches = linesgdf.loc[possible_matches_index]

            shply_line = possible_matches.geometry.unary_union
            try:
                newGeom = pntgdf.apply(lambda row: shply_line.interpolate(shply_line.project(row.geometry)), axis=1)

                pntgdf['geometry'] = newGeom
                snaplocList.append(pntgdf)

            except TypeError as te:
                print(te)
                print('index = {0}'.format(index))
                # pass
            # print(newGeom)
        except AssertionError as ae:
            print(ae)
            print('index = {0}'.format(index))



    snapPntLocs = pd.concat(snaplocList)
    snapPntLocs = snapPntLocs.reset_index(drop=True)

    return snapPntLocs

if __name__ == '__main__':
    main()

