#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions used for iQCconstants on startup.

@author: Ellen Wasbo
"""
from PyQt6.QtCore import QFile, QIODevice, QTextStream
import yaml

# Shield_NM_CT block start
import Shield_NM_CT.config.config_classes as cfc
import Shield_NM_CT.resources
# Shield_NM_CT block end


def read_yaml(fname=''):
    """Read yaml file from config_default (resources.py).

    Returns
    -------
    settings: list of objects
    """
    settings = []
    f_text = ''
    file = QFile(f':/config_defaults/{fname}.yaml')
    file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
    f_text = QTextStream(file).readAll()

    if f_text != '':
        docs = yaml.safe_load_all(f_text)
        for doc in docs:
            if doc is not None:
                if fname == 'isotopes':
                    settings.append(cfc.Isotope(**doc))
                elif fname == 'materials':
                    settings.append(cfc.Material(**doc))
                elif fname == 'ct_models':
                    settings.append(cfc.CT_model(**doc))
                elif fname == 'shield_data':
                    settings.append(cfc.ShieldData(**doc))
                elif fname == 'colormaps':
                    settings.append(cfc.ColorMap(**doc))

    return settings
