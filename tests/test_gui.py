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
    # F-18
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    doserate_values = [float(row[-1]) for row in table_list[1:-1]]
    expected_doserate_values = [7.71, 9.79, 9.79, 0.88,
                                1.93, 2.45, 2.45, 0.22]
    assert expected_doserate_values == doserate_values
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    expected_dose_values = [6.416, 8.1492, 0.8149, 0.7364,
                            1.604, 2.0373, 0.2037, 0.1841]
    assert expected_dose_values == dose_values

    # dose at floor below with same geometry and material as bottom 2m
    main.gui.current_floor = 0
    main.sum_dose_days()
    table_list = main.points_tab.get_table_as_list()
    doserate_center = float(table_list[-1][-1])
    assert doserate_center == expected_doserate_values[-1]


def test_start_settings(qtbot):
    main = MainWindow()
    qtbot.addWidget(main)
    main.run_settings()
    assert 1 == 1
