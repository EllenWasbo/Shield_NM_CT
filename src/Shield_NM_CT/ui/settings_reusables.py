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
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.scripts.mini_methods import create_empty_file
from Shield_NM_CT.scripts.mini_methods_format import valid_template_name
# Shield_NM_CT block end


class StackWidget(QWidget):
    """Class for general widget attributes for the stacked widgets."""

    def __init__(self, dlg_settings=None, header='', subtxt='', temp_alias='template',
                 temp_list=False, editable=True):
        """Initiate StackWidget.

        Parameters
        ----------
        dlg_settings: QDialog
            parent of stackWidget
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
        self.dlg_settings = dlg_settings
        self.temp_alias = temp_alias
        self.temp_list = temp_list
        self.edited = False
        self.lastload = None
        self.templates = None
        try:
            self.import_review_mode = self.dlg_settings.import_review_mode
            self.save_blocked = self.dlg_settings.main.save_blocked
        except AttributeError:
            self.import_review_mode = False
            self.save_blocked = False
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
            self.wid_temp_list = TempSelector(
                self, editable=editable, import_review_mode=self.import_review_mode)
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
        self.lastload = time()

        if hasattr(self, 'fname'):
            _, _, self.templates = cff.load_settings(fname=self.fname)
            # TODO: load also connected templates and fill lists?
            '''
            if 'patterns' in self.fname or self.fname == 'auto_templates':
                _, _, self.tag_infos = cff.load_settings(fname='tag_infos')

            if self.fname in ['auto_templates', 'auto_vendor_templates']:
                _, _, self.limits_and_plot_templates = cff.load_settings(
                    fname='limits_and_plot_templates')
                self.fill_list_limits_and_plot()
            '''

            if self.temp_list:
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
        if self.import_review_mode:
            self.refresh_templist_icons()
        else:
            self.wid_temp_list.list_temps.addItems(self.current_labels)
        self.wid_temp_list.list_temps.setCurrentRow(tempno)
        self.wid_temp_list.list_temps.blockSignals(False)

        self.update_data()

    def refresh_templist_icons(self):
        """Set green if marked for import and red if marked for ignore.

        Used if import review mode.
        """
        if hasattr(self, 'marked'):
            current_marked = self.marked[self.current_modality]
            current_ignore = self.marked_ignore[self.current_modality]
        else:
            current_marked = []
            current_ignore = []

        for i, label in enumerate(self.current_labels):
            if i in current_marked:
                icon = QIcon(f'{os.environ[ENV_ICON_PATH]}ok.png')
            elif i in current_ignore:
                icon = QIcon(f'{os.environ[ENV_ICON_PATH]}deleteRed.png')
            else:
                icon = QIcon()

            self.wid_temp_list.list_temps.addItem(QListWidgetItem(icon, label))

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
        if len(self.templates) == 0:
            self.templates = [copy.deepcopy(self.current_template)]
        else:
            if self.templates[0].label == '':
                self.templates[0] = copy.deepcopy(self.current_template)
            else:
                self.templates.append(copy.deepcopy(self.current_template))
        self.save()
        self.refresh_templist(selected_label=label)

    def duplicate(self, selected_id, new_label):
        """Duplicated template.

        Parameters
        ----------
        selected_id : int
            template number in list to duplicate
        new_label : str
            verified label of new template
        """
        self.templates.append(copy.deepcopy(self.templates[selected_id]))
        self.templates[-1].label = new_label
        self.save()
        self.refresh_templist(selected_label=new_label)

    def rename(self, newlabel):
        """Rename selected template."""
        tempno = self.current_labels.index(self.current_template.label)
        oldlabel = self.templates[self.current_modality][tempno].label
        self.current_template.label = newlabel
        self.templates[tempno].label = newlabel

        save_more = False
        more = None
        more_fnames = None
        log = []
        #TODO save more?
        '''
        if self.fname in ['paramsets', 'quicktest_templates',
                          'limits_and_plot_templates']:
            if self.fname in ['limits_and_plot_templates']:
                if self.current_template.type_vendor:
                    more_fnames = ['auto_vendor_templates']
                else:
                    more_fnames = ['auto_templates']
            else:
                more_fnames = ['auto_templates']
            for more_fname in more_fnames:
                _, path, auto_templates = cff.load_settings(fname=more_fname)

                if path != '':
                    if self.fname == 'paramsets':
                        ref_attr = 'paramset_label'
                    elif self.fname == 'quicktest_templates':
                        ref_attr = 'quicktemp_label'
                    elif self.fname == 'limits_and_plot_templates':
                        ref_attr = 'limits_and_plot_label'
                    temp_auto = cff.get_ref_label_used_in_auto_templates(
                        auto_templates, ref_attr=ref_attr)
                    _, temp_labels = np.array(temp_auto[mod]).T.tolist()
                    changed = False

                    if oldlabel in temp_labels:
                        for i, temp in enumerate(temp_labels):
                            if temp == oldlabel:
                                setattr(auto_templates[mod][i], ref_attr, newlabel)
                                changed = True

                    if changed:
                        log.append(
                            f'{self.fname[:-1]} {oldlabel} used in {more_fname}. '
                            'Label updated.')
                        save_more = True
                        if more is None:
                            more = [auto_templates]
                        else:
                            more.append(auto_templates)

        elif self.fname == 'digit_templates':
            more_fname = f'paramsets_{mod}'
            more_fnames = [more_fname]
            _, path, paramsets = cff.load_settings(fname=more_fname)

            if path != '':
                digit_labels_used = [temp.num_digit_label for temp in paramsets]

                changed = False
                if oldlabel in digit_labels_used:
                    for i, temp in enumerate(digit_labels_used):
                        if temp == oldlabel:
                            paramsets[i].num_digit_label = newlabel
                            changed = True

                if changed:
                    log.append(
                        f'{self.fname[:-1]} {oldlabel} used in paramsets. '
                        'Label updated.')
                    save_more = True
                    more = [auto_templates]
        '''
        self.save(save_more=save_more, more=more,
                  more_fnames=more_fnames, log=log)
        self.refresh_templist(selected_label=newlabel)

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
        def ct_doserates_tolist(templates):
            for key, templist in templates.items():
                for tempno, temp in enumerate(templist):
                    for imgno, img in enumerate(temp.images):
                        if isinstance(img, np.ndarray):  # to list to save to yaml
                            templates[key][tempno].images[imgno] = img.tolist()

        proceed = cff.verify_config_folder(self)
        if proceed:
            templates = self.templates
            proceed, errmsg = cff.check_save_conflict(self.fname, self.lastload)
            if errmsg != '':
                proceed = messageboxes.proceed_question(self, errmsg)
            if proceed:
                if self.fname == 'ct_doserates':
                    ct_doserates_tolist(templates)
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

    def __init__(self, parent, editable=True, import_review_mode=False):
        super().__init__()
        self.parent = parent
        self.setFixedWidth(400)

        self.vlo = QVBoxLayout()
        self.setLayout(self.vlo)
        self.vlo.addWidget(uir.LabelItalic(self.parent.temp_alias.title()+'s'))
        hlo_list = QHBoxLayout()
        self.vlo.addLayout(hlo_list)
        self.list_temps = QListWidget()
        self.list_temps.currentItemChanged.connect(self.parent.update_clicked_template)
        hlo_list.addWidget(self.list_temps)

        if import_review_mode:
            self.toolbar = ToolBarImportIgnore(self, temp_alias=self.parent.temp_alias)
            hlo_list.addWidget(self.toolbar)
        else:
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
                self.act_duplicate = QAction(
                    QIcon(f'{os.environ[ENV_ICON_PATH]}duplicate.png'),
                    'Duplicate ' + self.parent.temp_alias, self)
                self.act_duplicate.triggered.connect(self.duplicate)
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

                if self.parent.save_blocked:
                    self.act_clear.setEnabled(False)
                    self.act_add.setEnabled(False)
                    self.act_save.setEnabled(False)
                    self.act_duplicate.setEnabled(False)
                    self.act_rename.setEnabled(False)
                    self.act_up.setEnabled(False)
                    self.act_down.setEnabled(False)
                    self.act_delete.setEnabled(False)

                self.toolbar.addActions(
                    [self.act_clear, self.act_add, self.act_save, self.act_duplicate,
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

    def duplicate(self):
        """Duplicate template."""
        if self.parent.current_labels[0] == '':
            QMessageBox.warning(
                self, 'Empty list',
                'No template to duplicate.')
        else:
            proceed = True
            if self.parent.edited:
                res = messageboxes.QuestionBox(
                    parent=self, title='Duplicate or add edited?',
                    msg='''Selected template has changed.
                    Add with current parameters or duplicate original?''',
                    yes_text='Add new with current parameter',
                    no_text='Duplicate original')
                if res.exec():
                    self.add()
                    proceed = False

            if proceed:  # duplicate original
                sel = self.list_temps.currentItem()
                current_text = sel.text()
                duplicate_id = self.parent.current_labels.index(current_text)

                text, proceed = QInputDialog.getText(
                    self, 'New name',
                    'Name the new ' + self.parent.temp_alias + '                      ',
                    text=f'{current_text}_')
                text = valid_template_name(text)
                if proceed and text != '':
                    if text in self.parent.current_labels:
                        QMessageBox.warning(
                            self, 'Name already in use',
                            'This name is already in use.')
                    else:
                        self.parent.duplicate(duplicate_id, text)

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
            qtext = ''
            if hasattr(self.parent, 'list_used_in'):
                if self.parent.list_used_in.count() > 0:
                    qtext = ' and all links to automation templates'

            if confirmed is False:
                res = QMessageBox.question(
                    self, 'Delete?', f'Delete selected template{qtext}?',
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if res == QMessageBox.Yes:
                    confirmed = True
            if confirmed:
                row = self.list_temps.currentRow()
                if row < len(self.parent.current_labels):
                    self.parent.templates.pop(row)
                    if len(self.parent.templates) == 0:
                        self.parent.set_empty_template()

                    # also reset link to auto_templates
                    if qtext != '':
                        type_vendor = False
                        if self.parent.fname == 'limits_and_plot_templates':
                            type_vendor = self.parent.current_template.type_vendor
                        if type_vendor:
                            auto_labels = [
                                self.parent.list_used_in.item(i).text() for i
                                in range(self.parent.list_used_in.count())]
                            for temp in self.parent.auto_vendor_templates[
                                    self.parent.current_modality]:
                                if temp.label in auto_labels:
                                    temp.limits_and_plot_label = ''
                            auto_widget =\
                                self.parent.dlg_settings.widget_auto_vendor_templates
                            auto_widget.templates = copy.deepcopy(
                                self.parent.auto_vendor_templates)
                        else:
                            auto_labels = [
                                self.parent.list_used_in.item(i).text() for i
                                in range(self.parent.list_used_in.count())]
                            for temp in self.parent.auto_templates[
                                    self.parent.current_modality]:
                                if temp.label in auto_labels:
                                    if self.parent.fname == 'quicktest_templates':
                                        temp.quicktemp_label = ''
                                    elif self.parent.fname == 'limits_and_plot_templates':
                                        temp.limits_and_plot_label = ''
                                    else:
                                        temp.paramset_label = ''
                            auto_widget = self.parent.dlg_settings.widget_auto_templates
                            auto_widget.templates = copy.deepcopy(
                                self.parent.auto_templates)

                        auto_widget.lastload = self.parent.lastload
                        auto_widget.save()

                    self.parent.save()
                    self.parent.refresh_templist(selected_id=row-1)

    def mark_import(self, ignore=False):
        """If import review mode: Mark template for import or ignore."""
        if not hasattr(self.parent, 'marked'):  # initiate
            empty = []
            self.parent.marked_ignore = empty
            self.parent.marked = copy.deepcopy(empty)

        row = self.list_temps.currentRow()
        if ignore:
            if row not in self.parent.marked_ignore:
                self.parent.marked_ignore.append(row)
            if row in self.parent.marked:
                self.parent.marked.remove(row)
        else:
            if row not in self.parent.marked:
                self.parent.marked.append(row)
            if row in self.parent.marked_ignore:
                self.parent.marked_ignore.remove(row)

        self.parent.refresh_templist(selected_id=row)


class ToolBarImportIgnore(QToolBar):
    """Toolbar with import or ignore buttons for import mode of dlg_settings."""

    def __init__(self, parent, temp_alias='template', orientation=Qt.Vertical):
        """Initiate toolbar.

        Parameters
        ----------
        parent: widget with class method 'mark_import'
        temp_alias : str
            string to set type of data (parameterset or template)
        orientation: Qt.Vertical/Horizontal
            Default is Qt.Vertical
        """
        super().__init__()
        self.setOrientation(orientation)
        self.act_import = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}ok.png'),
            'Mark ' + temp_alias + ' for import', parent)
        self.act_import.triggered.connect(parent.mark_import)
        self.act_ignore = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}deleteRed.png'),
            'Mark ' + temp_alias + ' to ignore', parent)
        self.act_ignore.triggered.connect(
            lambda: parent.mark_import(ignore=True))

        self.addActions([self.act_import, self.act_ignore])