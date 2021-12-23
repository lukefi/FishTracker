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
from filterpy.kalman import KalmanFilter

class Track:
    """Kalman filter class for estimating the state of a 2D point.
    
    Filter uses (nearly) constant velocity state-space model.

    Attributes:
        delta_t: Time interval between samples. Not used currently.
        save_history: A boolean indicating if the track trajectory will be stored.
        len_history: Length of the track trajectory.
        status: Track's status as string: "Tentative", "Active", "Lost", "Removed".
        time_since_update: Number of frames from the last update.
        history: Track trajectory (history).
        id: Track's unique id.
        last_measurement: Latest measurement sed to update the track.
        last_position: Last position estimate for the track.
    """

    def __init__(self, id, detection):

        self.delta_t = 0.1

        self.save_history = True
        self.len_history = 10000
        self.history = np.empty((0, 2))

        self.status = "Tentative"
        self.time_since_update = 0

        self.id = id
        self.kf = KalmanFilter(dim_x=4, dim_z=2)

        dt = self.delta_t
        self.kf.F = np.array([[1, dt,  0,  0],
                              [0,  1,  0,  0],
                              [0,  0,  1, dt],  
                              [0,  0,  0,  1]])

        self.kf.H = np.array([[1, 0, 0, 0],
                              [0, 0, 1, 0]])


        self.kf.R *= 1.0
        self.kf.P *= 1.0
        self.kf.Q *= 0.1
        
        self.last_measurement = detection
        self.last_position = detection
        self.kf.x[0] = detection[0]
        self.kf.x[2] = detection[1]

        self.consecutive_updates = 0

    def _predict(self):
        """Performs the predict step of KF."""
        self.kf.predict()
        self.last_position = np.concatenate((self.kf.x[0], self.kf.x[2]))
        if self.save_history == True:
            self.history = np.vstack([self.history, [self.last_position]])
            if len(self.history) > self.len_history:
                self.history = np.delete(self.history, 0, axis=0)

    def pre_process(self):
        """Prepares track for update. Some logic here."""

        if self.status == "Removed":
            return

        self.time_since_update += 1
        self.last_measurement = np.empty((0, 2))

        # Set existing tracks initially lost
        if self.status == "Active":
            self.status = "Lost"
    
        # Perform predict step of KF
        self._predict()

    def post_process(self, min_hits):
        """Performs the update step of KF."""

        if self.status == "Removed":
            return

        # No matching measurement found
        if len(self.last_measurement) == 0:
            self.consecutive_updates = 0
            return

        self.kf.update(self.last_measurement)
        self.last_position = np.concatenate((self.kf.x[0], self.kf.x[2]))

        self.consecutive_updates += 1
        self.time_since_update = 0

        if self.status == "Tentative" and self.consecutive_updates >= min_hits:
            self.status = "Active"
           
        if self.status == "Lost":
            self.status = "Active"

    def delete(self, max_age):
        """Turns track state to Removed".
         
        Args:
            max_age: Number of frames the track lives without associated measurements.
        
        """
        if self.time_since_update >= max_age:
            self.status = "Removed"