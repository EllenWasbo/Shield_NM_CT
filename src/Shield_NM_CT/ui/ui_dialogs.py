#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for different dialogs of imageQC.

@author: Ellen Wasbo
"""

import os

from PyQt6.QtGui import QIcon, QPixmap
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox,
    QGroupBox, QButtonGroup, QDialogButtonBox, QSpinBox,
    QLabel, QRadioButton, QCheckBox, QFileDialog
    )

# Shield_NM_CT block block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    APPDATA, TEMPDIR, ENV_USER_PREFS_PATH, ENV_CONFIG_FOLDER, ENV_ICON_PATH
    )
from Shield_NM_CT.config.config_func import init_user_prefs
from Shield_NM_CT.ui import messageboxes
import Shield_NM_CT.resources
# Shield_NM_CT block end


class ShieldDialog(QDialog):
    """Dialog for reuse with Shield_NM_CT icon and flags."""

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}logo.png'))
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.CustomizeWindowHint)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

    def start_wait_cursor(self):
        """Block mouse events by wait cursor."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.instance().processEvents()

    def stop_wait_cursor(self):
        """Return to normal mouse cursor after wait cursor."""
        QApplication.restoreOverrideCursor()


class AboutDialog(ShieldDialog):
    """Info about Shield NM CT."""

    def __init__(self, version=''):
        super().__init__()
        self.setModal(True)
        self.setWindowTitle("Shield NM CT")

        layout = QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        logo = QLabel()
        im = QPixmap(f'{os.environ[ENV_ICON_PATH]}logo_128.png')
        logo.setPixmap(im)
        hlo_top = QHBoxLayout()
        layout.addLayout(hlo_top)
        hlo_top.addStretch()
        hlo_top.addWidget(logo)
        hlo_top.addStretch()

        header_text = """<html><head/><body>
            <p><span style=\" font-size:14pt;\">Shield NM CT</span></p>
            </body></html>"""
        hlo_header = QHBoxLayout()
        header = QLabel()
        header.setText(header_text)
        hlo_header.addStretch()
        hlo_header.addWidget(header)
        hlo_header.addStretch()
        layout.addLayout(hlo_header)

        info_text = f"""<html><head/><body>
            <p>Shield NM CT - a tool for calculating and exploring effects
            for different shielding setups and materials.<br><br>
            Author: Ellen Wasboe, Stavanger University Hospital<br>
            Current version: {version}
            </p>
            </body></html>"""
        label = QLabel()
        label.setText(info_text)
        layout.addWidget(label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok,
            QtCore.Qt.Orientation.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(20)
        layout.addWidget(buttons)

        self.setLayout(layout)


class StartUpDialog(ShieldDialog):
    """Startup dialog if config file not found."""

    def __init__(self):
        super().__init__()
        self.setModal(True)
        self.setWindowTitle("Welcome to Shield_NM_CT")

        layout = QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        logo = QLabel()
        im = QPixmap(':/icons/logo_128.png')
        logo.setPixmap(im)
        hlo_top = QHBoxLayout()
        layout.addLayout(hlo_top)
        hlo_top.addStretch()
        hlo_top.addWidget(logo)
        hlo_top.addStretch()

        header_text = """<html><head/><body>
            <p><span style=\" font-size:14pt;\">Welcome to Shield_NM_CT!</span></p>
            </body></html>"""
        hlo_header = QHBoxLayout()
        header = QLabel()
        header.setText(header_text)
        hlo_header.addStretch()
        hlo_header.addWidget(header)
        hlo_header.addStretch()
        layout.addLayout(hlo_header)

        info_text = f"""<html><head/><body>
            <p>Configurable settings can be saved at any desired location and can be
            shared between multiple users. <br>
            To let Shield_NM_CT remember the path to the config folder, the path
            have to be saved locally at one of thes options:</p>
            <ul>
            <li>Path saved on AppData <i>({APPDATA})</i></li>
            <li>Path saved on Temp <i>({TEMPDIR})</i></li>
            <li>Don't save the path, locate the path each time on startup</li>
            </ul>
            </body></html>"""
        label = QLabel()
        label.setText(info_text)
        layout.addWidget(label)
        layout.addSpacing(20)

        gb = QGroupBox('Options')
        lo = QVBoxLayout()
        gb.setLayout(lo)
        self.bGroup = QButtonGroup()

        btnTexts = [
            "Initiate user_preferences.yaml in AppData",
            "Initiate user_preferences.yaml in Temp",
            "Locate configuration folder for this session only",
            "No, I'll just have a look. Continue without config options."
            ]
        for i, t in enumerate(btnTexts):
            rb = QRadioButton(t)
            self.bGroup.addButton(rb, i)
            lo.addWidget(rb)

        self.bGroup.button(0).setChecked(True)

        layout.addWidget(gb)
        layout.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok,
            QtCore.Qt.Orientation.Horizontal, self)
        buttons.accepted.connect(self.press_ok)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(20)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_config_folder(self, ask_first=True):
        """Locate or initate config folder.

        Returns
        -------
        config_folder : str
            '' if failed or cancelled.
        """
        config_folder = ''
        locate = True
        if ask_first:
            quest = ('Locate or initiate shared configuration folder now?'
                     '(May also be done later from the Settings manager)')
            res = messageboxes.QuestionBox(
                self, title='Shared config folder', msg=quest,
                yes_text='Yes, now', no_text='No, later')
            if res.exec() == 0:
                locate = False
        if locate:
            dlg = QFileDialog()
            dlg.setFileMode(QFileDialog.FileMode.Directory)
            if dlg.exec():
                fname = dlg.selectedFiles()
                config_folder = os.path.normpath(fname[0])

        return config_folder

    def press_ok(self):
        """Verify selections when OK is pressed."""
        selection = self.bGroup.checkedId()
        if selection == 3:
            self.reject()
        else:
            if selection in [0, 1]:
                config_folder = self.get_config_folder()
            else:
                config_folder = self.get_config_folder(ask_first=False)

            status = True
            if selection == 0:  # APPDATA
                status, user_prefs_path, errmsg = init_user_prefs(
                    path=APPDATA, config_folder=config_folder)
                if status:  # TEMPDIR
                    os.environ[ENV_USER_PREFS_PATH] = user_prefs_path
            elif selection == 1:
                status, user_prefs_path, errmsg = init_user_prefs(
                    path=TEMPDIR, config_folder=config_folder)
                if status:
                    os.environ[ENV_USER_PREFS_PATH] = user_prefs_path

            if status is False:
                QMessageBox.warning(self, 'Issue with permission', errmsg)

            os.environ[ENV_CONFIG_FOLDER] = config_folder

            self.accept()

    def get_selection(self):
        """To get final selection from main window."""
        return self.bGroup.checkedId()


class HeightsDialog(ShieldDialog):
    """Figure to display heights definitions."""

    def __init__(self):
        super().__init__()
        self.setModal(True)
        self.setWindowTitle("Shield NM CT information")

        layout = QVBoxLayout()
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(20)
        logo = QLabel()
        im = QPixmap(f'{os.environ[ENV_ICON_PATH]}heights.png')
        logo.setPixmap(im)
        hlo_top = QHBoxLayout()
        layout.addLayout(hlo_top)
        hlo_top.addStretch()
        hlo_top.addWidget(logo)
        hlo_top.addStretch()

        info_text = """<html><head/><body>
            <p>The heights defined.</p>
            </body></html>"""
        label = QLabel()
        label.setText(info_text)
        layout.addWidget(label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok,
            QtCore.Qt.Orientation.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addSpacing(20)
        layout.addWidget(buttons)

        self.setLayout(layout)


class EditAnnotationsDialog(ShieldDialog):
    """Dialog to edit annotation settings."""

    def __init__(self, annotations=True, annotations_linethick=0,
                 annotations_fontsize=0, picker=0, snap_radius=0, canvas=None):
        super().__init__()
        self.canvas = canvas

        self.setWindowTitle('Set annotations')
        self.setMinimumHeight(400)
        self.setMinimumWidth(300)

        vlo = QVBoxLayout()
        self.setLayout(vlo)
        fLO = QFormLayout()
        vlo.addLayout(fLO)

        self.chk_annotations = QCheckBox('Show annotations')
        self.chk_annotations.setChecked(annotations)
        fLO.addRow(self.chk_annotations)

        self.spin_line = QSpinBox()
        self.spin_line.setRange(1, 100)
        self.spin_line.setValue(annotations_linethick)
        if self.canvas:
            self.spin_line.valueChanged.connect(
                lambda: self.canvas.update_annotations_linethick(self.spin_line.value())
                )
        fLO.addRow(QLabel('Line thickness'), self.spin_line)

        self.spin_font = QSpinBox()
        self.spin_font.setRange(5, 100)
        self.spin_font.setValue(annotations_fontsize)
        if self.canvas:
            self.spin_font.valueChanged.connect(
                lambda: self.canvas.update_annotations_fontsize(self.spin_font.value())
                )
        fLO.addRow(QLabel('Font size'), self.spin_font)

        self.spin_picker = QSpinBox()
        self.spin_picker.setRange(0, 100)
        self.spin_picker.setValue(picker)
        fLO.addRow(QLabel('Picker radius'), self.spin_picker)

        self.spin_snap_radius = QSpinBox()
        self.spin_snap_radius.setRange(0, 100)
        self.spin_snap_radius.setValue(snap_radius)
        fLO.addRow(QLabel('Snap radius'), self.spin_snap_radius)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vlo.addWidget(self.buttonBox)

    def get_data(self):
        """Get settings.

        Returns
        -------
        bool
            annotations
        int
            linethick
        int
            fontsize
        int
            picker
        int
            snap_radius
        """
        return (
            self.chk_annotations.isChecked(),
            self.spin_line.value(),
            self.spin_font.value(),
            self.spin_picker.value(),
            self.spin_snap_radius.value()
            )
