# usgs-download

## Download sample command:
```
python3 usgs-download.py -u username -p password -o path/to/output/files/directory
```

In addition, search `spatial_filter`, `temporal_filter`, and `acquisition_filter` in the script and modify if needed to download different areas and periods.

## Save Tiff files to .npz sample (RGB) command:
```
python3 filter.py --np_dir /path/to/dir/to/store/npz --input_dir /path/to/find/usgs/downloaded/tiff
```
In our dataset, for each Tiff file, `src_name.tif` of size (4,5000*5000) will be cropped by (4,512,512) shifted windows and save to one `src_name.npz` file.

## Save Tiff files to .npz sample (Greyscale) command:
```
python3 filter.py --input_dir /path/to/tif/dir --output_dir /path/to/dir/store/npz
```

## Load Tiff files from .npz sample command:
```
python3 filter.py --npz_file /path/to/dir/to/find/npz --tif_output_dir /path/to/store/tiff
```
Here you can load .tif from a .npz file to test if the saving process is correct.

## Convert npz predict mask to shapefile command:
```
python3 npz_to_shp.py --input_dir /path/to/npz/dir --output_dir /path/to/shp/dir
```
Here you convert a list of .npz files(each contain a batch output masks to .shp files.

## Convert npz_predict mask to TIFF command:
```
python3 npz_to_shp.py --input_dir /path/to/npz/dir --output_dir /path/to/tif/dir
```
Here you convert a list of .npz files(each contain a batch output masks to .tif files.
