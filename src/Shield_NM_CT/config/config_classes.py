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
    default_path: str = ''
    dark_mode: bool = False
    fontsize: int = 9
    annotations_linethick: int = 1
    annotations_fontsize: int = 10


@dataclass
class LastModified:
    """Class holding [username, epoch-time] for last change of config files."""

    isotopes: list = field(default_factory=list)
    materials: list = field(default_factory=list)
    ct_data: list = field(default_factory=list)
    general_values: list = field(default_factory=list)


@dataclass
class GeneralValues:
    """Class holding values for calculations."""

    working_days: int = 230
    c0: float = 1.7
    c1: float = 1.0
    c2: float = 0.5
    h0: float = 4.0
    h1: float = 4.0
    shield_mm_above: float = 200.0
    shield_material_above: str = 'Concrete'
    shield_mm_below: float = 200.0
    shield_material_below: str = 'Concrete'


@dataclass
class Isotope:
    """Isotope data and shielding."""

    label: str = ''  # visible name e.g. F-18
    half_life: float = 0.0  # half life in unit as specified by half_life_unit
    half_life_unit: str = 'hours'  # minutes, hours or days
    gamma_ray_constant: float = 0.0  # uSv/h per MBq @ 1m unshielded pointsource
    patient_constant: float = 0.0  # uSv/h per MBq @ 1m shielded by patient body


@dataclass
class CT_doserates:
    """Dataclass for coronal and sagittal CT doserate tables."""

    label: str = ''
    tables: list = field(default_factory=list)
    # list of numpy arrays for the coronal[0] and sagittal[1] doserate tables


@dataclass
class Material:
    """Material name and ID to save and read as yaml."""

    label: str = ''
    description: str = ''


@dataclass
class ShieldData:
    """TVLs and/or alpha, beta, gamma parameters for broad beam data."""

    kVp: float = 0.0  # if CT
    isotope_label: str = ''  # if NM source
    material_label: str = ''
    alpha: float = 0.0
    beta: float = 0.0
    gamma: float = 0.0
    TVL1: float = 0.0
    TVL2: float = 0.0
    TVLe: float = 0.0
