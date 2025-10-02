#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Shield NMCT - startup and GUI of MainWindow.

@author: EllenWasbo
url: https://github.com/EllenWasbo/shieldNMCT
"""

import sys
import os

from PyQt6.QtGui import QPixmap, QFont, QFontMetrics, QPalette, QColor
from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt

# Shield_NM_CT block start
from Shield_NM_CT.ui.ui_main import MainWindow
from Shield_NM_CT.ui.ui_dialogs import StartUpDialog
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    ENV_ICON_PATH, ENV_USER_PREFS_PATH, ENV_CONFIG_FOLDER
    )
import Shield_NM_CT.config.config_func as cff
# Shield_NM_CT block stop


def prepare_debug():
    """Set a tracepoint in PDB that works with Qt."""
    # https://stackoverflow.com/questions/1736015/debugging-a-pyqt4-app
    from PyQt6.QtCore import pyqtRemoveInputHook
    import pdb
    pyqtRemoveInputHook()
    # set up the debugger
    debugger = pdb.Pdb()
    debugger.reset()
    # custom next to get outside of function scope
    debugger.do_next(None)  # run the next command
    users_frame = sys._getframe().f_back  # frame where user invoked `pyqt_set_trace()`
    debugger.interaction(users_frame, None)
    # to matplotlib in this mode:
    # import matplotlib.pyplot as plt
    # plt.imshow(your_image) /or plt.plot(xs, ys)
    # plt.pause(1) not plt.show() which will show empty figure and errmsg


if __name__ == '__main__':
    developer_mode = False
    if developer_mode:
        prepare_debug()  # type c to continue, developer_mode=False in Shield_NM_CT.py to deactivate debugging

    user_prefs_status, user_prefs_path, user_prefs = cff.load_user_prefs()
    # verify that config_folder exists
    warnings = []
    if user_prefs.config_folder != '':
        if not os.path.exists(user_prefs.config_folder):
            msg = f'Config folder do not exist.({user_prefs.config_folder})'
            print(msg, flush=True)
            user_prefs.config_folder = ''
            warnings.append(msg)

    os.environ[ENV_USER_PREFS_PATH] = user_prefs_path
    os.environ[ENV_CONFIG_FOLDER] = user_prefs.config_folder

    try:
        from ctypes import windll  # Only exists on Windows.
        myappid = 'sus.shield_nm_ct.app.2'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except ImportError:
        pass

    app = QApplication(sys.argv)
    screen = app.primaryScreen()
    sz = screen.geometry()

    splash_img = QPixmap(':/icons/logo_splash.png')
    splash = QSplashScreen(
        splash_img, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()

    app.setStyle('Fusion')
    app.setStyleSheet(
        """
        QSplitter::handle:horizontal {
            width: 4px;
            background-color: #6e94c0;
            }
        QSplitter::handle:vertical {
            height: 4px;
            background-color: #6e94c0;
            }
        QWidget {
            padding: 2px;
            }
        QGroupBox {
            border-radius: 5px;
            border: 1px solid grey;
            margin-top: 10px;
            }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding-left: 10px;
            padding-top: -7px;
            font-style: italic;
            }
        QPushButton {
            border-style: solid;
            border-width: 2px;
            border-color: #888888;
            border-radius: 10px;
            padding: 6px;
            }
        QPushButton::hover {
            background-color: #aaaaaa
            }
        """)
    myFont = QFont()
    myFont.setPointSize(user_prefs.fontsize)
    app.setFont(myFont)
    font_metric = QFontMetrics(myFont)
    char_width = font_metric.averageCharWidth()

    bg_color = app.palette().window().color().value()
    font_color = app.palette().windowText().color().value()
    if bg_color < font_color:
        dark_mode = True
    else:
        dark_mode = False
    os.environ[ENV_ICON_PATH] = cff.get_icon_path(dark_mode)

    if dark_mode:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(
            QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(
            QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(palette)

    if os.environ[ENV_USER_PREFS_PATH] == '':
        dlg = StartUpDialog()
        dlg.show()
        splash.finish(dlg)
        dlg.exec()
    w = MainWindow(scX=sz.width(), scY=sz.height(), char_width=char_width,
                   developer_mode=developer_mode, warnings=warnings)
    w.show()
    splash.finish(w)
    app.exec()
