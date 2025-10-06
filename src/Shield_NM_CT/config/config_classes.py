#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Code holding the data classes used for configurable settings.

@author: Ellen Wasbo
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class UserPreferences:
    """Class holding local settings."""

    config_folder: str = ''
    fontsize: int = 9
    annotations_linethick: int = 1
    annotations_fontsize: int = 10
    picker: int = 10
    snap_radius: int = 20


@dataclass
class LastModified:
    """Class holding [username, epoch-time] for last change of config files."""

    isotopes: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    ct_data: list = field(default_factory=list)
    general_values: list = field(default_factory=list)
    shield_data: list = field(default_factory=list)
    colormaps: list = field(default_factory=list)


@dataclass
class GeneralValues:
    """Class holding values for calculations.

    NB: Materials and kV-sources need to match config_default/shield_data.yaml.
    """

    working_days: int = 230
    convert_to_mSv: bool = True  # multiply dose(rate) by 0.001 to obtain dose in mSv
    correct_thickness: bool = False  # perform geometrical thickness correction
    c0: float = 1.7
    c1: float = 1.0
    c2: float = 0.5
    h0: float = 4.0
    h1: float = 4.0
    shield_mm_above: float = 200.0
    shield_material_above: str = 'Concrete'
    shield_mm_below: float = 200.0
    shield_material_below: str = 'Concrete'
    kV_sources: list[str] = field(default_factory=lambda: ['CT 120 kVp', 'CT 140 kVp'])
    csv_separator: str = ';'
    csv_decimal: str = ','


@dataclass
class Isotope:
    """Isotope data and shielding."""

    label: str = ''  # visible name e.g. F-18
    half_life: float = 0.0  # half life in unit as specified by half_life_unit
    half_life_unit: str = 'hours'  # minutes, hours, days or years
    gamma_ray_constant: float = 0.0  # uSv/h per MBq @ 1m unshielded pointsource
    patient_constant: float = 0.0  # uSv/h per MBq @ 1m shielded by patient body


@dataclass
class CT_model:
    """Dataclass for CT doserate estimates."""

    label: str = ''
    unit_per: str = 'mAs'  # uGy/--
    scatter_factor_rear: float = 0.0
    rear_stop_angle: int = 40
    scatter_factor_gantry: float = 0.0
    front_stop_angle: int = -20
    scatter_factor_front: float = 0.0
    smooth_angles_rear: int = 0
    smooth_angles_front: int = 0
    angle_flatten_rear: int = 90
    angle_flatten_front: int = -90
    flatten_power: float = 1.


@dataclass
class Material:
    """Material name and display settings."""

    label: str = ''
    default_thickness: float = 0.0  # mm
    real_thickness: bool = False
    color: str = '#000000'


@dataclass
class ShieldData:
    """TVLs and/or alpha, beta, gamma parameters for broad beam data."""

    kV_source: str = ''  # if CT or other xray
    isotope: str = ''  # if NM source
    material: str = ''
    alpha: float = 0.0
    beta: float = 0.0
    gamma: float = 0.0
    hvl1: float = 0.0
    hvl2: float = 0.0
    tvl1: float = 0.0
    tvl2: float = 0.0

@dataclass
class ColorMap:
    """Dose (mSv) or doserate (uSv) values and colors to generate colormaps or cmap."""

    label: str = ''
    use: str = 'cmap'  # or table
    table: list = field(default_factory=list)  # [[dose, #rrggbb],[dose2, #rrggbb],...]
    cmap: str = ''
    cmin: float = 0.0
    cmax: float = 1.0
