#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings.

@author: Ellen Wasbo
"""
from __future__ import annotations

import os
from time import ctime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QListWidget, QMessageBox, QFileDialog
    )

# Shield_NM_CT block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    CONFIG_FNAMES, ENV_ICON_PATH
    )
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui.ui_dialogs import ShieldDialog
from Shield_NM_CT.ui.settings_reusables import StackWidget
from Shield_NM_CT.ui import settings_stacks
from Shield_NM_CT.ui import reusable_widgets as uir
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.scripts.mini_methods_format import time_diff_string
# Shield_NM_CT block end


class SettingsDialog(ShieldDialog):
    """GUI setup for the settings dialog window."""

    def __init__(
            self, main, initial_view='User local settings', initial_template_label=''):
        """Initiate Settings dialog.

        Parameters
        ----------
        main : MainWindow
        initial_view : str, optional
            title of widget to select from tree. The default is 'User local settings'.
        initial_template_label : str, optional
            If a preset template on opening. The default is ''.
        """
        super().__init__()
        self.main = main

        self.setWindowTitle('Settings manager')
        self.width1 = round(0.3 * self.main.gui.panel_width)
        self.width2 = round(1.2 * self.main.gui.panel_width)

        hlo = QHBoxLayout()
        self.setLayout(hlo)

        self.tree_settings = QTreeWidget()
        hlo.addWidget(self.tree_settings)
        self.stacked_widget = QStackedWidget()
        hlo.addWidget(self.stacked_widget)

        self.tree_settings.setColumnCount(1)
        self.tree_settings.setFixedWidth(self.width1)
        self.tree_settings.setHeaderHidden(True)
        self.tree_settings.itemClicked.connect(self.change_widget)

        self.stacked_widget.setFixedWidth(self.width2)

        self.list_txt_item_widget = []

        def add_widget(parent=None, snake='', title='', widget=None):
            setattr(self, f'item_{snake}', QTreeWidgetItem([title]))
            item = getattr(self, f'item_{snake}')
            if parent is None:
                self.tree_settings.addTopLevelItem(item)
            else:
                parent.addChild(item)
            setattr(self, f'widget_{snake}', widget)
            this_widget = getattr(self, f'widget_{snake}')
            self.stacked_widget.addWidget(this_widget)
            self.list_txt_item_widget.append((title, item, this_widget))

        add_widget(snake='user_settings', title='Local settings',
                   widget=UserSettingsWidget(self.main))
        add_widget(snake='shared_settings', title='Config folder',
                   widget=SharedSettingsWidget(self.main))
        add_widget(parent=self.item_shared_settings, snake='isotopes',
                   title='Isotopes',
                   widget=settings_stacks.IsotopeWidget(self.main))
        add_widget(parent=self.item_shared_settings, snake='ct_models',
                   title='CT scatter models',
                   widget=settings_stacks.CT_doserateWidget(self.main))
        add_widget(parent=self.item_shared_settings, snake='materials',
                   title='Materials',
                   widget=settings_stacks.MaterialWidget(self.main))
        add_widget(parent=self.item_shared_settings, snake='shield_data',
                   title='Shield data',
                   widget=settings_stacks.ShieldDataWidget(self.main))
        add_widget(parent=self.item_shared_settings, snake='colormaps',
                   title='Color settings',
                   widget=settings_stacks.ColormapSettingsWidget(self.main))

        item, widget = self.get_item_widget_from_txt(initial_view)
        self.tree_settings.setCurrentItem(item)
        self.tree_settings.expandToDepth(2)
        self.tree_settings.resizeColumnToContents(0)
        self.stacked_widget.setCurrentWidget(widget)
        self.previous_selected_txt = initial_view
        self.current_selected_txt = initial_view

        widget.update_from_yaml(initial_template_label=initial_template_label)

    def get_item_widget_from_txt(self, txt):
        """Find tree item and stack widget based on item txt."""
        item = self.list_txt_item_widget[0][1]  # default
        widget = self.list_txt_item_widget[0][2]  # default
        for tiw in self.list_txt_item_widget:
            if tiw[0] == txt:
                item = tiw[1]
                widget = tiw[2]

        return (item, widget)

    def change_widget(self, item):
        """Update visible widget in stack when selection in tree change."""
        prevtxtitem = self.current_selected_txt
        item = self.tree_settings.indexFromItem(item)
        txtitem = item.data(Qt.DisplayRole)

        # Settings changed - saved? Go back to prev if regret leaving unchanged
        _, prev_widget = self.get_item_widget_from_txt(prevtxtitem)
        edited = False
        try:
            edited = getattr(prev_widget, 'edited')
        except AttributeError:
            pass

        proceed = True
        if edited:
            proceed = messageboxes.proceed_question(
                self, 'Proceed and loose unsaved changes?')

        if proceed:
            self.main.start_wait_cursor()
            self.previous_selected_txt = self.current_selected_txt
            self.current_selected_txt = txtitem
            _, new_widget = self.get_item_widget_from_txt(txtitem)
            self.stacked_widget.setCurrentWidget(new_widget)
            new_widget.update_from_yaml()
            self.main.stop_wait_cursor()
        else:
            item, _ = self.get_item_widget_from_txt(
                self.previous_selected_txt)
            self.tree_settings.setCurrentItem(item)

    def closeEvent(self, event):
        """Test if unsaved changes before closing."""
        prevtxtitem = self.current_selected_txt
        _, prev_widget = self.get_item_widget_from_txt(prevtxtitem)
        edited = False
        try:
            edited = getattr(prev_widget, 'edited')
        except AttributeError:
            pass
        if edited:
            reply = QMessageBox.question(
                self, 'Unsaved changes',
                'Close and loose unsaved changes?',
                QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


class UserSettingsWidget(StackWidget):
    """Widget holding user settings."""

    def __init__(self, main):
        """Initiate."""
        header = 'Local settings'
        subtxt = '''Settings specific for the current user.<br>
        To be able to save any other settings, you will need to
        specify a config folder.<br>
        This config folder will hold all other settings and may
        be shared between users.<br>
        From start this may be an empty folder.'''
        super().__init__(main, header, subtxt)

        self.config_folder = QLineEdit()
        self.lbl_user_prefs_path = QLabel()
        self.chk_dark_mode = QCheckBox()
        self.fontsize = QSpinBox()
        self.annotations_linethick = QSpinBox()
        self.annotations_fontsize = QSpinBox()
        self.picker = QSpinBox()
        self.snap_radius = QSpinBox()

        self.vlo.addWidget(self.lbl_user_prefs_path)

        self.config_folder.setMinimumWidth(500)
        hlo_config_folder = QHBoxLayout()
        hlo_config_folder.addWidget(QLabel('Path to config folder:'))
        hlo_config_folder.addWidget(self.config_folder)
        toolbar = uir.ToolBarBrowse('Browse to find or initiate config folder')
        toolbar.act_browse.triggered.connect(
            lambda: self.locate_folder(self.config_folder))
        hlo_config_folder.addWidget(toolbar)
        self.vlo.addLayout(hlo_config_folder)
        self.vlo.addSpacing(50)

        hlo_mid = QHBoxLayout()
        vlo_1 = QVBoxLayout()
        vlo_2 = QVBoxLayout()
        hlo_mid.addLayout(vlo_1)
        hlo_mid.addSpacing(50)
        hlo_mid.addLayout(vlo_2)
        self.vlo.addLayout(hlo_mid)

        gb_gui = QGroupBox('GUI settings ')
        gb_gui.setFont(uir.FontItalic())
        vlo_gui = QVBoxLayout()
        self.fontsize.setRange(5, 15)
        self.fontsize.valueChanged.connect(self.flag_edit)
        hlo_fontsize = QHBoxLayout()
        hlo_fontsize.addWidget(QLabel('Set font size for GUI:'))
        hlo_fontsize.addWidget(self.fontsize)
        vlo_gui.addLayout(hlo_fontsize)
        hlo_dark_mode = QHBoxLayout()
        self.chk_dark_mode.clicked.connect(
            lambda: self.flag_edit(True))
        hlo_dark_mode.addWidget(QLabel('Dark mode'))
        hlo_dark_mode.addWidget(self.chk_dark_mode)
        hlo_dark_mode.addStretch()
        vlo_gui.addLayout(hlo_dark_mode)
        vlo_gui.addWidget(QLabel('Restart to make changes affect GUI.'))
        gb_gui.setLayout(vlo_gui)
        vlo_1.addWidget(gb_gui)

        gb_annot = QGroupBox('Annotation settings for floor map')
        gb_annot.setFont(uir.FontItalic())
        flo_annot = QFormLayout()
        self.annotations_linethick.setRange(5, 100)
        self.annotations_linethick.valueChanged.connect(self.flag_edit)
        flo_annot.addRow(QLabel('Line thickness:'), self.annotations_linethick)
        self.annotations_fontsize.setRange(5, 100)
        self.annotations_fontsize.valueChanged.connect(self.flag_edit)
        flo_annot.addRow(QLabel('Font size:'), self.annotations_fontsize)
        self.picker.setRange(0, 100)
        self.picker.valueChanged.connect(self.flag_edit)
        flo_annot.addRow(QLabel('Picker radius:'), self.picker)
        self.snap_radius.setRange(0, 100)
        self.snap_radius.valueChanged.connect(self.flag_edit)
        flo_annot.addRow(QLabel('Snap radius:'), self.snap_radius)
        gb_annot.setLayout(flo_annot)
        vlo_2.addWidget(gb_annot)

        btn_save_user_prefs = QPushButton('Save user preferences')
        btn_save_user_prefs.setIcon(QIcon(
            f'{os.environ[ENV_ICON_PATH]}save.png'))
        btn_save_user_prefs.clicked.connect(self.save_user)
        if self.main.save_blocked:
            btn_save_user_prefs.setEnabled(False)
        self.vlo.addWidget(btn_save_user_prefs)

        self.vlo.addStretch()

        self.vlo.addWidget(uir.HLine())
        self.vlo.addWidget(self.status_label)

    def update_from_yaml(self, initial_template_label=''):
        """Load settings from yaml and fill form."""
        _, path, self.user_prefs = cff.load_user_prefs()
        self.lbl_user_prefs_path.setText('User preferences saved in: ' + path)
        self.config_folder.setText(self.user_prefs.config_folder)
        self.fontsize.setValue(self.user_prefs.fontsize)
        self.chk_dark_mode.setChecked(self.user_prefs.dark_mode)
        self.annotations_linethick.setValue(self.user_prefs.annotations_linethick)
        self.annotations_fontsize.setValue(self.user_prefs.annotations_fontsize)
        self.picker.setValue(self.user_prefs.picker)
        self.snap_radius.setValue(self.user_prefs.snap_radius)
        self.flag_edit(False)

    def save_user(self):
        """Get current settings and save to yaml file."""
        if self.user_prefs.config_folder != self.config_folder.text():
            cff.remove_user_from_active_users()
        config_folder_changed = (
            self.config_folder.text() != self.user_prefs.config_folder)
        self.user_prefs.config_folder = self.config_folder.text()
        self.user_prefs.fontsize = self.fontsize.value()
        self.user_prefs.dark_mode = self.chk_dark_mode.isChecked()
        self.user_prefs.annotations_linethick = self.annotations_linethick.value()
        self.user_prefs.annotations_fontsize = self.annotations_fontsize.value()
        self.user_prefs.picker = self.picker.value()
        self.user_prefs.snap_radius = self.snap_radius.value()

        status_ok, path = cff.save_user_prefs(self.user_prefs, parentwidget=self)
        if status_ok:
            self.status_label.setText(f'Changes saved to {path}')
            self.flag_edit(False)
            cff.add_user_to_active_users()
            if config_folder_changed:
                self.main.update_general_values()
        else:
            QMessageBox.Warning(self, 'Warning',
                                f'Failed to save changes to {path}')


class SharedSettingsWidget(StackWidget):
    """Widget for shared settings."""

    def __init__(self, main):
        header = 'Config folder - shared settings'
        subtxt = '''Each of the sub-pages will display different settings
         saved in the config folder (specified in user settings).<br>
        Templates and settings will be saved as .yaml files. <br>
        Several users may link to the same config folder and
         share these settings.'''
        super().__init__(main, header, subtxt)
        self.width1 = main.gui.panel_width*0.3
        self.width2 = main.gui.panel_width*1.7

        self.lbl_config_folder = QLabel('-- not defined --')
        self.list_files = QListWidget()

        hlo_cf = QHBoxLayout()
        self.vlo.addLayout(hlo_cf)
        hlo_cf.addWidget(QLabel('Config folder: '))
        hlo_cf.addWidget(self.lbl_config_folder)
        hlo_cf.addStretch()
        btn_locate_config = QPushButton('Locate new or existing config folder')
        btn_locate_config.clicked.connect(self.locate_config)
        self.vlo.addWidget(btn_locate_config)

        if self.main.save_blocked:
            btn_locate_config.setEnabled(False)

        self.vlo.addWidget(self.list_files)

    def update_from_yaml(self, initial_template_label=''):
        """Update settings from yaml file."""
        self.list_files.clear()

        path = cff.get_config_folder()
        if path != '':
            self.lbl_config_folder.setText(path)
            active_users = cff.get_active_users()
            self.list_files.addItem('Active users:')
            for user, lastsession in active_users.items():
                self.list_files.addItem(' '.join(['  ', user, lastsession]))
            self.list_files.addItem('')

            status_ok, path, last_modified = cff.load_settings(fname='last_modified')
            if status_ok:
                for cfn in CONFIG_FNAMES:
                    if cff.get_config_filename(cfn) != '':  # in case deleted
                        try:
                            res = getattr(last_modified, cfn)
                            if len(res) > 0:
                                self.list_files.addItem(cfn + ':')
                                string = ' '.join(
                                    ['    last edited by',
                                     res[0], time_diff_string(res[1]),
                                     '(', ctime(res[1]), ')'])
                                if len(res) > 2:  # with version number
                                    string = string + ' in version ' + res[2]
                                self.list_files.addItem(string)
                        except AttributeError:
                            pass
        else:
            self.lbl_config_folder.setText('-- not defined --')

    def locate_config(self):
        """Browse to config folder."""
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.Directory)
        if dlg.exec():
            config_folder = dlg.selectedFiles()[0]
            self.change_config_user_prefs(config_folder)

    def change_config_user_prefs(self, folder):
        """Save new config folder and update."""
        _, _, user_prefs = cff.load_user_prefs()
        user_prefs.config_folder = os.path.normpath(folder)
        _, _ = cff.save_user_prefs(user_prefs, parentwidget=self)
        self.update_from_yaml()
        self.main.update_general_values()
