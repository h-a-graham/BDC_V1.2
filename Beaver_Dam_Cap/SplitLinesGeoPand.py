
import os
import geopandas as gpd
from shapely.geometry import Point, LineString
import sys

def main(home, rivers, epsg):
    rivers_gpd = gpd.read_file(rivers)

    # print(rivers_gpd.geometry.length.sum())
    # print(len(rivers_gpd.index))
    # print(rivers_gpd.geometry.length.max())

    split_gdf = split_recurs(rivers_gpd)

    split_gdf.crs = ({'init': 'epsg:' + epsg})

    # print(split_gdf.geometry.length.sum())
    # print(len(split_gdf.index))
    # print(split_gdf.geometry.length.max())

    split_gdf.to_file(os.path.join(home, "BDC_reaches.gpkg"))


def split_recurs(line_gdf):


    bare_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(line_gdf.geometry))
    bare_gdf = bare_gdf.explode()
    lineslist = []
    for i in range(0, len(bare_gdf.index)):
        line_2d = LineString([xy[0:2] for xy in list(bare_gdf.geometry.iloc[i].coords)])
        lineslist.append(line_2d)

    fixed_lines = itersplit(lineslist)

    fixed_gdf = gpd.GeoDataFrame(geometry=gpd.GeoSeries(fixed_lines))

    fixed_gdf['reach_length'] = fixed_gdf.geometry.length

    return fixed_gdf


def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
            LineString([(cp.x, cp.y)] + coords[i:])]


def itersplit(l_list):
    for idx, shape in enumerate(l_list):

        line_leng = l_list[idx].length

        if line_leng > 200:
            line1, line2 = cut(l_list[idx], line_leng/2)

            del l_list[idx]

            l_list.append(line1)
            l_list.append(line2)

    if all(i.length <= 200 for i in l_list) is False:
        itersplit(l_list)

    return l_list


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3])
