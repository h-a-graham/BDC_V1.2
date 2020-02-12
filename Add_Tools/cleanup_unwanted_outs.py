import os
import glob

def main():
    print("Cleaning up unwanted files from output folder")

    exp_f = os.path.abspath("D:/Work/GB_Beaver_Data/GB_BVI_Res_v2")
    ext1 = "**/*_BVI_1kml.tif"
    ext2 = "**/*_BVI_1km.tif"
    ext3 = "**/*_BHI_1kml.tif"
    ext4 = "**/*_BHI_1km.tif"

    clean_up(exp_f, ext1)
    clean_up(exp_f, ext2)
    clean_up(exp_f, ext3)
    clean_up(exp_f, ext4)


def clean_up(folder, ext):
    file_search = os.path.join(folder, ext)
    f_list = glob.glob(file_search, recursive=True)

    try:
        for file in f_list:
            os.remove(file)
    except Exception as e:
        print(e)




if __name__ == '__main__':
     main()