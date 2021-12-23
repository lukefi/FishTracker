# -*- coding: utf-8 -*-
"""
This file is part of Fish Tracker.
Copyright 2021, VTT Technical research centre of Finland Ltd.
Developed by: Otto Korkalo.

Fish Tracker is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Fish Tracker is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Fish Tracker.  If not, see <https://www.gnu.org/licenses/>.
"""

import numpy as np
import cv2
import random
import sys

from track import Track
from tracker import Tracker

"""
Example application for using the Tracker.

Needs two data files: test_data.npy (detections) and
test_image.png (for visualisation).
"""

def rgb(minimum, maximum, value):
    minimum, maximum = float(minimum), float(maximum)
    ratio = 2 * (value-minimum) / (maximum - minimum)
    b = int(max(0, 255*(1 - ratio)))
    r = int(max(0, 255*(ratio - 1)))
    g = 255 - b - r
    return r, g, b

def main():

    # Create tracker
    tracker = Tracker(max_age=20, min_hits=10, search_radius=30)

    # Load test data and baclground image for visualisation
    data = np.load("test_data.npy", allow_pickle=True)
    image_o = cv2.imread("test_image.png", 0)

    all_detections = []

    # Combine detectinons
    for i in range(len(data)):
        
        detections = np.empty((len(data[i]), 2))
        detections[:,0] = data[i][:,0] + (data[i][:,2] - data[i][:,0]) / 2.0
        detections[:,1] = data[i][:,1] + (data[i][:,3] - data[i][:,1]) / 2.0
        all_detections.append(detections)

    for i, detections in enumerate(all_detections):
 
        image_o_rgb = cv2.applyColorMap(image_o, cv2.COLORMAP_OCEAN)
 
        for detection in detections:
            cv2.circle(image_o_rgb, tuple(list(detection.astype(int))), 3, (0,128,255), -1)

        # Apply tracker for the set of detections (per frame)
        tracker.update(detections)

        # Get tracking results and visualize
        for t, track in enumerate(tracker.tracks):

            cv2.putText(image_o_rgb, str(track.consecutive_updates), tuple(list(track.last_position.astype(int))), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)
            cv2.circle(image_o_rgb, tuple(list(track.last_position.astype(int))), 10, (255,255,255), 1)
            random.seed(track.id*100)
            [rr,gg,bb] = rgb(0, 100, random.random()*100)

            previous = []
            for t in track.history:
                if len(previous) == 0:
                    previous = t
                
                if track.status == "Tentative":
                    cv2.line(image_o_rgb, tuple(list(previous.astype(int))), tuple(list(t.astype(int))), (128,128,128), 2)
                elif track.status == "Lost":
                    cv2.line(image_o_rgb, tuple(list(previous.astype(int))), tuple(list(t.astype(int))), (0,0,64), 2)
                elif track.status == "Active":
                    cv2.line(image_o_rgb, tuple(list(previous.astype(int))), tuple(list(t.astype(int))), (rr,gg,bb), 2)
                elif track.status == "Removed":
                    cv2.line(image_o_rgb, tuple(list(previous.astype(int))), tuple(list(t.astype(int))), (0,0,255), 2)

                previous = t

        cv2.imshow("image", image_o_rgb)
        key = cv2.waitKey(0)

        # Remove deleted tracks
        tracker.remove_deleted()


if __name__ == "__main__":
    main()