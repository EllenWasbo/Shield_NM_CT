#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings part automation.

@author: Ellen Wasbo
"""
import os
import re
import copy
import numpy as np
import pandas as pd
from time import time
from io import BytesIO

from PyQt6.QtCore import Qt, QItemSelectionModel, QFile, QIODevice
from PyQt6.QtGui import QIcon, QColor, QAction
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QAbstractItemView,
    QStackedWidget, QGroupBox, QToolBar, QLineEdit,
    QLabel, QPushButton, QButtonGroup, QRadioButton, QCheckBox,
    QComboBox, QDoubleSpinBox, QInputDialog, QColorDialog, QTableWidget,
    QDialogButtonBox, QMessageBox
    )
import matplotlib as mpl
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# Shield_NM_CT block start
from Shield_NM_CT.config import config_classes as cfc
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui.settings_reusables import StackWidget
from Shield_NM_CT.ui import reusable_widgets as uir
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.config.Shield_NM_CT_constants import ENV_ICON_PATH
from Shield_NM_CT.scripts.mini_methods_format import valid_template_name
from Shield_NM_CT.scripts.calculate_dose import generate_CT_doseratemap
from Shield_NM_CT.ui.ui_dialogs import ShieldDialog, DataFrameDisplay
# Shield_NM_CT block end


def read_booklet(isotope_name, parent):
    file = QFile(
        ':/config_defaults/radionuclide_information_booklet_2025_values.csv')
    file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text)
    df = pd.read_csv(file, sep=',', decimal=',')
    if isotope_name:
        df_this = df[df['Isotope'] == isotope_name]
    else:
        df_this = pd.DataFrame()
    if df_this.size == 0:
        # select from list
        dlg = DataFrameDisplay(
            parent, df,
            title='Available values',
            min_width=1100, min_height=500)
        if dlg.exec():
            rowno = dlg.get_row_number()
            if rowno > -1:
                df_this = df.iloc[rowno]

    return df_this


def import_shield_booklet(df_row, parent_stack, specific_material=''):
    """Import HVL/TVL for a given isotope in booklet table."""
    # add materials if not exist
    widget_shield_data = getattr(
        parent_stack.settings_dialog, 'widget_shield_data')
    widget_shield_data.update_from_yaml()
    materials = [x.label for x in widget_shield_data.materials]
    booklet_materials = ['Lead', 'Steel', 'Concrete']
    for material in booklet_materials:
        proceed_material = True
        if specific_material:
            if material != specific_material:
                proceed_material = False
        elif material not in materials:
            proceed_material = add_material(material, parent_stack)
            materials = [x.label for x in widget_shield_data.materials]
        if proceed_material:
            sel_idx = materials.index(material)
            bm_idx = booklet_materials.index(material)
            widget_shield_data.btns_source_type.button(0).setChecked(True)
            if not isinstance(df_row.iloc[0], str): # pandas series
                df_row = df_row.iloc[0]
            widget_shield_data.cbox_sources.setCurrentText(str(df_row.iloc[0]))
            widget_shield_data.refresh_templist(selected_label=material)
            widget_shield_data.current_template = cfc.ShieldData(
                isotope=df_row.iloc[0], material=material,
                hvl1 = float(df_row.iloc[4 + 4 * bm_idx + 0]),
                hvl2 = float(df_row.iloc[4 + 4 * bm_idx + 1]),
                tvl1 = float(df_row.iloc[4 + 4 * bm_idx + 2]),
                tvl2 = float(df_row.iloc[4 + 4 * bm_idx + 3])
                )
            widget_shield_data.update_data()
            tempno = widget_shield_data.find_index_of_template(
                selected_material_id=sel_idx)
            if tempno is not None:
                widget_shield_data.templates[tempno] = copy.deepcopy(
                    widget_shield_data.current_template)
            else:
                widget_shield_data.templates.append(
                    widget_shield_data.current_template)
            widget_shield_data.save_shield_data(update_before_save=False)
            widget_shield_data.refresh_templist(selected_label=material)


def add_material(material, parent_stack):
    """Add standard material (lead, steel, concrete)."""
    added = False
    proceed = messageboxes.proceed_question(
        parent_stack, f'Add material {material}?')
    if proceed:
        labels = ['Lead', 'Steel', 'Concrete']
        thicks = [2., 2., 200.]
        reals = [False, False, True]
        colors =  ['#0000bb', '#bb7733', '#555555']
        idx = labels.index(material)
        widget_materials = getattr(
            parent_stack.settings_dialog, 'widget_materials')
        widget_materials.update_from_yaml()
        widget_materials.add(material)
        widget_materials.current_template.default_thickness = thicks[idx]
        widget_materials.current_template.real_thickness = reals[idx]
        widget_materials.current_template.color = colors[idx]
        widget_materials.update_data()
        widget_materials.wid_temp_list.save()
        if widget_materials.edited is False:
            widget_shield_data = getattr(
                parent_stack.settings_dialog, 'widget_shield_data')
            widget_shield_data.update_from_yaml()
            added = True
    return added

class IsotopeWidget(StackWidget):
    """Isotope settings."""

    def __init__(self, settings_dialog):
        header = 'Isotopes'
        subtxt = ''
        super().__init__(settings_dialog, header, subtxt,
                         temp_list=True, temp_alias='isotope')
        self.fname = 'isotopes'
        self.empty_template = cfc.Isotope()

        self.half_life = QDoubleSpinBox(minimum=0, maximum=100000., decimals=2)
        self.half_life.valueChanged.connect(lambda: self.flag_edit(True))
        self.half_life_unit = QComboBox()
        self.half_life_unit.addItems(['minutes', 'hours', 'days', 'years'])
        self.half_life_unit.currentIndexChanged.connect(lambda: self.flag_edit(True))
        self.gamma_ray_constant = QDoubleSpinBox(decimals=5)
        self.gamma_ray_constant.valueChanged.connect(self.constants_changed)
        self.patient_constant = QDoubleSpinBox(decimals=5)
        self.patient_constant.valueChanged.connect(self.constants_changed)
        self.patient_percent = QLabel()

        self.wid_temp = QWidget(self)

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

        hlo_percent = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_percent)
        hlo_percent.addWidget(QLabel(
            'Patient constant relative to point source constant:'))
        hlo_percent.addWidget(self.patient_percent)
        hlo_percent.addStretch()
        btn_import_booklet = QPushButton(
            'Import values frow Radionuclide Information Booklet 2025')
        btn_import_booklet.clicked.connect(
            lambda: self.import_booklet('*selected*'))
        self.vlo_temp.addWidget(btn_import_booklet)

        self.vlo_temp.addStretch()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.half_life.setValue(self.current_template.half_life)
        self.half_life_unit.setCurrentText(self.current_template.half_life_unit)
        self.gamma_ray_constant.setValue(self.current_template.gamma_ray_constant)
        self.patient_constant.setValue(self.current_template.patient_constant)
        self.constants_changed()
        self.flag_edit(False)

    def get_current_template(self):
        """Get self.current_template where not dynamically set."""
        self.current_template.half_life = self.half_life.value()
        self.current_template.half_life_unit = self.half_life_unit.currentText()
        self.current_template.gamma_ray_constant = self.gamma_ray_constant.value()
        self.current_template.patient_constant = self.patient_constant.value()

    def constants_changed(self):
        """Edited constants."""
        self.flag_edit(True)
        txt = '-'
        if self.patient_constant.value() > 0 and self.gamma_ray_constant.value() > 0:
            ratio = self.patient_constant.value() / self.gamma_ray_constant.value()
            txt = f'{100*ratio:.1f} %'
        self.patient_percent.setText(txt)

    def import_booklet(self, isotope_name=''):
        if isotope_name == '*selected*':
            isotope_name = self.current_template.label
        df_row = read_booklet(isotope_name, self)
        if df_row.size > 0:
            proceed = True
            if isotope_name == '':
                text = df_row.iloc[0]
                if text in self.current_labels:
                    QMessageBox.warning(
                        self, 'Name already in use',
                        'This name is already in use.')
                    proceed = False
                else:
                    self.add(text)
            if proceed:
                self.current_template.half_life_unit = df_row.iloc[2]
                self.current_template.half_life = float(df_row.iloc[1])
                dcf = float(df_row.iloc[3])
                self.current_template.gamma_ray_constant = dcf
                self.current_template.patient_constant = dcf
                self.update_data()
                self.wid_temp_list.save()
                msg = (
                    'NB Gamma ray constant from patient is by default set '
                    'equal to gamma ray constant from point source.')
                QMessageBox.information(self, 'Information', msg,
                                        QMessageBox.StandardButton.Ok)
                proceed = messageboxes.proceed_question(
                    self,
                    'Proceed adding shield data for lead / steel / concrete ?')
                if proceed:
                    import_shield_booklet(df_row, self)
                    QMessageBox.information(
                        self, 'Information', 'Finished adding data',
                        QMessageBox.StandardButton.Ok)

    def delete(self):
        """Delete isotope and related shield data."""
        if len(self.templates) == 1:
            msg = 'Cannot delete last isotope.'
            QMessageBox.warning(self, 'Failed deleting isotope', msg)
        else:
            sel = self.current_template.label
            _, _, shield_data = cff.load_settings(fname='shield_data')
            in_shield = [temp.isotope for temp in shield_data]

            proceed = True
            if sel in in_shield:
                proceed = messageboxes.proceed_question(
                    self, 'Delete isotope and related shield data?')
            if proceed:
                idxs_used_current = [
                    i for i, val in enumerate(in_shield) if val==sel]
                if len(idxs_used_current) > 0:
                    idxs_used_current.reverse()
                    for idx in idxs_used_current:
                        shield_data.pop(idx)
                    _, path = cff.save_settings(
                        shield_data, fname='shield_data')

                    widget_shield_data = getattr(
                        self.settings_dialog, 'widget_shield_data')
                    widget_shield_data.update_from_yaml()
                    widget_shield_data.refresh_templist()

                idx = self.wid_temp_list.list_temps.currentIndex().row()
                self.templates.pop(idx)
                self.save()
                self.refresh_templist(selected_id=0)


class CTmapCanvas(FigureCanvasQTAgg):
    """Canvas for drawing the floor and overlays."""

    def __init__(self, parent):
        self.fig = Figure(figsize=(7, 7))
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(0., 0., 1., 1.)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.parent = parent
        self.overlay = None

        stream = QFile(':/icons/cor.png')
        if stream.open(QIODevice.OpenModeFlag.ReadOnly):
            data = stream.readAll()
            stream.close()
            self.background = mpl.image.imread(BytesIO(data))

        self.mpl_connect('motion_notify_event', self.on_move)

    def update_overlay(self):
        """Refresh overlay shown in image."""
        self.overlay = generate_CT_doseratemap(
            self.parent.current_template,
            map_shape=self.background.shape[0:2],
            source_xy=(500, 600), resolution=1./200, all_floors=False)
        self.scatter_factors.set(
            alpha=0.3, clim=(0., np.max(self.overlay)))
        self.scatter_factors.set_data(self.overlay)

        try:
            for contour in self.contours:
                try:
                    contour.remove()
                except ValueError:
                    pass
        except TypeError:
            self.contours.remove()
        except AttributeError:
            pass
        try:
            for txt in self.ax.texts:
                try:
                    txt.remove()
                except ValueError:
                    pass
        except AttributeError:
            pass
        levels = self.parent.current_template.scatter_factor_front * np.array([0.25, 1])
        levels = np.append(self.parent.current_template.scatter_factor_gantry, levels)
        manual_locations = [(300, 600), (500, 800), (500, 1000)]
        self.contours = self.ax.contour(self.overlay, levels, colors='black',
                                        linestyles=[':', '--', '-'])
        self.ax.clabel(self.contours, self.contours.levels, manual=manual_locations)

        self.draw_idle()

    def on_move(self, event):
        """When mouse cursor is moving in the canvas."""
        val = '-'
        postxt = 'z = -m, lat = -m, distance = -m'
        if event.inaxes and len(event.inaxes.get_images()) > 0:
            zpos = (event.ydata - 600)/200  # corrected for center, 200pix/meter
            latpos = (event.xdata - 500)/200
            postxt = (
                f'z   = {zpos:.2f}m\n'
                f'lat = {latpos:.2f}m\n'
                f'distance = {np.sqrt(zpos**2+latpos**2):.2f}m\n'
                )
            if self.overlay is not None:
                jj = round(event.ydata)
                ii = round(event.xdata)
                val = f'{self.overlay[jj, ii]:.3f}'

        self.anchored_text.txt.set_text(
            f'{postxt}{val} \u03bc' + f'Gy/{self.parent.current_template.unit_per}')
        self.draw_idle()

    def CTmap_draw(self):
        """Draw or update isodose map."""
        self.image = self.ax.imshow(self.background)
        self.scatter_factors = self.ax.imshow(
            0.*self.background, alpha=.3, cmap='hot_r')
        self.ax.autoscale(False)
        self.ax.axis('off')

        val = '-'
        postxt = 'z = -m, lat = -m, distance = -m'
        txt = f'{postxt}{val} \u03bc' + f'Gy/{self.parent.empty_template.unit_per}'

        self.anchored_text = mpl.offsetbox.AnchoredText(txt, loc='lower right')
        self.ax.add_artist(self.anchored_text)
        self.draw()


class CT_doserateWidget(StackWidget):
    """CT doserate settings."""

    def __init__(self, settings_dialog):
        header = 'CT scatter model'
        subtxt = ''
        super().__init__(settings_dialog, header, subtxt,
                         temp_list=True, temp_alias='CT scatter model')
        self.fname = 'ct_models'
        self.empty_template = cfc.CT_model()

        self.canvas = CTmapCanvas(self)

        self.scatter_factor_rear = QDoubleSpinBox(decimals=4, singleStep=0.01)
        self.scatter_factor_gantry = QDoubleSpinBox(decimals=4, singleStep=0.01)
        self.scatter_factor_front = QDoubleSpinBox(decimals=4, singleStep=0.01)
        self.rear_stop_angle = QDoubleSpinBox(
            minimum=0, maximum=80, decimals=0)
        self.front_stop_angle = QDoubleSpinBox(
            minimum=-80, maximum=0, decimals=0)
        self.unit_per = QLineEdit()
        self.smooth_angles_rear = QDoubleSpinBox(minimum=0, maximum=80, decimals=0)
        self.smooth_angles_front = QDoubleSpinBox(minimum=0, maximum=80, decimals=0)
        self.angle_flatten_rear = QDoubleSpinBox(
            minimum=0, maximum=90, decimals=0)
        self.angle_flatten_front = QDoubleSpinBox(
            minimum=-90, maximum=0, decimals=0)
        self.flatten_power = QDoubleSpinBox(decimals=1, singleStep=0.1, minimum=0.,
                                            maximum=100.)

        self.scatter_factor_rear.editingFinished.connect(self.parameter_changed)
        self.scatter_factor_gantry.editingFinished.connect(self.parameter_changed)
        self.scatter_factor_front.editingFinished.connect(self.parameter_changed)
        self.rear_stop_angle.editingFinished.connect(self.parameter_changed)
        self.front_stop_angle.editingFinished.connect(self.parameter_changed)
        self.unit_per.editingFinished.connect(lambda: self.flag_edit(True))
        self.smooth_angles_rear.editingFinished.connect(self.parameter_changed)
        self.smooth_angles_front.editingFinished.connect(self.parameter_changed)
        self.angle_flatten_rear.editingFinished.connect(self.parameter_changed)
        self.angle_flatten_front.editingFinished.connect(self.parameter_changed)
        self.flatten_power.editingFinished.connect(self.parameter_changed)

        vlo_parameters = QVBoxLayout()
        vlo_parameters.addWidget(uir.LabelHeader(
            'Scatter factors', 4))
        vlo_parameters.addWidget(uir.LabelItalic(
            'Based on <a href="https://pubmed.ncbi.nlm.nih.gov/22327169/">'
            'Wallace et al 2012</a>'))
        flo = QFormLayout()
        vlo_parameters.addLayout(flo)
        flo.addRow(QLabel('at 1m rear'), self.scatter_factor_rear)
        flo.addRow(QLabel('at 1m front'), self.scatter_factor_front)
        flo.addRow(QLabel('at 1m shielded by gantry'), self.scatter_factor_gantry)
        flo.addRow(QLabel('Unit = \u03bc' + 'Gy/'), self.unit_per)
        vlo_parameters.addWidget(QLabel('Angle range shielded by gantry'))
        hlo_angles = QHBoxLayout()
        vlo_parameters.addLayout(hlo_angles)
        hlo_angles.addWidget(QLabel('   '))
        hlo_angles.addWidget(self.front_stop_angle)
        hlo_angles.addWidget(QLabel('\u00b0 (front)'))
        hlo_angles.addWidget(self.rear_stop_angle)
        hlo_angles.addWidget(QLabel('\u00b0 (rear)'))

        vlo_parameters.addWidget(uir.LabelHeader('Fade down scatter factors', 4))
        flo_smooth = QFormLayout()
        vlo_parameters.addLayout(flo_smooth)
        flo_smooth.addRow(QLabel('Rear (\u00b0)'), self.smooth_angles_rear)
        flo_smooth.addRow(QLabel('Front (\u00b0)'), self.smooth_angles_front)

        vlo_parameters.addWidget(uir.LabelHeader('Flatten front/rear', 4))
        vlo_parameters.addWidget(uir.LabelItalic(
            'Use scatter factors above, but draw values at angles<br>'
            'indicated below closer to the center line'))
        hlo_flatten_rear = QHBoxLayout()
        vlo_parameters.addLayout(hlo_flatten_rear)
        hlo_flatten_rear.addWidget(QLabel('Flatten rear values for angles >'))
        hlo_flatten_rear.addWidget(self.angle_flatten_rear)
        hlo_flatten_rear.addWidget(QLabel('\u00b0'))

        hlo_flatten_front = QHBoxLayout()
        vlo_parameters.addLayout(hlo_flatten_front)
        hlo_flatten_front.addWidget(QLabel('Flatten front values for angles <'))
        hlo_flatten_front.addWidget(self.angle_flatten_front)
        hlo_flatten_front.addWidget(QLabel('\u00b0'))

        hlo_flatten_power = QHBoxLayout()
        vlo_parameters.addLayout(hlo_flatten_power)
        hlo_flatten_power.addWidget(QLabel('Flatten power:'))
        hlo_flatten_power.addWidget(self.flatten_power)
        hlo_flatten_power.addStretch()

        self.hlo.addLayout(vlo_parameters)
        self.hlo.addWidget(self.canvas)
        self.canvas.CTmap_draw()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def get_current_template(self):
        """Set self.current_template to current values changed by user input."""
        self.current_template.scatter_factor_rear = self.scatter_factor_rear.value()
        self.current_template.scatter_factor_gantry = self.scatter_factor_gantry.value()
        self.current_template.scatter_factor_front = self.scatter_factor_front.value()
        self.current_template.rear_stop_angle = self.rear_stop_angle.value()
        self.current_template.front_stop_angle = self.front_stop_angle.value()
        self.current_template.unit_per = self.unit_per.text()
        self.current_template.smooth_angles_rear = self.smooth_angles_rear.value()
        self.current_template.smooth_angles_front = self.smooth_angles_front.value()
        self.current_template.angle_flatten_front = self.angle_flatten_front.value()
        self.current_template.angle_flatten_rear = self.angle_flatten_rear.value()
        self.current_template.flatten_power = self.flatten_power.value()

    def parameter_changed(self):
        """Paramater to set scatter factors changed. Update map."""
        self.flag_edit(True)
        self.get_current_template()
        self.canvas.update_overlay()

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.scatter_factor_rear.setValue(self.current_template.scatter_factor_rear)
        self.scatter_factor_gantry.setValue(self.current_template.scatter_factor_gantry)
        self.scatter_factor_front.setValue(self.current_template.scatter_factor_front)
        self.rear_stop_angle.setValue(self.current_template.rear_stop_angle)
        self.front_stop_angle.setValue(self.current_template.front_stop_angle)
        self.unit_per.setText(self.current_template.unit_per)
        self.smooth_angles_rear.setValue(self.current_template.smooth_angles_rear)
        self.smooth_angles_front.setValue(self.current_template.smooth_angles_front)
        self.angle_flatten_front.setValue(self.current_template.angle_flatten_front)
        self.angle_flatten_rear.setValue(self.current_template.angle_flatten_rear)
        self.flatten_power.setValue(self.current_template.flatten_power)
        self.canvas.update_overlay()


class MaterialWidget(StackWidget):
    """Material settings."""

    def __init__(self, settings_dialog):
        header = 'Materials'
        subtxt = ''
        super().__init__(settings_dialog, header, subtxt,
                         temp_list=True, temp_alias='material')
        self.fname = 'materials'
        self.empty_template = cfc.Material()

        self.color_label = QLabel('    ')
        btn_color = QPushButton('Change color')
        btn_color.clicked.connect(self.change_color)
        self.default_thickness = QDoubleSpinBox(minimum=0, maximum=1000., decimals=1)
        self.default_thickness.valueChanged.connect(lambda: self.flag_edit(True))
        self.real_thickness = QCheckBox('Show real dimension (if more than 1 pixel)')
        self.real_thickness.clicked.connect(lambda: self.flag_edit(True))

        self.wid_temp = QWidget(self)
        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        hlo_color = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_color)
        hlo_color.addWidget(QLabel('Wall color:'))
        hlo_color.addWidget(self.color_label)
        hlo_color.addWidget(btn_color)
        hlo_color.addStretch()

        hlo_default = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_default)
        hlo_default.addWidget(QLabel(
            'Default wall thickness when material selected:'))
        hlo_default.addWidget(self.default_thickness)
        hlo_default.addWidget(QLabel('mm'))
        hlo_default.addStretch()

        self.vlo_temp.addWidget(self.real_thickness)
        self.vlo_temp.addStretch()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.color_label.setStyleSheet(
            f'QLabel{{background-color: {self.current_template.color};}}')
        self.default_thickness.setValue(self.current_template.default_thickness)
        self.real_thickness.setChecked(self.current_template.real_thickness)
        self.flag_edit(False)

    def get_current_template(self):
        """Get self.current_template where not dynamically set."""
        self.current_template.default_thickness = self.default_thickness.value()
        self.current_template.real_thickness = self.real_thickness.isChecked()

    def change_color(self):
        """Open dialog to select color."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_template.color = color.name()
            self.flag_edit(True)
            self.color_label.setStyleSheet(
                f'QLabel{{background-color: {self.current_template.color};}}')

    def delete(self):
        """Delete material and related shield_data."""
        if len(self.templates) == 1:
            msg = 'Cannot delete last material.'
            QMessageBox.warning(self, 'Failed deleting material', msg)
        else:
            sel = self.current_template.label
            _, _, shield_data = cff.load_settings(fname='shield_data')
            in_shield = [temp.material for temp in shield_data]

            proceed = True
            if sel in in_shield:
                proceed = messageboxes.proceed_question(
                    self, 'Delete material and related shield data?')
            if proceed:
                idxs_used_current = [
                    i for i, val in enumerate(in_shield) if val==sel]
                if len(idxs_used_current) > 0:
                    idxs_used_current.reverse()
                    for idx in idxs_used_current:
                        shield_data.pop(idx)
                    _, path = cff.save_settings(
                        shield_data, fname='shield_data')

                    widget_shield_data = getattr(
                        self.settings_dialog, 'widget_shield_data')
                    widget_shield_data.update_from_yaml()
                    widget_shield_data.refresh_templist()

                idx = self.wid_temp_list.list_temps.currentIndex().row()
                self.templates.pop(idx)
                self.save()
                self.refresh_templist(selected_id=0)

                save_general = False
                gvls = self.main.general_values
                if gvls.shield_material_above == sel:
                    gvls.shield_material_above = self.templates[0].label
                    save_general = True
                if gvls.shield_material_below == sel:
                    gvls.shield_material_below = self.templates[0].label
                    save_general = True
                if save_general:
                    _, path = cff.save_settings(gvls, fname='general_values')


class ShieldDataWidget(StackWidget):
    """ShieldData settings."""

    def __init__(self, settings_dialog):
        header = 'Shield Data'
        subtxt = (
            'Combining isotope or kVp with materials to set shield properties.<br>'
            'The Archer equations for broad beam transmission is used if \u03b1, '
            '\u03b2, \u03b3 for this equation are defined.<br>'
            'Else half and tenth value layer is used to calculate the transmission '
            'according to the method described in '
            '<a href="https://open.canada.ca/data/en/dataset/ac988c2a-ce33-4e8e-bf64-2c052c50892f">'
            'Radionuclide Information Booklet (2025)</a>.'
            )
        super().__init__(settings_dialog, header, subtxt, temp_list=True, temp_alias='material')
        self.fname = 'shield_data'
        self.empty_template = cfc.ShieldData()

        self.alpha = QDoubleSpinBox(minimum=-100, maximum=100., decimals=5)
        self.alpha.valueChanged.connect(lambda: self.flag_edit(True))
        self.beta = QDoubleSpinBox(minimum=-100, maximum=100., decimals=5)
        self.beta.valueChanged.connect(lambda: self.flag_edit(True))
        self.gamma = QDoubleSpinBox(minimum=-100, maximum=100., decimals=4)
        self.gamma.valueChanged.connect(lambda: self.flag_edit(True))
        self.hvl1 = QDoubleSpinBox(maximum=1000., decimals=3)
        self.hvl1.valueChanged.connect(lambda: self.flag_edit(True))
        self.hvl2 = QDoubleSpinBox(maximum=1000., decimals=3)
        self.hvl2.valueChanged.connect(lambda: self.flag_edit(True))
        self.tvl1 = QDoubleSpinBox(maximum=1000., decimals=3)
        self.tvl1.valueChanged.connect(lambda: self.flag_edit(True))
        self.tvl2 = QDoubleSpinBox(maximum=1000., decimals=3)
        self.tvl2.valueChanged.connect(lambda: self.flag_edit(True))

        self.cbox_sources = QComboBox(self)
        self.cbox_sources.currentIndexChanged.connect(self.source_changed)

        self.gb_source_type = QGroupBox('Source type...')
        self.gb_source_type.setFont(uir.FontItalic())
        self.btns_source_type = QButtonGroup()
        hlo = QHBoxLayout()
        for i, txt in enumerate(['Isotope', 'kVp']):
            rbtn = QRadioButton(txt)
            if i == 0:
                rbtn.setChecked(True)
            self.btns_source_type.addButton(rbtn, i)
            hlo.addWidget(rbtn)
            rbtn.clicked.connect(self.source_type_changed)
        self.gb_source_type.setLayout(hlo)

        self.toolbar_kV_source = QToolBar()
        self.toolbar_kV_source.setOrientation(Qt.Orientation.Vertical)
        self.act_add_kV_source = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}add.png'), 'Add kV source', self)
        self.act_add_kV_source.triggered.connect(self.add_kV_source)
        self.act_rename_kV_source = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}rename.png'),
            'Rename kV source', self)
        self.act_rename_kV_source.triggered.connect(self.rename_kV_source)
        self.act_delete_kV_source = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}delete.png'),
            'Delete kV source', self)
        self.act_delete_kV_source.triggered.connect(self.delete_kV_source)

        if self.main.save_blocked:
            self.act_add_kV_source.setEnabled(False)
            self.act_rename_kV_source.setEnabled(False)
            self.act_delete_kV_source.setEnabled(False)

        self.toolbar_kV_source.addActions(
            [self.act_add_kV_source, self.act_rename_kV_source,
             self.act_delete_kV_source])
        self.toolbar_kV_source.setVisible(False)

        self.wid_temp_list.vlo_top.addWidget(self.gb_source_type)
        hlo_sources = QHBoxLayout()
        self.wid_temp_list.vlo_top.addLayout(hlo_sources)
        hlo_sources.addWidget(self.cbox_sources)
        hlo_sources.addWidget(self.toolbar_kV_source)

        self.wid_temp_list.toolbar.setVisible(False)

        btn_save = QPushButton('Save')
        btn_save.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}save.png'))
        btn_save.clicked.connect(
            lambda: self.save_shield_data(update_before_save=True))
        if self.main.save_blocked:
            btn_save.setEnabled(False)
        btn_delete = QPushButton('Delete')
        btn_delete.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}delete.png'))
        btn_delete.clicked.connect(self.delete_shield_data)
        if self.main.save_blocked:
            btn_delete.setEnabled(False)

        self.wid_temp = QWidget(self)

        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        hlo = QHBoxLayout()
        self.vlo_temp.addLayout(hlo)
        flo1 = QFormLayout()
        hlo.addLayout(flo1)
        flo1.addRow(uir.LabelHeader(
            'Archer equation used (if \u03b1, \u03b2, \u03b3 set)', 3))
        flo1.addRow(QLabel('\u03b1 (mm-1):'), self.alpha)
        flo1.addRow(QLabel('\u03b2 (mm-1):'), self.beta)
        flo1.addRow(QLabel('\u03b3:'), self.gamma)
        flo2 = QFormLayout()
        hlo.addLayout(flo2)
        flo2.addRow(uir.LabelHeader(
            'Alternative 2 if \u03b1, \u03b2, \u03b3 = 0', 3))
        flo2.addRow(QLabel('HVL1 (mm): '), self.hvl1)
        flo2.addRow(QLabel('HVL2 (mm): '), self.hvl2)
        flo2.addRow(QLabel('TVL1 (mm): '), self.tvl1)
        flo2.addRow(QLabel('TVL2 (mm): '), self.tvl2)
        self.btn_import_booklet = QPushButton(
            'Import values frow Radionuclide Information Booklet 2025')
        flo2.addRow(self.btn_import_booklet)
        self.btn_import_booklet.clicked.connect(self.import_booklet)
        self.vlo_temp.addStretch()
        hlo_btns = QHBoxLayout()
        self.vlo_temp.addLayout(hlo_btns)
        hlo_btns.addWidget(btn_save)
        hlo_btns.addWidget(btn_delete)

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def refresh_templist(self, selected_id=0, selected_label=''):
        """Update the list of templates, and self.current... - override StackWidget.

        Parameters
        ----------
        selected_id : int, optional
            index to select in template list. The default is 0.
        selected_label : str, optional
            label to select in template list (override index)
            The default is ''.
        """
        # show list of materials with bold font for those defined for current source
        self.current_labels = [x.label for x in self.materials]
        curr_source_is_isotope = self.btns_source_type.button(0).isChecked()
        curr_source = self.cbox_sources.currentText()
        if curr_source_is_isotope:
            materials_defined = [
                x.material for x in self.templates if x.isotope == curr_source]
        else:
            materials_defined = [
                x.material for x in self.templates if x.kV_source == curr_source]

        self.wid_temp_list.list_temps.blockSignals(True)
        self.wid_temp_list.list_temps.clear()
        self.wid_temp_list.list_temps.addItems(self.current_labels)
        for i in range(self.wid_temp_list.list_temps.count()):
            item = self.wid_temp_list.list_temps.item(i)
            if item.text() not in materials_defined:
                item.setForeground(QColor("gray"))

        if selected_label != '':
            tempno = self.current_labels.index(selected_label)
        else:
            tempno = selected_id
        tempno = max(tempno, 0)
        if tempno > len(self.current_labels)-1:
            tempno = len(self.current_labels)-1
        self.wid_temp_list.list_temps.setCurrentRow(tempno)
        self.wid_temp_list.list_temps.blockSignals(False)

        if len(self.current_labels) == 0:
            self.current_template = copy.deepcopy(self.empty_template)
        else:
            self.update_current_template(selected_id=tempno)

        self.update_data()

    def fill_list_sources(self):
        """Fill list of sources based on selection of source type."""
        if self.btns_source_type.button(0).isChecked():
            labels = [isotope.label for isotope in self.isotopes]
            self.toolbar_kV_source.setVisible(False)
            self.btn_import_booklet.setVisible(True)
        else:
            labels = self.main.general_values.kV_sources
            self.toolbar_kV_source.setVisible(True)
            self.btn_import_booklet.setVisible(False)
        self.blockSignals(True)
        self.cbox_sources.clear()
        self.cbox_sources.addItems(labels)
        self.blockSignals(False)
        self.cbox_sources.setCurrentIndex(0)

    def update_clicked_template(self):
        """Update data after new template selected (clicked)."""
        if self.edited:
            res = messageboxes.QuestionBox(
                parent=self, title='Save changes?',
                msg='Save changes before changing template?')
            res.exec()
            if res.clickedButton() == res.yes:
                self.get_current_template(ignore_material=True)
                tempno = self.find_index_of_template()
                self.templates[tempno] = copy.deepcopy(self.current_template)
                self.save_shield_data(update_before_save=False)
            else:
                self.flag_edit(False)

        row = self.wid_temp_list.list_temps.currentIndex().row()
        self.update_current_template(selected_id=row)
        self.update_data()

    def update_current_template(self, selected_id=0):
        """Update self.current_template from saved by source and material."""
        tempno = self.find_index_of_template(selected_material_id=selected_id)
        if tempno is not None:
            self.current_template = copy.deepcopy(self.templates[tempno])
        else:
            self.current_template = copy.deepcopy(self.empty_template)

    def update_data(self):
        """Refresh GUI after selecting template."""
        self.alpha.setValue(self.current_template.alpha)
        self.beta.setValue(self.current_template.beta)
        self.gamma.setValue(self.current_template.gamma)
        self.hvl1.setValue(self.current_template.hvl1)
        self.hvl2.setValue(self.current_template.hvl2)
        self.tvl1.setValue(self.current_template.tvl1)
        self.tvl2.setValue(self.current_template.tvl2)
        self.flag_edit(False)

    def source_type_changed(self):
        """User changed source type."""
        if self.edited:
            res = messageboxes.QuestionBox(
                parent=self, title='Save changes?',
                msg='Save changes before changing selections?')
            res.exec()
            if res.clickedButton() == res.yes:
                self.save_shield_data(update_before_save=True)
            else:
                self.flag_edit(False)
        self.fill_list_sources()
        row = self.wid_temp_list.list_temps.currentIndex().row()
        self.update_current_template(selected_id=row)
        self.update_data()

    def source_changed(self):
        """Update on new source selected."""
        if self.edited:
            res = messageboxes.QuestionBox(
                parent=self, title='Save changes?',
                msg='Save changes before changing selections?')
            res.exec()
            if res.clickedButton() == res.yes:
                self.save_shield_data(update_before_save=True)
            else:
                self.flag_edit(False)
        if hasattr(self, 'current_template'):
            self.refresh_templist(selected_label=self.current_template.material)
        else:
            self.refresh_templist()

    def save_general_and_shield_data(self):
        """Save general_values and shield_data. Assume verify_save already."""
        ok_save1, path1 = cff.save_settings(
            self.main.general_values, fname='general_values')
        self.lastload_general_values = time()
        ok_save2, path2 = cff.save_settings(
            self.main.shield_data, fname='shield_data')
        if not all([ok_save1, ok_save2]):
            if ok_save1 == ok_save2:
                msg = f'Failed saving to {path1} and {path2}'
            else:
                if ok_save1:
                    msg = (f'Failed saving to {path2}. Might cause mismatch later.'
                           'Verify yaml files.')
                else:
                    msg = (f'Failed saving to {path1}. Might cause mismatch later.'
                           'Verify yaml files.')
            QMessageBox.warning(self, 'Failed saving config files', msg)
        else:
            self.lastload_general_values = time()
            self.lastload = time()

    def add_kV_source(self):
        """Add kV source."""
        text, proceed = QInputDialog.getText(
            self, 'New name',
            'Name the new kV sourcce                     ')
        # todo also ask if add as current or as empty
        text = valid_template_name(text)
        if proceed and text != '':
            if text in self.main.general_values.kV_sources:
                QMessageBox.warning(
                    self, 'Name already in use',
                    'This name is already in use.')
            else:
                ok_save = self.verify_save(
                    'general_values', self.lastload_general_values)
                if ok_save:
                    self.main.general_values.kV_sources.append(text)
                    ok_save, path = cff.save_settings(
                        self.main.general_values, fname='general_values')
                    if ok_save:
                        self.lastload_general_values = time()
                        self.cbox_sources.addItem(text)
                        self.cbox_sources.setCurrentText(text)
                    else:
                        QMessageBox.warning(
                            self, 'Failed saving new kV source',
                            f'Failed saving to {path}')

    def rename_kV_source(self):
        """Rename current kV_source. Ask for new name and verify."""
        if len(self.main.general_values.kV_sources) == 0:
            QMessageBox.warning(self, 'Empty list', 'No kV source to rename.')
        else:
            current_text = self.cbox_sources.currentText()
            text, proceed = QInputDialog.getText(
                self, 'New name',
                'Rename kV_source                      ',
                text=current_text)
            text = valid_template_name(text)
            if proceed and text != '' and current_text != text:
                if text in self.main.general_values.kV_sources:
                    QMessageBox.warning(
                        self, 'Name already in use',
                        'This name is already in use.')
                else:
                    ok_save1 = self.verify_save(
                        'general_values', self.lastload_general_values)
                    ok_save2 = self.verify_save(
                        self.fname, self.lastload)
                    if ok_save1 and ok_save2:
                        row = self.cbox_sources.currentIndex()
                        self.main.general_values.kV_sources[row] = text
                        for temp in self.main.shield_data:
                            if temp.kV_source == current_text:
                                temp.kV_source = text
                        self.main.renamed_kV_sources[0].append(current_text)
                        self.main.renamed_kV_sources[1].append(text)
                        self.blockSignals(True)
                        self.cbox_sources.clear()
                        labels = self.main.general_values.kV_sources
                        self.cbox_sources.addItems(labels)
                        self.cbox_sources.setCurrentText(text)
                        self.blockSignals(False)
                        self.save_general_and_shield_data()
                        #self.refresh_templist(selected_label=text)

    def delete_kV_source(self):
        """Delete kV_source."""
        ok_save1 = self.verify_save('general_values', self.lastload_general_values)
        ok_save2 = self.verify_save(self.fname, self.lastload)
        if ok_save1 and ok_save2:
            current_value = self.cbox_sources.currentText()
            used = [x.kV_source for x in self.templates]

            proceed = True
            if current_value in used:
                proceed = messageboxes.proceed_question(
                    self, 'Delete kV source and related shield data?')
            if proceed:
                self.main.general_values.kV_sources.remove(current_value)
                idxs_used_current = [
                    i for i, val in enumerate(used) if val == current_value]
                idxs_used_current.reverse()
                for idx in idxs_used_current:
                    self.templates.pop(idx)
                self.save_general_and_shield_data()
                self.fill_list_sources()
                self.refresh_templist()

    def find_index_of_template(self, selected_material_id=None):
        """Find index of template holding selected source and material.

        Parameters
        ----------
        selected_material_id : int, optional
            Specify index of material. The default is None.

        Returns
        -------
        index : int
            Index of template in shield_data templates
        """
        source = self.cbox_sources.currentText()
        if selected_material_id is None:
            row = self.wid_temp_list.list_temps.currentIndex().row()
            material = self.current_labels[row]
        else:
            material = self.current_labels[selected_material_id]
        index = None
        for i, temp in enumerate(self.templates):
            if self.btns_source_type.button(0).isChecked():
                match = (temp.isotope == source)
            else:
                match = (temp.kV_source == source)
            if match:
                match = (temp.material == material)
                if match:
                    index = i
                    break
        return index

    def import_booklet(self):
        df_row = read_booklet(self.cbox_sources.currentText(), self)
        if df_row.size > 0:
            selected_id = self.wid_temp_list.list_temps.currentIndex().row()
            sel_mat = self.materials[selected_id]
            res = messageboxes.QuestionBox(
                parent=self, title='This or all materials?',
                msg='Import for selected material or all materials '
                'defined in the booklet?',
                yes_text=f'Selected material ({sel_mat.label})',
                no_text='All materials (Lead, Steel, Concrete)')
            res.exec()
            specific_material = ''
            if res.clickedButton() == res.yes:
                specific_material = sel_mat.label
            import_shield_booklet(df_row, self,
                                  specific_material=specific_material)

    def save_shield_data(self, update_before_save=True):
        """Save shield data."""
        if update_before_save:
            tempno = self.find_index_of_template()
            self.get_current_template()
            if tempno is not None:
                self.templates[tempno] = copy.deepcopy(self.current_template)
            else:
                self.templates.append(self.current_template)
        ok_save = self.verify_save(self.fname, self.lastload)
        if ok_save:
            # verify that either all aplha,beta,gamma not zero
            # or hvl,tvls all >0
            if not all([
                    self.current_template.alpha,
                    self.current_template.beta,
                    self.current_template.gamma]):
                if any([
                        self.current_template.alpha,
                        self.current_template.beta,
                        self.current_template.gamma]):
                    ok_save = False
                    msg = (
                        'Alpha, beta or gamma is nonzero. These should all be '
                        'zero or all nonzero to avoid confusion. '
                        'Saving failed.')
                    QMessageBox.warning(self, 'Confusing values', msg)
                elif not all([
                        self.current_template.hvl1,
                        self.current_template.hvl2,
                        self.current_template.tvl1,
                        self.current_template.tvl2]):
                    ok_save = False
                    msg = (
                        'Either alpha, beta, gamma should be nonzero or all '
                        'HVL and TVL should be nonzero. Saving failed.')
                    QMessageBox.warning(self, 'Incorrect values', msg)
        if ok_save:
            ok_save, path = cff.save_settings(
                self.templates, fname=self.fname)
            self.status_label.setText(f'Changes saved to {path}')
            self.flag_edit(False)
            self.lastload = time()

    def delete_shield_data(self):
        """Delete shield data."""
        index = self.find_index_of_template()
        if index is not None:
            self.templates.pop(index)
            self.save_shield_data(update_before_save=False)
            self.refresh_templist(selected_label=self.current_template.material)
        else:
            self.status_label.setText('Nothing to delete from saved templates.')

    def get_current_template(self, ignore_material=False):
        """Get self.current_template from screen values, possibly changed."""
        if self.cbox_sources.currentText() != '':
            if not hasattr(self, 'current_template'):
                self.current_template = copy.deepcopy(self.empty_template)
            if self.btns_source_type.button(0).isChecked():
                self.current_template.isotope = self.cbox_sources.currentText()
                self.current_template.kV_source = ''
            else:
                self.current_template.kV_source = self.cbox_sources.currentText()
                self.current_template.isotope = ''
            if not ignore_material:
                row = self.wid_temp_list.list_temps.currentIndex().row()
                self.current_template.material = self.current_labels[row]
            self.current_template.alpha = self.alpha.value()
            self.current_template.beta = self.beta.value()
            self.current_template.gamma = self.gamma.value()
            self.current_template.hvl1 = self.hvl1.value()
            self.current_template.hvl2 = self.hvl2.value()
            self.current_template.tvl1 = self.tvl1.value()
            self.current_template.tvl2 = self.tvl2.value()
        else:
            self.current_template = copy.deepcopy(self.empty_template)


class ColormapSettingsWidget(StackWidget):
    """Widget for setting colormaps."""

    def __init__(self, settings_dialog):
        header = 'Colormaps'
        subtxt = 'Configre colors for dose and doserate limits.'
        super().__init__(settings_dialog, header, subtxt, temp_list=True, temp_alias='colormap')
        self.fname = 'colormaps'
        self.empty_template = cfc.ColorMap()
        self.active_row = 0
        self.empty_row = [0.0, '#000000']
        self.table_list = []
        self.wid_temp_list.toolbar.setVisible(False)

        self.gb_use = QGroupBox('Define colors by...')
        self.gb_use.setFont(uir.FontItalic())
        self.btns_use = QButtonGroup()
        self.btns_use.setExclusive(True)
        btns_hlo = QHBoxLayout()
        for i, txt in enumerate(['table', 'colormap']):
            rbtn = QRadioButton(txt)
            self.btns_use.addButton(rbtn, i)
            btns_hlo.addWidget(rbtn)
            rbtn.clicked.connect(self.use_changed)
        self.gb_use.setLayout(btns_hlo)

        self.stack_use = QStackedWidget()
        self.widget_table = QWidget()
        self.widget_colormap = QWidget()
        self.stack_use.addWidget(self.widget_table)
        self.stack_use.addWidget(self.widget_colormap)

        self.table = QTableWidget(1, 3)
        self.table.setMinimumHeight(250)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection)
        self.table_headers = [
            ['For dose higher than', 'Color', 'Color code'],
            ['For doserate higher than', 'Color', 'Color code'],
            ['Occupancy factor', 'Color', 'Color code']
            ]
        self.table.setHorizontalHeaderLabels(self.table_headers[0])
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 40*self.main.gui.char_width)
        self.table.setColumnWidth(1, 25*self.main.gui.char_width)
        self.table.setColumnWidth(2, 25*self.main.gui.char_width)
        self.add_cell_widgets(0)

        self.table_toolbar = QToolBar()
        self.table_toolbar.setOrientation(Qt.Orientation.Vertical)

        self.colorbar = uir.ColorBar()
        self.txt_colorbar = QLineEdit('')
        self.txt_colorbar.editingFinished.connect(self.cmap_changed)
        self.btn_colorbar = QPushButton('Select...')
        self.btn_colorbar.clicked.connect(self.select_cmap)
        self.cmin = QDoubleSpinBox(minimum=0, maximum=10000., decimals=2)
        self.cmin.valueChanged.connect(lambda: self.flag_edit(True))
        self.cmax = QDoubleSpinBox(minimum=0, maximum=10000., decimals=2)
        self.cmax.valueChanged.connect(lambda: self.flag_edit(True))

        act_delete = QAction('Delete', self)
        act_delete.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}delete.png'))
        act_delete.setToolTip('Delete selected row')
        act_delete.triggered.connect(self.delete_row)

        act_add = QAction('Add', self)
        act_add.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}add.png'))
        act_add.setToolTip('Add new row after selected row')
        act_add.triggered.connect(self.add_row)

        act_edit = QAction('Edit', self)
        act_edit.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}edit.png'))
        act_edit.setToolTip('Edit color of selected row')
        act_edit.triggered.connect(self.edit_color_row)

        act_up = QAction('Move up', self)
        act_up.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}moveUp.png'))
        act_up.setToolTip('Move selected row up')
        act_up.triggered.connect(lambda: self.move_row(direction='up'))

        act_down = QAction('Move down', self)
        act_down.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}moveDown.png'))
        act_down.setToolTip('Move selected row down')
        act_down.triggered.connect(lambda: self.move_row(direction='down'))

        self.table_toolbar.addActions([act_delete, act_add, act_up, act_down,
                                       act_edit])

        btn_save = QPushButton('Save')
        btn_save.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}save.png'))
        btn_save.clicked.connect(self.save_colormap)
        if self.main.save_blocked:
            btn_save.setEnabled(False)

        self.wid_temp = QWidget(self)
        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        self.vlo_temp.addWidget(self.gb_use)
        self.vlo_temp.addWidget(self.stack_use)

        vlo_tab = QVBoxLayout()
        hlo_tab = QHBoxLayout()
        self.widget_table.setLayout(vlo_tab)
        vlo_tab.addLayout(hlo_tab)
        hlo_tab.addWidget(self.table_toolbar)
        hlo_tab.addWidget(self.table)
        vlo_tab.addWidget(QLabel(
            'Colormap might mix colors if the separate colors are from very '
            'different (i.e. red vs green or blue).'))

        vlo_colorbar = QVBoxLayout()
        self.widget_colormap.setLayout(vlo_colorbar)
        hlo_colorbar = QHBoxLayout()
        vlo_colorbar.addLayout(hlo_colorbar)
        hlo_colorbar.addWidget(self.colorbar)
        hlo_colorbar.addWidget(self.txt_colorbar)
        hlo_colorbar.addWidget(self.btn_colorbar)
        hlo_colorbar.addStretch()
        hlo_cminmax = QHBoxLayout()
        vlo_colorbar.addLayout(hlo_cminmax)
        hlo_cminmax.addWidget(QLabel('Minimum'))
        hlo_cminmax.addWidget(self.cmin)
        hlo_cminmax.addSpacing(20)
        hlo_cminmax.addWidget(QLabel('Maximum'))
        hlo_cminmax.addWidget(self.cmax)
        hlo_cminmax.addStretch()
        vlo_colorbar.addStretch()

        self.vlo_temp.addStretch()
        self.vlo_temp.addWidget(btn_save)

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def add_cell_widgets(self, row, initial_value=0.0, initial_color='#000000'):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.CellSpinBox(
            self, initial_value=initial_value, min_val=0., max_val=200,
            row=row, col=0, step=0.25, decimals=3))
        self.table.setCellWidget(row, 1, uir.ColorCell(
            self, initial_color=initial_color, row=row, col=1))
        self.table.setCellWidget(row, 2, uir.TextCell(
            self, initial_text=initial_color, row=row, col=2))

    def delete_row(self):
        """Delete selected row.

        Returns
        -------
        row : int
            index of the deleted row
        """
        row = self.active_row
        if row > -1:
            proceed = messageboxes.proceed_question(self, 'Delete active row?')
            if proceed:
                if len(self.table_list) == 1:
                    self.add_cell_widgets(0)
                    self.table.removeRow(1)
                    self.table_list = [copy.deepcopy(self.empty_row)]
                    self.active_row = 0
                else:
                    self.table.removeRow(row)
                    self.table_list.pop(row)
                    self.update_row_number(row, -1)
                self.select_row_col(row, 0)
            else:
                row = -1
        return row

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        newrow : int
            index of the new row
        """
        newrow = -1
        if self.active_row == -1:
            newrow = self.table.rowCount()
        else:
            newrow = self.active_row + 1
            self.update_row_number(newrow, 1)
        self.table.insertRow(newrow)
        self.add_cell_widgets(newrow)
        self.table_list.insert(newrow, copy.deepcopy(self.empty_row))
        self.select_row_col(newrow, 1)
        return newrow

    def move_row(self, direction='up'):
        if self.active_row == -1:
            msg = 'Select a row to move'
            QMessageBox.warning(self, 'No row selected', msg)
        else:
            row = self.active_row
            popped = self.table_list.pop(row)
            new_row = row - 1 if direction == 'up' else row + 1
            self.table_list.insert(new_row, popped)
            self.update_table()
            self.select_row_col(new_row, 0)

    def edit_color_row(self):
        """Edit color for active row."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.table_list[self.active_row][1] = color.name()
            w = self.table.cellWidget(self.active_row, 1)
            w.setStyleSheet(
                f'QLabel{{background-color: {color.name()};}}')
            w = self.table.cellWidget(self.active_row, 2)
            w.setText(color.name())
            self.flag_edit(True)

    def cell_changed(self, row, col, decimals=None):
        """Value changed by user input."""
        w = self.table.cellWidget(self.active_row, col)
        if col == 0:
            value = w.value()  # self.table_list[row][col]
            if decimals:
                value = round(value, decimals)
            self.table_list[row][col] = value
        else:
            code = w.text()
            if re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', code):
                w = self.table.cellWidget(self.active_row, 1)
                w.setStyleSheet(
                    f'QLabel{{background-color: {code};}}')
            else:
                msg = 'Color code is not a valid hex-string (#rrggbb)'
                QMessageBox.warning(self, 'Color code not valid', msg)
        self.flag_edit(True)

    def select_row_col(self, row, col):
        """Set focus on selected row and col."""
        index = self.table.model().index(row, col)
        self.table.selectionModel().select(
            index, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
        self.active_row = row

    def cell_selection_changed(self, row, col):
        """Cell widget got focus. Change active row and highlight."""
        self.select_row_col(row, col)

    def update_row_number(self, first_row_to_adjust, row_adjust):
        """Adjust row number of cell widgets after inserting/deleting rows.

        Parameters
        ----------
        first_row_to_adjust : int
            first row number to adjust by row_adjust
        row_adjust : int
            number to adjust row numbers by
        """
        for i in range(first_row_to_adjust, self.table.rowCount()):
            for j in range(self.table.columnCount()):
                w = self.table.cellWidget(i, j)
                w.row = w.row + row_adjust

    def select_cmap(self):
        dlg = CmapSelectDialog(self)
        res = dlg.exec()
        if res:
            cmap = dlg.get_cmap()
            self.current_template.cmap = cmap
            self.txt_colorbar.setText(cmap)
            self.colorbar.colorbar_draw(cmap=cmap)
            self.flag_edit(True)

    def cmap_changed(self):
        try:
            cmap = self.txt_colorbar.text()
            self.colorbar.colorbar_draw(cmap=cmap)
            self.current_template.cmap = cmap
            self.flag_edit(True)
        except ValueError:
            msg = f'{cmap} is not a supported cmap value for matplotlib.'
            QMessageBox.warning(self, 'Failed setting colormap', msg)

    def use_changed(self):
        """Use table or cmap changed - or possibly changed."""
        if self.btns_use.button(0).isChecked():
            self.current_template.use = 'table'
            self.stack_use.setCurrentIndex(0)
        else:
            self.current_template.use = 'cmap'
            self.stack_use.setCurrentIndex(1)
        self.flag_edit(True)

    def update_table(self):
        """Update after order changed (new self.table_list)."""
        self.table.setRowCount(0)

        for i, row in enumerate(self.table_list):
            self.table.insertRow(i)
            self.add_cell_widgets(i, initial_value=row[0], initial_color=row[1])

    def update_data(self):
        """Refresh GUI after selecting template."""
        tempno = self.current_labels.index(self.current_template.label)
        self.table.setHorizontalHeaderLabels(self.table_headers[tempno])
        self.table_list = self.templates[tempno].table
        self.update_table()
        '''
        self.table.setRowCount(0)

        for i, row in enumerate(self.table_list):
            self.table.insertRow(i)
            self.add_cell_widgets(i, initial_value=row[0], initial_color=row[1])
        '''

        self.txt_colorbar.setText(self.current_template.cmap)
        self.colorbar.colorbar_draw(cmap=self.current_template.cmap)
        self.cmin.setValue(self.current_template.cmin)
        self.cmax.setValue(self.current_template.cmax)

        self.blockSignals(True)
        if self.current_template.use == 'table':
            self.btns_use.button(0).setChecked(True)
        else:
            self.btns_use.button(1).setChecked(True)
        self.blockSignals(False)
        self.use_changed()

        self.flag_edit(False)

    def save_colormap(self):
        """Save current colormap."""
        tempno = self.current_labels.index(self.current_template.label)
        self.templates[tempno] = copy.deepcopy(self.current_template)
        self.templates[tempno].table = copy.deepcopy(self.table_list)
        ok_save = self.verify_save(self.fname, self.lastload)
        if self.current_template.use == 'cmap':
            cmin = self.cmin.value()
            cmax = self.cmax.value()
            if cmax <= cmin:
                ok_save = False
                msg = 'Colormap maximum have to be larger than the minimum.'
                QMessageBox.warning(self, 'Failed saving settings', msg)
            else:
                self.templates[tempno].cmin = cmin
                self.templates[tempno].cmax = cmax
        else:  # table
            values = np.array([row[0] for row in self.table_list])
            if values.size > 1:
                orderdiff = np.diff(np.argsort(values))
                if np.min(orderdiff) < 1 or np.max(orderdiff) > 1:
                    ok_save = False
                    msg = 'Values need to be ascending.'
                    QMessageBox.warning(self, 'Failed saving settings', msg)
        if ok_save:
            ok_save, path = cff.save_settings(
                self.templates, fname=self.fname)
            self.status_label.setText(f'Changes saved to {path}')
            self.flag_edit(False)
            self.lastload = time()


class CmapSelectDialog(ShieldDialog):
    """Dialog to select matplotlib colormap."""

    def __init__(self, current_cmap='rainbow'):
        super().__init__()
        self.setWindowTitle('Select colormap')
        self.setMinimumHeight(300)
        self.setMinimumWidth(300)
        vlo = QVBoxLayout()
        self.setLayout(vlo)

        self.cmaps = ['rainbow', 'viridis', 'YlOrRd', 'OrRd',
                      'autumn', 'hot', 'Reds']
        self.list_cmaps = QComboBox()
        self.list_cmaps.addItems(self.cmaps)
        self.list_cmaps.setCurrentIndex(0)
        self.list_cmaps.currentIndexChanged.connect(self.update_preview)
        self.chk_reverse = QCheckBox('Reverse')
        self.chk_reverse.clicked.connect(self.update_preview)
        self.colorbar = uir.ColorBar()

        vlo.addWidget(QLabel('Select colormap:'))
        vlo.addWidget(self.list_cmaps)
        vlo.addWidget(self.chk_reverse)
        vlo.addWidget(self.colorbar)
        hlo_buttons = QHBoxLayout()
        vlo.addLayout(hlo_buttons)

        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        vlo.addWidget(self.buttonBox)

        self.update_preview()

    def update_preview(self):
        """Sort elements by name or date."""
        cmap = self.get_cmap()
        self.colorbar.colorbar_draw(cmap=cmap)

    def get_cmap(self):
        """Return selected indexes in list."""
        cmap = self.list_cmaps.currentText()
        if self.chk_reverse.isChecked():
            cmap = cmap + '_r'
        return cmap