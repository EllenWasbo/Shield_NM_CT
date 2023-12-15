#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for different dialogs of imageQC.

@author: Ellen Wasbo
"""

import os
import numpy as np

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, qApp, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QMessageBox,
    QGroupBox, QButtonGroup, QDialogButtonBox, QSpinBox, QDoubleSpinBox,
    QPushButton, QTableWidget, QLineEdit,
    QLabel, QRadioButton, QCheckBox, QFileDialog
    )

# Shield_NM_CT block block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    APPDATA, TEMPDIR, ENV_USER_PREFS_PATH, ENV_CONFIG_FOLDER, ENV_ICON_PATH
    )
from Shield_NM_CT.config.config_func import init_user_prefs
from Shield_NM_CT.config.config_classes import CT_doserates
from Shield_NM_CT.ui import messageboxes
import Shield_NM_CT.ui.reusable_widgets as uir
import Shield_NM_CT.resources
# Shield_NM_CT block end


class ShieldDialog(QDialog):
    """Dialog for reuse with Shield_NM_CT icon and flags."""

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}logo.png'))
        self.setWindowFlags(self.windowFlags() | Qt.CustomizeWindowHint)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

    def start_wait_cursor(self):
        """Block mouse events by wait cursor."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        qApp.processEvents()

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
        layout.setAlignment(QtCore.Qt.AlignCenter)
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
            QDialogButtonBox.Ok,
            QtCore.Qt.Horizontal, self)
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
        layout.setAlignment(QtCore.Qt.AlignCenter)
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
            QDialogButtonBox.Ok,
            QtCore.Qt.Horizontal, self)
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
            dlg.setFileMode(QFileDialog.Directory)
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
        layout.setAlignment(QtCore.Qt.AlignCenter)
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
            QDialogButtonBox.Ok,
            QtCore.Qt.Horizontal, self)
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
        fLO.addRow(QLabel('Sap radius'), self.spin_snap_radius)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
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


class EditCTdosemapDialog(ShieldDialog):
    """Dialog to edit annotation settings."""

    def __init__(self, initial_template=CT_doserates()):
        super().__init__()
        self.template = None

        self.setWindowTitle('Generate or edit CT dosemap')
        self.setMinimumHeight(400)
        self.setMinimumWidth(700)

        vlo = QVBoxLayout()
        self.setLayout(vlo)

        self.factor_rear = QDoubleSpinBox(
            value=initial_template.scatter_factor_rear, decimals=3)
        self.factor_gantry = QDoubleSpinBox(
            value=initial_template.scatter_factor_gantry, decimals=3)
        self.factor_front = QDoubleSpinBox(
            value=initial_template.scatter_factor_front, decimals=3)
        self.stop_rear = QSpinBox(
            value=initial_template.rear_stop_angle, minimum=0, maximum=80)
        self.stop_front = QDoubleSpinBox(
            value=initial_template.front_stop_angle, minimum=-80, maximum=0, decimals=0)
        self.unit_per = QLineEdit()
        self.unit_per.setText(initial_template.unit_per)

        vlo.addWidget(uir.LabelHeader(
            'Generate dosemap from scatter factors at 1 m', 4))
        vlo.addWidget(QLabel('Scatter factors at 1m distance from isocenter:'))
        flo = QFormLayout()
        vlo.addLayout(flo)
        flo.addRow(QLabel('Rear of gantry'), self.factor_rear)
        flo.addRow(QLabel('Side of gantry'), self.factor_gantry)
        flo.addRow(QLabel('Front of gantry'), self.factor_front)
        flo.addRow(QLabel('Gantry angle rear (\u00b0)'), self.stop_rear)
        flo.addRow(QLabel('Gantry angle front (\u00b0)'), self.stop_front)
        flo.addRow(QLabel('\u03bc' + 'Gy/unit where unit is'), self.unit_per)
        vlo.addWidget(uir.LabelItalic(
            'Based on <a href="https://pubmed.ncbi.nlm.nih.gov/22327169/">'
            'Wallace et al 2012</a>'))
        btn_alternative1 = QPushButton('Use scatter factors above')
        btn_alternative1.clicked.connect(self.use_alternative1)
        vlo.addWidget(btn_alternative1)

        column_headers = [str(val) for val in np.arange(-2, 4, 0.5)]
        self.cor_table = QTableWidget(4, 12)
        self.cor_table.setHorizontalHeaderLabels(column_headers)
        row_labels = [str(val) for val in np.arange(1.5, -0.5, -0.5)]
        self.cor_table.setVerticalHeaderLabels(row_labels)
        vlo.addWidget(uir.LabelHeader('Values coronal view', 3))
        vlo.addWidget(self.cor_table)
        self.sag_table = QTableWidget(7, 12)
        self.sag_table.setHorizontalHeaderLabels(column_headers)
        row_labels = [str(val) for val in np.arange(1.5, -1.5, -0.5)]
        self.sag_table.setVerticalHeaderLabels(row_labels)
        vlo.addWidget(uir.LabelHeader('Values sagital view', 3))
        vlo.addWidget(self.sag_table)
        btn_alternative2 = QPushButton('Use tabular values above')
        btn_alternative2.clicked.connect(self.use_alternative2)
        vlo.addWidget(btn_alternative2)

        self.fill_tables(initial_template.tables)

        buttons = QDialogButtonBox.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.rejected.connect(self.reject)
        vlo.addWidget(self.buttonBox)

    def fill_tables(self, values):
        """Fill tables with current values if any."""
        if values:
            pass  #TODO

    def use_alternative1(self):
        """Use scatter factors as Wallace 2012."""
        self.template = CT_doserates(
            unit_per=self.unit_per.text(),
            scatter_factor_rear=self.factor_rear.value(),
            scatter_factor_gantry=self.factor_gantry.value(),
            scatter_factor_front=self.factor_front.value(),
            rear_stop_angle=self.stop_rear.value(),
            front_stop_angle=self.stop_front.value(),
            )
        self.accept()

    def use_alternative2(self):
        """Tabulated CT doserate values."""
        cor_values = []
        sag_values = []
        #TODO read tables
        self.template = CT_doserates(
            unit_per=self.unit_per.text(),
            tables=[cor_values, sag_values]
            )
        self.accept()
