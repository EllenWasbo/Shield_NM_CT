#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User interface for configuration settings -  reusable classes.

@author: Ellen Wasbo
"""
import os
from time import time
import copy
import numpy as np

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QBrush, QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QLabel, QAction,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox, QFileDialog
    )

# Shield_NM_CT block start
from Shield_NM_CT.config.Shield_NM_CT_constants import ENV_ICON_PATH
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui import reusable_widgets as uir
from Shield_NM_CT.ui.ui_dialogs import EditCTdosemapDialog
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.scripts.mini_methods import create_empty_file
from Shield_NM_CT.scripts.mini_methods_format import valid_template_name
# Shield_NM_CT block end


class StackWidget(QWidget):
    """Class for general widget attributes for the stacked widgets."""

    def __init__(self, main=None, header='', subtxt='', temp_alias='template',
                 temp_list=False, editable=True):
        """Initiate StackWidget.

        Parameters
        ----------
        main: MainWindow
        header : str
            header text
        subtxt : str
            info text under header text
        temp_alias : str
            string to set type of data (parameterset or template +?)
            title over labels and used in tooltip
            for the buttons of ModTempSelector
        temp_list : bool
            add TempSelector
        editable : bool
            False = hide toolbar for save/edit + hide edited
        """
        super().__init__()
        self.main = main
        self.temp_alias = temp_alias
        self.temp_list = temp_list
        self.edited = False
        self.lastload = None
        self.templates = None
        self.status_label = QLabel('')

        self.vlo = QVBoxLayout()
        self.setLayout(self.vlo)
        if header != '':
            self.vlo.addWidget(uir.LabelHeader(header, 3))
        if subtxt != '':
            self.vlo.addWidget(uir.LabelItalic(subtxt))
        self.vlo.addWidget(uir.HLine())

        if self.temp_list:
            self.hlo = QHBoxLayout()
            self.vlo.addLayout(self.hlo)
            self.wid_temp_list = TempSelector(self, editable=editable)
            self.hlo.addWidget(self.wid_temp_list)

    def flag_edit(self, flag=True):
        """Indicate some change."""
        if flag:
            self.edited = True
            self.status_label.setText('**Unsaved changes**')
        else:
            self.edited = False
            self.status_label.setText('')

    def update_from_yaml(self, initial_template_label=''):
        """Refresh settings from yaml file."""
        self.lastload = self.main.lastload

        if hasattr(self, 'fname'):
            self.templates = getattr(self.main, self.fname)
            if self.fname == 'shield_data':
                self.lastload_general_values = self.main.lastload
                self.fill_list_sources()

            if self.temp_list:
                if self.fname == 'ct_doserates':
                    self.sag_tab.canvas.CTmap_draw()
                    self.cor_tab.canvas.CTmap_draw()
                self.refresh_templist(selected_label=initial_template_label)
            else:
                self.update_data()

    def refresh_templist(self, selected_id=0, selected_label=''):
        """Update the list of templates, and self.current...

        Parameters
        ----------
        selected_id : int, optional
            index to select in template list. The default is 0.
        selected_label : str, optional
            label to select in template list (override index)
            The default is ''.
        """
        self.current_labels = [obj.label for obj in self.templates]

        if selected_label != '':
            tempno = self.current_labels.index(selected_label)
        else:
            tempno = selected_id
        tempno = max(tempno, 0)
        if tempno > len(self.current_labels)-1:
            tempno = len(self.current_labels)-1

        if len(self.current_labels) == 0:
            self.current_template = copy.deepcopy(self.empty_template)
        else:
            self.update_current_template(selected_id=tempno)

        self.wid_temp_list.list_temps.blockSignals(True)
        self.wid_temp_list.list_temps.clear()
        self.wid_temp_list.list_temps.addItems(self.current_labels)
        self.wid_temp_list.list_temps.setCurrentRow(tempno)
        self.wid_temp_list.list_temps.blockSignals(False)

        self.update_data()

    def update_clicked_template(self):
        """Update data after new template selected (clicked)."""
        if self.edited:
            res = messageboxes.QuestionBox(
                parent=self, title='Save changes?',
                msg='Save changes before changing template?')
            if res.exec():
                self.wid_temp_list.save(label=self.current_template.label)
            else:
                self.flag_edit(False)

        tempno = self.wid_temp_list.list_temps.currentIndex().row()
        self.update_current_template(selected_id=tempno)
        self.update_data()

    def update_current_template(self, selected_id=0):
        """Update self.current_template by label or id."""
        self.current_template = copy.deepcopy(
            self.templates[selected_id])

    def set_empty_template(self):
        """Set default template when last in template list is deleted."""
        self.templates = [copy.deepcopy(self.empty_template)]

    def locate_folder(self, widget):
        """Locate folder and set widget.text() to path.

        Parameters
        ----------
        widget : QLineEdit
            reciever of the path text
        """
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.Directory)
        if widget.text() != '':
            dlg.setDirectory(widget.text())
        if dlg.exec():
            fname = dlg.selectedFiles()
            widget.setText(os.path.normpath(fname[0]))
            self.flag_edit()

    def locate_file(self, widget, title='Locate file',
                    filter_str='All files (*)', opensave=False):
        """Locate file and set widget.text() to path.

        Parameters
        ----------
        widget : QLineEdit
            reciever of the path text
        """
        if opensave:
            fname, _ = QFileDialog.getSaveFileName(
                self, title, widget.text(), filter=filter_str)
            if fname != '':
                create_empty_file(fname, self, proceed=True)
        else:
            fname, _ = QFileDialog.getOpenFileName(
                self, title, widget.text(), filter=filter_str)
        if fname != '':
            widget.setText(os.path.normpath(fname))
        self.flag_edit()

    def get_data(self):
        """Update current_template into templates. Called by save."""
        if (hasattr(self.__class__, 'get_current_template')
            and callable(getattr(
                self.__class__, 'get_current_template'))):
            self.get_current_template()

    def add(self, label):
        """Add empty_template to list."""
        # self.get_data()  # if get_current_template exist
        self.current_template = copy.deepcopy(self.empty_template)
        self.current_template.label = label
        if self.fname == 'ct_doserates':
            dlg = EditCTdosemapDialog()
            res = dlg.exec()
            if res:
                set_template = dlg.template
                if set_template:
                    self.current_template = dlg.template
        if len(self.templates) == 0:
            self.templates = [copy.deepcopy(self.current_template)]
        else:
            if self.templates[0].label == '':
                self.templates[0] = copy.deepcopy(self.current_template)
            else:
                self.templates.append(copy.deepcopy(self.current_template))
        self.save()
        self.refresh_templist(selected_label=label)

    def rename(self, newlabel):
        """Rename selected template."""
        tempno = self.current_labels.index(self.current_template.label)
        self.current_template.label = newlabel
        self.templates[tempno].label = newlabel
        #TODO save more? (related templates see imageQCpy settings_reusables)
        self.save()
        self.refresh_templist(selected_label=newlabel)

    def verify_save(self, fname, lastload):
        """Verify that save is possible and not in conflict with other users."""
        proceed = cff.verify_config_folder(self)
        if proceed:
            proceed, errmsg = cff.check_save_conflict(fname, lastload)
            if errmsg != '':
                proceed = messageboxes.proceed_question(self, errmsg)
        return proceed

    def save(self, save_more=False, more=None, more_fnames=None, log=[]):
        """Save template and other connected templates if needed.

        Parameters
        ----------
        save_more : bool, optional
            Connected templates to be saved exist. The default is False.
        more : list of templates, optional
            Connected templates to save. The default is None.
        more_fnames : list of str, optional
            fnames of connected templates. The default is None.
        log : list of str, optional
            Log from process of connected templates. The default is [].
        """
        proceed = cff.verify_config_folder(self)
        if proceed:
            templates = self.templates
            proceed, errmsg = cff.check_save_conflict(self.fname, self.lastload)
            if errmsg != '':
                proceed = messageboxes.proceed_question(self, errmsg)
            if proceed:
                ok_save, path = cff.save_settings(templates, fname=self.fname)
                if ok_save:
                    if save_more:
                        ok_save = []
                        for i, more_fname in enumerate(more_fnames):
                            proceed, errmsg = cff.check_save_conflict(
                                more_fname, self.lastload)
                            if errmsg != '':
                                proceed = messageboxes.proceed_question(self, errmsg)
                            if proceed:
                                ok_save_this, path = cff.save_settings(
                                    more[i], fname=more_fname)
                                ok_save.append(ok_save_this)
                        if len(ok_save) > 0:
                            if all(ok_save):
                                dlg = messageboxes.MessageBoxWithDetails(
                                    self, title='Updated related templates',
                                    msg=('Related templates also updated. '
                                         'See details to view changes performed'),
                                    details=log, icon=QMessageBox.Information)
                                dlg.exec()

                    self.status_label.setText(
                        f'Changes saved to {path}')
                    self.flag_edit(False)
                    self.lastload = time()
                else:
                    QMessageBox.warning(
                        self, 'Failed saving', f'Failed saving to {path}')


class TempSelector(QWidget):
    """Widget with list of templates and toolbar."""

    def __init__(self, parent, editable=True):
        super().__init__()
        self.parent = parent
        self.setFixedWidth(400)

        self.vlo = QVBoxLayout()
        self.setLayout(self.vlo)
        self.vlo_top = QVBoxLayout()
        self.vlo.addLayout(self.vlo_top)

        self.vlo.addWidget(uir.LabelItalic(self.parent.temp_alias.title()+'s'))
        hlo_list = QHBoxLayout()
        self.vlo.addLayout(hlo_list)
        self.list_temps = QListWidget()
        self.list_temps.currentItemChanged.connect(self.parent.update_clicked_template)
        hlo_list.addWidget(self.list_temps)

        if editable:
            self.toolbar = QToolBar()
            self.toolbar.setOrientation(Qt.Vertical)
            hlo_list.addWidget(self.toolbar)
            self.act_clear = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}clear.png'),
                'Clear ' + self.parent.temp_alias + ' (reset to default)', self)
            self.act_clear.triggered.connect(self.clear)
            self.act_add = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}add.png'),
                'Add current values as new ' + self.parent.temp_alias, self)
            self.act_add.triggered.connect(self.add)
            self.act_save = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}save.png'),
                'Save current values to ' + self.parent.temp_alias, self)
            self.act_save.triggered.connect(self.save)
            self.act_rename = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}rename.png'),
                'Rename ' + self.parent.temp_alias, self)
            self.act_rename.triggered.connect(self.rename)
            self.act_up = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}moveUp.png'),
                'Move up', self)
            self.act_up.triggered.connect(self.move_up)
            self.act_down = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}moveDown.png'),
                'Move down', self)
            self.act_down.triggered.connect(self.move_down)
            self.act_delete = QAction(
                QIcon(f'{os.environ[ENV_ICON_PATH]}delete.png'),
                'Delete ' + self.parent.temp_alias, self)
            self.act_delete.triggered.connect(self.delete)

            if self.parent.main.save_blocked:
                self.act_clear.setEnabled(False)
                self.act_add.setEnabled(False)
                self.act_save.setEnabled(False)
                self.act_rename.setEnabled(False)
                self.act_up.setEnabled(False)
                self.act_down.setEnabled(False)
                self.act_delete.setEnabled(False)

            self.toolbar.addActions(
                [self.act_clear, self.act_add, self.act_save,
                 self.act_rename, self.act_up,
                 self.act_down, self.act_delete])

    def keyPressEvent(self, event):
        """Accept Delete and arrow up/down key on list templates."""
        if event.key() == Qt.Key_Delete:
            self.delete()
        else:
            super().keyPressEvent(event)

    def clear(self):
        """Clear template - set like empty_template."""
        try:
            self.parent.clear()
        except AttributeError:
            try:
                lbl = self.parent.current_template.label
                self.parent.current_template = copy.deepcopy(
                    self.parent.empty_template)
                self.parent.current_template.label = lbl
                self.parent.update_data()
                self.parent.flag_edit(True)
            except AttributeError:
                print('Missing empty template (method clear in ModTempSelector)')

    def add(self):
        """Add new template to list. Ask for new name and verify."""
        text, proceed = QInputDialog.getText(
            self, 'New name',
            'Name the new ' + self.parent.temp_alias + '                      ')
        # todo also ask if add as current or as empty
        text = valid_template_name(text)
        if proceed and text != '':
            if text in self.parent.current_labels:
                QMessageBox.warning(
                    self, 'Name already in use',
                    'This name is already in use.')
            else:
                self.parent.add(text)
        if self.parent.fname == 'digit_templates':
            self.parent.edit_template()

    def save(self, label=None):
        """Save button pressed or specific save on label."""
        if self.parent.current_template.label == '':
            self.add()
        else:
            if label is False or label is None:
                idx = self.list_temps.currentIndex().row()
            else:
                idx = self.parent.current_labels.index(label)
            self.parent.get_data()  # if get_current_template exist
            self.parent.templates[idx] = copy.deepcopy(
                self.parent.current_template)
            self.parent.save()

    def rename(self):
        """Rename current template. Ask for new name and verify."""
        if self.parent.current_labels[0] == '':
            QMessageBox.warning(
                self, 'Empty list',
                'No template to rename.')
        else:
            proceed = True
            if self.parent.fname != 'shield_data':
                if self.parent.edited:
                    res = messageboxes.QuestionBox(
                        parent=self, title='Rename edited?',
                        msg='''Selected template has changed.
                        Save changes before rename?''',
                        yes_text='Yes',
                        no_text='Cancel')
                    if res.exec():
                        self.save()
                    else:
                        proceed = False

            if proceed:
                sel = self.list_temps.currentItem()
                if sel is not None:
                    current_text = sel.text()

                    text, proceed = QInputDialog.getText(
                        self, 'New name',
                        'Rename ' + self.parent.temp_alias + '                      ',
                        text=current_text)
                    text = valid_template_name(text)
                    if proceed and text != '' and current_text != text:
                        if text in self.parent.current_labels:
                            QMessageBox.warning(
                                self, 'Name already in use',
                                'This name is already in use.')
                        else:
                            self.parent.rename(text)

    def move_up(self):
        """Move template up if possible."""
        row = self.list_temps.currentRow()
        if row > 0:
            popped_temp = self.parent.templates.pop(row)
            self.parent.templates.insert(row - 1, popped_temp)
            self.parent.save()
            self.parent.refresh_templist(selected_id=row-1)

    def move_down(self):
        """Move template down if possible."""
        row = self.list_temps.currentRow()
        if row < len(self.parent.current_labels)-1:
            popped_temp = self.parent.templates.pop(row)
            self.parent.templates.insert(row + 1, popped_temp)
            self.parent.save()
            self.parent.refresh_templist(selected_id=row+1)

    def delete(self, confirmed=False):
        """Delete template."""
        if self.parent.current_labels[0] == '':
            QMessageBox.warning(
                self, 'Empty list',
                'No template to delete.')
        else:
            res = QMessageBox.question(
                self, 'Delete?', f'Delete selected {self.parent.temp_alias}?',
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if res == QMessageBox.Yes:
                confirmed = True
            if confirmed:
                self.parent.delete()
