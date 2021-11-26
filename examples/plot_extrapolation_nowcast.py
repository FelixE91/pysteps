#!/bin/env python
"""
Extrapolation nowcast
=====================

This tutorial shows how to compute and plot an extrapolation nowcast using
Finnish radar data.

"""

from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from pprint import pprint
from pysteps import io, motion, nowcasts, rcparams, verification
from pysteps.utils import conversion, transformation
from pysteps.visualization import plot_precip_field, quiver

###############################################################################
# Read the radar input images
# ---------------------------
#
# First, we will import the sequence of radar composites.
# You need the pysteps-data archive downloaded and the pystepsrc file
# configured with the data_source paths pointing to data folders.

# Selected case
date = datetime.strptime("201609281600", "%Y%m%d%H%M")
data_source = rcparams.data_sources["fmi"]
n_leadtimes = 12

###############################################################################
# Load the data from the archive
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

root_path = data_source["root_path"]
path_fmt = data_source["path_fmt"]
fn_pattern = data_source["fn_pattern"]
fn_ext = data_source["fn_ext"]
importer_name = data_source["importer"]
importer_kwargs = data_source["importer_kwargs"]
timestep = data_source["timestep"]

# Find the input files from the archive
fns = io.archive.find_by_date(
    date, root_path, path_fmt, fn_pattern, fn_ext, timestep, num_prev_files=2
)

# Read the radar composites
importer = io.get_method(importer_name, "importer")
reflectivity, _, metadata = io.read_timeseries(fns, importer, legacy=True, **importer_kwargs)

# Convert to rain rate
precip = reflectivity.pysteps.to_rainrate()

# Plot the rainfall field
plot_precip_field(precip[-1, :, :], geodata=metadata)
plt.show()

# Store the last frame for plotting it later later
R_ = precip[-1, :, :].copy()

# Log-transform the data to unit of dBR
precip = precip.pysteps.db_transform()

# Nicely print the metadata
pprint(metadata)

###############################################################################
# Compute the nowcast
# -------------------
#
# The extrapolation nowcast is based on the estimation of the motion field,
# which is here performed using a local tracking approach (Lucas-Kanade).
# The most recent radar rainfall field is then simply advected along this motion
# field in oder to produce an extrapolation forecast.

# Estimate the motion field with Lucas-Kanade
oflow_method = motion.get_method("LK")
V = oflow_method(precip[-3:, :, :])

# Extrapolate the last radar observation
extrapolate = nowcasts.get_method("extrapolation")
precip[~np.isfinite(precip)] = metadata["zerovalue"]
R_f = extrapolate(precip[-1, :, :], V, n_leadtimes)

# Back-transform to rain rate
R_f = R_f.pysteps.db_transform(inverse=True)

# Plot the motion field
plot_precip_field(R_, geodata=metadata)
quiver(V, geodata=metadata, step=50)
plt.show()

###############################################################################
# Verify with FSS
# ---------------
#
# The fractions skill score (FSS) provides an intuitive assessment of the
# dependency of skill on spatial scale and intensity, which makes it an ideal
# skill score for high-resolution precipitation forecasts.

# Find observations in the data archive
fns = io.archive.find_by_date(
    date,
    root_path,
    path_fmt,
    fn_pattern,
    fn_ext,
    timestep,
    num_prev_files=0,
    num_next_files=n_leadtimes,
)
# Read the radar composites
R_o, _, metadata_o = io.read_timeseries(fns, importer, legacy=True, **importer_kwargs)
R_o = R_o.pysteps.to_rainrate(zr_a=223.0, zr_b=1.53)

# Compute fractions skill score (FSS) for all lead times, a set of scales and 1 mm/h
fss = verification.get_method("FSS")
scales = [2, 4, 8, 16, 32, 64, 128, 256, 512]
thr = 1.0
score = []
for i in range(n_leadtimes):
    score_ = []
    for scale in scales:
        score_.append(fss(R_f[i, :, :], R_o[i + 1, :, :], thr, scale))
    score.append(score_)

plt.figure()
x = np.arange(1, n_leadtimes + 1) * timestep
plt.plot(x, score)
plt.legend(scales, title="Scale [km]")
plt.xlabel("Lead time [min]")
plt.ylabel("FSS ( > 1.0 mm/h ) ")
plt.title("Fractions skill score")
plt.show()

# sphinx_gallery_thumbnail_number = 3
