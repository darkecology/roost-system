import numpy as np
from tqdm import tqdm 
import copy

class Tracker:

    """ 
        Alg: Greedy algorithm for associating detections across frames, then Kalmen filter to smooth the tracking 
        The tracking algorithm uses a lot of heuristics: (1) bird expansion rate (2) time interval between frames
        Input: detection across frames on a certain station in daily basis
            detections =  [{'scanname', 'det_ID', 'det_score', 'im_bbox': ('x', 'y', 'r')}]
        Output: tracks
            tracks     =  [{'track_ID', 'det_IDs', 'det_or_pred', 'state': {'mean', 'var'}}]
    
    """

    def __init__(self, imsize=600): 
        
        # Based on our AAAI paper, the dispersion rate is 6.61 m/s, corresponding to 1.59 pixel/min in a 600**2 image
        dispersion_rate = 1.59 
        self.params = {
                        'radius_velocity': dispersion_rate * imsize / 600,
                        'max_center_velocity': 3, #empirical max velocity of roost center per minute (unit=pixel) 
                        'R_multiplier': 100, # multiplier in covariance matrix of measurement formula
                        'Q_multiplier': 5, # multiplier in covariance matrix of state transition formula
                        'P_multiplier': 1, # multiplier in the initial error covariance matrix
                      }


    def tracking(self, scans, detections):
        """
            Associate and smooth detections in scans; If not detection in a scan, then tracking algorithm will 
            predict one based on tracking history

            Args: 
                scans: a list of scan name 
                detections: the predictions from the detection model 

            Return:
                updated detections and tracks 
        """


        tracks = [] 
        if scans is None:
            scans = list(set([det["scanname"] for det in detections]))

        """ (0) get ready """
        # sort the scans based on scan time
        scans.sort(key=lambda x: int(x[4:12] + x[13:19])) # the first 4 characters are radar station name

        # add a new field in detections to indicate whether the det has been tracked
        for det in detections:
            det['track_ID'] = -1

        count_track = 1
        for scan_idx, scan in enumerate(tqdm(scans[:-1], desc="Tracking")): # ignore the last frame
            
            """ (1) start from the first frame, if the detections is not tracked yet, init a track """
            for det_idx, det in enumerate(detections):
                if det['scanname'] == scan and det['track_ID'] == -1:
                    # start a track
                    # Note: the original implementation only starts a track if the det_score is higher than 0.5 
                    # and the time from the sunrise is smaller than 30 mins)
                    # here we init a track regardless the frame time to get higher recall
                    detections[det_idx]['track_ID'] = count_track
                    state_mean = np.array([det['im_bbox'][0],  # x
                                           det['im_bbox'][1],  # y
                                           det['im_bbox'][2],  # radious
                                                           0,  # velocity of x                 
                                                           0,  # velocity of y
                             self.params['radius_velocity']])  # velocity of radius
                    state_var = np.eye(6) * self.params['P_multiplier'] # the initial error covariance matrix 
                    track_state = {'mean': state_mean, 'var': state_var}
                    tracks.append({ 'track_ID'   : count_track, 
                                    'det_IDs'    : [det['det_ID']], # list of tracked roost predictions
                                    'det_or_pred': [True], # 1: detection; 0: predicted by physical model 
                                    'state'      : track_state,
                                   })
                    count_track += 1

            """ (2) sort the tracks by the number of dets inside tracks (not the preds from phisical model) """
            tracks.sort(key = lambda x: sum(x['det_or_pred']), reverse=True)

            """ (3) start from the first track, find the best match in the next frame, apply kalman filter  """
            next_scan = scans[scan_idx+1] 
            next_dets_idx = [idx for idx, det in enumerate(detections) if det['scanname'] == next_scan]
            next_dets = np.array(detections)[next_dets_idx]
            # minute from 0:00 am
            delta_t = (int(next_scan[13:15]) - int(scan[13:15])) * 60 + int(next_scan[15:17]) - int(scan[15:17]) 
            for track_idx, track in enumerate(tracks):

                # fine the best match
                if len(next_dets) == 0: # no detections in the next frame 
                    best_next_idx, best_next_det = None, None
                else:
                    best_next_idx, best_next_det = self._find_NN(track['state']['mean'], next_dets, delta_t)  

                if best_next_idx is None:
                    # if no match found in the next frame, predict one based on the track state 
                    updated_state, next_bbox = self._kalman_filter(track['state'], None, None, delta_t)
                    # create a new roost prediction, update every field except scanname
                    roost_pred  =  {'scanname'  : next_scan,
                                    'track_ID'  : track['track_ID'],
                                    'det_ID'    : len(detections),
                                    'det_score' : -1,
                                    'im_bbox'   : next_bbox,}
                    detections.append(roost_pred)
                    # update the state of track,        
                    tracks[track_idx]['det_IDs'].append(roost_pred['det_ID'])
                    tracks[track_idx]['det_or_pred'].append(False)
                else:
                    # apply kalman filter
                    updated_state, next_bbox = self._kalman_filter(track['state'], best_next_det['im_bbox'], 
                                                                   best_next_det['det_score'], delta_t) 
                    detections[next_dets_idx[best_next_idx]]['track_ID'] = track['track_ID']
                    # here I overwrite the original bbox from faster RCNN 
                    detections[next_dets_idx[best_next_idx]]['im_bbox'] = next_bbox 
                    # update the state of track,        
                    tracks[track_idx]['det_IDs'].append(detections[next_dets_idx[best_next_idx]]['det_ID'])
                    tracks[track_idx]['det_or_pred'].append(True)
                tracks[track_idx]['state'] = updated_state

        detections, tracks = self.NMS_tracks(detections, tracks)
        
        return detections, tracks

    def _find_NN(self, track_state, next_dets, t):

        """ 
            Find the nearest detections in the next frame 

            Args: 
                track_state: x, y, r, v_x, v_y, v_r 
                next_dets:   detections in the next frame 
                t:  time interval between adjancent frames 

            Return:
                the best not-yet-matched detections in the next frame
        """

        x, y, r = track_state[:3]
        center_dist = []
        r_change = []
        for idx, next_det in enumerate(next_dets):
            xx, yy, rr = next_det['im_bbox']
            if next_det['track_ID'] == -1:
                center_dist.append(np.sqrt((xx-x) ** 2 + (yy-y) ** 2))
                r_change.append(rr - r)
            else: # this detection has been tracked
                center_dist.append(np.inf)
                r_change.append(np.inf)

        center_dist, r_change = np.array(center_dist), np.array(r_change)
        # Here are some heuristics to find the best match, however, no rigirous ablation study is done to verify 
        # whether each of them are optimal or necessary, it works in practice anyway.
        # (1) the distance should be less than 3*time_interval 
        # (2) change in radius should be higher than 0.1 * radius, but less than 2.7 * time_interval
        match_list = np.where(((center_dist < self.params['max_center_velocity'] * t) &  # roost should not move too far
                               (r_change <= self.params['radius_velocity'] * t)  & # roost should not expand too much
                               (r_change > -0.1 * r)))[0] # roost should not shrink too much
        if len(match_list) == 0: # no match found
            return None, None
        best_match_idx = match_list[np.argsort(center_dist[match_list])[0]]
        return best_match_idx, next_dets[best_match_idx]


    def _kalman_filter(self, track_state, det_bbox, det_score, t):

        """ 
            Given the current state of the track (e.g., position, velocity), 
            and the best detection matched in the next frame, update the state of the track

            Args:
                track_state: the state of the track in the current frame np.array([x, y, r, v_x, v_y, v_r])
                det_bbxo   : the best match of the track in the next frame 
                det_score  : the detection score of the best match 
                t          : the time interval between the two frames
            
            Return:
                updated state of track
                
            This implementation of Kalman filter is based on: 
                    http://web.mit.edu/kirtley/kirtley/binlustuff/literature/control/Kalman%20filter.pdf
        """

        Phi = np.array([[1,0,0,t,0,0],    # x + x_v * t: new x position of roost center
                      [0,1,0,0,t,0],    # y + y_v * t: new y position of roost center
                      [0,0,1,0,0,t],    # r + r_v * t: new roost radius 
                      [0,0,0,1,0,0],    # constant x_v: velocity of roost center in x axis
                      [0,0,0,0,1,0],    # constant y_v: velocity of roost center in y axis
                      [0,0,0,0,0,1]])   # constant r_v: expansion rate of roost radius
        Q = np.eye(6) * self.params['Q_multiplier'] # covariance matrix of noise in state projection formula
        H = np.eye(3, 6)                # H.dot(state) extracts (x, y, r): connection between state and measurement

        X_prev = track_state['mean']    # state at k-th step
        P_prev = track_state['var']     # error covariance matrix at k-th step
        X = Phi.dot(X_prev)               # state projection to (k+1)-th step
        P_prior = Phi.dot(P_prev).dot(Phi.T) + Q  # error covariance matrix at (k+1)-th step

        if det_bbox is None:
            # if no detection to be tracked in the next frame, return the prediction from constant-velocity model
            P = P_prior
        else:
            # otherwise, smooth using Kalman filter
            # R is the covairance matrix of noise in measurement, here I assume it is correlated to det score
            R = np.eye(3) + self.params['R_multiplier'] * np.eye(3) * (1 - det_score)
            # Kalman Gain
            '''
            P_prior_inv = np.linalg.inv(P_prior)
            R_inv = np.linalg.inv(R)
            P = np.linalg.inv(P_prior_inv + H.T.dot(R_inv).dot(H))
            K = P.dot(H.T).dot(R_inv)
            '''
            # below is the most common Kalman filter formula, not sure where the above formula from in caffe version
            # the Kalman gain is equivalent, but the P is different, I believe below should be right
            # but the above also works in practice, anyway 
            K = P_prior.dot(H.T).dot(np.linalg.inv(H.dot(P_prior).dot(H.T) + R))
            P = (1 - K.dot(H)).dot(P_prior)
            # Linear equation
            X = X + K.dot(det_bbox - H.dot(X))

        return {'mean': X, 'var': P}, H.dot(X)


    def NMS_tracks(self, detections, tracks):
        """
            Apply Non-Maximum Suppression on the tracks 

            Args:
                detections: the updated detections after tracking 
                tracks:     the tracks from the above tracking algorithm 

            Returns:
                updated tracks with new field "NMS_suppressed": 
                            True means track is suppressed by NMS; 
                            False means track is not suppressed by NMS
        """
        # (1) sort the tracks
        tracks.sort(key= lambda x: sum(x["det_or_pred"]), reverse=True)
        det_dict = {}
        for det in detections:
            det_dict[det["det_ID"]] = det
        # init
        for track in tracks:
            track["NMS_suppressed"] = False

        # (2) start from the first tracks, measure its overlap with other tracks
        # get the dets from track1 and from track2, measure the overlap, if higher than a thresh, overlap+1
        # for i, track_i in enumerate(tqdm(tracks, desc="NMS on tracks")):
        for i, track_i in enumerate(tracks):
            for j, track_j in enumerate(tracks[i+1:]):
                cooccur_num = 0  # number of co-occurred frames
                overlap_dets = 0 # number of overlapped detections
                for det_ID_i in track_i["det_IDs"]:
                    for det_ID_j in track_j["det_IDs"]:
                        if ((det_dict[det_ID_i]["scanname"] == det_dict[det_ID_j]["scanname"]) and
                            (det_dict[det_ID_i]["det_score"] != -1) and  # score=-1: bbox is from Kalman filter
                            (det_dict[det_ID_j]["det_score"] != -1)):

                            cooccur_num += 1
                            if self._is_det_overlapped(det_dict[det_ID_i]["im_bbox"], 
                                                       det_dict[det_ID_j]["im_bbox"]):
                                overlap_dets += 1
                if cooccur_num != 0 and (overlap_dets / cooccur_num >= 0.5):
                    track_j["NMS_suppressed"] = True
        
        for track in tracks:
            for det_ID in track["det_IDs"]:
                det_dict[det_ID]["track_NMS"] = track["NMS_suppressed"]

        return detections, tracks


    def _is_det_overlapped(self, bbox1, bbox2):
        x1,y1,r1 = bbox1
        x2,y2,r2 = bbox2
        if np.sqrt((x1-x2)**2 + (y1-y2)**2) < max(r1, r2):
            return True
        else:
            return False


if __name__ == "__main__":

    tracker = Tracker()
    
    detections = [{'scanname':'KDOX20111010_071218_V06',
                    'det_ID': 1, 
                    'det_score': 0.99, 
                    'im_bbox': [10, 10, 10]}, 
                  {'scanname':'KDOX20111010_071218_V06', 
                    'det_ID': 2, 
                    'det_score': 0.40, 
                    'im_bbox': [50, 50, 10]}, 
                  {'scanname':'KDOX20111010_072218_V06', 
                    'det_ID': 3, 
                    'det_score': 0.99, 
                    'im_bbox': [12, 12, 15]}, 
                  {'scanname':'KDOX20111010_072218_V06', 
                    'det_ID': 4, 
                    'det_score': 0.79, 
                    'im_bbox': [55, 55, 20]}, 
                  {'scanname':'KDOX20111010_073218_V06', 
                    'det_ID': 3, 
                    'det_score': 0.85, 
                    'im_bbox': [16, 16, 25]}, 
                  {'scanname':'KDOX20111010_073218_V06', 
                    'det_ID': 4, 
                    'det_score': 0.79, 
                    'im_bbox': [56, 56, 35]}, 
                  {'scanname':'KDOX20111010_073218_V06', 
                    'det_ID': 4, 
                    'det_score': 0.79, 
                    'im_bbox': [30, 30, 20]},
                 ]

    detections, tracks = tracker.tracking(detections)
    for det in detections:
        print(det)
    for track in tracks:
        print(track)
