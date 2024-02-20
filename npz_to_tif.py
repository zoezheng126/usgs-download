import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import shapes
import os
from tqdm import tqdm
import argparse

# convert a binary mask to shapefile
# must include original tif's transform and output directory
def convert(binary_array,crop_info, shp_dir, h=512, w=512):
    a,b,d,e = crop_info['a'].item(),crop_info['b'].item(),crop_info['d'].item(),crop_info['e'].item()
    x_offset, y_offset = crop_info['x_offset'].item(), crop_info['y_offset'].item()
    filename = crop_info['filename'].item()
    crs = crop_info['crs']
    patch_filename = f'{filename[:-4]}_{x_offset}_{y_offset}.tif'
    output_tif_path = os.path.join(shp_dir,patch_filename)
    if hasattr(binary_array, "numpy"):
        binary_array = binary_array.numpy()
    if binary_array.shape == (h, w):
        binary_array = binary_array.reshape(1,h,w).astype(np.uint8)

    transform = rasterio.Affine(a, b, x_offset,
                                d, e, y_offset)
    with rasterio.open(output_tif_path, 'w', driver='GTiff',
                           height=h,
                           width=w,
                           count=1,
                           dtype=binary_array.dtype,
                           crs=crs,
                           transform=transform) as dst:
                                dst.write(binary_array)

    

def main(args):

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        result = "Directory created successfully."
    else:
        result = "Directory already exists."
    print(result)

    for f in tqdm(os.listdir(args.input_dir)):
            shp_batch = os.path.join(args.input_dir,f)

            with np.load(shp_batch, allow_pickle=True) as npz:
                    results = {key: npz[key] for key in npz.files}
                    for item in results['batch_result']:
                            b = dict(item)
                            mask = b['pred_mask']
                            crop_info = b['crop_info']
                            convert(mask,crop_info,args.output_dir)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, required=True, help='The directory to store np array')
    parser.add_argument('--output_dir', type=str, required=True, help='directory to find usgs tif files')
    args = parser.parse_args()
    main(args)
