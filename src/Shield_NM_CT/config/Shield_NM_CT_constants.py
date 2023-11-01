#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Constants accessible for shield_nm_ct.

@author: Ellen Wasbø
"""

import os

# Shield_NM_CT block block start
import Shield_NM_CT.config.config_classes as cfc
from Shield_NM_CT.config import shield_constants_functions
# Shield_NM_CT block block end


USERNAME = os.getlogin()

# version string used to caluclate increasing number for comparison
# convention: A.B.C-bD where A,B,C,D is numbers < 100 and always increasing
VERSION = '2.0.0_b1'
APPDATA = os.path.join(os.environ['APPDATA'], 'Shield_NM_CT')
TEMPDIR = r'C:\Windows\Temp\Shield_NM_CT'  # alternative to APPDATA if needed

# os.environ variable keys to save global settings in session
ENV_USER_PREFS_PATH = 'SHIELD_NM_CT_USER_PREFS_PATH'
ENV_CONFIG_FOLDER = 'SHIELD_NM_CT_CONFIG_FOLDER'
ENV_ICON_PATH = 'SHIELD_NM_CT_ICON_PATH'

USER_PREFS_FNAME = 'user_preferences.yaml'

CONFIG_FNAMES = {
    'isotopes': {
        'saved_as': 'object_list',
        'default': shield_constants_functions.read_yaml(fname='isotopes')
        },
    'ct_doserates': {
        'saved_as': 'object_list',
        'default': shield_constants_functions.read_yaml(fname='ct_doserates')
        },
    'shield_data': {
        'saved_as': 'object_list',
        'default': shield_constants_functions.read_yaml(fname='shield_data')
        },
    'materials': {
        'saved_as': 'object_list',
        'default': shield_constants_functions.read_yaml(fname='materials')
        },
    'general_values': {
        'saved_as': 'object',
        'default': cfc.GeneralValues(),
        },
    'active_users': {
        'saved_as': 'dict',
        'default': {},
        },
    'last_modified': {
        'saved_as': 'object',
        'default': cfc.LastModified(),
        }
    }
