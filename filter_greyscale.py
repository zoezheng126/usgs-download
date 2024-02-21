import rasterio
import numpy as np
import os
from tqdm import tqdm
import time
from rasterio.windows import Window
import argparse
import geopandas as gpd
from rasterio.features import rasterize

PATH_TO_CENTERLINE = '/scratch/bbkc/zoezheng126/Greyscale/ISGS_Centerlines'
CENTERLINE_DIR = [name for name in os.listdir(PATH_TO_CENTERLINE)]
print(CENTERLINE_DIR)
def load_mask(path, src):
    meta = src.meta
    gdf = gpd.read_file(path)
    shapes = ((geom, 1) for geom in gdf.geometry)
    gt_mask = rasterize(shapes, out_shape=(meta['height'], meta['width']), fill=0, transform=src.transform, dtype='float32')

    return gt_mask

def find_shp(tif_filename):
    for name in CENTERLINE_DIR:
        if name in tif_filename:
            path = os.path.join(PATH_TO_CENTERLINE, name)
            shapefile = [name for name in os.listdir(path)
                  if name.endswith('.shp')][0]
            
            return os.path.join(path, shapefile)

# crop and save to tif directly
def crop(src, i_c, j_c,crop_tif_path, s_path = None, h=512,w=512):
    transformer = rasterio.transform.AffineTransformer(src.transform)
    # top left geographics (x,y) coordinates of cropped tif
    x_offset, y_offset = transformer.xy(i_c, j_c)
    cropped_data = src.read(window=Window(j_c, i_c, h, w))

        # Adjust the transform
    transform = rasterio.Affine(src.transform.a, src.transform.b, x_offset,
                                src.transform.d, src.transform.e, y_offset)
    with rasterio.open(crop_tif_path, 'w', driver='GTiff',
                   height=cropped_data.shape[1],
                   width=cropped_data.shape[2],
                   count=src.count,
                   dtype=cropped_data.dtype,
                   crs=src.crs,
                   transform=transform) as dst:
                        dst.write(cropped_data)
                        
    #makeup_mask(transform,crop_tif_path, s_path,h,w)

# crop and later save to one np file for each 5000*5000 tif                        
def crop_to_npz(src, i_c, j_c, h=512, w=512):
    # Compute the top left geographic (x, y) coordinates of the cropped TIFF
    x_offset, y_offset = src.xy(i_c, j_c)
    
    # Read the cropped data from the source
    cropped_data = src.read(window=Window(j_c, i_c, h, w))

    # Save cropped data, transform, and CRS to a NumPy (NPZ) file
    #np.savez(npz_path, data=cropped_data, transform=transform, crs=src.crs)
    return {
            'data': cropped_data,
            'crs': src.crs,
            'x_offset': x_offset,
            'y_offset': y_offset
    }

def check_ndwi_sum(ndwi, i_c, j_c, h=512, w=512, pad=256):
    """
    Check if the sum of NDWI values in a specific area is greater than 100.

    :param ndwi: NDWI array of shape (h, w)
    :param img: Image array of shape (4, h, w)
    :param i_c: Row index for the top-left corner of the cropped area
    :param j_c: Column index for the top-left corner of the cropped area
    :param h: Height of the cropped area
    :param w: Width of the cropped area
    :return: True if the sum of NDWI values in the area is greater than 100, False otherwise
    """
    if i_c + h > ndwi.shape[0] or j_c + w > ndwi.shape[1]:
        raise ValueError("Cropped area extends beyond the dimensions of the NDWI array")

    # Extract the corresponding area from the NDWI array
    i_c = max(0, i_c - pad)
    i_c_h = min(ndwi.shape[0], i_c + h + pad)
    j_c = max(0, j_c - pad)
    j_c_w = min(ndwi.shape[1], j_c + w + pad)

    ndwi_area = ndwi[i_c:i_c_h, j_c:j_c_w]

    # Check if the sum of the NDWI values in the area is greater than 100
    return np.sum(ndwi_area) > 0
    

def sliding_crop(src, ndwi, h=512, w=512):
    tif = src.read()
    _,tif_h,tif_w=tif.shape
    x_start,y_start=0,0
    x_end, y_end = 0,0
    results = []
    while (y_end < tif_h):
        y_end = y_start + h
        if y_end > tif_h:
            y_start = tif_h - h
            if y_start < 0: break
            y_end = tif_h + 1
        x_start,x_end = 0,0
        while (x_end < tif_w):
            x_end = x_start + w
            if x_end > tif_w: 
                x_start = tif_w - w
                if x_start < 0: break
                x_end = tif_w + 1
            if check_ndwi_sum(ndwi,y_start,x_start,h,w):
                metadata = crop_to_npz(src, y_start, x_start)
                results.append(metadata)
                
            x_start = x_end
        y_start = y_end
    return results

def save_npz_crops_to_tiffs(cropping_results, base_tiff_path,a,b,d,e,count,filename):
    """
    Save crops stored in cropping results to individual TIFF files.

    Parameters:
    - cropping_results: The dictionary of loaded cropping results.
    - base_tiff_path: Base path for saving TIFF files.
    """
    data = cropping_results['data']
    tiff_name = f"{str(filename)[:-4]}_crop_{cropping_results['x_offset']}_{cropping_results['y_offset']}.tif"
    tiff_path = os.path.join(base_tiff_path, tiff_name)
    trans = rasterio.Affine(a, b, cropping_results['x_offset'],
                            d, e, cropping_results['y_offset'])
    with rasterio.open(tiff_path, 'w', driver='GTiff',
                        height=512, width=512,
                        count=count, dtype=data.dtype,
                        crs=cropping_results['crs'],
                        transform=trans) as dst:
        dst.write(data)

def load_tif_from_np(npz_path,base_tiff_path):
    with np.load(npz_path, allow_pickle=True) as npz:
        results = {key: npz[key] for key in npz.files}

        a = results['a']
        b = results['b']
        d = results['d']
        e = results['e']
        count = results['count']
        filename = results['filename']
        for r in results['accumulated_results']:
            save_npz_crops_to_tiffs(r,base_tiff_path,a,b,d,e,count,filename)

def main(args):
    outputs = []
    input_dir = args.input_dir
    npz_path = args.output_dir
    
    for filename in tqdm(os.listdir(input_dir)):
        tmp = os.path.join(input_dir,filename)
        if args.shp_path != None:
            shp_path = args.shp_path
        else:
            shp_path = find_shp(filename)
        if shp_path == None:
            outputs.append(filename)
            continue
        print(tmp)
        print(shp_path)
        with rasterio.open(tmp) as src:
            centerline = load_mask(shp_path, src)
            src_name = filename[:-4] + '.npz'
            results = sliding_crop(src,centerline, h=512,w=512)
            npz_file = os.path.join(npz_path, src_name)
            np.savez_compressed(npz_file, accumulated_results=results,\
                                a=src.transform.a, b=src.transform.b,\
                                d=src.transform.d, e=src.transform.e,\
                                    count=src.count, filename=filename)
    return outputs

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # crop tif to npz
    parser.add_argument('--input_dir', type=str, default=None, help='directory to find usgs tif files')
    parser.add_argument('--output_dir', type=str, help='The directory to store npz files')
    parser.add_argument('--shp_path', type=str, default=None, help='path to the centerline file')
    # load tif from npz
    parser.add_argument('--npz_file', type=str, default=None, help='path to npz file')
    parser.add_argument('--tif_output_dir', type=str, default=None, help='directory to store tif files from numpy')
    args = parser.parse_args()
    if args.npz_file == None and args.tif_output_dir == None:
        if not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
            result = "Output directory created successfully."
        else:
            result = "Output directory already exists."
        print(result)
        outputs = main(args)
        print(f'the following tif do not have a corresponding shapefile: \n{outputs}')
    else:
        load_tif_from_np(args.npz_file, args.tif_output_dir)

    
