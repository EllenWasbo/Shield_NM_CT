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
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    ENV_ICON_PATH, MARKER_STYLE)
from Shield_NM_CT.ui import messageboxes
import Shield_NM_CT.ui.reusable_widgets as uir
from Shield_NM_CT.scripts import mini_methods
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

        self.act_duplicate = QAction('Duplicate', self)
        self.act_duplicate.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}duplicate.png'))
        self.act_duplicate.setToolTip('Duplicate')
        self.act_duplicate.triggered.connect(table.duplicate_row)

        act_export = QAction('Export CSV', self)
        act_export.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}fileCSV.png'))
        act_export.setToolTip('Export table to CSV')
        act_export.triggered.connect(lambda: table.export_csv())

        act_import = QAction('Import CSV', self)
        act_import.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}import.png'))
        act_import.setToolTip('Import table from CSV')
        act_import.triggered.connect(lambda: table.import_csv())

        self.addActions([
            act_delete, act_add, self.act_duplicate, act_export, act_import])


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
                if self.main.dose_dict:
                    self.main.sum_dose_days()
            elif self.label == 'Walls':
                if col == 3:  # material label
                    # set default material thickness?
                    # curr_thickness = self.get_cell_value(row, 4)
                    w = self.table.cellWidget(row, 4)
                    thickness = self.get_default_thickness_from_material(value)
                    w.blockSignals(True)  # avoid update annotations twice
                    w.setValue(thickness)
                    self.table_list[row][4] = thickness
                    w.blockSignals(False)
                self.update_wall_annotation(row, remove_already=True)
                self.highlight_selected_in_image()
                if self.main.dose_dict:
                    self.main.reset_dose()  # TODO or calculate dose?
            elif 'source' in self.label:
                self.update_current_source_annotation()
                if self.main.dose_dict:
                    print(f'calculate row {row}')
                    self.main.calculate_dose(source_number=row, modality=self.modality)
            elif self.label == 'point':
                self.update_current_source_annotation()
                if self.main.dose_dict:
                    self.main.sum_dose_days()

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
        x, y = mini_methods.get_pos_from_text(tabitem.text())

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
                    x, y, markersize=self.main.gui.annotations_markersize[0],
                    markeredgewidth=1, picker=self.main.gui.picker,
                    gid=f'{self.modality}_{line_index}',
                    **MARKER_STYLE[self.modality])
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

    def remove_source_annotations(self, all_sources=True, modalities=[]):
        """Remove annotations for sources.

        Parameters
        ----------
        all_sources : bool, optional
            If true remove all source annotations. The default is True.
        modalities : list of str
            specifiec modalities to remove annotations for.
        """
        if all_sources:
            modalities = ['NM', 'CT', 'OT', 'point']
        else:
            if len(modalities) == 0:
                modalities = [self.modality]

        canvas = self.main.wFloorDisplay.canvas
        index_lines = []
        if len(canvas.ax.lines) > 0:
            for i, line in enumerate(canvas.ax.lines):
                gid = line.get_gid()
                gid_split = gid.split('_')
                if len(gid_split) == 2:
                    if gid_split[0] in modalities:
                        try:
                            index_lines.append(i)
                        except ValueError:
                            pass
        # remove all present source-annotations
        if len(index_lines) > 0:
            index_lines.reverse()
            for i in index_lines:
                canvas.ax.lines[i].remove()
        canvas.reset_hover_pick()

    def update_source_annotations(self, all_sources=True, modalities=[]):
        """Update annotations for sources.

        Parameters
        ----------
        all_sources : bool, optional
            If true generate all annotations, else only specific. The default is True.
        modalities : list of str
            'NM', 'CT'
        """
        canvas = self.main.wFloorDisplay.canvas

        if all_sources:
            modalities = ['NM', 'CT', 'OT', 'point']
        else:
            if len(modalities) == 0:
                modalities = [self.modality]
        self.remove_source_annotations(all_sources=all_sources, modalities=modalities)

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
                        x, y = mini_methods.get_pos_from_text(tabitem.text())
                        if x is not None:
                            canvas.ax.plot(
                                x, y, **MARKER_STYLE[w.modality],
                                markersize=w.main.gui.annotations_markersize[0],
                                markeredgewidth=1,
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
            try:
                x, y = mini_methods.get_pos_from_text(tabitem.text())
                self.main.wFloorDisplay.canvas.sourcepos_highlight()
            except AttributeError:
                pass
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
        elif hasattr(w, 'setCurrentText'):
            content = w.currentText()
        elif hasattr(w, 'setValue'):
            content = w.value()
        else:
            content = None

        return content

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
                    elif hasattr(w, 'setCurrentText'):
                        datarow.append(w.currentText())
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
                        elif hasattr(w, 'setCurrentText'):
                            val = str(df.iat[row, col])
                            w.setCurrentText(val)
                        elif hasattr(w, 'setValue'):
                            val = float(df.iat[row, col])
                            w.setValue(val)
                        else:
                            val = ''
                        self.table_list[row][col - 1] = val
                        w.blockSignals(False)
                self.select_row_col(0, 0)


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
        self.c0.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='c0'))
        self.c1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c1.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='c1'))
        self.c2 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c2.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='c2'))
        self.h0 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h0.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='h0'))
        self.h1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h1.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='h1'))

        self.shield_mm_above = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_above.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='shield_mm_above'))
        self.shield_material_above = QComboBox()
        self.shield_material_above.currentTextChanged.connect(
            lambda: self.param_changed_from_gui(attribute='shield_material_above'))
        self.shield_mm_below = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_below.editingFinished.connect(
            lambda: self.param_changed_from_gui(attribute='shield_mm_below'))
        self.shield_material_below = QComboBox()
        self.shield_material_below.currentTextChanged.connect(
            lambda: self.param_changed_from_gui(attribute='shield_material_below'))

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

    def param_changed_from_gui(self, attribute=''):
        """Update general_values with value from GUI.

        Parameters
        ----------
        attribute : str
            attribute name in general_values
        """
        try:
            content = self.sender().value()
        except AttributeError:
            try:
                content = self.sender().currentText()
            except AttributeError:
                content = None
        if content:
            setattr(self.main.general_values, attribute, content)
            if self.main.dose_dict:
                reset_dose = False
                if self.main.wCalculate.chk_correct_thickness_geometry.isChecked():
                    reset_dose = True
                elif isinstance(content, str):
                    reset_dose = True
                if reset_dose:
                    self.main.reset_dose()

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
        line_length = np.sqrt((x1-x0)**2 + (y1-y0)**2)
        if line_length > 0:
            self.main.gui.calibration_factor = (
                self.main.gui.scale_length / line_length)
            self.main.gui.scale_start = (x0, y0)
            self.main.gui.scale_end = (x1, y1)
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
        self.material_strings = [x.label for x in self.main.materials]
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

    def highlight_selected_in_image(self):
        """Highlight area in image if area positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x0, y0, width, height = mini_methods.get_area_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.add_area_highlight(
                x0, y0, width, height)

    def update_occ_map(self, update_overlay=True):
        """Update array containing occupation factors and redraw."""
        self.main.occ_map = np.ones(self.main.image.shape[0:2])
        if self.main.gui.current_floor == 1:
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
                    x0, y0, width, height = mini_methods.get_area_from_text(
                        tabitem.text())
                    self.main.occ_map[y0:y0+height, x0:x0+width] = self.table_list[i][3]
                    areas_this.append(Rectangle(
                        (x0, y0), width, height, edgecolor='blue',
                        linewidth=self.main.gui.annotations_linethick, fill=False,
                        picker=True, gid=f'areas_{i}'))
                    self.main.wFloorDisplay.canvas.ax.add_patch(areas_this[-1])
            self.main.wFloorDisplay.canvas.image_overlay.set_data(self.main.occ_map)
        if update_overlay:
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
        self.rectify.clicked.connect(self.rectify_changed)
        self.hlo_extra.addWidget(self.rectify)

        self.label = 'Walls'
        self.main = main
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Wall name', 'x0,y0,x1,y1', 'Material', 'Thickness (mm)'])
        material = self.main.materials[0]
        self.empty_row = [True, '', '', material.label,
                          material.default_thickness]
        self.material_strings = [x.label for x in self.main.materials]
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
            self, initial_value=self.empty_row[4],
            row=row, col=4, max_val=400., step=1.0))

    def update_materials(self):
        """Update ComboBox of all rows when list of materials changed in settings."""
        self.material_strings = [x.label for x in self.main.materials]
        warnings = []
        self.blockSignals(True)
        for row in range(self.table.rowCount()):
            prev_val = self.get_cell_value(row, 3)
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.material_strings, row=row, col=3))
            w = self.table.cellWidget(row, 3)
            if prev_val in self.material_strings:
                w.setCurrentText(prev_val)
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

    def rectify_changed(self):
        """Update main.gui.rectify when settings manually changed."""
        self.main.gui.rectify = self.rectify.isChecked()

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
            try:
                tabitem.setText(text)
                self.table_list[self.active_row][2] = text
                self.update_wall_annotations()
                self.main.reset_dose()
            except (AttributeError, IndexError):
                self.select_row_col(0, 0)

    def get_color_from_material(self, material):
        """Return color for given material label.

        Parameters
        ----------
        material : str
            material label.

        Returns
        -------
        color : str
            named color or #rrggbb
        """
        color = ''
        for x in self.main.materials:
            if x.label == material:
                color = x.color
                break
        return color

    def get_default_thickness_from_material(self, material):
        """Return default_thickness for given material label.

        Parameters
        ----------
        material : str
            material label.

        Returns
        -------
        default_thickness : float
        """
        default_thickness = 0.
        for x in self.main.materials:
            if x.label == material:
                default_thickness = x.default_thickness
                break
        return default_thickness

    def get_linewidth(self, material, thickness):
        """Return linewidth in pixels for given settings on material.

        Parameters
        ----------
        material : str
            material label
        thickness : float
            material thickness in mm

        Returns
        -------
        linewidth : float
        """
        linewidth = self.main.gui.annotations_linethick
        if self.main.gui.calibration_factor is not None:
            canvas = self.main.wFloorDisplay.canvas
            xlim = canvas.ax.get_xlim()
            ylim = canvas.ax.get_ylim()
            dx, dy = np.ptp(xlim), np.ptp(ylim)
            size_inches = (canvas.fig.get_figwidth(), canvas.fig.get_figheight())
            size_points = 72 * np.array(size_inches)  # canvas.fig.dpi or 72?
            points_pr_pixel = size_points / np.array((dx, dy))
            points_pr_mm = (
                0.001 * np.min(points_pr_pixel) / self.main.gui.calibration_factor)

            for x in self.main.materials:
                if x.label == material:
                    if x.real_thickness:
                        real_linewidth = (
                            thickness * points_pr_mm)
                        if real_linewidth > linewidth:
                            linewidth = float(real_linewidth)
                    break

        return linewidth

    def update_wall_annotation(self, row=None, remove_already=False):
        """Update annotations for given wall number."""
        canvas = self.main.wFloorDisplay.canvas
        if remove_already:
            for line in canvas.ax.lines:
                gid_split = line.get_gid().split('_')
                if gid_split[0] == 'walls':
                    try:
                        if row == int(gid_split[1]):
                            line.remove()
                            break
                    except ValueError:
                        pass

            for text in canvas.ax.texts:
                gid_split = line.get_gid().split('_')
                if gid_split[0] == 'walls':
                    try:
                        if row == int(gid_split[1]):
                            text.remove()
                            break
                    except (ValueError, TypeError):
                        pass

        tabitem = self.table.cellWidget(row, 2)
        x0, y0, x1, y1 = mini_methods.get_wall_from_text(tabitem.text())
        if any([
                x0, x1, y0, y1,
                self.table.cellWidget(row, 0).isChecked()]):
            material = self.table.cellWidget(row, 3).currentText()
            color = self.get_color_from_material(material)
            thickness = self.table.cellWidget(row, 4).value()
            linewidth = self.get_linewidth(material, thickness)
            canvas.ax.plot(
                [x0, x1], [y0, y1],
                linestyle='-', marker='o', fillstyle='none', solid_capstyle='butt',
                linewidth=linewidth, color=color,
                markersize=self.main.gui.annotations_markersize[0],
                markeredgecolor='blue', markeredgewidth=0,
                picker=self.main.gui.picker,
                gid=f'walls_{row}')

            add_thickness = (
                True if 'Wall thickness' in self.main.wVisual.annotate_texts()
                else False
                )

            if add_thickness:
                x, y = (x0+x1) // 2, (y0+y1) // 2
                if x0 == x1:
                    rotation = 90
                    x -= linewidth
                    ha, va = 'right', 'center'
                else:
                    rotation = 0
                    y -= linewidth
                    ha, va = 'center', 'bottom'
                canvas.ax.annotate(
                    f'{thickness:.1f} mm', xy=(x, y), ha=ha, va=va,
                    rotation=rotation,
                    fontsize=self.main.gui.annotations_fontsize, color=color,
                    gid=f'walls_{row}')

        canvas.draw_idle()

    def remove_wall_lines(self):
        """Remove wall annotation lines."""
        canvas = self.main.wFloorDisplay.canvas
        if len(canvas.ax.lines) > 0:
            for line in canvas.ax.lines:
                if line.get_gid():
                    if 'walls' in line.get_gid():
                        line.remove()
            canvas.draw_idle()

    def remove_thickness_texts(self):
        """Remove all wall thickness text annotations."""
        canvas = self.main.wFloorDisplay.canvas
        if len(canvas.ax.texts) > 0:
            for text in canvas.ax.texts:
                if text.get_gid():
                    if 'walls' in text.get_gid():
                        text.remove()
            canvas.draw_idle()

    def update_wall_annotations(self):
        """Update annotations for walls."""
        self.remove_wall_lines()
        self.remove_thickness_texts()
        canvas = self.main.wFloorDisplay.canvas
        canvas.reset_hover_pick()
        for i in range(self.table.rowCount()):
            self.update_wall_annotation(i)
        self.highlight_selected_in_image()

    def highlight_selected_in_image(self):
        """Highlight area in image if area positions given."""
        if self.active_row > -1:
            self.main.wFloorDisplay.canvas.wall_highlight()

    def delete_row(self):
        """Delete selected row."""
        removed_row = super().delete_row()
        if removed_row > -1:
            if self.main.dose_dict:
                self.main.reset_dose()  # TODO or update

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
            self.table.cellWidget(added_row, 4).setValue(float(values_above[4]))

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
    """GUI for adding/editing CT sources."""

    def __init__(self, main):
        super().__init__(
            header='CT sources',
            info=(
                'For stray radiation using coronal and sagittal doserate map.<br>'
                '(Use "Other sources" if isotropic stray radiation.)<br>'
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
        self.table.setColumnCount(9)
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
        warnings = []
        self.blockSignals(True)
        for row in range(self.table.rowCount()):
            prev_val = self.get_cell_value(row, 3)
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.kV_source_strings, row=row, col=3))
            w = self.table.cellWidget(row, 3)
            if prev_val in self.kV_source_strings:
                w.setCurrentText(prev_val)
            else:
                if prev_val is not None:
                    warnings.append(
                        f'kV source ({prev_val}) no longer available. '
                        f'Please control source in row number {row}.')
        self.blockSignals(False)
        if warnings:
            dlg = messageboxes.MessageBoxWithDetails(
                self, title='Warnings',
                msg='Found issues for selected source types',
                info='See details',
                icon=QMessageBox.Warning,
                details=warnings)
            dlg.exec()

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


class OTsourcesTab(InputTab):
    """GUI for adding/editing kV sources with same doserate in all directions."""

    def __init__(self, main):
        super().__init__(
            header='Other kV sources',
            info=(
                'kV sources for isotropic stray radiation.<br>'
                '<br>'
                'Select position of source in floor plan (mouse click).<br>'
                'Select the row for which you want to set this source position.<br>'
                'Press the "Get..."-button to fetch the coordinates.<br>'
                '<br>'
                'Specify parameters for the sources:<br>'
                '   - kV source = Select named kV-source as defined in Settings - '
                'Shield Data<br>'
                '   - ' + '\u03bc' + 'Sv @ 1m pr procedure (on average)<br>'
                '   - # pr workday = average number of procedures pr working day. '
                'Dose multiplied with number of working days specified above.'
                ),
            btn_get_pos_text='Get source coordinates as marked in image')

        self.modality = 'OT'
        self.label = f'{self.modality} sources'
        self.main = main
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Source name', 'x,y', 'kV source',
             '\u03bc'+'Sv @ 1m pr procedure', '# procedures pr workday'])
        self.empty_row = [True, '', '', self.main.general_values.kV_sources[0],
                          5.0, 0.0]
        self.kV_source_strings = self.main.general_values.kV_sources
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 20*self.main.gui.char_width)
        self.table.setColumnWidth(2, 13*self.main.gui.char_width)
        self.table.setColumnWidth(3, 20*self.main.gui.char_width)
        self.table.setColumnWidth(4, 25*self.main.gui.char_width)
        self.table.setColumnWidth(5, 25*self.main.gui.char_width)

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
        self.table.setCellWidget(row, 4, uir.CellSpinBox(
            self, initial_value=5.,
            row=row, col=4, max_val=1000, step=1, decimals=1))  # uSv @1m pr procedure
        self.table.setCellWidget(row, 5, uir.CellSpinBox(
            self, initial_value=0, row=row, col=5,
            max_val=100, step=1, decimals=0))  # pr workday

    def update_kV_sources(self):
        """Update ComboBox of all rows when list of kV_sources changed from settings."""
        self.kV_source_strings = [x.label for x in self.main.general_values.kV_sources]
        warnings = []
        self.blockSignals(True)
        for row in range(self.table.rowCount()):
            prev_val = self.get_cell_value(row, 3)
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.kV_source_strings, row=row, col=3))
            w = self.table.cellWidget(row, 3)
            if prev_val in self.kV_source_strings:
                w.setCurrentText(prev_val)
            else:
                if prev_val is not None:
                    warnings.append(
                        f'kV source ({prev_val}) no longer available. '
                        f'Please control source in row number {row}.')
        self.blockSignals(False)
        if warnings:
            dlg = messageboxes.MessageBoxWithDetails(
                self, title='Warnings',
                msg='Found issues for selected source types',
                info='See details',
                icon=QMessageBox.Warning,
                details=warnings)
            dlg.exec()

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
            self.table.cellWidget(added_row, 4).setValue(float(values_above[4]))
            self.table.cellWidget(added_row, 5).setValue(int(values_above[5]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(added_row, i).blockSignals(False)
            self.update_row_number(added_row, 1)

            self.select_row_col(added_row, 1)
            self.table_list[added_row] = copy.deepcopy(values_above)
            # TODO: change label to one not used yet
            # TODO: update floor display


class PointsTab(InputTab):
    """GUI for adding/editing calculation points."""

    def __init__(self, main):
        super().__init__(
            header='Calculation points',
            info=(
                'Add specific (named) points to tabulate calculated dose.<br>'
                '<br>'
                'Select position of source in floor plan (mouse click).<br>'
                'Select the row for which you want to set this calculation point.<br>'
                'Press the "Get..."-button to fetch the coordinates.<br>'
                ),
            btn_get_pos_text='Get point coordinates as marked in image')

        self.modality = 'point'
        self.label = 'point'
        self.main = main
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Label', 'x,y',
             'Total dose (mSv)', 'NM max doserate (' + '\u03bc' + 'Sv/h)'])
        self.empty_row = [True, '', '', '', '']
        self.table_list = [copy.deepcopy(self.empty_row)]
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.main.gui.char_width)
        self.table.setColumnWidth(1, 20*self.main.gui.char_width)
        self.table.setColumnWidth(2, 13*self.main.gui.char_width)
        self.table.setColumnWidth(3, 20*self.main.gui.char_width)
        self.table.setColumnWidth(4, 35*self.main.gui.char_width)
        self.tb.act_duplicate.setVisible(False)

        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, uir.InputCheckBox(self, row=row, col=0))
        self.table.setCellWidget(row, 1, uir.TextCell(self, row=row, col=1))  # name
        self.table.setCellWidget(row, 2, uir.TextCell(self, row=row, col=2))  # x,y
        self.table.setCellWidget(row, 3, uir.TextCell(self, row=row, col=3))  # dose
        self.table.setCellWidget(row, 4, uir.TextCell(self, row=row, col=4))  # doserate

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
            # TODO: update display
        return added_row

    def duplicate_row(self):
        """Override to make TableToolBar happy."""
        pass
