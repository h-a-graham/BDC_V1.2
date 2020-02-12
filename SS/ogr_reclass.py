import ogr
vecmap_shp = ""
# import shapefile in ogr to get extents
driver = ogr.GetDriverByName("ESRI Shapefile")
vecmap = driver.Open(vecmap_shp, 1)
vecmap_ogr = vecmap.GetLayer()

schema = []
ldefn = vecmap_ogr.GetLayerDefn()
for n in range(ldefn.GetFieldCount()):
    fdefn = ldefn.GetFieldDefn(n)
    schema.append(fdefn.name)

if 'BVI_Val' in schema:
    vecmap.lDeleteField('BVI_Val')

fieldDefn = ogr.FieldDefn('BVI_Val', ogr.OFTReal)
fieldDefn.SetWidth(5)
fieldDefn.SetPrecision(0)
vecmap_ogr.CreateField(fieldDefn)

print("starting the classification")
for feature in vecmap_ogr:
    landcov = feature.GetField("FeatDesc")
    print(landcov)

    if landcov == "Boulders":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Boulders and Sand":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Boulders and Shingle":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Broad-leafed woodland":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Broad-leafed woodland and Shru":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Building polygon":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Coniferous woodland":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Coniferous woodland and Shrub":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Custom landform polygon":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Glasshouse polygon":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Gravel Pit":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Heathland":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Heathland and Boulders":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Heathland and Marsh":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Heathland and Unimproved Grass":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Inland Rock":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Inland water polygon":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Marsh":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Marsh and Unimproved Grass":
        feature.SetField("BVI_Val_A", 2)
    elif landcov == "Mixed woodland":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Mixed woodland and Shrub":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Mud":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Orchard":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Reeds":
        feature.SetField("BVI_Val_A", 2)
    elif landcov == "Refuse or Slag Heap":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Sand":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Sand Pit":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Sea polygon":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Shingle":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Shingle and Mud":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Shingle and Sand":
        feature.SetField("BVI_Val_A", 0)
    elif landcov == "Shrub":
        feature.SetField("BVI_Val_A", 5)
    elif landcov == "Shrub and  Boulders":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Shrub and Heathland":
        feature.SetField("BVI_Val_A", 2)
    elif landcov == "Shrub and Heathland and Boulde":
        feature.SetField("BVI_Val_A", 2)
    elif landcov == "Shrub and Heathland and Unimpr":
        feature.SetField("BVI_Val_A", 2)
    elif landcov == "Shrub and Marsh":
        feature.SetField("BVI_Val_A", 4)
    elif landcov == "Shrub and Marsh and Heath":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Shrub and Marsh and Unimproved":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Shrub and Unimproved Grass":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Shrub and Unimproved Grass and":
        feature.SetField("BVI_Val_A", 3)
    elif landcov == "Unimproved Grass":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Unimproved Grass and Boulders":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Unimproved Grass and Sand":
        feature.SetField("BVI_Val_A", 1)
    elif landcov == "Unimproved Grass and Shingle":
        feature.SetField("BVI_Val_A", 1)
    else:
        feature.SetField("BVI_Val_A", -99)

    vecmap_ogr.SetFeature(feature)
    print(feature.GetField("BVI_Val_A"))

print("loop finished")
vecmap_ogr.ResetReading()
print("close datasets")
vecmap_ogr.Destroy()

###################################