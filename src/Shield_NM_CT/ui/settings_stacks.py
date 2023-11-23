#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings part automation.

@author: Ellen Wasbo
"""
import os
import copy
from time import time

from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QToolBar,
    QLabel, QPushButton, QButtonGroup, QRadioButton, QAction, QCheckBox,
    QComboBox, QDoubleSpinBox, QInputDialog, QColorDialog, QTableWidget,
    QMessageBox
    )

# Shield_NM_CT block start
from Shield_NM_CT.config import config_classes as cfc
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui.settings_reusables import StackWidget
from Shield_NM_CT.ui import reusable_widgets as uir
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.config.Shield_NM_CT_constants import ENV_ICON_PATH
from Shield_NM_CT.scripts.mini_methods_format import valid_template_name
# Shield_NM_CT block end


class IsotopeWidget(StackWidget):
    """Isotope settings."""

    def __init__(self, main):
        header = 'Isotopes'
        subtxt = ''
        super().__init__(main, header, subtxt,
                         temp_list=True, temp_alias='isotope')
        self.fname = 'isotopes'
        self.empty_template = cfc.Isotope()

        self.half_life = QDoubleSpinBox(minimum=0, maximum=100000., decimals=2)
        self.half_life.valueChanged.connect(lambda: self.flag_edit(True))
        self.half_life_unit = QComboBox()
        self.half_life_unit.addItems(['minutes', 'hours', 'days'])
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
        if self.patient_constant.value() > 0:
            ratio = self.patient_constant.value() / self.gamma_ray_constant.value()
            txt = f'{100*ratio:.1f} %'
        self.patient_percent.setText(txt)

    def delete(self):
        """After verifying at will."""
        # not possible if used in shield data


class MaterialWidget(StackWidget):
    """Material settings."""

    def __init__(self, main):
        header = 'Materials'
        subtxt = ''
        super().__init__(main, header, subtxt,
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
        """After verifying at will."""
        # not possible if used in shield data


class ShieldDataWidget(StackWidget):
    """ShieldData settings."""

    def __init__(self, main):
        header = 'Shield Data'
        subtxt = (
            'Combining isotope or kVp with materials to set shield properties.<br>'
            'The Archer equations for broad beam transmission is used if \u03b1, '
            '\u03b2, \u03b3 for this equation are defined.<br>'
            'Else half and tenth value layer is used to calculate the transmission '
            'according to the method described in '
            '<a href="https://nuclearsafety.gc.ca/pubs_catalogue/uploads/radionuclide-information-booklet-2022-eng.pdf">'
            'Radionuclide Information Booklet (2023)</a>.'
            )
        super().__init__(main, header, subtxt, temp_list=True, temp_alias='material')
        self.fname = 'shield_data'
        self.empty_template = cfc.ShieldData()

        self.alpha = QDoubleSpinBox(minimum=-100, maximum=100., decimals=4)
        self.alpha.valueChanged.connect(lambda: self.flag_edit(True))
        self.beta = QDoubleSpinBox(minimum=-100, maximum=100., decimals=4)
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
        self.toolbar_kV_source.setOrientation(Qt.Vertical)
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
        btn_save.clicked.connect(self.save_shield_data)
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
        flo1.addRow(QLabel('\u03b1:'), self.alpha)
        flo1.addRow(QLabel('\u03b2:'), self.beta)
        flo1.addRow(QLabel('\u03b3:'), self.gamma)
        flo2 = QFormLayout()
        hlo.addLayout(flo2)
        flo2.addRow(QLabel('HVL1 (mm): '), self.hvl1)
        flo2.addRow(QLabel('HVL2 (mm): '), self.hvl2)
        flo2.addRow(QLabel('TVL1 (mm): '), self.tvl1)
        flo2.addRow(QLabel('TVL2 (mm): '), self.tvl2)

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
        self.current_labels = [x.label for x in self.main.materials]
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
            labels = [isotope.label for isotope in self.main.isotopes]
            self.toolbar_kV_source.setVisible(False)
        else:
            labels = self.main.general_values.kV_sources
            self.toolbar_kV_source.setVisible(True)
        self.blockSignals(True)
        self.cbox_sources.clear()
        self.cbox_sources.addItems(labels)
        self.blockSignals(False)
        self.cbox_sources.setCurrentIndex(0)

    def update_current_template(self, selected_id=0):
        """Update self.current_template by source and material."""
        tempno = self.find_index_of_template(selected_material_id=selected_id)
        if tempno is not None:
            self.current_template = copy.deepcopy(self.templates[tempno])

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
            if res.exec():
                self.save_shield_data()
            else:
                self.flag_edit(False)
        self.fill_list_sources()
        self.update_current_template()
        self.update_data()

    def source_changed(self):
        """Update on new source selected."""
        if self.edited:
            res = messageboxes.QuestionBox(
                parent=self, title='Save changes?',
                msg='Save changes before changing selections?')
            if res.exec():
                self.save_shield_data()
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
                    self.main.general_values.kV_source.append(text)
                    ok_save, path = cff.save_settings(
                        self.main.general_values, fname='general_values')
                    if ok_save:
                        self.lastload_general_values = time()
                        self.cbox_sources.addItem(text)
                        self.cbox_sources.setCurrentText(text)
                    else:
                        QMessageBox.warning(
                            self, f'Failed saving new kV source',
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
                            if temp.kV_source == row.text():
                                temp.kV_source = text

                        self.save_general_and_shield_data()
                        self.refresh_templist(selected_label=text)

    def delete_kV_source(self):
        """Delete kV_source."""
        ok_save1 = self.verify_save('general_values', self.lastload_general_values)
        ok_save2 = self.verify_save(self.fname, self.lastload)
        if ok_save1 and ok_save2:
            current_value = self.current_template.kV_source
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
        index = None
        self.get_current_template()
        for i, temp in enumerate(self.templates):
            if self.btns_source_type.button(0).isChecked():
                match = (temp.isotope == self.current_template.isotope)
            else:
                match = (temp.kV_source == self.current_template.kV_source)
            if match:
                match = (temp.material == self.current_template.material)
                if match:
                    index = i
                    break
        return index

    def save_shield_data(self, update_before_save=True):
        """Save shield data."""
        if update_before_save:
            tempno = self.find_index_of_current_template()
            self.get_current_template()
            if tempno is not None:
                self.templates[tempno] = copy.deepcopy(self.current_template)
            else:
                self.templates.append(self.current_template)
        ok_save = self.verify_save(self.fname, self.lastload)
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
            self.save_shield_data(update_before_save=False)
        else:
            self.status_label.setText('Nothing to delete from saved templates.')

    def get_current_template(self):
        """Get self.current_template where not dynamically set."""
        if self.cbox_sources.currentText() != '':
            if not hasattr(self, 'current_template'):
                self.current_template = copy.deepcopy(self.empty_template)
            if self.btns_source_type.button(0).isChecked():
                self.current_template.isotope = self.cbox_sources.currentText()
                self.current_template.kV_source = ''
            else:
                self.current_template.kV_source = self.cbox_sources.currentText()
                self.current_template.isotope = ''
            if self.current_template.isotope == self.current_template.kV_source:
                breakpoint()
            row = self.wid_temp_list.list_temps.currentIndex().row()
            self.current_template.material = self.current_labels[row]
            self.current_template.alpha = self.alpha.value()
            self.current_template.beta = self.beta.value()
            self.current_template.gamma = self.gamma.value()
            self.current_template.hvl1 = self.hvl1.value()
            self.current_template.hvl2 = self.hvl2.value()
            self.current_template.tvl1 = self.tvl1.value()
            self.current_template.tvl2 = self.tvl2.value()


class ColormapSettingsWidget(StackWidget):
    """Widget for setting colormaps."""

    def __init__(self, main):
        header = 'Colormaps'
        subtxt = 'Configre colors for dose and doserate limits.'
        super().__init__(main, header, subtxt, temp_list=True, temp_alias='colormap')
        self.fname = 'colormaps'
        self.empty_template = cfc.ColorMap()
        self.active_row = 0
        self.empty_row = [0.0, '#000000']
        self.table_list = []
        self.wid_temp_list.toolbar.setVisible(False)

        self.table = QTableWidget(1, 2)
        self.table.setMinimumHeight(250)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setHorizontalHeaderLabels(
            ['For dose(rate) higher than', 'Color'])
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 40*self.main.gui.char_width)
        self.table.setColumnWidth(1, 25*self.main.gui.char_width)
        self.add_cell_widgets(0)

        table_toolbar = QToolBar()
        table_toolbar.setOrientation(Qt.Vertical)

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

        table_toolbar.addActions([act_delete, act_add, act_edit])

        btn_save = QPushButton('Save')
        btn_save.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}save.png'))
        btn_save.clicked.connect(self.save_colormap)
        if self.main.save_blocked:
            btn_save.setEnabled(False)

        self.wid_temp = QWidget(self)
        self.hlo.addWidget(self.wid_temp)
        self.vlo_temp = QVBoxLayout()
        self.wid_temp.setLayout(self.vlo_temp)

        hlo = QHBoxLayout()
        self.vlo_temp.addLayout(hlo)
        hlo.addWidget(table_toolbar)
        hlo.addWidget(self.table)

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
        self.table_list.insert(newrow, copy.deepcopy(self.empty_row))
        self.select_row_col(newrow, 1)
        return newrow

    def edit_color_row(self):
        """Edit color for active row."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.table_list[self.active_row][1] = color.name()
            w = self.table.cellWidget(self.active_row, 1)
            w.setStyleSheet(
                f'QLabel{{background-color: {color.name()};}}')
            self.flag_edit(True)

    def cell_changed(self, row, col, decimals=None):
        """Value changed by user input."""
        value = self.get_cell_value(row, col)
        if decimals:
            value = round(value, decimals)
        self.table_list[row][col] = value
        self.flag_edit(True)

    def select_row_col(self, row, col):
        """Set focus on selected row and col."""
        index = self.table.model().index(row, col)
        self.table.selectionModel().select(
            index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
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

    def update_data(self):
        """Refresh GUI after selecting template."""
        tempno = self.current_labels.index(self.current_template.label)
        self.table_list = self.templates[tempno].table
        self.table.setRowCount(0)

        for i, row in enumerate(self.table_list):
            self.table.insertRow(i)
            self.add_cell_widgets(i, initial_value=row[0], initial_color=row[1])

        self.flag_edit(False)

    def save_colormap(self):
        """Save current colormap."""
        tempno = self.current_labels.index(self.current_template.label)
        self.templates[tempno].table = copy.deepcopy(self.table_list)
        ok_save = self.verify_save(self.fname, self.lastload)
        if ok_save:
            ok_save, path = cff.save_settings(
                self.templates, fname=self.fname)
            self.status_label.setText(f'Changes saved to {path}')
            self.flag_edit(False)
            self.lastload = time()
