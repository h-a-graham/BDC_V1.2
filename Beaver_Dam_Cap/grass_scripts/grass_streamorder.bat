set burndem=%1
set so_vec=%2
set flwacc=%3


call r.import input=%burndem% output=dem --overwrite
call g.region -p rast=dem
call r.watershed elev=dem accumulation=facc thresh=1200 -a --overwrite
call r.out.gdal input=facc output=%flwacc% format=GTiff --overwrite
call r.stream.extract elev=dem accumulation=facc stream_raster=rivras direction=fdir thresh=1200 --overwrite
call r.stream.order stream_rast=rivras direction=fdir elev=dem accumulation=facc strahler=strord_ras stream_vect=sovec --overwrite
call v.out.ogr input=sovec type=line output=%so_vec% format=GPKG --overwrite
