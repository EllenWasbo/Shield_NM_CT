# -*- coding: utf-8 -*-
"""
Created on Mon May  2 13:52:24 2022

@author: ewas
"""
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

def register_cmaps(name, colors):
    """Register colormaps for use in program."""
    #colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]  # RGB
    map_object = LinearSegmentedColormap.from_list(
        name, colors, n_bin=len(colors))
    plt.register_cmap(cmap=map_object)
