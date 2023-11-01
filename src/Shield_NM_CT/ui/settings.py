#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings.

@author: Ellen Wasbo
"""
from __future__ import annotations

import os
from pathlib import Path
from time import ctime
from dataclasses import dataclass, field
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QSpinBox, QCheckBox,
    QListWidget, QMessageBox, QDialogButtonBox, QFileDialog
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
            self, main, initial_view='User local settings', initial_template_label='',
            width1=300, width2=1000, import_review_mode=False):
        """Initiate Settings dialog.

        Parameters
        ----------
        main : MainWindow or ImportMain
            MainWindow if not import review mode
        initial_view : str, optional
            title of widget to select from tree. The default is 'User local settings'.
        initial_template_label : str, optional
            If a preset template on opening. The default is ''.
        width1 : int, optional
            width of tree widget. The default is 200.
        width2 : it, optional
            width of the right panel. The default is 800.
        import_review_mode : bool, optional
            special settings if reviewing settings to import. The default is False.
        """
        super().__init__()
        self.main = main
        self.import_review_mode = import_review_mode
        if import_review_mode is False:
            self.setWindowTitle('Settings manager')
            self.width1 = 0.5 * self.main.gui.panel_width
            self.width2 = self.main.gui.panel_width
        else:
            self.setWindowTitle('Import review - configuration settings')
            self.width1 = width1
            self.width2 = width2

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

        def add_widget(parent=None, snake='', title='', widget=None,
                       exclude_if_empty=True):
            proceed = True
            if import_review_mode and exclude_if_empty:
                if getattr(self.main, snake, {}) == {}:
                    proceed = False
            if proceed:
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

        if import_review_mode is False:
            add_widget(snake='user_settings', title='Local settings',
                       widget=UserSettingsWidget(self))
            add_widget(snake='shared_settings', title='Config folder',
                       widget=SharedSettingsWidget(self))
        else:
            add_widget(snake='shared_settings', title='Settings for import',
                       widget=SharedSettingsImportWidget(self),
                       exclude_if_empty=False)

        add_widget(parent=self.item_shared_settings, snake='isotopes',
                   title='Isotopes',
                   widget=settings_stacks.IsotopeWidget(self))
        add_widget(parent=self.item_shared_settings, snake='materials',
                   title='Materials',
                   widget=settings_stacks.MaterialWidget(self))

        item, widget = self.get_item_widget_from_txt(initial_view)
        self.tree_settings.setCurrentItem(item)
        self.tree_settings.expandToDepth(2)
        self.tree_settings.resizeColumnToContents(0)
        self.stacked_widget.setCurrentWidget(widget)
        self.previous_selected_txt = initial_view
        self.current_selected_txt = initial_view

        if import_review_mode is False:
            widget.update_from_yaml(initial_template_label=initial_template_label)
        else:
            self.update_import_main()

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
            try:
                self.main.start_wait_cursor()
            except AttributeError:
                pass  # if ImportMain not MainWindow
            self.previous_selected_txt = self.current_selected_txt
            self.current_selected_txt = txtitem
            _, new_widget = self.get_item_widget_from_txt(txtitem)
            self.stacked_widget.setCurrentWidget(new_widget)
            if not self.import_review_mode:
                new_widget.update_from_yaml()
            try:
                self.main.stop_wait_cursor()
            except AttributeError:
                pass  # if ImportMain not MainWindow
        else:
            item, _ = self.get_item_widget_from_txt(
                self.previous_selected_txt)
            self.tree_settings.setCurrentItem(item)

    def closeEvent(self, event):
        """Test if unsaved changes before closing."""
        if self.import_review_mode:
            reply = QMessageBox.question(
                self, 'Cancel import?',
                'To finish import go to first page (Settings for import) and '
                'select what to include in the import. Proceed cancel import?',
                QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                event.accept()
            else:
                event.ignore()
        else:
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

    def import_from_yaml(self):
        """Import settings from another config folder."""
        def select_yaml_files_for_import(filenames):
            """Select which files to import from a config_folder."""
            dlg = SelectImportFilesDialog(filenames)
            if dlg.exec():
                filenames = dlg.get_checked_files()
            else:
                filenames = []
            return filenames

        dlg = QFileDialog(self, 'Locate config folder to import settings from')
        dlg.setFileMode(QFileDialog.Directory)
        filenames = []
        if dlg.exec():
            import_folder = dlg.selectedFiles()[0]
            if import_folder == cff.get_config_folder():
                QMessageBox.warning(
                    self, 'Select another folder',
                    'Cannot import from the current config folder.')
            else:
                filenames = [x.stem for x in Path(import_folder).glob('*')
                             if x.suffix == '.yaml']
                acceptable_filenames = [*CONFIG_FNAMES]
                acceptable_filenames.remove('active_users')
                acceptable_filenames.remove('last_modified')
                filenames = [filename for filename in filenames
                             if filename in acceptable_filenames]

                if len(filenames) == 0:
                    QMessageBox.warning(
                        self, 'No template files found',
                        'No template file found in the selected folder.')
                else:
                    filenames = select_yaml_files_for_import(filenames)

        if len(filenames) > 0:
            import_main = ImportMain()
            for fname in filenames:
                _, _, temps = cff.load_settings(
                    fname=fname, temp_config_folder=import_folder)
                setattr(import_main, fname, temps)
            dlg = SettingsDialog(
                import_main, initial_view='Config folder',
                width1=self.width1, width2=self.width2,
                import_review_mode=True)
            res = dlg.exec()
            if res:
                import_main = dlg.get_marked()
                same_names = cff.import_settings(import_main)
                if same_names:
                    QMessageBox.information(
                        self, 'Information',
                        ('Imported one or more templates with same name as '
                         'templates already set. The imported template names '
                         'was marked with _import.'))
                # TODO if later option to import from the different widgets
                # _, widget = self.get_item_widget_from_txt(
                #    self.previous_selected_txt)
                self.widget_shared_settings.update_from_yaml()

    def update_import_main(self):
        """Update templates of all widgets according to import_main.

        Similar to settings_reusables.py - StackWidget def update_from_yaml.
        TODO: syncronize these two better...?
        """
        lists = [fname for fname, item in CONFIG_FNAMES.items()
                      if item['saved_as'] == 'object_list']
        for snake in lists:
            temps = getattr(self.main, snake, {})
            if temps != {}:
                try:
                    widget = getattr(self, f'widget_{snake}')
                    widget.templates = temps
                    try:
                        widget.current_template = temps[widget.current_modality][0]
                        #TODO
                        '''if dependent on others:
                        if snake in [
                                '...']:
                            widget.... = self.main....
                        '''

                        widget.update_data()
                    except IndexError:
                        pass
                except AttributeError:
                    pass

    #TODO - coupled templates when import?
    '''
    def mark_extra(self, widget, label_this, mod):
        """Also mark coupled templates."""
        all_labels = [
            temp.label for temp in widget.templates[mod]]
        if label_this in all_labels:
            idxs = get_all_matches(all_labels, label_this)
            try:
                marked_idxs = widget.marked[mod]
            except AttributeError:
                empty = {}
                for key in QUICKTEST_OPTIONS:
                    empty[key] = []
                widget.marked = empty
                widget.marked_ignore = copy.deepcopy(empty)
                marked_idxs = []
            for idx in idxs:
                if idx not in marked_idxs:
                    marked_idxs.append(idx)
                    if hasattr(widget.templates[mod][idx], 'num_digit_label'):
                        self.mark_digit_temps(widget.templates[mod][idx], mod=mod)
            widget.marked[mod] = marked_idxs

    def mark_digit_temps(self, paramset, mod='CT'):
        """Also mark digit_template when paramset is marked."""
        if paramset.num_digit_label != '':
            widget = self.widget_digit_templates
            self.mark_extra(widget, paramset.num_digit_label, mod)
    '''

    def set_marked(self, marked=True, import_all=False):
        """Set type of marking to ImportMain."""
        self.main.marked = marked
        self.main.import_all = import_all
        self.accept()

    def get_marked(self):
        """Extract marked or not ignored templates and update ImportMain.

        Parameters
        ----------
        marked : bool
            True if import all marked, False if import all but ignored.
        """
        import_main = self.main
        marked = import_main.marked
        import_all = import_main.import_all
        if import_all is False:
            lists = [fname for fname, item in CONFIG_FNAMES.items()
                     if item['saved_as'] == 'object_list']
            for snake in lists:
                object_list = getattr(import_main, snake, None)
                new_objects = []
                try:
                    widget = getattr(self, f'widget_{snake}')
                    object_list = getattr(import_main, snake)
                    marked_this = widget.marked if marked else widget.marked_ignore
                    if marked_this:
                        if len(widget.marked) == 0:
                            setattr(import_main, snake, [])
                        else:
                            indexes = [widget.indexes[i] for i in widget.marked]
                            new_objects = [obj for i, obj in enumerate(object_list)
                                           if i in indexes]
                            setattr(import_main, snake, new_objects)
                    else:
                        if len(widget.marked_ignore) == 0:
                            pass
                        else:
                            ignore_ids = [widget.indexes[i] for i
                                          in widget.marked_ignore]
                            new_objects = [obj for i, obj in enumerate(object_list)
                                           if i not in ignore_ids]
                            setattr(import_main, snake, new_objects)

                except AttributeError:
                    pass  # marked not set

            list_objects = [fname for fname, item in CONFIG_FNAMES.items()
                            if item['saved_as'] == 'object']
            list_objects.remove('last_modified')
            for snake in list_objects:
                proceed = True
                try:
                    widget = getattr(self, f'widget_{snake}')
                except AttributeError:
                    setattr(import_main, snake, None)
                    proceed = False
                if proceed:
                    try:
                        if marked is False and widget.marked_ignore:
                            setattr(import_main, snake, None)
                        elif marked and widget.marked is False:
                            setattr(import_main, snake, None)
                    except AttributeError:  # widget.marked not set
                        if marked:
                            setattr(import_main, snake, None)

        return import_main


class UserSettingsWidget(StackWidget):
    """Widget holding user settings."""

    def __init__(self, dlg_settings):
        """Initiate.

        Parameters
        ----------
        save_blocked : bool
            Block save button if user_preferences.yaml not available.
            Default is False.
        """
        header = 'Local settings'
        subtxt = '''Settings specific for the current user.<br>
        To be able to save any other settings, you will need to
        specify a config folder.<br>
        This config folder will hold all other settings and may
        be shared between users.<br>
        From start this may be an empty folder.'''
        super().__init__(dlg_settings, header, subtxt)

        self.config_folder = QLineEdit()
        self.default_path = QLineEdit()
        self.lbl_user_prefs_path = QLabel()
        self.chk_dark_mode = QCheckBox()
        self.font_size = QSpinBox()

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

        self.default_path.setMinimumWidth(500)
        hlo_default_path = QHBoxLayout()
        hlo_default_path.addWidget(QLabel('Default path for loading/saving projects:'))
        hlo_default_path.addWidget(self.default_path)
        toolbar = uir.ToolBarBrowse('Browse to set default path')
        toolbar.act_browse.triggered.connect(
            lambda: self.locate_folder(self.default_path))
        hlo_default_path.addWidget(toolbar)
        self.vlo.addLayout(hlo_default_path)
        self.vlo.addSpacing(50)

        hlo_mid = QHBoxLayout()
        vlo_1 = QVBoxLayout()
        hlo_mid.addLayout(vlo_1)
        self.vlo.addLayout(hlo_mid)

        gb_gui = QGroupBox('GUI settings')
        gb_gui.setFont(uir.FontItalic())
        vlo_gui = QVBoxLayout()
        self.font_size.setRange(5, 15)
        self.font_size.valueChanged.connect(self.flag_edit)
        hlo_font_size = QHBoxLayout()
        hlo_font_size.addWidget(QLabel('Set font size for GUI:'))
        hlo_font_size.addWidget(self.font_size)
        hlo_font_size.addWidget(QLabel('(Restart to update GUI)'))
        hlo_font_size.addStretch()
        vlo_gui.addLayout(hlo_font_size)
        hlo_dark_mode = QHBoxLayout()
        self.chk_dark_mode.clicked.connect(
            lambda: self.flag_edit(True))
        hlo_dark_mode.addWidget(QLabel('Dark mode'))
        hlo_dark_mode.addWidget(self.chk_dark_mode)
        hlo_dark_mode.addWidget(QLabel('(restart to update)'))
        hlo_dark_mode.addStretch()
        vlo_gui.addLayout(hlo_dark_mode)
        gb_gui.setLayout(vlo_gui)
        vlo_1.addWidget(gb_gui)
        vlo_1.addSpacing(50)

        hlo_mid.addStretch()

        btn_save_user_prefs = QPushButton('Save user preferences')
        btn_save_user_prefs.setIcon(QIcon(
            f'{os.environ[ENV_ICON_PATH]}save.png'))
        btn_save_user_prefs.clicked.connect(self.save_user)
        if self.save_blocked:
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
        self.default_path.setText(self.user_prefs.default_path)
        self.font_size.setValue(self.user_prefs.font_size)
        self.chk_dark_mode.setChecked(self.user_prefs.dark_mode)
        self.flag_edit(False)

    def save_user(self):
        """Get current settings and save to yaml file."""
        if self.user_prefs.config_folder != self.config_folder.text():
            cff.remove_user_from_active_users()
        self.user_prefs.config_folder = self.config_folder.text()
        self.user_prefs.default_path = self.default_path.text()
        self.user_prefs.font_size = self.font_size.value()
        self.user_prefs.dark_mode = self.chk_dark_mode.isChecked()

        status_ok, path = cff.save_user_prefs(self.user_prefs, parentwidget=self)
        if status_ok:
            self.status_label.setText(f'Changes saved to {path}')
            self.flag_edit(False)
            cff.add_user_to_active_users()
        else:
            QMessageBox.Warning(self, 'Warning',
                                f'Failed to save changes to {path}')


class SharedSettingsWidget(StackWidget):
    """Widget for shared settings."""

    def __init__(self, dlg_settings):
        header = 'Config folder - shared settings'
        subtxt = '''Each of the sub-pages will display different settings
         saved in the config folder (specified in user settings).<br>
        Templates and settings will be saved as .yaml files. <br>
        Several users may link to the same config folder and
         share these settings.'''
        super().__init__(dlg_settings, header, subtxt)
        self.width1 = dlg_settings.main.gui.panel_width*0.3
        self.width2 = dlg_settings.main.gui.panel_width*1.7

        self.lbl_config_folder = QLabel('-- not defined --')
        self.list_files = QListWidget()

        hlo_cf = QHBoxLayout()
        self.vlo.addLayout(hlo_cf)
        hlo_cf.addWidget(QLabel('Config folder: '))
        hlo_cf.addWidget(self.lbl_config_folder)
        hlo_cf.addStretch()
        btn_locate_config = QPushButton('Locate new or existing config folder')
        btn_locate_config.clicked.connect(self.locate_config)
        btn_import = QPushButton(
            'Import from another config folder')
        btn_import.clicked.connect(self.dlg_settings.import_from_yaml)
        self.vlo.addWidget(btn_locate_config)
        self.vlo.addWidget(btn_import)

        if self.save_blocked:
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


class SharedSettingsImportWidget(StackWidget):
    """Widget to replace SharedSettingsWidget when import_review_mode."""

    def __init__(self, dlg_settings):
        header = 'Settings for import'
        subtxt = '''Mark templates for import or mark templates to ignore.<br>
        Then get back to this window to import according to your selections.'''
        super().__init__(dlg_settings, header, subtxt)
        btn_all = QPushButton('Import all')
        btn_all_but = QPushButton('Import all except for those marked to ignore')
        btn_marked = QPushButton('Import only marked')
        self.vlo.addWidget(btn_all)
        self.vlo.addWidget(btn_marked)
        self.vlo.addWidget(btn_all_but)
        self.vlo.addStretch()

        header_text = """<html><head/><body>
            <p><span style=\" font-size:20pt;color:gray\"><i>Review mode!</i></span></p>
            </body></html>"""
        info_text = """<html><head/><body>
            <p><span style=\" font-size:14pt;color:gray\"><i>Return to this tab
            (from tree list at your left hand) when you have decided what to include
            and not</i></span></p></body></html>"""
        self.vlo.addWidget(QLabel(header_text))
        self.vlo.addWidget(QLabel(info_text))
        self.vlo.addStretch()

        btn_all.clicked.connect(
            lambda: self.dlg_settings.set_marked(True, import_all=True))
        btn_marked.clicked.connect(
            lambda: self.dlg_settings.set_marked(True))
        btn_all_but.clicked.connect(
            lambda: self.dlg_settings.set_marked(False))


@dataclass
class ImportMain:
    """Class to replace MainWindow + hold imported templates when import_review_mode."""

    save_blocked: bool = True
    marked: bool = True
    include_all: bool = False
    isotopes: list = field(default_factory=list)
    ct_doserates: list = field(default_factory=list)
    shield_data: list = field(default_factory=list)
    materials: list = field(default_factory=list)


class SelectImportFilesDialog(ShieldDialog):
    """Dialog to select files to import from."""

    def __init__(self, filenames):
        super().__init__()
        self.setWindowTitle('Select files to import from')
        vlo = QVBoxLayout()
        self.setLayout(vlo)

        vlo.addWidget(QLabel('Select files to import from'))
        self.list_widget = uir.ListWidgetCheckable(
            texts=filenames,
            set_checked_ids=list(np.arange(len(filenames)))
            )
        vlo.addWidget(self.list_widget)
        self.btn_select_all = QPushButton('Deselect all')
        self.btn_select_all.clicked.connect(self.select_all)
        vlo.addWidget(self.btn_select_all)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        button_box = QDialogButtonBox(buttons)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        vlo.addWidget(button_box)

    def select_all(self):
        """Select or deselect all in list."""
        if self.btn_select_all.text() == 'Deselect all':
            set_state = Qt.Unchecked
            self.btn_select_all.setText('Select all')
        else:
            set_state = Qt.Checked
            self.btn_select_all.setText('Deselect all')

        for i in range(len(self.list_widget.texts)):
            item = self.list_widget.item(i)
            item.setCheckState(set_state)

    def get_checked_files(self):
        """Get list of checked testcode ids."""
        return self.list_widget.get_checked_texts()
