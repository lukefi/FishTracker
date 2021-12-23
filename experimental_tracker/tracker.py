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
from scipy.optimize import linear_sum_assignment

from track import Track

class Tracker:
    """Tracker class for track management.

    Takes care of track management: creating, updating and deleting tracks. Uses
    global nearest neighbour in data association. Indivual tracks are maintained
    by Track class using KF.

    Attributes:
        max_age: Max number of frames that a tracks survives without new measurements.
        min_hits: Min number of consecutive measurements needed for initiating new track.
        search_radius: Euclidean gating threshold for data association.
    """

    @staticmethod
    def linear_assignment(cost_matrix):
        """Solves point pairs that minimize global data association cost.

        Args:
            cost_matrix: Cost matrix defining ataassociatino costs between point pairs.

        Returns:
            The data associatiion list.
        """

        x, y = linear_sum_assignment(cost_matrix)
        return np.array(list(zip(x, y)))

    @staticmethod
    def distance(d1, d2):
        return (d1[0]-d2[0])**2 + (d1[1]-d2[1])**2 

    @staticmethod
    def compute_cost(pt_1, pt_2, radius=10):
        """Computes cost matrix between two detections based on Euclidean distance.

        Args:
            pt_1: Array of 2D points.
            pt_2: Array array of 2D points.

        Returns:
            The cost matrix.
        """

        cost_matrix = np.zeros(shape=(len(pt_1), len(pt_2)))

        for i, p1 in enumerate(pt_1):
            for j, p2 in enumerate(pt_2):
                d = Tracker.distance(p1, p2)
                cost_matrix[i,j] = d

        cost_matrix[cost_matrix > radius ** 2] = float(1e100) # TODO 

        return cost_matrix

    @staticmethod
    def match_points(points_1, points_2, search_radius=10):
        """Computes data association task between two point sets. 
 
        Args:
            points_1: Numpy array of 2D points.
            points_2: Numpy array of 2D points.
            search_radius: Euclidean distance threshold for confirming match.

        Returns:
            Indices of mathed points.
            Unmatched points from points_1.
            Unmatched points from points_2.
        """

        if len(points_1) == 0 or len(points_2) == 0:
            return [], list(range(0, len(points_1))), list(range(0, len(points_2)))

        cost_matrix = Tracker.compute_cost(points_1, points_2, search_radius)
        indices = Tracker.linear_assignment(cost_matrix)

        matched_indices = []
        for __, idx in enumerate(indices):
            if cost_matrix[idx[0],idx[1]] <  search_radius ** 2:
                matched_indices.append(idx)

        matched_indices = np.array(matched_indices)

        if len(matched_indices) == 0:
            return [], list(range(0, len(points_1))), list(range(0, len(points_2)))

        unmatched_pts1 = []
        for pt, __ in enumerate(points_1):
            if pt not in matched_indices[:,0]:
                unmatched_pts1.append(pt)

        unmatched_pts2 = []     
        for pt, __ in enumerate(points_2):
            if pt not in matched_indices[:,1]:
                unmatched_pts2.append(pt)
        
        return matched_indices, unmatched_pts1, unmatched_pts2

    def __init__(self, max_age=5, min_hits=3, search_radius=10):
        """Inits Tracker class."""

        self.max_age = max_age
        self.min_hits = min_hits
        self.search_radius = search_radius

        self.tracks = []
        self._frame_counter = 0

    def get_track_points(self):
        """Returns an array (Numpy) of latest track positions."""

        track_points = np.empty((0,2))
        for t, __ in enumerate(self.tracks):
            track_points = np.vstack([track_points, [self.tracks[t].last_position]])
        return track_points

    def _match_detections_and_tracks(self, detections):
        """Computes data association between measurements and existing tracks.
 
        Args:
            detections: Measurements, Numpy array of 2D points.

        Returns:
            Unmatched detections.
        """

        track_points = self.get_track_points()
        ma_indices, um_detections, __ = Tracker.match_points(detections, track_points, self.search_radius)

        # All detetctions unmatched
        if len(ma_indices) == 0:
            return detections

        # Update measurements for associated tracks
        for idx in ma_indices:
            self.tracks[idx[1]].last_measurement = detections[idx[0]]
        
        return detections[um_detections]

    def _remove_tentative(self): #TODO paremmin
        for t1 in self.tracks:
            if t1.status is "Removed":
                continue
            t1_loc = t1.last_position
            for t2 in self.tracks:
                if t2.status is "Removed":
                    continue
                t2_loc = t2.last_position
                cost = Tracker.distance(t1_loc, t2_loc)
                if cost == 0:
                    continue
                if cost < self.search_radius ** 2:
                    if t1.status is "Tentative":
                        t1.status = "Removed"
                    if t1.status is "Active" and t2.status is "Tentative":
                        t2.status = "Removed"

    def _initiate_new_tracks(self, detections):
        """Creates new tracks from detections.
 
        Args:
            detections: Measurements, Numpy array of 2D points.
        """

        for i, detection in enumerate(detections):
            # Do not initialize new track too close to existing tracks
            can_initialize = True
            for track in self.tracks:
                track_position = track.last_position
                cost = Tracker.distance(track_position, detection)
                if cost < self.search_radius ** 2:
                    can_initialize = False

            if can_initialize:
                self.tracks.append(Track(self._frame_counter, detection))

    def remove_deleted(self):
        self.tracks = [t for t in self.tracks if not t.status == "Removed"]

    def update(self, detections = np.empty((0, 2))):
        """Performs track management steps.
 
        Args:
            detections: Measurements, Numpy array of 2D points.
        """

        self._frame_counter += 1

        # Predict states etc.
        for track in self.tracks:
            track.pre_process()

        # Remove tentative inside tracks
        self._remove_tentative()
        #self.remove_deleted()

        # Data association
        unmatched_detections = self._match_detections_and_tracks(detections)

        # 
        for track in self.tracks:
            track.post_process(self.min_hits)

        self._initiate_new_tracks(unmatched_detections)

        for track in self.tracks:
            track.delete(self.max_age)

        self.remove_deleted()
