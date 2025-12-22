# ImageStag Filters - Coordinate Transforms
"""
Bidirectional coordinate transformation classes.

These classes allow mapping points between original and transformed
coordinate systems, useful for:
- Mapping detected features from distorted to corrected images
- Projecting overlay graphics onto transformed images
- Inverse lookups for image compositing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np


Point = tuple[float, float]
Points = Sequence[Point] | np.ndarray


@dataclass
class CoordinateTransform(ABC):
    """Base class for bidirectional coordinate transforms.

    Transforms map points between source (original) and destination
    (transformed) coordinate systems.

    Usage:
        # Apply transform to get transformed result
        result, transform = filter.apply_with_transform(image)

        # Map a point from source to destination
        dst_point = transform.forward((100, 200))

        # Map a point from destination back to source
        src_point = transform.inverse((150, 180))

        # Transform multiple points at once
        dst_points = transform.forward_points([(0, 0), (100, 100), (200, 50)])
    """

    @abstractmethod
    def forward(self, point: Point) -> Point:
        """Transform a single point from source to destination coordinates.

        Args:
            point: (x, y) in source coordinates

        Returns:
            (x, y) in destination coordinates
        """
        pass

    @abstractmethod
    def inverse(self, point: Point) -> Point:
        """Transform a single point from destination to source coordinates.

        Args:
            point: (x, y) in destination coordinates

        Returns:
            (x, y) in source coordinates
        """
        pass

    def forward_points(self, points: Points) -> np.ndarray:
        """Transform multiple points from source to destination.

        Args:
            points: Sequence of (x, y) points or Nx2 array

        Returns:
            Nx2 numpy array of transformed points
        """
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)
        return np.array([self.forward((p[0], p[1])) for p in pts])

    def inverse_points(self, points: Points) -> np.ndarray:
        """Transform multiple points from destination to source.

        Args:
            points: Sequence of (x, y) points or Nx2 array

        Returns:
            Nx2 numpy array of transformed points
        """
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)
        return np.array([self.inverse((p[0], p[1])) for p in pts])


@dataclass
class IdentityTransform(CoordinateTransform):
    """Identity transform - no coordinate change."""

    def forward(self, point: Point) -> Point:
        return point

    def inverse(self, point: Point) -> Point:
        return point


@dataclass
class LensTransform(CoordinateTransform):
    """Transform for lens distortion correction.

    Maps between distorted (original) and undistorted (corrected) coordinates.

    - forward(): distorted -> undistorted
    - inverse(): undistorted -> distorted
    """
    camera_matrix: np.ndarray = field(repr=False)
    dist_coeffs: np.ndarray = field(repr=False)
    new_camera_matrix: np.ndarray = field(repr=False)
    image_size: tuple[int, int] = (0, 0)

    def forward(self, point: Point) -> Point:
        """Transform from distorted to undistorted coordinates."""
        import cv2

        # cv2.undistortPoints expects Nx1x2 array
        pts = np.array([[[point[0], point[1]]]], dtype=np.float64)

        # Undistort the point
        undistorted = cv2.undistortPoints(
            pts,
            self.camera_matrix,
            self.dist_coeffs,
            P=self.new_camera_matrix
        )

        return (float(undistorted[0, 0, 0]), float(undistorted[0, 0, 1]))

    def inverse(self, point: Point) -> Point:
        """Transform from undistorted to distorted coordinates."""
        # To go from undistorted to distorted, we need to apply distortion
        # This is done by normalizing the point, applying distortion model,
        # then projecting back

        fx = self.new_camera_matrix[0, 0]
        fy = self.new_camera_matrix[1, 1]
        cx = self.new_camera_matrix[0, 2]
        cy = self.new_camera_matrix[1, 2]

        # Normalize point (remove new camera matrix)
        x_norm = (point[0] - cx) / fx
        y_norm = (point[1] - cy) / fy

        # Apply distortion model
        k1, k2, p1, p2, k3 = self.dist_coeffs[:5]

        r2 = x_norm**2 + y_norm**2
        r4 = r2**2
        r6 = r2**3

        # Radial distortion
        radial = 1 + k1*r2 + k2*r4 + k3*r6

        # Tangential distortion
        x_dist = x_norm * radial + 2*p1*x_norm*y_norm + p2*(r2 + 2*x_norm**2)
        y_dist = y_norm * radial + p1*(r2 + 2*y_norm**2) + 2*p2*x_norm*y_norm

        # Project back using original camera matrix
        fx_orig = self.camera_matrix[0, 0]
        fy_orig = self.camera_matrix[1, 1]
        cx_orig = self.camera_matrix[0, 2]
        cy_orig = self.camera_matrix[1, 2]

        x_out = x_dist * fx_orig + cx_orig
        y_out = y_dist * fy_orig + cy_orig

        return (float(x_out), float(y_out))

    def forward_points(self, points: Points) -> np.ndarray:
        """Efficiently transform multiple points from distorted to undistorted."""
        import cv2

        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)

        # Reshape for cv2: Nx1x2
        pts_cv = pts.reshape(-1, 1, 2)

        undistorted = cv2.undistortPoints(
            pts_cv,
            self.camera_matrix,
            self.dist_coeffs,
            P=self.new_camera_matrix
        )

        return undistorted.reshape(-1, 2)

    def inverse_points(self, points: Points) -> np.ndarray:
        """Transform multiple points from undistorted to distorted."""
        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)

        return np.array([self.inverse((p[0], p[1])) for p in pts])


@dataclass
class PerspectiveTransform(CoordinateTransform):
    """Transform for perspective correction.

    Maps between original and perspective-corrected coordinates.

    - forward(): original -> corrected
    - inverse(): corrected -> original
    """
    matrix: np.ndarray = field(repr=False)
    inverse_matrix: np.ndarray = field(repr=False)

    @classmethod
    def from_points(
        cls,
        src_points: np.ndarray,
        dst_points: np.ndarray
    ) -> 'PerspectiveTransform':
        """Create transform from source and destination points.

        Args:
            src_points: 4x2 array of source points
            dst_points: 4x2 array of destination points

        Returns:
            PerspectiveTransform instance
        """
        import cv2

        src = np.asarray(src_points, dtype=np.float32)
        dst = np.asarray(dst_points, dtype=np.float32)

        matrix = cv2.getPerspectiveTransform(src, dst)
        inverse_matrix = cv2.getPerspectiveTransform(dst, src)

        return cls(matrix=matrix, inverse_matrix=inverse_matrix)

    def forward(self, point: Point) -> Point:
        """Transform from original to corrected coordinates."""
        import cv2

        pts = np.array([[[point[0], point[1]]]], dtype=np.float64)
        transformed = cv2.perspectiveTransform(pts, self.matrix)
        return (float(transformed[0, 0, 0]), float(transformed[0, 0, 1]))

    def inverse(self, point: Point) -> Point:
        """Transform from corrected to original coordinates."""
        import cv2

        pts = np.array([[[point[0], point[1]]]], dtype=np.float64)
        transformed = cv2.perspectiveTransform(pts, self.inverse_matrix)
        return (float(transformed[0, 0, 0]), float(transformed[0, 0, 1]))

    def forward_points(self, points: Points) -> np.ndarray:
        """Efficiently transform multiple points forward."""
        import cv2

        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)

        pts_cv = pts.reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pts_cv, self.matrix)
        return transformed.reshape(-1, 2)

    def inverse_points(self, points: Points) -> np.ndarray:
        """Efficiently transform multiple points inverse."""
        import cv2

        pts = np.asarray(points, dtype=np.float64)
        if pts.ndim == 1:
            pts = pts.reshape(1, 2)

        pts_cv = pts.reshape(-1, 1, 2)
        transformed = cv2.perspectiveTransform(pts_cv, self.inverse_matrix)
        return transformed.reshape(-1, 2)
