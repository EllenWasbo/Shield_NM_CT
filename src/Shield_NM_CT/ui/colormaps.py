# -*- coding: utf-8 -*-
"""
Created on Mon May  2 13:52:24 2022

@author: ewas
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def register_cmaps():
    """Register colormaps for use in program."""
    # get colormap
    ncolors = 256

    color_array = plt.get_cmap('rainbow')(range(ncolors))
    color_array[:, -1] = np.linspace(0.,1., ncolors)
    map_object = LinearSegmentedColormap.from_list(
        name='rainbow_alpha', colors=color_array)
    plt.register_cmap(cmap=map_object)
