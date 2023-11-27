# -*- coding: utf-8 -*-
"""
Tests on GUI.

@author: ewas
"""
import os
from pathlib import Path

from pandas import read_clipboard

from Shield_NM_CT.ui.ui_main import MainWindow
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    ENV_USER_PREFS_PATH, ENV_CONFIG_FOLDER, ENV_ICON_PATH)
from Shield_NM_CT.config.config_func import get_icon_path


os.environ[ENV_USER_PREFS_PATH] = ''
os.environ[ENV_CONFIG_FOLDER] = ''
os.environ[ENV_ICON_PATH] = get_icon_path(False)
path_tests = Path(__file__).parent

# to mouseclick:
#qtbot.mouseClick(main.tab_ct.btnRunHom, QtCore.Qt.LeftButton)


def test_open_project(qtbot):
    project_path = path_tests / 'simple_project'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    doserate_values = [float(row[-1]) for row in table_list]
    expected_doserate_values = [11.26, 14.3, 14.3, 1.29, 2.81, 3.57, 3.57, 0.32]
    assert expected_doserate_values == doserate_values

    dose_values = [float(row[-2]) for row in table_list]
    expected_dose_values = [11.26, 14.3, 14.3, 1.29, 2.81, 3.57, 3.57, 0.32]
    assert expected_doserate_values == doserate_values

    main.NMsources_tab.table_list[3] = 'Tc-99m'
    main.NMsources_tab.table_list[4] = 10000

    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    doserate_values = [float(row[-1]) for row in table_list]
    expected_doserate_values = [2.45, 195, 195, 5.02, 2.45/4, 195/4, 195/5, 5.02/4]


def test_start_settings(qtbot):
    main = MainWindow()
    qtbot.addWidget(main)
    main.run_settings()
    assert 1 == 1
