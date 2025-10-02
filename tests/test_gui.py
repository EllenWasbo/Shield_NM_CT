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


def test_simple_project(qtbot):
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


def test_simple_project_90(qtbot):
    project_path = path_tests / 'simple_project_90'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)
    # F-18
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    expected_dose_values = [0.8149, 6.416, 0.7364, 8.1492,
                            0.2037, 1.604, 0.1841, 2.0373]
    assert expected_dose_values == dose_values


def test_simple_project_oblique_(qtbot):
    project_path = path_tests / 'simple_project_oblique'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)
    # F-18
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    expected_dose_values = [8.1492, 8.1492, 0.8149, 8.1492,
                            1.604, 1.604, 0.0184, 0.1841]
    assert expected_dose_values == dose_values


def test_simple_project_oblique_90(qtbot):
    project_path = path_tests / 'simple_project_oblique_90'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)
    # F-18
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    expected_dose_values = [8.1492, 8.1492, 0.8149, 8.1492, 
                            1.604, 0.1841, 0.1604, 0.1841]
    assert expected_dose_values == dose_values


def test_siemens_CT(qtbot):
    project_path = path_tests / 'SiemensCT_verify'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)

    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    expected_dose_values = [2.698, 3.6, 4.1997, 4.1986,
                            2.521, 5.5385, 7.2, 7.4641,
                            0.7052, 5.6723, 14.4, 16.7942,
                            0.328, 0.656, 22.6894, 0.0,
                            0.3644, 0.82, 0.0, 0.0,
                            0.9464, 5.8844, 34.51, 0.0,
                            3.523, 8.6275, 14.7264, 14.625,
                            3.8344, 6.0, 6.5638, 6.5,
                            3.12, 3.6816, 3.6825, 3.6562,
                            2.2941, 2.3642, 2.352, 2.34,
                            1.6363, 1.641, 1.6312, 1.625,
                            1.2057, 1.204, 1.1973]
    assert expected_dose_values == dose_values

    main.CTsources_tab.table_list[0][3] = 90  # rotate 90 degrees
    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:-1]]
    assert dose_values[16] == 6.5
    assert dose_values[7] == 0.3644


def test_siemens_CT_floor(qtbot):
    project_path = path_tests / 'SiemensCT_floor_above_verify'
    main = MainWindow()
    qtbot.addWidget(main)
    main.open_project(path=project_path)

    main.calculate_dose()
    table_list = main.points_tab.get_table_as_list()
    dose_values = [float(row[-2]) for row in table_list[1:]]
    expected_dose_values = [4.1986, 7.4641, 16.7942, 0.0, 0.0, 0.0, 14.625,
                            6.5, 3.6562, 2.34, 1.625, 1.1939]
    assert expected_dose_values == dose_values

    # all c0,c1,c2 = 0 and no shielding
    main.gui.current_floor = 0  # above
    main.general_values.h1 = 1.
    main.sum_dose_days()
    table_list = main.points_tab.get_table_as_list()
    dose_center = float(table_list[5][-2])
    assert dose_center == 0.82  # same as 1m left (shaded by gantry)


def test_start_settings(qtbot):
    main = MainWindow()
    qtbot.addWidget(main)
    main.run_settings()
    assert 1 == 1
