from EA_Catch_Extracter import get_WaterBody_List

from EA_Catch_Extracter import WBs_from_List
import os

out_file = os.path.abspath("C:/Users/hughg/Desktop/EA_Catch_Extracter/test_Folder/Kent_Leven_WaterBodies.shp")
# catchment_list = [3536]
# catchment_list = get_WaterBody_List.getWaterBodies(catch_type='OperationalCatchment', catch_num= 3123)
# catchment_list = get_WaterBody_List.getWaterBodies(catch_type='ManagementCatchment', catch_num=3045)
# pick one of the following



epsg_code = 27700
# format = 'GeoJSON'

WBs_from_List.main(catchment_list=catchment_list, out_file=out_file, epsg_code=epsg_code)