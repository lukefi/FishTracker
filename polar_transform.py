import math
import numpy as np
import cv2

def cart2pol(x, y):
	rho = np.sqrt(x**2 + y**2)
	phi = np.arctan2(y, x)
	return(rho, phi)

def pol2cart(rho, phi):
	x = rho * np.cos(phi)
	y = rho * np.sin(phi)
	return(x, y)
	
def linear(x, min_x, max_x, min_y, max_y):
	return (x - min_x) / (max_x - min_x) * (max_y - min_y) + min_y

class PolarTransform:
	def __init__(self, pol_shape, cart_height, radius_limits, beam_angle):
		print("Init mapping")
		self.pol_shape = pol_shape
		self.setCartShape(cart_height, beam_angle)
		self.radius_limits = radius_limits
		self.angle_limits = (np.pi/2 - beam_angle/2, np.pi/2 + beam_angle/2)
		# self.center = (self.cart_shape[0] - 1, (self.cart_shape[1] - 1) / 2)
		self.center = (0, (self.cart_shape[1] - 1) / 2)
		self.metric_cart_shape = (radius_limits[1], self.cart_shape[1] / self.cart_shape[0] * radius_limits[1])

		self.map_x = np.zeros(self.cart_shape, dtype=np.float32)
		self.map_y = np.zeros(self.cart_shape, dtype=np.float32)

		for j in range(self.cart_shape[0]):	
			for i in range(self.cart_shape[1]):
				_j = self.cart_shape[0] - j - 1
				self.map_y[j, i], self.map_x[j, i] = self.cart2polImage(_j, i)
		print("End mapping")

	def setCartShape(self, height, angle):
		half_width = height * np.sin(angle/2)

		self.cart_shape = (height, 2 * math.ceil(half_width))
		
	def pix2metC(self, y, x):
		""" Transforms from cartesian pixel coordinates to cartesian metric coordinates
		"""

		_x = linear(x, 0, self.cart_shape[1] - 1, 0, self.metric_cart_shape[1])
		_y = linear(y, 0, self.cart_shape[0] - 1, 0, self.metric_cart_shape[0])
		return (_y, _x)

	def pix2metCI(self, y, x):
		""" Transforms from cartesian pixel coordinates to cartesian metric coordinates (inverted y-axis)
		"""

		_x = linear(x, 0, self.cart_shape[1] - 1, 0, self.metric_cart_shape[1])
		_y = linear(self.cart_shape[0] - y, 0, self.cart_shape[0] - 1, 0, self.metric_cart_shape[0])
		return (_y, _x)

	def getMetricDistance(self, y1, x1, y2, x2):
		y_met, x_met = self.pix2metC(y2-y1, x2-x1)
		rho_met, phi_met = cart2pol(x_met, y_met)
		return rho_met, phi_met
		
	def met2pixC(self, y, x):
		""" Transforms from cartesian metric coordinates to cartesian pixel coordinates
		"""

		_x = linear(x, 0, self.metric_cart_shape[1], 0, self.cart_shape[1] - 1)
		_y = linear(y, 0, self.metric_cart_shape[0], 0, self.cart_shape[0] - 1)
		return (_y, _x)
		
		
	def pix2metP(self, rho, phi):
		""" Transforms from polar pixel coordinates to polar metric coordinates
		"""

		_rho = linear(rho, -0.5, self.pol_shape[0] - 0.5, self.radius_limits[0], self.radius_limits[1])
		_phi = linear(phi, -0.5, self.pol_shape[1] - 0.5, *self.angle_limits)
		return (_rho, _phi)
	
	def met2pixP(self, rho, phi):
		""" Transforms from polar metric coordinates to polar pixel coordinates
		"""

		_rho = linear(rho, self.radius_limits[0], self.radius_limits[1], -0.5, self.pol_shape[0] - 0.5)
		_phi = linear(phi, *self.angle_limits, -0.5, self.pol_shape[1] - 0.5)
		return (_rho, _phi)

	def cart2polMetric(self, y, x, invert_y=False):
		""" Transforms cartesian pixel coordinates to polar metric coordinates
			by first transforming the pixel coordinates to cartesian metric coordinates
			and then to polar metric coordinates.
		"""
		if invert_y:
			y_met, x_met = self.pix2metC(y-self.cart_shape[0]-self.center[0], self.center[1]-x)
		else:
			y_met, x_met = self.pix2metC(y-self.center[0], self.center[1]-x)
		rho_met, phi_met = cart2pol(x_met, y_met)
		#print("{:.2f} {:.2f}\n{:.2f} {:.2f}\n{:.2f} {:.2f}\n".format(x,y,x_met,y_met,rho_met,phi_met))
		return rho_met, phi_met
		
	def cart2polImage(self, y, x):
		""" Transforms cartesian pixel coordinates to polar pixel coordinates
			by first transforming the pixel coordinates to cartesian metric coordinates,
			then to polar metric coordinates and finally to polar pixel coordinates.
		"""
		y_met, x_met = self.pix2metC(y-self.center[0], self.center[1]-x)
		rho_met, phi_met = cart2pol(x_met, y_met)
		rho, phi = self.met2pixP(rho_met, phi_met)
		return rho, phi

	#TODO: def pol2cartImage(self, rho, phi):

	def remap(self, image, interpolation=cv2.INTER_NEAREST):
		if not isinstance(image, np.ndarray) or image.shape != self.pol_shape:
			raise ValueError("Passed array is not of the right shape")

		return cv2.remap(cv2.flip(image,0), self.map_x, self.map_y, interpolation)
