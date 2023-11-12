# -*- coding: utf-8 -*-
"""User interface for tabs of main window in Shield_NM_CT.

@author: EllenWasbo
"""
import os
import numpy as np
import copy
import pandas as pd

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QItemSelectionModel
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableWidget, QPushButton, QLabel, QDoubleSpinBox, QCheckBox, QComboBox,
    QAction, QToolBar, QMessageBox, QFileDialog
    )
from matplotlib.patches import Rectangle

# Shield_NM_CT block start
from Shield_NM_CT.config.Shield_NM_CT_constants import ENV_ICON_PATH
from Shield_NM_CT.ui import messageboxes
import Shield_NM_CT.ui.reusable_widgets as uir
import Shield_NM_CT.resources
# Shield_NM_CT block end


class TableToolBar(QToolBar):
    """Toolbar connected to the tables defining areas,walls and sources."""

    def __init__(self, table):
        super().__init__()

        self.setOrientation(Qt.Vertical)

        act_delete = QAction('Delete', self)
        act_delete.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}delete.png'))
        act_delete.setToolTip('Delete selected row (Del)')
        act_delete.triggered.connect(table.delete_row)

        act_add = QAction('Add', self)
        act_add.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}add.png'))
        act_add.setToolTip('Add new row after selected row (+)')
        act_add.triggered.connect(table.add_row)

        act_duplicate = QAction('Duplicate', self)
        act_duplicate.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}duplicate.png'))
        act_duplicate.setToolTip('Duplicate')
        act_duplicate.triggered.connect(table.duplicate_row)

        act_export = QAction('Export CSV', self)
        act_export.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}fileCSV.png'))
        act_export.setToolTip('Export table to CSV')
        act_export.triggered.connect(lambda: table.export_csv())

        act_import = QAction('Import CSV', self)
        act_import.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}import.png'))
        act_import.setToolTip('Import table from CSV')
        act_import.triggered.connect(lambda: table.import_csv())

        self.addActions([act_delete, act_add, act_duplicate, act_export, act_import])


class InputTab(QWidget):
    """Common GUI for input tabs."""

    def __init__(self, header='', info='', btn_get_pos_text='Get pos from figure'):
        super().__init__()
        self.cellwidget_is_text = False

        self.vlo = QVBoxLayout()
        self.setLayout(self.vlo)
        self.vlo.addWidget(uir.LabelHeader(header, 4))
        self.btn_get_pos = QPushButton(f'   {btn_get_pos_text}   (Enter \u23ce)')
        self.btn_get_pos.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}selectArrow.png'))
        self.btn_get_pos.setStyleSheet('border-color: #6e94c0; border-width: 4px;')
        hlo_push = QHBoxLayout()
        self.hlo_extra = QHBoxLayout()  # for additional widgets before info
        hlo_push.addWidget(self.btn_get_pos)
        hlo_push.addLayout(self.hlo_extra)
        if info != '':
            hlo_push.addSpacing(20)
            hlo_push.addWidget(uir.InfoTool(info, parent=self))
        hlo_push.addStretch()
        self.vlo.addLayout(hlo_push)
        self.btn_get_pos.clicked.connect(self.get_pos)
        self.hlo = QHBoxLayout()
        self.vlo.addLayout(self.hlo)
        self.table = QTableWidget(1, 3)
        self.table.verticalHeader().setVisible(False)
        self.table.setMinimumHeight(500)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        #self.table.currentCellChanged.connect(self.cell_selection_changed)

        self.table_list = []
        # table as list for easy access for computations, import/export
        self.active_row = -1

        try:
            self.tb = TableToolBar(self)
        except AttributeError:  # Scale missing methods as toolbar hidden
            self.tb = QToolBar(self)
        self.hlo.addWidget(self.tb)
        self.hlo.addWidget(self.table)

    def cell_changed(self, row, col, decimals=None):
        """Value changed by user input."""
        value = self.get_cell_value(row, col)
        if decimals:
            value = round(value, decimals)
        self.table_list[row][col] = value
        if col != 1:  # name
            if self.label == 'Areas':
                self.update_occ_map()
            elif 'source' in self.label or 'point' in self.label:
                self.update_current_source_annotation()
            self.main.reset_dose()

    def get_pos(self):
        """Get positions for element as defined in figure.

        Assume point - or override this function.
        """
        if self.active_row > -1:
            text = (f'{self.main.gui.x1:.0f}, {self.main.gui.y1:.0f}')
            tabitem = self.table.cellWidget(self.active_row, 2)
            tabitem.setText(text)
            self.table_list[self.active_row][2] = text
            self.update_source_annotations()
            self.main.reset_dose()

    def update_current_source_annotation(self):
        """Update annotations for active source."""
        tabitem = self.table.cellWidget(self.active_row, 2)
        x, y = self.get_pos_from_text(tabitem.text())

        canvas = self.main.wFloorDisplay.canvas
        line_index = None
        for i, line in enumerate(canvas.ax.lines):
            gid = line.get_gid()
            gid_split = gid.split('_')
            if len(gid_split) == 2:
                try:
                    row = int(gid_split[1])
                    if row == self.active_row and gid_split[0] == self.modality:
                        line_index = i
                        break
                except ValueError:
                    pass

        if line_index is None:  # add
            if x is not None:
                canvas.ax.plot(
                    x, y, 'bo',
                    markersize=self.main.gui.annotations_markersize[0],
                    markeredgecolor='red', markeredgewidth=0,
                    picker=self.main.gui.picker,
                    gid=f'{self.modality}_{i}')
                if self.modality == 'CT':
                    canvas.ax.lines[-1].set_marker(
                        canvas.CT_marker(self.table_list[i][5])[0])
                    canvas.set_CT_marker_properties(-1)
                self.highlight_selected_in_image()
        else:  # update
            if self.modality == 'CT':
                canvas.ax.lines[line_index].set_marker(
                    canvas.CT_marker(self.table_list[self.active_row][5])[0])
                canvas.set_CT_marker_properties(line_index)
            if x is not None:
                canvas.ax.lines[line_index].set_data(x, y)
            else:
                canvas.ax.lines[line_index].remove()
            canvas.draw_idle()

    def update_source_annotations(self, all_sources=True, modalities=[]):
        """Update annotations for sources.

        Parameters
        ----------
        all_sources : bool, optional
            If true generate all annotations, else only active. The default is True.
        modalities : list of str
            'NM', 'CT'
        """
        canvas = self.main.wFloorDisplay.canvas
        index_lines = []
        gid_indexes = []
        if len(canvas.ax.lines) > 0:
            for i, line in enumerate(canvas.ax.lines):
                gid = line.get_gid()
                gid_split = gid.split('_')
                if len(gid_split) == 2:
                    try:
                        row = int(gid_split[1])
                        index_lines.append(i)
                        gid_indexes.append(row)
                    except ValueError:
                        pass

        if all_sources:
            modalities = ['NM', 'CT']
        else:
            if len(modalities) == 0:
                modalities = [self.modality]

        # remove all present source-annotations
        if len(index_lines) > 0:
            index_lines.reverse()
            for i in index_lines:
                canvas.ax.lines[i].remove()
        canvas.reset_hover_pick()

        for tab_no in range(self.main.tabs.count()):
            proceed = False
            w = self.main.tabs.widget(tab_no)
            if hasattr(w, 'modality'):
                if w.modality in modalities:
                    proceed = True
            if proceed:
                for i in range(w.table.rowCount()):
                    if w.table_list[i][0]:  # if active
                        tabitem = w.table.cellWidget(i, 2)
                        x, y = w.get_pos_from_text(tabitem.text())
                        if x is not None:
                            canvas.ax.plot(
                                x, y, 'bo',
                                markersize=w.main.gui.annotations_markersize[0],
                                markeredgecolor='red', markeredgewidth=0,
                                picker=w.main.gui.picker,
                                gid=f'{w.modality}_{i}')
                            if w.modality == 'CT':
                                canvas.ax.lines[-1].set_marker(
                                    canvas.CT_marker(w.table_list[i][5])[0])
                                canvas.set_CT_marker_properties(-1)

        self.highlight_selected_in_image()

    def highlight_selected_in_image(self):
        """Highlight source position in image if positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x, y = self.get_pos_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.sourcepos_highlight()
        else:
            self.main.wFloorDisplay.canvas.draw_idle()  # in case of previous changes

    def select_row_col(self, row, col):
        """Set focus on selected row and col."""
        index = self.table.model().index(row, col)
        self.table.selectionModel().select(
            index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        self.active_row = row

    def cell_selection_changed(self, row, col):
        """Cell widget got focus. Change active row and highlight."""
        w = self.table.cellWidget(row, col)
        if isinstance(w, uir.TextCell):
            self.cellwidget_is_text = True
        else:
            self.cellwidget_is_text = False
        self.select_row_col(row, col)
        try:
            self.highlight_selected_in_image()
        except AttributeError:
            pass

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
                if self.label == 'Areas':
                    self.update_occ_map()
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

    def get_cell_value(self, row, col):
        """Set value of cell depending on type of widget in cell."""
        w = self.table.cellWidget(row, col)
        if hasattr(w, 'setChecked'):
            content = w.isChecked()
        elif hasattr(w, 'setText'):
            content = w.text()
        elif hasattr(w, 'setValue'):
            content = w.value()
        else:
            content = None

        return content

    def get_pos_from_text(self, text):
        """Get coordinate string as coordinates.

        Parameters
        ----------
        text : str
            "x, y"

        Returns
        -------
        x : int
        y : int
            as for coords for Rectangle
        """
        coords = text.split(', ')
        if len(coords) == 2:
            x = int(coords[0])
            y = int(coords[1])
        else:
            x = None
            y = None

        return (x, y)

    def get_table_as_list(self):
        """Get table as list."""
        datalist = []
        if self.table.rowCount() > 0:
            columnHeaders = []
            for j in range(self.table.model().columnCount()):
                columnHeaders.append(self.table.horizontalHeaderItem(j).text())
            datalist.append(columnHeaders)

            for row in range(self.table.rowCount()):
                datarow = []
                for col in range(self.table.columnCount()):
                    w = self.table.cellWidget(row, col)
                    if hasattr(w, 'setChecked'):
                        datarow.append(w.isChecked())
                    elif hasattr(w, 'setText'):
                        datarow.append(w.text())
                    elif hasattr(w, 'setValue'):
                        val = round(w.value(), w.decimals())
                        datarow.append(val)

                    else:
                        datarow.append('')
                datalist.append(datarow)

        return datalist

    def export_csv(self, path=''):
        """Export table to csv."""
        if path == '':
            fname = QFileDialog.getSaveFileName(
                self, 'Save table', filter="CSV file (*.csv)")
            path = fname[0]

        if len(path) > 0:
            datalist = self.get_table_as_list()
            if len(datalist) > 0:
                df = pd.DataFrame(datalist[1:], columns=datalist[0])
                df.to_csv(path, sep=self.main.general_values.csv_separator,
                          decimal=self.main.general_values.csv_decimal)

    def import_csv(self, path='', ncols_expected=5):
        """Import table from csv."""
        if path == '':
            fname = QFileDialog.getOpenFileName(
                self, 'Import table', filter="CSV file (*.csv)")
            path = fname[0]

        if len(path) > 0:
            df = pd.read_csv(path, sep=self.main.general_values.csv_separator,
                             decimal=self.main.general_values.csv_decimal)
            df = df.fillna('')

            nrows, ncols = df.shape
            if ncols != ncols_expected:
                pass  # TODO - ask for other separator, decimal, active ignored
            else:
                self.table.setRowCount(0)
                self.table_list = []

                for row in range(nrows):
                    self.table.insertRow(row)
                    self.table_list.append(copy.deepcopy(self.empty_row))
                    self.add_cell_widgets(row)
                    for col in range(1, ncols):
                        w = self.table.cellWidget(row, col - 1)
                        w.blockSignals(True)
                        if hasattr(w, 'setChecked'):
                            val = bool(df.iat[row, col])
                            w.setChecked(val)
                        elif hasattr(w, 'setText'):
                            val = str(df.iat[row, col])
                            w.setText(val)
                        elif hasattr(w, 'setValue'):
                            val = float(df.iat[row, col])
                            w.setValue(val)
                        else:
                            val = ''
                        self.table_list[row][col - 1] = val
                        w.blockSignals(False)


class ScaleTab(InputTab):
    """GUI for scaling floor plan."""

    def __init__(self, main):
        super().__init__(
            header='Scale floor plan',
            info=(
                'Draw line of known length in floor plan'
                ' (click, drag, release).<br>'
                'Press the "Get..."-button to fetch the positions of the line.<br>'
                'Set the actual length of this line to calibrate'
                ' the scale of the floor plan.'
                ),
            btn_get_pos_text='Get scale coordinates as marked in image')

        self.label = 'Scale'
        self.main = main
        self.c0 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c0.editingFinished.connect(lambda: self.main.reset_dose(floor=0))
        self.c1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c1.editingFinished.connect(lambda: self.main.reset_dose(floor=1))
        self.c2 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c2.editingFinished.connect(lambda: self.main.reset_dose(floor=2))
        self.h0 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h0.editingFinished.connect(lambda: self.main.reset_dose(floor=1))
        self.h1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h1.editingFinished.connect(lambda: self.main.reset_dose(floor=2))

        self.shield_mm_above = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_above.editingFinished.connect(
            lambda: self.main.reset_dose(floor=2))
        self.shield_material_above = QComboBox()
        self.shield_material_above.currentTextChanged.connect(
            lambda: self.main.reset_dose(floor=2))
        self.shield_mm_below = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_below.editingFinished.connect(
            lambda: self.main.reset_dose(floor=0))
        self.shield_material_below = QComboBox()
        self.shield_material_below.currentTextChanged.connect(
            lambda: self.main.reset_dose(floor=0))

        self.tb.setVisible(False)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(
            ['Line positions x0,y0,x1,y1', 'Actual length (m)'])
        self.empty_row = ['', 0.0]
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 40*self.main.gui.char_width)
        self.table.setColumnWidth(1, 25*self.main.gui.char_width)
        self.add_cell_widgets(0)
        self.table.setMinimumHeight(100)

        self.vlo.addWidget(uir.LabelHeader('Floor heights', 4))
        hlo_heights = QHBoxLayout()
        self.vlo.addLayout(hlo_heights)
        img_lbl = QLabel()
        im = QPixmap(':/icons/heights.png')
        img_lbl.setPixmap(im)
        hlo_heights.addWidget(img_lbl)
        vlo_heights = QVBoxLayout()
        hlo_heights.addLayout(vlo_heights)
        flo = QFormLayout()
        vlo_heights.addLayout(flo)
        flo.addRow(QLabel('Floor height H1 (m)'), self.h1)
        flo.addRow(QLabel('Floor height H0 below (m)'), self.h0)
        flo.addRow(QLabel('Source height above floor C1 (m)'), self.c1)
        flo.addRow(QLabel('Calculation height floor above C2 (m)'), self.c2)
        flo.addRow(QLabel('Calculation height floor below C0 (m)'), self.c0)
        vlo_heights.addSpacing(20)
        flo1 = QFormLayout()
        vlo_heights.addLayout(flo1)
        flo1.addRow(QLabel('Shield thickness floor above (mm)'),
                    self.shield_mm_above)
        flo1.addRow(QLabel('Shield material floor above'),
                    self.shield_material_above)
        flo1.addRow(QLabel('Shield thickness floor below (mm)'),
                    self.shield_mm_below)
        flo1.addRow(QLabel('Shield material floor below'),
                    self.shield_material_below)

        self.vlo.addStretch()

        self.update_heights()
        self.update_material_lists(first=True)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.TextCell(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.CellSpinBox(
            self, row=row, col=1, max_val=200., step=1.0, decimals=3))

    def get_pos(self):
        """Get line positions as defined in figure."""
        if self.main.gui.x1 + self.main.gui.y1 > 0:
            text = (
                f'{self.main.gui.x0:.0f}, '
                f'{self.main.gui.y0:.0f}, '
                f'{self.main.gui.x1:.0f}, '
                f'{self.main.gui.y1:.0f}'
                )
            tabitem = self.table.cellWidget(0, 0)
            tabitem.setText(text)
            self.main.gui.scale_start = (
                self.main.gui.x0, self.main.gui.y0)
            self.main.gui.scale_end = (
                self.main.gui.x1, self.main.gui.y1)
            if self.main.gui.calibration_factor:
                self.update_scale()

    def get_scale_from_text(self, text):
        """Get coordinate string for scale.

        Parameters
        ----------
        text : str
            "x0, y0, x1, y1"

        Returns
        -------
        x0 : int
        y0 : int
        x1 : int
        y1 : int
            as for coords for scale
        """
        coords = text.split(', ')
        if len(coords) == 4:
            x0 = int(coords[0])
            y0 = int(coords[1])
            x1 = int(coords[2])
            y1 = int(coords[3])
        else:
            x0 = 0
            y0 = 0
            x1 = 0
            y1 = 0

        return (x0, y0, x1, y1)

    def update_scale(self):
        """Update calibration factor."""
        tabitem = self.table.cellWidget(0, 0)
        x0, y0, x1, y1 = self.get_scale_from_text(tabitem.text())
        lineLen = np.sqrt((x1-x0)**2 + (y1-y0)**2)
        self.main.gui.calibration_factor = (
            self.main.gui.scale_length / lineLen)
        self.main.wFloorDisplay.canvas.add_scale_highlight(
            x0, y0, x1, y1)
        self.main.CTsources_tab.update_source_annotations()
        # TODO self.main.update_dose()

    def update_heights(self):
        """Update floor heights."""
        self.blockSignals(True)
        self.c0.setValue(self.main.general_values.c0)
        self.c1.setValue(self.main.general_values.c1)
        self.c2.setValue(self.main.general_values.c2)
        self.h0.setValue(self.main.general_values.h0)
        self.h1.setValue(self.main.general_values.h1)
        self.shield_mm_above.setValue(self.main.general_values.shield_mm_above)
        self.shield_mm_below.setValue(self.main.general_values.shield_mm_below)
        self.blockSignals(False)

    def update_material_lists(self, first=False):
        """Update selectable lists."""
        self.material_strings = self.main.general_values.materials
        if first:
            prev_above = self.main.general_values.shield_material_above
            prev_below = self.main.general_values.shield_material_below
        else:
            prev_above = self.shield_material_above.currentText()
            prev_below = self.shield_material_below.currentText()
        warnings = []
        self.blockSignals(True)
        self.shield_material_above.clear()
        self.shield_material_above.addItems(self.material_strings)
        if prev_above in self.material_strings:
            self.shield_material_above.setCurrentText(prev_above)
        else:
            self.shield_material_above.setCurrentText(self.material_strings[0])
            warnings.append(f'Shield material of floor above ({prev_above}) no longer '
                            'available. Please control selected material.')
        self.shield_material_below.clear()
        self.shield_material_below.addItems(self.material_strings)
        if prev_below in self.material_strings:
            self.shield_material_below.setCurrentText(prev_below)
        else:
            self.shield_material_below.setCurrentText(self.material_strings[0])
            warnings.append(f'Shield material of floor below ({prev_below}) no longer '
                            'available. Please control selected material.')
        self.blockSignals(False)
        if warnings:
            dlg = messageboxes.MessageBoxWithDetails(
                self, title='Warnings',
                msg='Found issues for selected materials',
                info='See details',
                icon=QMessageBox.Warning,
                details=warnings)
            dlg.exec()

    def cell_changed(self, row, col, decimals=None):
        """Value changed by user input."""
        value = self.get_cell_value(0, 1)
        if decimals:
            value = round(value, decimals)
        self.main.gui.scale_length = value
        self.update_scale()


class AreasTab(InputTab):
    """GUI for adding/editing areas to define occupancy factors."""

    def __init__(self, main):
        super().__init__(
            header='Areas - for occupancy factors',
            info=(
                'Mark areas to set the occupancy factor other than default 1.0.<br>'
                'Mark an area in the floor plan'
                ' (click, drag, release).<br>'
                'Select the row for which you want to set this area.<br>'
                'Press the "Get..."-button to fetch the positions of the area.<br>'
                'Set the occupancy factor for the area.'
                ),
            btn_get_pos_text='Get area as marked in image')

        self.label = 'Areas'
        self.main = main
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Area name', 'x0,y0,x1,y1', 'Occupancy factor'])
        self.empty_row = [True, '', '', 1.]
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 30*self.main.gui.char_width)
        self.table.setColumnWidth(2, 30*self.main.gui.char_width)
        self.table.setColumnWidth(3, 30*self.main.gui.char_width)
        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.InputCheckBox(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.TextCell(self, row=row, col=1))
        self.table.setCellWidget(row, 2, uir.TextCell(self, row=row, col=2))
        self.table.setCellWidget(row, 3, uir.CellSpinBox(
            self, initial_value=1., min_val=0., max_val=1., row=row, col=3))

    def get_pos(self):
        """Get positions for element as defined in figure."""
        text = (
            f'{self.main.gui.x0:.0f}, '
            f'{self.main.gui.y0:.0f}, '
            f'{self.main.gui.x1:.0f}, '
            f'{self.main.gui.y1:.0f}'
            )
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            tabitem.setText(text)
        self.table_list[self.active_row][2] = text
        self.highlight_selected_in_image()
        self.update_occ_map()

    def get_area_from_text(self, text):
        """Get coordinate string for area as area.

        Parameters
        ----------
        text : str
            "x0, y0, x1, y1"

        Returns
        -------
        x0 : int
        y0 : int
        width : int
        height : int
            as for coords for Rectangle
        """
        coords = text.split(', ')
        if len(coords) == 4:
            x0 = int(coords[0])
            y0 = int(coords[1])
            width = int(coords[2]) - x0
            height = int(coords[3]) - y0
        else:
            x0 = 0
            y0 = 0
            width = 1
            height = 1

        return (x0, y0, width, height)

    def highlight_selected_in_image(self):
        """Highlight area in image if area positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x0, y0, width, height = self.get_area_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.add_area_highlight(
                x0, y0, width, height)

    def update_occ_map(self):
        """Update array containing occupation factors and redraw."""
        # reset occ_map, rectangle annotations and related parameters
        self.main.occ_map = np.ones(self.main.image.shape[0:2])
        if len(self.main.wFloorDisplay.canvas.ax.patches) > 0:
            index_patches = []
            for i, patch in enumerate(self.main.wFloorDisplay.canvas.ax.patches):
                index_patches.append(i)
            if len(index_patches) > 0:
                index_patches.reverse()
                for i in index_patches:
                    self.main.wFloorDisplay.canvas.ax.patches[i].remove()
        self.main.wFloorDisplay.canvas.reset_hover_pick()

        areas_this = []
        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x0, y0, width, height = self.get_area_from_text(tabitem.text())
                self.main.occ_map[y0:y0+height, x0:x0+width] = self.table_list[i][3]
                areas_this.append(Rectangle(
                    (x0, y0), width, height, edgecolor='blue',
                    linewidth=self.main.gui.annotations_linethick, fill=False,
                    picker=True, gid=f'{i}'))
                self.main.wFloorDisplay.canvas.ax.add_patch(areas_this[-1])
        self.main.wFloorDisplay.canvas.image_overlay.set_data(self.main.occ_map)
        self.main.wFloorDisplay.canvas.image_overlay.set(
            cmap='rainbow', alpha=self.main.gui.alpha_overlay, clim=(0., 1.))
        self.main.wFloorDisplay.canvas.draw_idle()

    def delete_row(self):
        """Delete selected row."""
        removed_row = super().delete_row()
        if removed_row > -1:
            self.update_occ_map()

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        added_row : int
            index of the new row
        """
        added_row = super().add_row()
        if added_row > -1:
            self.add_cell_widgets(added_row)
        return added_row

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        added_row = self.add_row()
        if added_row > -1:
            values_above = self.table_list[added_row - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(True)

            self.table.cellWidget(added_row, 0).setChecked(values_above[0])
            self.table.cellWidget(added_row, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(added_row, 2).setText(values_above[2])
            self.table.cellWidget(added_row, 3).setValue(float(values_above[3]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(False)
            self.update_row_number(added_row, 1)

            self.select_row_col(added_row, 1)
            self.table_list[added_row] = copy.deepcopy(values_above)


class WallsTab(InputTab):
    """GUI for adding/editing walls."""

    def __init__(self, main):
        super().__init__(
            header='Walls',
            info=(
                'Draw a line for a shielded wall in the floor plan'
                ' (click, drag, release).<br>'
                'Select the row for which you want to set these positions.<br>'
                'Press the "Get..."-button to fetch the positions of the line.<br>'
                'Define shielding material and thickness.<br>'
                'The "Rectify" option (default on) will automatically adjust the wall '
                'coordinates to horizontal or vertical when added.<br>'
                'To keep the wall oblique, deselect "Rectify".'
                ),
            btn_get_pos_text='Get wall coordinates as marked in image')
        self.rectify = QCheckBox("Rectify")
        self.rectify.setChecked(True)
        self.hlo_extra.addWidget(self.rectify)

        self.label = 'Walls'
        self.main = main
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Wall name', 'x0,y0,x1,y1', 'Material', 'Thickness (mm)'])
        self.empty_row = [True, '', '', 'Lead', 0.0]
        self.material_strings = self.main.general_values.materials
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 30*self.main.gui.char_width)
        self.table.setColumnWidth(2, 30*self.main.gui.char_width)
        self.table.setColumnWidth(3, 30*self.main.gui.char_width)
        self.table.setColumnWidth(4, 30*self.main.gui.char_width)
        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.InputCheckBox(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.TextCell(self, row=row, col=1))
        self.table.setCellWidget(row, 2, uir.TextCell(self, row=row, col=2))
        self.table.setCellWidget(row, 3, uir.CellCombo(
            self, self.material_strings, row=row, col=3))
        self.table.setCellWidget(row, 4, uir.CellSpinBox(
            self, row=row, col=4, max_val=400., step=1.0))

    def update_materials(self):
        """Update ComboBox of all rows when list of materials changed in settings."""
        self.material_strings = self.main.general_values.materials
        warnings = []
        self.blockSignals(True)
        for row in range(self.table.rowCount()):
            prev_val = self.get_cell_value(row, 3)
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.material_strings, row=row, col=3))
            w = self.table.cellWidget(row, 3)
            if prev_val in self.material_strings:
                w.setText(prev_val)
            else:
                if prev_val is not None:
                    warnings.append(
                        f'Material ({prev_val}) no longer available. '
                        f'Please control material of walls row number {row}.')
        self.blockSignals(False)
        if warnings:
            dlg = messageboxes.MessageBoxWithDetails(
                self, title='Warnings',
                msg='Found issues for selected materials',
                info='See details',
                icon=QMessageBox.Warning,
                details=warnings)
            dlg.exec()

    def get_pos(self):
        """Get positions for element as defined in figure."""
        if self.active_row > -1:
            text = (
                f'{self.main.gui.x0:.0f}, '
                f'{self.main.gui.y0:.0f}, '
                f'{self.main.gui.x1:.0f}, '
                f'{self.main.gui.y1:.0f}'
                )
            tabitem = self.table.cellWidget(self.active_row, 2)
            tabitem.setText(text)
            self.table_list[self.active_row][2] = text
            self.update_wall_annotations()
            self.main.reset_dose()

    def get_wall_from_text(self, text):
        """Get coordinate string for wall.

        Parameters
        ----------
        text : str
            "x0, y0, x1, y1"

        Returns
        -------
        x0 : int
        y0 : int
        x1 : int
        y1 : int
            as for coords for wall
        """
        coords = text.split(', ')
        if len(coords) == 4:
            x0 = int(coords[0])
            y0 = int(coords[1])
            x1 = int(coords[2])
            y1 = int(coords[3])
        else:
            x0 = 0
            y0 = 0
            x1 = 0
            y1 = 0

        return (x0, y0, x1, y1)

    def update_wall_annotations(self):
        """Update annotations for walls."""
        canvas = self.main.wFloorDisplay.canvas
        index_lines = []
        gid_indexes = []
        if len(canvas.ax.lines) > 0:
            for i, line in enumerate(canvas.ax.lines):
                try:
                    row = int(line.get_gid())
                    index_lines.append(i)
                    gid_indexes.append(row)
                except ValueError:
                    pass

        # remove all present wall annotations
        if len(index_lines) > 0:
            index_lines.reverse()
            for i in index_lines:
                canvas.ax.lines[i].remove()
        canvas.reset_hover_pick()

        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x0, y0, x1, y1 = self.get_wall_from_text(tabitem.text())
                canvas.ax.plot(
                    [x0, x1], [y0, y1], 'bo-', fillstyle='none',
                    linewidth=self.main.gui.annotations_linethick,
                    markersize=self.main.gui.annotations_markersize[0],
                    markeredgecolor='blue', markeredgewidth=0,
                    picker=self.main.gui.picker,
                    gid=f'{i}')

        self.highlight_selected_in_image()

    def highlight_selected_in_image(self):
        """Highlight area in image if area positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x0, y0, x1, y1 = self.get_wall_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.wall_highlight()

    def delete_row(self):
        """Delete selected row."""
        removed_row = super().delete_row()
        if removed_row > -1:
            pass
            # TODO:self.main.update_dose()

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        added_row : int
            index of the new row
        """
        added_row = super().add_row()
        if added_row > -1:
            self.add_cell_widgets(added_row)
            # TODO: if not duplicate_row calling: self.main.update_dose()
        return added_row

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        added_row = self.add_row()
        if added_row > -1:
            values_above = self.table_list[added_row - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(True)

            self.table.cellWidget(added_row, 0).setChecked(values_above[0])
            self.table.cellWidget(added_row, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(added_row, 2).setText(values_above[2])
            self.table.cellWidget(added_row, 3).setCurrentText(values_above[3])
            self.table.cellWidget(added_row, 3).setValue(float(values_above[3]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(False)
            self.update_row_number(added_row, 1)

            self.select_row_col(added_row, 1)
            self.table_list[added_row] = copy.deepcopy(values_above)


class NMsourcesTab(InputTab):
    """GUI for adding/editing NM sources."""

    def __init__(self, main):
        super().__init__(
            header='NM sources - radioactive sources',
            info=(
                'Select position of source in floor plan (mouse click).<br>'
                'Select the row for which you want to set this source position.<br>'
                'Press the "Get..."-button to fetch the coordinates.<br>'
                '<br>'
                'Specify parameters for the sources:<br>'
                '   - A0 = activity at start (t0)<br>'
                '   - t1 = when activity reaches this position (hours after t0)<br>'
                '   - duration = duration of activity at this position (hours)<br>'
                '   - Rest void = rest fraction after voiding<br>'
                '   - # pr workday = average number of procedures pr working day. '
                'Dose multiplied with number of working days specified above.'
                ),
            btn_get_pos_text='Get source coordinates as marked in image')

        self.modality = 'NM'
        self.label = f'{self.modality} sources'
        self.main = main
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Source name', 'x,y', 'Isotope', 'In patient',
             'A0 (MBq)', 't1 (hours)', 'Duration (hours)', 'Rest void',
             '# pr workday'])
        self.empty_row = [True, '', '', 'F-18', True, 0.0, 0.0, 0.0, 1.0, 0.0]
        self.isotope_strings = [x.label for x in self.main.isotopes]
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 25*self.main.gui.char_width)
        self.table.setColumnWidth(2, 15*self.main.gui.char_width)
        self.table.setColumnWidth(3, 13*self.main.gui.char_width)
        self.table.setColumnWidth(4, 13*self.main.gui.char_width)
        self.table.setColumnWidth(5, 13*self.main.gui.char_width)
        self.table.setColumnWidth(6, 13*self.main.gui.char_width)
        self.table.setColumnWidth(7, 20*self.main.gui.char_width)
        self.table.setColumnWidth(8, 13*self.main.gui.char_width)
        self.table.setColumnWidth(9, 17*self.main.gui.char_width)

        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.InputCheckBox(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.TextCell(self, row=row, col=1))
        self.table.setCellWidget(row, 2, uir.TextCell(self, row=row, col=2))
        self.table.setCellWidget(row, 3, uir.CellCombo(
            self, self.isotope_strings, row=row, col=3))
        self.table.setCellWidget(row, 4, uir.InputCheckBox(self, row=row, col=4))
        self.table.setCellWidget(row, 5, uir.CellSpinBox(
            self, row=row, col=5, max_val=100000, step=10, decimals=0))
        self.table.setCellWidget(row, 6, uir.CellSpinBox(
            self, row=row, col=6, max_val=1000, step=0.1, decimals=1))
        self.table.setCellWidget(row, 7, uir.CellSpinBox(
            self, row=row, col=7, max_val=100, step=0.1, decimals=1))
        self.table.setCellWidget(row, 8, uir.CellSpinBox(
            self, initial_value=1., row=row, col=8))
        self.table.setCellWidget(row, 9, uir.CellSpinBox(
            self, row=row, col=9, max_val=100, step=1, decimals=1))

    def update_isotopes(self):
        """Update ComboBox of all rows when list of isotopes changed in settings."""
        self.isotope_strings = [x.label for x in self.main.isotopes]
        for row in range(self.table.rowCount()):
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.isotope_strings, row=row, col=3))

    def update_NM_dose(self, update_row=None):
        """Update array containing NM dose and redraw."""
        # if update_row specific only update this else calculate all (when import)
        # apply wall shielding for each source
        # now sum
        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x, y = self.get_pos_from_text(tabitem.text())
                # TODO ....
        self.main.wFloorDisplay.canvas.floor_draw()

    def delete_row(self):
        """Delete selected row."""
        removed_row = super().delete_row()
        if removed_row > -1:
            self.update_source_annotations()

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        added_row : int
            index of the new row
        """
        added_row = super().add_row()
        if added_row > -1:
            self.add_cell_widgets(added_row)
            # TODO: update floor display
        return added_row

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        added_row = self.add_row()
        if added_row > -1:
            values_above = self.table_list[added_row - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(True)

            self.table.cellWidget(added_row, 0).setChecked(values_above[0])
            self.table.cellWidget(added_row, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(added_row, 2).setText(values_above[2])
            self.table.cellWidget(added_row, 3).setCurrentText(values_above[3])
            self.table.cellWidget(added_row, 4).setChecked(values_above[4])
            self.table.cellWidget(added_row, 5).setValue(float(values_above[5]))
            self.table.cellWidget(added_row, 6).setValue(float(values_above[6]))
            self.table.cellWidget(added_row, 7).setValue(float(values_above[7]))
            self.table.cellWidget(added_row, 8).setValue(float(values_above[8]))
            self.table.cellWidget(added_row, 9).setValue(int(values_above[9]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(False)
            self.update_row_number(added_row, 1)

            self.select_row_col(added_row, 1)
            self.table_list[added_row] = copy.deepcopy(values_above)
            # TODO: change label to one not used yet
            # TODO: update floor display


class CTsourcesTab(InputTab):
    """GUI for adding/editing NM sources."""

    def __init__(self, main):
        super().__init__(
            header='CT sources',
            info=(
                'For stray radiation using coronal and sagittal doserate map.<br>'
                '(Use "kV sources" if isotropic stray radiation.)<br>'
                '<br>'
                'Select position of source in floor plan (mouse click).<br>'
                'Select the row for which you want to set this source position.<br>'
                'Press the "Get..."-button to fetch the coordinates.<br>'
                '<br>'
                'Specify parameters for the sources:<br>'
                '   - kV source = Select named kV-source as defined in Settings - '
                'Shield Data<br>'
                '   - Doserate map'
                '   - Rotation = rotation of CT footprint, 0 = gantry up on screen<br>'
                '   - kVp correction = if CT dosemap defined for max kVp, you may '
                'correct by a effective factor if kVp generally lower<br>'
                '   - mAs pr patient = total mAs on average pr CT examination<br>'
                '   - # pr workday = average number of procedures pr working day. '
                'Dose multiplied with number of working days specified above.'
                ),
            btn_get_pos_text='Get source coordinates as marked in image')

        self.modality = 'CT'
        self.label = f'{self.modality} sources'
        self.main = main
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Source name', 'x,y', 'kV source', 'Doserate map',
             'Rotation', 'kVp correction', 'mAs pr patient', '# pr workday'])
        self.empty_row = [True, '', '', self.main.general_values.kV_sources[0],
                          'Siemens Edge 140 kVp', 0, 1.0, 4000, 0.0]
        self.kV_source_strings = self.main.general_values.kV_sources
        self.ct_doserate_strings = [x.label for x in self.main.ct_doserates]
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 20*self.main.gui.char_width)
        self.table.setColumnWidth(2, 13*self.main.gui.char_width)
        self.table.setColumnWidth(3, 20*self.main.gui.char_width)
        self.table.setColumnWidth(4, 25*self.main.gui.char_width)
        self.table.setColumnWidth(5, 13*self.main.gui.char_width)
        self.table.setColumnWidth(6, 19*self.main.gui.char_width)
        self.table.setColumnWidth(7, 19*self.main.gui.char_width)
        self.table.setColumnWidth(8, 19*self.main.gui.char_width)

        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.InputCheckBox(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.TextCell(self, row=row, col=1))  # name
        self.table.setCellWidget(row, 2, uir.TextCell(self, row=row, col=2))  # x,y
        self.table.setCellWidget(row, 3, uir.CellCombo(
            self, self.kV_source_strings, row=row, col=3))  # kV source
        self.table.setCellWidget(row, 4, uir.CellCombo(
            self, self.ct_doserate_strings, row=row, col=4))  # doserate map
        self.table.setCellWidget(row, 5, uir.CellSpinBox(
            self, row=row, col=5, min_val=-360, max_val=360,
            step=45, decimals=0))  # rot
        self.table.setCellWidget(row, 6, uir.CellSpinBox(
            self, initial_value=1.,
            row=row, col=6, max_val=1.0, step=0.1, decimals=2))  # kVp corr
        self.table.setCellWidget(row, 7, uir.CellSpinBox(
            self, initial_value=4000, row=row, col=7,
            max_val=10000, step=100, decimals=0))  # mAs pr pat
        self.table.setCellWidget(row, 8, uir.CellSpinBox(
            self, initial_value=30, row=row, col=8, decimals=0))  # pr workday

    def update_kV_sources(self):
        """Update ComboBox of all rows when list of kV_sources changed from settings."""
        self.kV_source_strings = [x.label for x in self.main.general_values.kV_sources]
        for row in range(self.table.rowCount()):
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.kV_source_strings, row=row, col=3))

    def update_CT_dose(self, update_row=None):
        """Update array containing CT dose and redraw."""
        # if update_row specific only update this else calculate all (when import)
        # apply wall shielding for each source
        # now sum
        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x, y = self.get_pos_from_text(tabitem.text())
                # TODO ....
        self.main.wFloorDisplay.canvas.floor_draw()

    def delete_row(self):
        """Delete selected row."""
        removed_row = super().delete_row()
        if removed_row > -1:
            self.update_source_annotations()

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        added_row : int
            index of the new row
        """
        added_row = super().add_row()
        if added_row > -1:
            self.add_cell_widgets(added_row)
            # TODO: update floor display
        return added_row

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        added_row = self.add_row()
        if added_row > -1:
            values_above = self.table_list[added_row - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(True)

            self.table.cellWidget(added_row, 0).setChecked(values_above[0])
            self.table.cellWidget(added_row, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(added_row, 2).setText(values_above[2])
            self.table.cellWidget(added_row, 3).setCurrentText(values_above[3])
            self.table.cellWidget(added_row, 4).setCurrentText(values_above[4])
            self.table.cellWidget(added_row, 5).setValue(int(values_above[5]))
            self.table.cellWidget(added_row, 6).setValue(float(values_above[6]))
            self.table.cellWidget(added_row, 7).setValue(int(values_above[7]))
            self.table.cellWidget(added_row, 8).setValue(int(values_above[8]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(False)
            self.update_row_number(added_row, 1)

            self.select_row_col(added_row, 1)
            self.table_list[added_row] = copy.deepcopy(values_above)
            # TODO: change label to one not used yet
            # TODO: update floor display
