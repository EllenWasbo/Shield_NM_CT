#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings part automation.

@author: Ellen Wasbo
"""
import os
import copy
from time import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QBrush, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QToolBar, QLabel, QLineEdit, QPushButton, QAction, QSpinBox, QCheckBox,
    QListWidget, QComboBox, QDoubleSpinBox,
    QMessageBox, QDialogButtonBox, QInputDialog, QFileDialog
    )

# Shield_NM_CT block start
from Shield_NM_CT.config import config_classes as cfc
from Shield_NM_CT.ui.settings_reusables import StackWidget
from Shield_NM_CT.ui import reusable_widgets as uir
# Shield_NM_CT block end


class IsotopeWidget(StackWidget):
    """Isotope settings."""

    def __init__(self, dlg_settings):
        header = 'Isotopes'
        subtxt = ''
        super().__init__(dlg_settings, header, subtxt,
                         temp_list=True, temp_alias='isotope')
        self.fname = 'isotopes'
        self.empty_template = cfc.Isotope()

        self.half_life = QDoubleSpinBox(minimum=0, maximum=100000., decimals=2)
        self.half_life.valueChanged.connect(lambda: self.flag_edit(True))
        self.half_life_unit = QComboBox()
        self.half_life_unit.addItems(['minutes', 'hours', 'days'])
        self.half_life_unit.currentIndexChanged.connect(lambda: self.flag_edit(True))
        self.gamma_ray_constant = QDoubleSpinBox(decimals=5)
        self.gamma_ray_constant.valueChanged.connect(lambda: self.flag_edit(True))
        self.patient_constant = QDoubleSpinBox(decimals=5)
        self.patient_constant.valueChanged.connect(lambda: self.flag_edit(True))

        self.wid_temp = QWidget(self)
        if self.import_review_mode:
            self.wid_temp.setEnabled(False)

        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        hlo_half_life = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_half_life)
        hlo_half_life.addWidget(QLabel('Half life:'))
        hlo_half_life.addWidget(self.half_life)
        hlo_half_life.addWidget(self.half_life_unit)
        hlo_half_life.addStretch()

        hlo_constant1 = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_constant1)
        hlo_constant1.addWidget(QLabel(
            'Gamma ray constant (point source) [uSv/h per MBq @ 1m]:'))
        hlo_constant1.addWidget(self.gamma_ray_constant)
        hlo_constant1.addStretch()

        hlo_constant2 = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_constant2)
        hlo_constant2.addWidget(QLabel(
            'Gamma ray constant from patient [uSv/h per MBq @ 1m]:'))
        hlo_constant2.addWidget(self.patient_constant)
        hlo_constant2.addStretch()

        self.vlo_temp.addStretch()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.half_life.setValue(self.current_template.half_life)
        self.half_life_unit.setCurrentText(self.current_template.half_life_unit)
        self.gamma_ray_constant.setValue(self.current_template.gamma_ray_constant)
        self.patient_constant.setValue(self.current_template.patient_constant)
        self.flag_edit(False)

    def get_current_template(self):
        """Get self.current_template where not dynamically set."""
        self.current_template.half_life = self.half_life.value()
        self.current_template.half_life_unit = self.half_life_unit.currentText()
        self.current_template.gamma_ray_constant = self.gamma_ray_constant.value()
        self.current_template.patient_constant = self.patient_constant.value()


class MaterialWidget(StackWidget):
    """Material list."""

    def __init__(self, dlg_settings):
        header = 'Materials'
        subtxt = ''
        super().__init__(dlg_settings, header, subtxt,
                         temp_list=True, temp_alias='material')
        self.fname = 'materials'
        self.empty_template = cfc.Material()

        self.desciption = QLineEdit()
        self.description.editingFinished.connect(lambda: self.flag_edit(True))

        self.wid_temp = QWidget(self)
        if self.import_review_mode:
            self.wid_temp.setEnabled(False)

        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        hlo = QHBoxLayout()
        self.vlo_temp.addLayout(hlo)
        hlo.addWidget(QLabel(
            'Material description (optional):'))
        hlo.addWidget(self.description)
        hlo.addStretch()

        self.vlo_temp.addStretch()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.description.setText(self.current_template.description)
        self.flag_edit(False)

    def get_current_template(self):
        """Get self.current_template where not dynamically set."""
        self.current_template.description = self.description.text()
