import os
import numpy as np
import matplotlib as mpl
import matplotlib.figure as mplfigure
import matplotlib.pyplot as plt
import cv2
import imageio
from tqdm import tqdm
import itertools
import pyart
from wsrlib import slant2ground
from roosts.utils.counting_util import calc_n_animals, xyr2geo, get_unique_sweeps
import roosts.utils.file_util as fileUtil
from roosts.utils.time_util import scan_key_to_local_time

class Visualizer:

    """
        Visualize the detection and tracking results
    """


    def __init__(self, width=600, height=600, sun_activity=None):
        self.width = width
        self.height = height
        assert sun_activity in ["sunrise", "sunset"]
        self.sun_activity = sun_activity

    def draw_detections(
        self,
        image_paths,
        detections,
        outdir,
        score_thresh=0.005,
        save_gif=True,
        vis_track=False,
        vis_track_after_NMS=True
    ):
        """ 
            Draws detections on the images
        
            Args:
                image_paths: absolute path of images, type: list
                detections:  the output of detector or tracker with the structure 
                             {"scanname":xx, "im_bbox": xx, "det_ID": xx, 'det_score': xx}
                             type: list of dict
                outdir: path to save images
                score_thresh: only display bbox with score higher than threshold
                save_gif:   save image sequence as gif on a single station in daily basis

            Returns: 
                image with bboxes
        """
        fileUtil.mkdir(outdir)
        outpaths = []

        if not vis_track:
            # if visualize track, some detections are predicted by Kalman filter which may not have det score
            detections = [det for det in detections if det["det_score"] >= score_thresh]
    
        if vis_track and vis_track_after_NMS:
             # the track is not suppressed by NMS
            detections = [det for det in detections if ("track_NMS" in det.keys()) and (not det["track_NMS"])]

        for image_path in tqdm(image_paths, desc="Visualizing"):

            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            scanname = os.path.splitext(os.path.basename(image_path))[0]
            dets = [det for det in detections if det["scanname"] in scanname]
            outname = os.path.join(outdir, os.path.basename(image_path))
            self.overlay_detections(image, dets, outname)
            outpaths.append(outname)

        if save_gif:
            gif_path = os.path.join(outdir, scanname.split("_")[0] + '.gif')
            self.save_gif(outpaths, gif_path)
            return gif_path
            
        return True


    def draw_dets_multi_thresh(
        self,
        image_paths,
        detections,
        outdir
    ):
        """ 
            Draws detections on the images under different score thresholds
        
            Args:
                image_paths: absolute path of images, type: list
                detections:  the output of detector or tracker with the structure 
                             {"scanname":xx, "im_bbox": xx, "det_ID": xx, 'det_score': xx}
                             type: list of dict
                outdir: path to save images

            Returns: 
                image with bboxes
        """
        fileUtil.mkdir(outdir)
        outpaths = []

        dets_multi_thresh = {} 
        for score_thresh in [0.0, 0.05, 0.1, 0.3, 0.5, 0.7]:
            dets_multi_thresh[score_thresh] = [det for det in detections if det["det_score"] >= score_thresh]

        for image_path in tqdm(image_paths, desc="Visualizing"):

            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            scanname = os.path.splitext(os.path.basename(image_path))[0]

            out_thre = []
            for score_thresh in [0.0, 0.05, 0.1, 0.3, 0.5, 0.7]:
                dets = [det for det in dets_multi_thresh[score_thresh] if det["scanname"] in scanname]
                outname_thre = os.path.join(outdir, scanname + "%.2f.jpg" % score_thresh)
                self.overlay_detections(image, dets, outname_thre)
                out_thre.append(outname_thre)

            outname = os.path.join(outdir, os.path.basename(image_path))
            outpaths.append(outname)
            # merge files and delect useless files
            figs = []
            for out in out_thre:
                fig = cv2.imread(out)
                fig = cv2.resize(fig, (300, 300))
                figs.append(fig)
            fileUtil.delete_files(out_thre)
            fig_all = cv2.hconcat(figs)
            cv2.imwrite(outname, fig_all)

        gif_path = os.path.join(outdir, scanname.split("_")[0] + '.gif')
        self.save_gif(outpaths, gif_path)
        return gif_path
        

    def draw_tracks_multi_thresh(
        self,
        image_paths,
        detections,
        tracks,
        outdir,
        vis_track_after_NMS=True,
        vis_track_after_merge=True,
        ignore_rain=True
    ):
        """ 
            Draws tracks on the images under different threholds
        
            Args:
                image_paths: absolute path of images, type: list
                detections:  the output of detector or tracker with the structure 
                             {"scanname":xx, "im_bbox": xx, "det_ID": xx, 'det_score': xx}
                             type: list of dict
                outdir: path to save images
                ignore_rain: do not visualize the rain track

            Returns: 
                image with bboxes
        """
        fileUtil.mkdir(outdir)
        outpaths = []

        # NOTE: vis_track_after_NMS is useless, because the tracks have been suppressed in-place by tracker
        if vis_track_after_NMS:
            tracks = [t for t in tracks if not t["NMS_suppressed"]]
            display_option = "track_ID"

        if vis_track_after_merge:
            display_option = "merge_track_ID"

        if ignore_rain:
            tracks = [t for t in tracks if ("is_rain" in t.keys() and (not t["is_rain"]))]

        tracks_multi_thresh = {} 
        for score_thresh in [1, 2, 3, 4, 5, 6]: # number of bbox from detector in a track
            # id_list = [t["det_IDs"] for t in tracks if sum(t["det_or_pred"]) >= score_thresh]
            id_list = []
            for track in tracks:
                if sum(track["det_or_pred"]) >= score_thresh:
                    for idx in range(len(track["det_or_pred"])-1, -1, -1):
                        if track["det_or_pred"][idx]:
                            last_pred_idx = idx
                            break
                    # do not viz the tail of tracks
                    id_list.append(track["det_IDs"][:last_pred_idx+1])

            tracks_multi_thresh[score_thresh] = list(itertools.chain(*id_list))

        for image_path in tqdm(image_paths, desc="Visualizing"):
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            scanname = os.path.splitext(os.path.basename(image_path))[0]
            dets = [det for det in detections if det["scanname"] in scanname]

            out_thre = []
            for score_thresh in [1, 2, 3, 4, 5, 6]:
                dets_thre = [det for det in dets if det["det_ID"] in tracks_multi_thresh[score_thresh]]
                outname_thre = os.path.join(outdir, scanname + "%.2f.jpg" % score_thresh)
                self.overlay_detections(image, dets_thre, outname_thre, display_option)
                out_thre.append(outname_thre)

            outname = os.path.join(outdir, os.path.basename(image_path))
            outpaths.append(outname)
            # merge files and delect useless files
            figs = []
            for out in out_thre:
                fig = cv2.imread(out)
                fig = cv2.resize(fig, (300, 300))
                figs.append(fig)
            fileUtil.delete_files(out_thre)
            fig_all = cv2.hconcat(figs)
            cv2.imwrite(outname, fig_all)

        gif_path = os.path.join(outdir, scanname.split("_")[0] + '.gif')
        self.save_gif(outpaths, gif_path)
        return gif_path


    def overlay_detections(self, image, detections, outname, display_option='det_score'):
        """ Overlay bounding boxes on images  """

        fig = mplfigure.Figure(frameon=False)
        dpi = fig.get_dpi()
        fig.set_size_inches(
            (self.width + 1e-2 ) / dpi,
            (self.height + 1e-2 ) / dpi,
        )
        ax = fig.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.axis("off")
        ax.imshow(image, extent=(0, self.width, self.height, 0), interpolation="nearest")
       
        for det in detections:
            x, y, r = det["im_bbox"]
            score = det["det_score"]

            ax.add_patch(
                plt.Rectangle((x-r, y-r), 
                               2*r,
                               2*r, fill=False,
                               edgecolor= '#FF00FF', linewidth=3)
                )
            if  display_option == "track_ID":
                if "track_ID" in det.keys():
                    ax.text(x-r, y-r-2,
                            '{:d}'.format(det["track_ID"]),
                            bbox=dict(facecolor='blue', alpha=0.7),
                            fontsize=14, color='white')
            elif display_option == "merge_track_ID":
                if "merge_track_ID" in det.keys():
                    display_text = det["merge_track_ID"]
                elif "track_ID" in det.keys():
                    display_text = '{:d}'.format(det["track_ID"])
                else:
                    continue
                ax.text(x-r, y-r-2,
                        display_text,
                        bbox=dict(facecolor='blue', alpha=0.7),
                        fontsize=14, color='white')
            else: # det_score
                ax.text(x-r, y-r-2,
                        '{:.3f}'.format(score),
                        bbox=dict(facecolor='#FF00FF', alpha=0.7),
                        fontsize=14, color='white')
        fig.savefig(outname) 
        plt.close()


    def save_gif(self, image_paths, outpath):
        """ 
            imageio may load the image in a different format from matplotlib,
            so I just reload the images from local disk by imageio.imread 
        """
        seq = []
        image_paths.sort()
        for image_path in image_paths:
            seq.append(imageio.imread(image_path))
        kargs = {"duration": 0.5}
        imageio.mimsave(outpath, seq, "GIF", **kargs)
            

    def count_and_save(
        self, detections, tracks, geosize, count_cfg,
        scan_dir, scanname2key, tracks_path, sweeps_path
    ):
        """Save the list of tracks for UI, also save the list of sweeps and their animal counts"""
        det_dict = {}
        for det in detections:
            det_dict[det["det_ID"]] = det

        with open(tracks_path, 'a+') as f:
            for track in tqdm(tracks, desc="Write tracks into csv"):
                if (("is_windfarm" in track.keys() and track["is_windfarm"]) or
                    ("is_rain" in track.keys() and track["is_rain"])):
                    continue

                # remove the tail of tracks (which are generated from Kalman filter instead of detector)
                for idx in range(len(track["det_or_pred"]) - 1, -1, -1):
                    if track["det_or_pred"][idx]:
                        last_pred_idx = idx
                        break

                for idx, det_ID in enumerate(track["det_IDs"]):
                    # do not report the tail of tracks
                    if idx > last_pred_idx:
                        break

                    det = det_dict[det_ID]
                    from_sun_activity = f"from_{self.sun_activity}"

                    xyr = xyr2geo(
                        det["im_bbox"][0], det["im_bbox"][1], det["im_bbox"][2],
                        rmax=geosize / 2,  # 300000km / 2
                        k=count_cfg["count_scaling"]
                    )  # geometric offset to radar
                    det["geo_dist"] = (xyr[0] ** 2 + xyr[1] ** 2) ** 0.5

                    local_time = scan_key_to_local_time(det["scanname"])

                    f.write(
                        ",".join([
                            # UI will convert this track index i into SSSSYYYYMMDD-i
                            # YYYYMMDD: local date
                            # https://github.com/darkecology/roostui/blob/69265e027705d4505870275839fd0a5c86be9ed5/js/vis.js#L479
                            f"{det['track_ID']:d}",

                            det["scanname"],
                            f"{det[from_sun_activity]:.3f}",  # number of minutes from sunrise or sunset

                            f"{det['det_score']:.3f}",
                            f"{det['im_bbox'][0]:.3f}", f"{det['im_bbox'][1]:.3f}", f"{det['im_bbox'][2]:.3f}",
                            f"{det['geo_bbox'][0]:.3f}", f"{det['geo_bbox'][1]:.3f}", f"{det['geo_bbox'][2]:.3f}",
                            f"{det['geo_dist']:.3f}",

                            local_time,
                        ]) + ","
                    )  # will add more fields below

                    # Now look into sweeps
                    radar = pyart.io.read_nexrad_archive(
                        os.path.join(scan_dir, scanname2key[det["scanname"]])
                    )
                    try:
                        sweep_indexes, sweep_angles = get_unique_sweeps(radar)
                        sweep_indexes_and_angles = sorted(zip(sweep_indexes, sweep_angles), key=lambda x: x[1])

                        # count scan-wise bad pixels according to the lowest sweep
                        # do not need to re-count at each bounding box, but so be it since counting is not slow
                        sweep_index, sweep_angle = sweep_indexes_and_angles[0]
                        _, height = slant2ground(det["geo_dist"], sweep_angle)
                        assert height <= count_cfg["max_height"]

                        scan_wise_bad_pixel_counts = [""]
                        for xcorr_threshold in count_cfg["xcorr_threshold"]:
                            for linZ_threshold in count_cfg["linZ_threshold"].keys():
                                (
                                    n_radar_pixels,
                                    n_xcorrAboveC_pixels,
                                    n_xcorrBelowC_refAboveD_pixels,
                                    _
                                ) = calc_n_animals(
                                    radar,
                                    sweep_index,
                                    (0, 0, geosize / 2),  # the entire rendered region
                                    count_cfg["rcs"],
                                    xcorr_threshold=xcorr_threshold,
                                    linZ_threshold=linZ_threshold
                                )

                                if scan_wise_bad_pixel_counts[0] == "":
                                    scan_wise_bad_pixel_counts[0] = f"{n_radar_pixels}"

                                if xcorr_threshold is np.nan:
                                    scan_wise_bad_pixel_counts += [
                                        f"{n_xcorrBelowC_refAboveD_pixels}",
                                    ]
                                else:
                                    scan_wise_bad_pixel_counts += [
                                        f"{n_xcorrAboveC_pixels}",
                                        f"{n_xcorrBelowC_refAboveD_pixels}",
                                    ]
                        f.write(",".join(scan_wise_bad_pixel_counts) + "\n")
                    except:
                        scan_wise_bad_pixel_counts = [""]
                        for xcorr_threshold in count_cfg["xcorr_threshold"]:
                            for linZ_threshold in count_cfg["linZ_threshold"].keys():
                                if xcorr_threshold is np.nan:
                                    scan_wise_bad_pixel_counts += [""]
                                else:
                                    scan_wise_bad_pixel_counts += ["", ""]
                        f.write(",".join(scan_wise_bad_pixel_counts) + "\n")
                        continue  # next bounding box

                    # loop over sweeps and count the number of animals in each sweep
                    # adapted from code by Maria C. T. D. Belotti
                    with open(sweeps_path, 'a+') as ff:
                        for sweep_index, sweep_angle in sweep_indexes_and_angles:
                            try:
                                _, height = slant2ground(det["geo_dist"], sweep_angle)
                                if height > count_cfg["max_height"]:
                                    break  # exhausted all sweeps within the height threshold, next bounding box

                                # for this sweep
                                output = [
                                    # This sweep file is not processed by the UI
                                    # Directly use SSSSYYYYMMDD-i to match with the UI processed tracks file
                                    # YYYYMMDD: local date
                                    f"{det['scanname'][:4]}{local_time[:8]}-{det['track_ID']:d}",

                                    det["scanname"],
                                    f"{sweep_index}",
                                    f"{sweep_angle:.3f}",
                                    f"{count_cfg['count_scaling']:.3f}",
                                ]

                                pixel_and_animal_counts = [""]
                                for xcorr_threshold in count_cfg["xcorr_threshold"]:
                                    for linZ_threshold in count_cfg["linZ_threshold"].keys():
                                        (
                                            n_roost_pixels,
                                            n_xcorrAboveC_pixels,
                                            n_xcorrBelowC_refAboveD_pixels,
                                            n_xcorrBelowC_refBelowD_animals
                                        ) = calc_n_animals(
                                            radar,
                                            sweep_index,
                                            xyr,
                                            count_cfg["rcs"],
                                            xcorr_threshold=xcorr_threshold,
                                            linZ_threshold=linZ_threshold
                                        )

                                        if pixel_and_animal_counts[0] == "":
                                            pixel_and_animal_counts[0] = f"{n_roost_pixels}"

                                        if xcorr_threshold is np.nan:
                                            pixel_and_animal_counts += [
                                                f"{n_xcorrBelowC_refAboveD_pixels}",
                                                f"{n_xcorrBelowC_refBelowD_animals:.3f}"
                                            ]
                                        else:
                                            pixel_and_animal_counts += [
                                                f"{n_xcorrAboveC_pixels}",
                                                f"{n_xcorrBelowC_refAboveD_pixels}",
                                                f"{n_xcorrBelowC_refBelowD_animals:.3f}"
                                            ]
                                ff.write(",".join(output + pixel_and_animal_counts) + "\n")

                            except:
                                continue  # next sweep