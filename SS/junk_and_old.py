def merge_tcd_ras_fail(tcd_cop_fold, OrdSurv_Grid, scratch, epsg_code):
    # basicvaly fuck this bit - get rid and we'll just use arcpy.
    print("create masking area")

    gb_area = gpd.read_file(OrdSurv_Grid, driver="ESRI Shapefile")

    minx, miny, maxx, maxy = gb_area.geometry.total_bounds

    lon_list = [minx, minx, maxx, maxx]
    lat_list = [miny, maxy, maxy, miny]

    polygon_geom = Polygon(zip(lon_list, lat_list))
    crs = gb_area.crs
    # print(crs)

    print("create clip polygon")

    polygongb = gpd.GeoDataFrame(index=[0], crs=crs, geometry=[polygon_geom])  # create polygon in native epsg

    print("import rasters")
    #import the rasters
    tcd_3030_cop = os.path.join(tcd_cop_fold, r"TCD_2015_020m_eu_03035_d05_E30N30",
                                r"TCD_2015_020m_eu_03035_d05_E30N30.TIF")
    tcd_3040_cop = os.path.join(tcd_cop_fold, r"TCD_2015_020m_eu_03035_d05_E30N40",
                                r"TCD_2015_020m_eu_03035_d05_E30N40.TIF")
    tcd_cop = os.path.join(tcd_cop_fold, "TCD_GB_merge.TIF")


    print("open rasters in rasterio")
    src1 = rasterio.open(tcd_3030_cop)
    # src1 = gdal.Open(tcd_3030_cop, gdalconst.GA_ReadOnly)
    # src2 = gdal.Open(tcd_3040_cop, gdalconst.GA_ReadOnly)
    src2 = rasterio.open(tcd_3040_cop)

    print("get raster crs")
    # proj = osr.SpatialReference(wkt=src1.GetProjection())  # get the raster epsg
    # ras_crs = (proj.GetAttrValue('AUTHORITY', 1))
    ras_crs = src1.crs


    # prj = src1.GetProjection()
    # srs = osr.SpatialReference(wkt=prj)
    # ras_crs= str(srs.GetAttrValue("AUTHORITY", 1))

    print(ras_crs)


    print("convert clip polygon to raster crs")
    poly = polygongb.to_crs(ras_crs)

    polygon_outp = os.path.join(scratch, "GB_poly.shp")
    poly.to_file(polygon_outp, driver="ESRI Shapefile")
    minx, miny, maxx, maxy = poly.geometry.total_bounds

    poly = None
    polygongb = None
    #
    # poly = gpd.read_file(polygon_outp, driver="ESRI Shapefile")
    print("polygon_created")

    shapely_polygon = shapely.geometry.box(minx, miny, maxx, maxy)

    feature = gpd.GeoSeries([shapely_polygon]).to_json() #__geo_interface__
    print(feature)

    # processing.runalg('gdalogr:cliprasterbymasklayer', input, mask, no_data, alpha_band, keep_resolution, extra, output)
    # with fiona.open(polygongb, "r") as shapefile:
    #     features = [feature["geometry"] for feature in shapefile]
    # print(features)
    print("clip rasters by polygon area")

    clip_src1, out_transform1 = mask(src1, feature, crop=True, invert=False, filled=True)
    clip_src1 = numpy.squeeze(clip_src1, 0)
    tcd3030clip = os.path.join(scratch, "tcd3030clip.tif")
    with rasterio.open(tcd3030clip, 'w', driver='GTiff', width=clip_src1.shape[0], height=clip_src1.shape[1],
                       count=1, dtype=np.uint16, transform=out_transform1, crs=src2.crs,
                       compress='lzw') as tcdclip1:
        tcdclip1.write(clip_src1, indexes=1)

    clip_src2, out_transform2 = mask(src2, feature, crop=True, invert=False, filled=True)
    clip_src2 = numpy.squeeze(clip_src2, 0)
    tcd3040clip = os.path.join(scratch, "tcd3040clip.tif")
    with rasterio.open(tcd3040clip, 'w', driver='GTiff', width=clip_src2.shape[0], height=clip_src2.shape[1],
                       count=1, dtype=np.uint16, transform=out_transform2, crs=src2.crs,
                       compress='lzw') as tcdclip2:
        tcdclip2.write(clip_src2, indexes=1)


    clip_src1 = None
    clip_src2 = None

    print("run merge")
    srcs_to_mosaic = [tcdclip1, tcdclip2]
    arr, out_trans = merge(srcs_to_mosaic)

    print("writing results to raster")
    with rasterio.open(
            tcd_cop,
            'w',
            driver='GTiff',
            width=arr.shape[0],
            height=arr.shape[1],
            count=1,
            dtype=np.uint16,
            # nodata=255,
            transform=out_trans,
            crs=src1.crs,
            compress='lzw') as dst:
        dst.write(arr, indexes=1)

    src1 = None
    src2 = None
    arr = None
    polygon = None
    clip_src1 = None
    clip_src2 = None

    return tcd_cop