import numpy as np

import pyart
from wsrlib import *

import pandas as pd
import csv

import scipy

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# requirements:
#  - wsrlib
#  - pyproj
#  - netcdf4
#  - scipy

# Import station information database:
# from radar_stations_data import *

import pytz

def get_horizontal_beamwidth(number_of_azimuths):
    '''
    Get the horizontal beamwidth of the current radar data in degrees. These angles are usually reported in degrees,
    but we convert them to radians for manipulation.

    Parameters
    ----------
    number_of_azimuths: int
        number of azimuth bins in the current radar data

    Returns
    -------
    theta: float
        the horizontal beamwidth angle (in radians)
    '''

    # Array of possible horizontal resolutions:
    array = np.array([360, 720])

    # Find the index of the value closest to the number of azimuths:
    idx = (np.abs(array - number_of_azimuths)).argmin()

    # Number of angular bins available:
    angular_bins = array[idx]

    # Calculate the angle of each bin, convert to radians:
    theta_rad = np.deg2rad(360/angular_bins)

    return theta_rad

def get_sampling_volume(theta_rad, phi_rad, rng_gate, rngs, equation="chilson"):
    '''
    Get the sampling volume for each range-along-the-azimuth distance, depending on the year and the
    range gate of the current radar data loaded.

    Parameters
    ----------
    theta_rad: float
        horizontal beamwidth angle in radians
    phi_rad: float
        vertical beamwidth angle in radians
    rng_gate: float
        distance between subsequent cells along the range
    rngs: array
        ranges along the azimuth obtained from the radar scan

    Returns
    -------
    volume_range: array
        returns an array containing the sampling volume in cubic kilometers for each range-along-the-azimuth distance
    '''
    if equation == "chilson":
        # Calculate volume in cubic meters:
        volume_range = (( 0.35 * np.sqrt(2 * np.pi) ) / (2 * np.log(2) ) ) * (np.pi * (rngs**2) * rng_gate * (theta_rad * phi_rad))/4

        # Convert to cubic kilometers to match reflectivity units:
        volume_range = volume_range * 10**-9

        return volume_range

    elif equation == "rinehart":
        print("Using Rinehart volume.")
        # Calculate volume in cubic meters:
        volume_range = np.pi * rngs**2 * theta_rad * phi_rad * rng_gate / (8 * np.log(2))

        # Convert to cubic kilometers to match reflectivity units:
        volume_range = volume_range * 10**-9

        return volume_range


def image2xy(x, y, r=0, dim=600, rmax=150000):
    '''
    Convert from image coordinates to (x,y) coordinates offset from radar

    '''

    x0 = y0 = dim/2.0 # origin
    x =  (x - x0)*2*rmax/dim
    y = -(y - y0)*2*rmax/dim
    r = r*2*rmax/dim

    return (x, y, r)


def get_rcs(mass):
    '''
    Return presumed radar cross section of a bird given its mass in grams.

    Parameters
    ----------
    mass: float
        mass of the bird species in grams (refer to Handbook of Body Masses by Dunning, 2008)

    Returns
    -------
    rcs: float
        radar cross section of given speces in cm^2
    '''

    return 10**(0.699*np.log10(mass))


def calc_number_of_birds(radar, sweep_number, detection_coordinates, rcs, threshold, method):
    '''
    Calculate the number of birds using one of two methods: either by using radar's native polar
    coordinates or by calculating the height-by-range and assuming all pixels in a cartesian grid have the same area.

    Parameters
    ----------
    radar: Radar
        Py-Art radar object
    sweep_number: int
        number of the sweep in the Py-Art format (first is 0)
    real_angle: float
        real value of the sweep angle, obtained from the radar file
    detection_coordinates: tuple
        a tuple containing the (x, y) coordinates of the roost and the roost radius in meters
    rcs: float
        radar cross section of target species
    threshold: float
        over this value given in linear scale, reflectivity will be set to zero.
    method: string
        what method to use, either "polar" or "by_diameter"

    Returns
    -------
    number_of_birds: float
        number of birds calculated by chosen method
    '''

    # Get sampled ranges in meters:
    rngs = radar.range['data']
    rng_max = max(rngs)

    #Get range gate in meters:
    rng_gate = radar.range["meters_between_gates"]

    # Get the azimuths of each ray:
    azs = radar.get_azimuth(sweep_number)

    # Get the cartesian coordinates of each gate (sampling bin):
    coords = radar.get_gate_x_y_z(sweep = sweep_number)
    coords = np.array(coords)

    # Retrieve sweep and convert to reflectivity (eta):
    sweep = radar.get_field(sweep=sweep_number, field_name="reflectivity")

    # If the pixel is NaN, we will set it to the least possible value in dBZ scale:
    sweep = sweep.filled(-33)

    # Convert dBZ to m^2/km^3:
    sweep, _ = z_to_refl(idb(sweep))

    # Get the shape of the sweep matrix:
    number_of_azimuths = sweep.shape[0]
    number_of_ranges = sweep.shape[1]

    # Separate the results in two matrices, one for x-coordinates, one for y-coordinates:
    # Note: we will have, for each combination of azimuth and range, the correspoding value
    # of x and of y.
    x = coords[0]
    y = coords[1]

    # Get the unique values, meaning the entire range of possible coordinates along the x and y axis:
    x_unique = np.unique(x)
    y_unique = np.unique(y)

    x_c, y_c, r_c = detection_coordinates

    # Get a rectangle of radius rc around the center of the roost:
    x_inds = np.where(np.abs(x_unique - x_c) < r_c)
    y_inds = np.where(np.abs(y_unique - y_c) < r_c)

    # Find rectangle maximum and minimum values along each axis:
    x_min = min(x_unique[x_inds])
    x_max = max(x_unique[x_inds])
    y_min = min(y_unique[y_inds])
    y_max = max(y_unique[y_inds])

    # Use the extreme values to create two masks, one for each axis array:
    x_mask = (x > x_min) & (x < x_max).astype(int)
    y_mask = (y > y_min) & (y < y_max).astype(int)

    # Create a new mask that has the intersection between x_mask and y_mask:
    i = 0
    j = 0

    mask = np.zeros((number_of_azimuths, number_of_ranges))

    for i in range(number_of_azimuths):
        for j in range(number_of_ranges):
            if ((x_mask[i,j] == 1) and (y_mask[i,j] == 1)):
                mask[i,j] = 1
            else:
                mask[i,j] = 0

    if method == "polar":

        theta_rad = get_horizontal_beamwidth(number_of_azimuths)
        phi_rad = np.deg2rad(1)

        volume_range = get_sampling_volume(theta_rad, phi_rad, rng_gate, rngs)

        # Apply mask to sweep matrix
        masked = sweep*mask

        # Get the percentage of pixels that exceed the threshold and filter them:
        roost_area = sum(sum(masked > 0))
        overthresh_percent = sum(sum(masked > threshold))/roost_area
        masked[masked > threshold] = 0

        # Create an intermediate array where each cell is a multiplication of reflectivity and volume:
        # This array will have the same dimensions as the raw radar data:
        roost_matrix = []

        for i in range(len(masked)):
            ray = masked[i]
            prod = (ray*volume_range)/rcs
            roost_matrix.append(prod)

        roost_matrix = np.array(roost_matrix)

        number_of_birds = sum(sum(roost_matrix))

    return number_of_birds, masked, overthresh_percent, volume_range
