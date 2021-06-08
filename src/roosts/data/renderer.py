import os
import numpy as np
from wsrlib import pyart, radar2mat
import logging
import time
import matplotlib.pyplot as plt
import matplotlib.colors as pltc
from matplotlib import image
from tqdm import tqdm

ARRAY_Y_DIRECTION   = "xy" # default radar direction, y is first dim (row), large y is north, row 0 is south
ARRAY_R_MAX         = 150000.0
ARRAY_DIM           = 600
ARRAY_ATTRIBUTES    = ["reflectivity", "velocity", "spectrum_width"]
ARRAY_ELEVATIONS    = [0.5, 1.5, 2.5, 3.5, 4.5]
ARRAY_RENDER_CONFIG = {"ydirection":          ARRAY_Y_DIRECTION,
                       "fields":              ARRAY_ATTRIBUTES,
                       "coords":              "cartesian",
                       "r_min":               2125.0,       # default: first range bin of WSR-88D
                       "r_max":               ARRAY_R_MAX,  # 459875.0 default: last range bin
                       "r_res":               250,          # default: super-res gate spacing
                       "az_res":              0.5,          # default: super-res azimuth resolution
                       "dim":                 ARRAY_DIM,    # num pixels on a side in Cartesian rendering
                       "sweeps":              None,
                       "elevs":               ARRAY_ELEVATIONS,
                       "use_ground_range":    True,
                       "interp_method":       'nearest'}
DUALPOL_DIM             = 600
DUALPOL_ATTRIBUTES      = ["differential_reflectivity", "cross_correlation_ratio", "differential_phase"]
DUALPOL_ELEVATIONS      = [0.5, 1.5, 2.5, 3.5, 4.5]
DUALPOL_RENDER_CONFIG   = {"ydirection":          ARRAY_Y_DIRECTION,
                           "fields":              DUALPOL_ATTRIBUTES,
                           "coords":              "cartesian",
                           "r_min":               2125.0,       # default: first range bin of WSR-88D
                           "r_max":               ARRAY_R_MAX,  # default 459875.0: last range bin
                           "r_res":               250,          # default: super-res gate spacing
                           "az_res":              0.5,          # default: super-res azimuth resolution
                           "dim":                 DUALPOL_DIM,  # num pixels on a side in Cartesian rendering
                           "sweeps":              None,
                           "elevs":               DUALPOL_ELEVATIONS,
                           "use_ground_range":    True,
                           "interp_method":       "nearest"}

####### render as images #######
# visualization settings
COLOR_ARRAY = [
    '#006400', # for not scaled boxes
    '#FF00FF', # scaled to RCNN then to user factor 0.7429 which is sheldon average
    '#800080',
    '#FFA500',
    '#FFFF00'
]
NORMALIZERS = {
        'reflectivity':              pltc.Normalize(vmin=  -5, vmax= 35),
        'velocity':                  pltc.Normalize(vmin= -15, vmax= 15),
        'spectrum_width':            pltc.Normalize(vmin=   0, vmax= 10),
        'differential_reflectivity': pltc.Normalize(vmin=  -4, vmax= 8),
        'differential_phase':        pltc.Normalize(vmin=   0, vmax= 250),
        'cross_correlation_ratio':   pltc.Normalize(vmin=   0, vmax= 1.1)
}

class Renderer:

    """ 
        Extract radar products from raw radar scans, 
        save the products in npz files, 
        save the dualpol data for postprocessing,
        render ref1 and rv1 for visualization     
        delete the radar scans 

        input: directories to save rendered arrays and images and rendering configs
        output: npz_files: for detection module to load/preprocess data
                img_files: for visualization
                scan_names: for tracking module to know the full image set

    """

    def __init__(self, 
                 npz_dir, roosts_ui_data_dir,
                 array_render_config=ARRAY_RENDER_CONFIG, 
                 dualpol_render_config=DUALPOL_RENDER_CONFIG):

        self.npzdir = npz_dir
        self.ref_imgdir = os.path.join(roosts_ui_data_dir, 'ref0.5_images')
        self.rv_imgdir = os.path.join(roosts_ui_data_dir, 'rv0.5_images')
        self.imgdirs = {("reflectivity", 0.5): self.ref_imgdir, ("velocity", 0.5): self.rv_imgdir}
        self.array_render_config = array_render_config
        self.dualpol_render_config = dualpol_render_config


    def render(self, scan_paths):
        scan = os.path.splitext(os.path.basename(scan_paths[0]))[0]
        station = scan[0:4]
        year = scan[4:8]
        month = scan[8:10]
        date = scan[10:12]
        key_prefix = f"{year}/{month}/{date}/{station}"

        npzdir = os.path.join(self.npzdir, key_prefix)
        ref_imgdir = os.path.join(self.ref_imgdir, key_prefix)
        rv_imgdir = os.path.join(self.rv_imgdir, key_prefix)
        os.makedirs(npzdir, exist_ok = True)
        os.makedirs(ref_imgdir, exist_ok = True)
        os.makedirs(rv_imgdir, exist_ok = True)

        log_path = os.path.join(npzdir, "rendering.log")
        array_error_log_path = os.path.join(npzdir, "array_error_scans.log")
        dualpol_error_log_path = os.path.join(npzdir, "dualpol_error_scans.log")
        logger = logging.getLogger(key_prefix)
        filelog = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s : %(message)s')
        formatter.converter = time.gmtime
        filelog.setFormatter(formatter)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(filelog)

        npz_files = [] # for detection module to load/preprocess data
        img_files = [] # for visualization
        scan_names = [] # for tracking module to know the full image set
        array_errors = []  # to record scans from which array rendering fails
        dualpol_errors = []  # to record scans from which dualpol array rendering fails

        for scan_file in tqdm(scan_paths, desc="Rendering"):
            
            scan = os.path.splitext(os.path.basename(scan_file))[0]
            npz_path = os.path.join(npzdir, f"{scan}.npz")
            ref1_path = os.path.join(ref_imgdir, f"{scan}.png")

            """
            if os.path.exists(npz_path) and os.path.exists(ref1_path):
                npz_files.append(npz_path)
                img_files.append(ref1_path)
                scan_names.append(scan)
                continue
            """
            arrays = {}

            try:
                radar = pyart.io.read_nexrad_archive(scan_file)
                logger.info('Loaded scan %s' % scan)
            except Exception as ex:
                logger.error('Exception while loading scan %s - %s' % (scan, str(ex)))
                array_errors.append(scan)
                dualpol_errors.append(scan)
                continue

            try:
                data, _, _, y, x = radar2mat(radar, **self.array_render_config)
                logger.info('Rendered a npy array from scan %s' % scan)
                if data.shape != (len(self.array_render_config["fields"]), len(self.array_render_config["elevs"]),
                                  self.array_render_config["dim"], self.array_render_config["dim"]):
                    logger.info(f"  Unexpectedly, its shape is {data.shape}.")
                arrays["array"] = data
            except Exception as ex:
                logger.error('Exception while rendering a npy array from scan %s - %s' % (scan, str(ex)))
                array_errors.append(scan)

            try:
                data, _, _, y, x = radar2mat(radar, **self.dualpol_render_config)
                logger.info('Rendered a dualpol npy array from scan %s' % scan)
                if data.shape != (len(self.dualpol_render_config["fields"]), len(self.dualpol_render_config["elevs"]),
                                  self.dualpol_render_config["dim"], self.dualpol_render_config["dim"]):
                    logger.info(f"  Unexpectedly, its shape is {data.shape}.")
                arrays["dualpol_array"] = data
            except Exception as ex:
                logger.error('Exception while rendering a dualpol npy array from scan %s - %s' % (scan, str(ex)))
                dualpol_errors.append(scan)

            if len(arrays) > 0:
                np.savez_compressed(npz_path, **arrays)
                self.render_img(arrays["array"], key_prefix, scan) # render ref1 and rv1 images
                npz_files.append(npz_path)
                img_files.append(ref1_path)
                scan_names.append(scan)

        if len(array_errors) > 0:
            with open(array_error_log_path, 'a+') as f:
                f.write('\n'.join(array_errors) + '\n')
        if len(dualpol_errors) > 0:
            with open(dualpol_error_log_path, 'a+') as f:
                f.write('\n'.join(dualpol_errors) + '\n')

        del logger
        return npz_files, img_files, scan_names 


    def render_img(self, array, key_prefix, scan):
        # input: numpy array containing radar products
        attributes = self.array_render_config['fields']
        elevations = self.array_render_config['elevs']
        for attr, elev in self.imgdirs:
            cm = plt.get_cmap(pyart.config.get_field_colormap(attr))
            rgb = cm(NORMALIZERS[attr](array[attributes.index(attr), elevations.index(elev), :, :]))
            rgb = rgb[::-1, :, :3]  # flip the y axis; omit the fourth alpha dimension, NAN are black but not white
            image.imsave(os.path.join(self.imgdirs[(attr, elev)], key_prefix, f"{scan}.png"), rgb)

