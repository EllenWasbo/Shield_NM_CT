# -*- coding: utf-8 -*-
"""User interface for main window of Shield_NM_CT.

@author: EllenWasbo
"""
import sys
import os
from io import BytesIO
import numpy as np
import copy
from time import time
from dataclasses import dataclass
from pathlib import Path
import shutil
import webbrowser

from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtCore import Qt, QTimer, QFile
from PyQt5.QtWidgets import (
    QApplication, qApp, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QButtonGroup, QScrollArea, QTabWidget,
    QPushButton, QLabel, QSpinBox,
    QRadioButton, QCheckBox, QSlider, QToolButton,
    QMenu, QAction, QMessageBox, QFileDialog
    )
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg, NavigationToolbar2QT)
from matplotlib.figure import Figure
import matplotlib.image as mpimg
from matplotlib import patches
from matplotlib.path import Path
from matplotlib import transforms
from matplotlib.transforms import Affine2D
from matplotlib.markers import MarkerStyle

# Shield_NM_CT block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    VERSION, ENV_ICON_PATH, ENV_CONFIG_FOLDER, ENV_USER_PREFS_PATH, ANNOTATION_OPTIONS)
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui import ui_main_tabs
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.ui import settings
import Shield_NM_CT.ui.reusable_widgets as uir
from Shield_NM_CT.ui.ui_dialogs import AboutDialog, EditAnnotationsDialog
from Shield_NM_CT.scripts.calculate_dose import calculate_dose
import Shield_NM_CT.resources
# Shield_NM_CT block end


@dataclass
class GuiData():
    """Class to keep variables."""

    image_path = ''
    load_path = ''
    scale_start = ()
    scale_end = ()
    scale_length = 0.
    calibration_factor = None  # float: meters/pixel
    x0 = 0.0  # mouse x coordinate FloorCanvas.on_press
    x1 = 0.0  # mouse x coordinate on_motion (if already pressed) and on_release
    y0 = 0.0  # same as above for y coordinate
    y1 = 0.0
    current_tab = 'Scale'
    rectify = False  # if in tab Walls and rectify is selected
    annotations = True
    annotations_fontsize = 15
    annotations_linethick = 3
    annotations_markersize = (12, 17)  # first standard, second hovered
    annotations_delta = (20, 20)
    handle_size = 15
    picker = 10  # picker margin for point and line
    alpha_image = 1.0
    alpha_overlay = 0.5
    panel_width = 400
    panel_height = 700
    char_width = 7
    zoom_active = False


class MainWindow(QMainWindow):
    """Class main window of ShieldNMCT."""

    def __init__(self, scX=1400, scY=700, char_width=7,
                 developer_mode=False, warnings=[]):
        super().__init__()

        self.image = np.zeros(2)
        self.occ_map = np.zeros(2)
        self.dose_dict = {}  # dictionary holding dose calculations
        self.ct_dose_map = np.zeros(2)

        self.save_blocked = False
        if os.environ[ENV_USER_PREFS_PATH] == '':
            if os.environ[ENV_CONFIG_FOLDER] == '':
                self.save_blocked = True

        if os.environ[ENV_CONFIG_FOLDER] != '':
            cff.add_user_to_active_users()

        self.update_settings()

        self.gui = GuiData()
        self.gui.panel_width = round(0.48*scX)
        self.gui.panel_height = round(0.86*scY)
        self.gui.char_width = char_width
        self.gui.annotations_linethick = self.user_prefs.annotations_linethick
        self.gui.annotations_fontsize = self.user_prefs.annotations_fontsize

        self.setWindowTitle('Shield NM CT v ' + VERSION)
        self.setWindowIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}logo.png'))
        self.setGeometry(
            round(self.gui.panel_width*0.02),
            round(self.gui.panel_height*0.05),
            round(self.gui.panel_width*2+30),
            round(self.gui.panel_height+50)
            )

        self.create_menu_toolBar()

        stream = QFile(':/icons/floorPlan_big.png')
        if stream.open(QFile.ReadOnly):
            data = stream.readAll()
            stream.close()
            self.default_floorplan = mpimg.imread(BytesIO(data))

        self.wFloorDisplay = FloorWidget(self)
        self.wVisual = VisualizationWidget(self)
        self.wCalculate = CalculateWidget(self)

        self.tabs = QTabWidget()
        self.scale_tab = ui_main_tabs.ScaleTab(self)
        self.areas_tab = ui_main_tabs.AreasTab(self)
        self.walls_tab = ui_main_tabs.WallsTab(self)
        self.NMsources_tab = ui_main_tabs.NMsourcesTab(self)
        self.CTsources_tab = ui_main_tabs.CTsourcesTab(self)
        #TODO self.FLsources_tab = ui_main_tabs.FLsources_tab(self)
        self.tabs.addTab(self.scale_tab, "Scale")
        self.tabs.addTab(self.areas_tab, "Areas")
        self.tabs.addTab(self.walls_tab, "Walls")
        self.tabs.addTab(self.NMsources_tab, "NM sources")
        self.tabs.addTab(self.CTsources_tab, "CT sources")
        #TODOself.tabs.addTab(self.FLsources_tab, "Fluoro sources")
        self.tabs.currentChanged.connect(self.new_tab_selection)

        bbox = QHBoxLayout()

        self.split_lft_rgt = QSplitter(Qt.Horizontal)
        wid_lft = QWidget()
        wid_rgt = QWidget()
        lo_lft = QVBoxLayout()
        lo_rgt = QVBoxLayout()
        wid_lft.setLayout(lo_lft)
        wid_rgt.setLayout(lo_rgt)
        self.split_lft_rgt.addWidget(wid_lft)
        self.split_lft_rgt.addWidget(wid_rgt)
        bbox.addWidget(self.split_lft_rgt)

        # Fill left box
        self.split_lft = QSplitter(Qt.Vertical)
        lo_lft.addWidget(self.split_lft)
        wid_top = QWidget()
        wid_btm = QWidget()
        lo_top = QVBoxLayout()
        lo_btm = QVBoxLayout()
        wid_top.setLayout(lo_top)
        wid_btm.setLayout(lo_btm)
        self.split_lft.addWidget(wid_top)
        self.split_lft.addWidget(wid_btm)
        lo_top.addWidget(self.wFloorDisplay)
        lo_btm.addWidget(self.wVisual)

        # Fill right box
        self.split_rgt = QSplitter(Qt.Vertical)
        lo_rgt.addWidget(self.split_rgt)
        wid_top = QWidget()
        wid_btm = QWidget()
        lo_top = QVBoxLayout()
        lo_btm = QVBoxLayout()
        wid_top.setLayout(lo_top)
        wid_btm.setLayout(lo_btm)
        self.split_rgt.addWidget(wid_top)
        self.split_rgt.addWidget(wid_btm)
        lo_top.addWidget(self.wCalculate)
        lo_btm.addWidget(self.tabs)

        widFull = QWidget()
        widFull.setLayout(bbox)
        widFull.setFixedSize(2.*self.gui.panel_width, self.gui.panel_height)

        scroll = QScrollArea()
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidgetResizable(True)
        scroll.setWidget(widFull)
        self.setCentralWidget(scroll)
        self.reset_split_sizes()

        self.update_image()

        if len(warnings) > 0:
            QTimer.singleShot(300, lambda: self.show_warnings(warnings))

    def show_warnings(self, warnings=[]):
        """Show startup warnings when screen initialised."""
        dlg = messageboxes.MessageBoxWithDetails(
            self, title='Warnings',
            msg='Found issues during startup',
            info='See details',
            icon=QMessageBox.Warning,
            details=warnings)
        dlg.exec()

    def update_settings(self, after_edit_settings=False):
        """Refresh data from settings files affecting GUI in main window."""
        if after_edit_settings is False:
            print('Reading configuration settings...')
        self.lastload = time()
        _, _, self.user_prefs = cff.load_user_prefs()
        if self.user_prefs.dark_mode:
            plt.style.use('dark_background')
        _, _, self.isotopes = cff.load_settings(fname='isotopes')
        _, _, self.materials = cff.load_settings(fname='materials')
        _, _, self.ct_doserates = cff.load_settings(fname='ct_doserates')
        _, _, self.shield_data = cff.load_settings(fname='shield_data')
        _, _, self.general_values = cff.load_settings(fname='general_values')

        if after_edit_settings:
            self.NMsources_tab.update_isotopes()
            self.walls_tab.update_materials()
            self.scale_tab.update_material_lists()

    def load_floor_plan_image(self):
        """Open image and update GUI."""
        fname = QFileDialog.getOpenFileName(
            self, 'Load floor plan image',
            os.path.join(self.user_prefs.default_path, 'floorplan.png'),
            "PNG files (*.png);;All files (*)")

        if len(fname[0]) > 0:
            self.gui.image_path = fname[0]
            self.wFloorDisplay.canvas.reset_hover_pick()
            self.update_image()

    def update_image(self):
        """Load image from file or default, reset related maps."""
        if self.gui.image_path == '':
            self.image = self.default_floorplan
        else:
            self.image = mpimg.imread(self.gui.image_path)

        # initiate maps
        self.occ_map = np.ones(self.image.shape[0:2], dtype=float)
        try:
            self.areas_tab.update_occ_map()
        except AttributeError:
            pass
        self.ct_dose_map = np.zeros(self.image.shape[0:2], dtype=float)
        self.wFloorDisplay.canvas.floor_draw()

    def reset_dose(self, floor=None):
        #TODO reset if floor = None, else reset if current floor is floor
        #also reset NM dose
        pass

    def calculate_dose(self):
        status, msgs = calculate_dose(self)  # updating self.dose_dict
        if msgs:
            dlg = messageboxes.MessageBoxWithDetails(
                self, title='Warnings',
                msg='Found issues during calculation',
                info='See details',
                icon=QMessageBox.Warning,
                details=msgs)
            dlg.exec()
        if status:
            if 'Dose' not in self.overlay_text():
                self.wVisual.btns_overlay.button(2).setChecked(True)
            else:
                self.wFloorDisplay.canvas.update_dose_overlay()

    def update_dose_days(self):
        #TODO - number of working days changed - update dose if exists
        #self.wCalculate.working_days.value()
        pass

    def keyReleaseEvent(self, event):
        """Trigger get_pos when Enter/Return pressed."""
        if isinstance(event, QKeyEvent):
            if event.key() == Qt.Key_Return:
                self.tabs.currentWidget().get_pos()
            elif event.key() == Qt.Key_Plus:
                if self.gui.current_tab != 'Scale':
                    if self.tabs.currentWidget().cellwidget_is_text is False:
                        try:
                            self.tabs.currentWidget().add_row()
                        except AttributeError:
                            pass
            elif event.key() == Qt.Key_Delete:
                if self.gui.current_tab != 'Scale':
                    if self.tabs.currentWidget().cellwidget_is_text is False:
                        try:
                            self.tabs.currentWidget().delete_row()
                        except AttributeError:
                            pass

    def exit_app(self):
        """Exit app."""
        sys.exit()

    def about(self):
        """Show about info."""
        dlg = AboutDialog(version=VERSION)
        dlg.exec()

    def wiki(self):
        """Open wiki url."""
        url = 'https://github.com/EllenWasbo/Shield_NM_CT/wiki'
        webbrowser.open(url=url, new=1)

    def start_wait_cursor(self):
        """Block mouse events by wait cursor."""
        QApplication.setOverrideCursor(Qt.WaitCursor)
        qApp.processEvents()

    def stop_wait_cursor(self):
        """Return to normal mouse cursor after wait cursor."""
        QApplication.restoreOverrideCursor()

    def new_tab_selection(self, i):
        """Remove temporary, tab-specific annotations + more settings."""
        self.gui.rectify = False
        if hasattr(self.tabs.currentWidget(), 'label'):
            self.gui.current_tab = self.tabs.currentWidget().label
            if hasattr(self.wFloorDisplay.canvas, 'ax'):
                self.wFloorDisplay.canvas.reset_hover_pick()
                if len(self.wFloorDisplay.canvas.ax.patches) > 0:
                    for i, p in enumerate(
                            self.wFloorDisplay.canvas.ax.patches):
                        if p.get_gid() == 'area_temp':
                            self.wFloorDisplay.canvas.ax.patches[i].remove()
                            break
                if len(self.wFloorDisplay.canvas.ax.lines) > 0:
                    index_to_remove = []
                    for i, p in enumerate(
                            self.wFloorDisplay.canvas.ax.lines):
                        if p.get_gid() == 'line_temp':
                            index_to_remove.append(i)
                    if index_to_remove:
                        index_to_remove.reverse()
                        for i in index_to_remove:
                            self.wFloorDisplay.canvas.ax.lines[i].remove()
                self.blockSignals(True)
                if self.gui.current_tab in ANNOTATION_OPTIONS:
                    self.wVisual.btns_annotate.button(
                        ANNOTATION_OPTIONS.index(self.gui.current_tab)).setChecked(True)
                if self.gui.current_tab == 'Areas':
                    self.wVisual.set_alpha_overlay(0.2)
                    self.wVisual.btns_overlay.button(1).setChecked(True)
                    self.areas_tab.update_occ_map()
                elif self.gui.current_tab == 'Walls':
                    self.wVisual.btns_overlay.button(0).setChecked(True)
                    self.gui.rectify = self.walls_tab.rectify.isChecked()
                elif ('source' in self.gui.current_tab
                      or 'point' in self.gui.current_tab):
                    self.wVisual.btns_overlay.button(0).setChecked(True)
                    self.tabs.currentWidget().update_source_annotations()
                self.blockSignals(False)

    def reset_split_sizes(self):
        """Set and reset QSplitter sizes."""
        self.split_lft.setSizes(
            [round(self.gui.panel_height*0.8), round(self.gui.panel_height*0.2)])
        self.split_rgt.setSizes(
            [round(self.gui.panel_height*0.2), round(self.gui.panel_height*0.8)])
        self.split_lft_rgt.setSizes(
            [round(self.gui.panel_width*.8), round(self.gui.panel_width*1.2)])

    def set_split_max_img(self):
        """Set QSplitter to maximized image."""
        self.split_lft.setSizes(
            [round(self.gui.panel_height), 0])
        self.split_lft_rgt.setSizes(
            [round(self.gui.panel_width*2), 0])

    def reset_all(self):
        """Reset all data and GUI."""
        self.gui = GuiData()
        self.occ_map = np.zeros(2)
        self.ct_dose_map = np.zeros(2)
        for widget in [
                self.areas_tab,
                self.walls_tab,
                self.NMsources_tab]: #TODO increase list
            widget.table.setRowCount(0)
            widget.add_cell_widgets(0)
            widget.table_list = [copy.deepcopy(self.areas_tab.empty_row)]
        #TODO reset scale?
        #TODO reset floor heights?
        self.wFloorDisplay.canvas.floor_draw()

    def open_project(self):
        """Load image and tables from folder."""
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setDirectory(self.user_prefs.default_path)
        if dlg.exec():
            self.reset_all()
            fname = dlg.selectedFiles()
            path = Path(os.path.normpath(fname[0]))
            files = [x for x in path.glob('*')]
            file_bases = [x.stem for x in files]
            if 'floorplan' in file_bases:
                idx = file_bases.index('floorplan')
                self.gui.image_path = files[idx].resolve().as_posix()
                self.wFloorDisplay.canvas.floor_draw()
            if 'areas' in file_bases:
                idx = file_bases.index('areas')
                self.areas_tab.import_csv(path=files[idx].resolve().as_posix())
                self.areas_tab.update_occ_map()

    def save_project(self, save_as=False):
        """Save image and tables in folder or update if loaded from folder.

        Parameters
        ----------
        save_as : bool
            True if new folder should be created. Default is False.

        """
        path = ''
        if self.gui.load_path == '' or save_as:
            # start new project folder
            dlg = QFileDialog()
            dlg.setFileMode(QFileDialog.Directory)
            dlg.setDirectory(self.user_prefs.default_path)
            if dlg.exec():
                fname = dlg.selectedFiles()
                path = os.path.normpath(fname[0])
        else:
            path = self.gui.load_path

        if path != '':
            if os.access(path, os.W_OK):
                # overwrite floorplan image and csv tables
                imgPath = Path(self.gui.image_path)
                if imgPath.parent != Path(path):
                    shutil.copyfile(
                        self.gui.image_path,
                        os.path.join(path, f'floorplan{imgPath.suffix}'))
                self.areas_tab.export_csv(
                    path=os.path.join(path, 'areas.csv'))
                # TODO - other tables too
            else:
                QMessageBox.warning(
                    self, 'Failed saving', f'No writing permission for {path}')

    def run_settings(self, initial_view='', initial_template_label=''):
        """Display settings dialog."""
        if initial_view == '':
            dlg = settings.SettingsDialog(self)
        else:
            dlg = settings.SettingsDialog(
                self, initial_view=initial_view,
                initial_template_label=initial_template_label)
        dlg.exec()
        self.update_settings(after_edit_settings=True)

    def create_menu_toolBar(self):
        """GUI of MenuBar and main ToolBar."""
        menu_bar = self.menuBar()
        tool_bar = self.addToolBar('first')

        act_load_floor_img = QAction('Load floor plan image...', self)
        act_load_floor_img.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}floorPlan.png'))
        act_load_floor_img.setToolTip('Load floor plan image...')
        act_load_floor_img.triggered.connect(self.load_floor_plan_image)

        act_load_project = QAction('Load project...', self)
        act_load_project.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}open.png'))
        act_load_project.setToolTip('Load project...')
        act_load_project.triggered.connect(self.open_project)

        act_save_project = QAction('Save project', self)
        act_save_project.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}save.png'))
        act_save_project.setToolTip('Save project')
        act_save_project.triggered.connect(self.save_project)

        act_save_project_as = QAction('Save project as...', self)
        act_save_project_as.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}save_as.png'))
        act_save_project_as.setToolTip('Save project as...')
        act_save_project_as.triggered.connect(
            lambda: self.save_project(save_as=True))

        act_settings = QAction('Settings', self)
        act_settings.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}gears.png'))
        act_settings.setToolTip('Open the user settings manager')
        act_settings.triggered.connect(self.run_settings)

        act_quit = QAction('&Quit', self)
        act_quit.setShortcut('Ctrl+Q')
        act_quit.triggered.connect(self.exit_app)

        act_about = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}info.png'),
            'About Shield_NM_CT...', self)
        act_about.triggered.connect(self.about)
        act_wiki = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}globe.png'),
            'Wiki ...', self)
        act_wiki.triggered.connect(self.wiki)
        act_reset_layout = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}layout_reset.png'),
            'Reset split layout', self)
        act_reset_layout.triggered.connect(self.reset_split_sizes)

        # fill menus
        mFile = QMenu('&File', self)
        mFile.addActions([act_load_floor_img, act_load_project, act_save_project,
                          act_save_project_as, act_quit])
        menu_bar.addMenu(mFile)
        mSett = QMenu('&Settings', self)
        mSett.addAction(act_settings)
        menu_bar.addMenu(mSett)
        mHelp = QMenu('&Help', self)
        mHelp.addActions([act_about, act_wiki])
        menu_bar.addMenu(mHelp)

        # fill toolbar
        tool_bar.addActions([act_load_floor_img, act_load_project,
                             act_save_project, act_save_project_as])
        tool_bar.addWidget(QLabel('             '))
        tool_bar.addActions([act_reset_layout, act_settings])


class FloorCanvas(FigureCanvasQTAgg):
    """Canvas for drawing the floor and overlays."""

    def __init__(self, main):
        self.fig = Figure()
        #self.fig, self.ax = plt.subplots()
        self.ax = self.fig.add_subplot(111)
        self.fig.subplots_adjust(0., 0., 1., 1.)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.main = main
        self.setParent(main)

        self.font = {
            'family': 'serif', 'color': 'darkred', 'weight': 'normal', 'size': 16}

        self.area_temp = patches.Rectangle((0, 0), 1, 1)
        self.area_highlight = patches.Rectangle((0, 0), 1, 1)
        self.current_artist = None  # picked artist
        self.hovered_artist = None  # artist detected on hover
        self.mouse_pressed = False
        self.info_text = None
        self.handles_visible = False  # True if handles for editing shown
        self.drag_handle = False  # True if handles for editing by drag picked

        # INFO:
        '''
        gid used for different artists:
        'line_temp':	 dotted line for marked new line
        'scale': line for currently defined scale (line)
        'scale_text': text for currently defined length of scale line
        'measured_text': text for length of line_temp if scale set
        'area_temp': dotted Rectangle for marked area
        'area_highlight': red dottet Rectangle for selected row in Areas table
        'point_release'
        '(source modality_){int}': row number in table for current tab
        'handle_?': pickable Rectangle to drag position of line (_start, _end)
                        or of area (_left, _right, _top, _bottom)
        '''

        self.mpl_connect("button_press_event", self.on_press)
        self.mpl_connect("button_release_event", self.on_release)
        self.mpl_connect("motion_notify_event", self.on_motion)
        self.mpl_connect("pick_event", self.on_pick)
        #self.ax.callbacks.connect("xlim_changed", self.on_zoom_changed_event)

    def on_press(self, event):
        """When mouse button pressed."""
        self.mouse_pressed = True
        if self.main.gui.zoom_active is False:
            self.main.gui.x0, self.main.gui.y0 = event.xdata, event.ydata
            self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata

            if self.main.gui.current_tab == 'Areas':
                self.area_temp = patches.Rectangle(
                    (0, 0), 1, 1, edgecolor='k', linestyle='--',
                    linewidth=2., fill=False, gid='area_temp')
                if len(self.ax.patches) > 0:
                    for i, p in enumerate(self.ax.patches):
                        if p.get_gid() == 'area_temp':
                            self.ax.patches[i].remove()
                self.ax.add_patch(self.area_temp)
                self.draw()
            elif self.main.gui.current_tab in ['Scale', 'Walls']:
                if len(self.ax.lines) > 0:
                    for i, p in enumerate(self.ax.lines):
                        if p.get_gid() == 'line_temp':
                            self.ax.lines[i].remove()
                if self.handles_visible is False:
                    if self.main.gui.rectify:
                        diff_x = abs(self.main.gui.x0 - self.main.gui.x1)
                        diff_y = abs(self.main.gui.y0 - self.main.gui.y1)
                        if diff_x > diff_y:  # keep y0
                            self.main.gui.y1 = self.main.gui.y0
                        else:  # keep x0
                            self.main.gui.x1 = self.main.gui.x0
                    self.ax.plot([self.main.gui.x0, self.main.gui.x1],
                                 [self.main.gui.y0, self.main.gui.y1],
                                 'k--', linewidth=2., gid='line_temp')
            else:
                pass

    def on_motion(self, event):
        """When mouse pressed and moved."""
        if self.mouse_pressed:
            if self.main.gui.zoom_active is False:
                if self.main.gui.x0 is not None:
                    self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata
                    if self.main.gui.current_tab == 'Areas':
                        self.update_area_on_drag()
                    elif self.main.gui.current_tab in ['Scale', 'Walls']:
                        if self.drag_handle:
                            self.update_wall_on_drag()
                        else:
                            for p in self.ax.lines:
                                if p.get_gid() == 'line_temp':
                                    if self.main.gui.rectify:
                                        diff_x = abs(self.main.gui.x0 - self.main.gui.x1)
                                        diff_y = abs(self.main.gui.y0 - self.main.gui.y1)
                                        if diff_x > diff_y:  # keep y0
                                            self.main.gui.y1 = self.main.gui.y0
                                        else:  # keep x0
                                            self.main.gui.x1 = self.main.gui.x0
                                    p.set_data(
                                        [self.main.gui.x0, self.main.gui.x1],
                                        [self.main.gui.y0, self.main.gui.y1])
                                    self.draw_idle()
                                    break
                            if self.main.gui.current_tab == 'Scale':
                                self.add_measured_length()
                    else:
                        self.drag_handle = True
                        self.update_source_on_drag()
        else:  # on hover
            if (
                    self.handles_visible is False
                    and event.inaxes == self.ax
                    and self.main.gui.current_tab != 'Scale'
                    ):
                prev_hovered_artist = self.hovered_artist
                hit = False
                if self.main.gui.current_tab == 'Areas':
                    for patch in self.ax.patches:
                        contain_event, index = patch.contains(event)
                        gid = patch.get_gid()
                        if contain_event and 'handle' not in gid:
                            self.hovered_artist = patch
                            hit = True
                    if hit is False:
                        self.hovered_artist = None
                else:
                    for line in self.ax.lines:
                        contain_event, index = line.contains(event)
                        if contain_event:
                            self.hovered_artist = line
                            hit = True
                    if hit is False:
                        self.hovered_artist = None
                    else:
                        if 'CT' not in self.hovered_artist.get_gid():
                            self.hovered_artist.set_markersize(
                                self.main.gui.annotations_markersize[1])
                        else:
                            self.set_CT_marker_properties(
                                marker=self.hovered_artist, hover=True)
                        self.info_text.set_visible(True)
                        self.draw_idle()

                if prev_hovered_artist != self.hovered_artist:  # redraw
                    if prev_hovered_artist is not None:
                        # reset linethickness or markersize
                        if self.main.gui.current_tab == 'Areas':
                            prev_hovered_artist.set_linewidth(
                                self.main.gui.annotations_linethick)
                        elif self.main.gui.current_tab == 'Walls':
                            try:
                                curr_lw = plt.getp(prev_hovered_artist, 'linewidth')
                                prev_hovered_artist.set_linewidth(curr_lw - 2)
                                prev_hovered_artist.set_markeredgewidth(0)
                            except:
                                print('TypeError')
                        else:
                            if 'CT' not in prev_hovered_artist.get_gid():
                                prev_hovered_artist.set_markersize(
                                    self.main.gui.annotations_markersize[0])
                            else:
                                self.set_CT_marker_properties(
                                    marker=prev_hovered_artist, hover=False)
                        self.draw_idle()
                    if self.hovered_artist is None:
                        self.info_text.set_visible(False)
                        self.draw_idle()
                    else:
                        if self.main.gui.current_tab == 'Areas':
                            self.hovered_artist.set_linewidth(
                                self.main.gui.annotations_linethick + 2)
                        elif self.main.gui.current_tab == 'Walls':
                            try:
                                curr_lw = plt.getp(self.hovered_artist, 'linewidth')
                                self.hovered_artist.set_linewidth(curr_lw + 2)
                                self.hovered_artist.set_markeredgewidth(3)
                            except:
                                print('TypeError')
                        else:
                            if 'CT' not in self.hovered_artist.get_gid():
                                self.hovered_artist.set_markersize(
                                    self.main.gui.annotations_markersize[1])
                            else:
                                self.set_CT_marker_properties(
                                    marker=self.hovered_artist, hover=True)
                        self.update_info_text(event)
                        self.draw_idle()

    def on_release(self, event):
        """When mouse button released."""
        if self.mouse_pressed:
            self.mouse_pressed = False
        if self.main.gui.zoom_active is False:
            self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata

            if self.main.gui.current_tab in ['Areas', 'Scale', 'Walls']:
                if self.main.gui.x1 is not None:
                    width = np.abs(self.main.gui.x1 - self.main.gui.x0)
                    height = np.abs(self.main.gui.y1 - self.main.gui.y0)
                else:
                    width = 0
                    height = 0

                if self.drag_handle is False and (width + height) > 20:
                    if self.main.gui.current_tab == 'Areas':
                        self.area_temp.set_width(width)
                        self.area_temp.set_height(height)
                        self.area_temp.set_xy((
                            min(self.main.gui.x0, self.main.gui.x1),
                            min(self.main.gui.y0, self.main.gui.y1)))
                    elif self.main.gui.current_tab in ['Scale', 'Walls']:
                        for p in self.ax.lines:
                            if p.get_gid() == 'line_temp':
                                if self.main.gui.rectify:
                                    diff_x = abs(self.main.gui.x0 - self.main.gui.x1)
                                    diff_y = abs(self.main.gui.y0 - self.main.gui.y1)
                                    if diff_x > diff_y:  # keep y0
                                        self.main.gui.y1 = self.main.gui.y0
                                    else:  # keep x0
                                        self.main.gui.x1 = self.main.gui.x0
                                p.set_data(
                                    [self.main.gui.x0, self.main.gui.x1],
                                    [self.main.gui.y0, self.main.gui.y1])
                                break
                elif self.drag_handle:
                    self.finish_drag()

            else:  # mark release position
                if hasattr(self, 'ax'):
                    create_new = True
                    for p in self.ax.lines:
                        if p.get_gid() == 'point_release':
                            create_new = False
                            p.set_data(event.xdata, event.ydata)
                            break
                    if create_new:
                        self.ax.plot(
                            event.xdata, event.ydata,
                            'ko', fillstyle='none',
                            markersize=self.main.gui.annotations_markersize[0],
                            gid='point_release')

                if self.drag_handle:
                    self.finish_drag()

            self.draw_idle()

    def on_pick(self, event):
        """When mouse button picking objects."""
        if self.current_artist != event.artist:
            self.current_artist = event.artist
            gid = self.current_artist.get_gid()
            if 'handle' in gid:
                self.drag_handle = True
            else:
                if '_' in gid:
                    gid_split = gid.split('_')
                    gid = gid_split[1]
                try:
                    row = int(gid)
                except ValueError:
                    row = None
                if row is not None:
                    self.main.tabs.currentWidget().select_row_col(row, 1)
                    # Create handle_ to drag
                    if isinstance(self.current_artist, patches.Rectangle):
                        self.current_artist.set_picker(False)
                        [xmin, ymin], [xmax, ymax] = (
                            self.current_artist.get_bbox().get_points())
                        xmid = (xmax + xmin) // 2
                        ymid = (ymax + ymin) // 2
                        half = self.main.gui.handle_size // 2
                        handles = [  # gid, pos
                            ('handle_left', (xmin-half, ymid-half)),
                            ('handle_top', (xmid-half, ymin-half)),
                            ('handle_right', (xmax-half, ymid-half)),
                            ('handle_bottom', (xmid-half, ymax-half))
                             ]
                    elif self.main.gui.current_tab == 'Walls':
                        self.current_artist.set_picker(False)
                        self.current_artist.set_markeredgewidth(0)
                        xs, ys = self.current_artist.get_data()
                        half = self.main.gui.handle_size // 2
                        handles = [  # gid, pos
                            ('handle_start', (xs[0]-half, ys[0]-half)),
                            ('handle_end', (xs[1]-half, ys[1]-half))
                            ]
                    else:
                        self.sourcepos_highlight()
                        handles = []

                    for handle in handles:
                        self.ax.add_patch(
                            patches.Rectangle(
                                handle[1],
                                self.main.gui.handle_size, self.main.gui.handle_size,
                                edgecolor='black', facecolor='white',
                                linewidth=2, fill=True, picker=True,
                                gid=handle[0])
                            )
                        self.handles_visible = True
                        self.draw_idle()

    def on_zoom_changed(self):
        """Redraw walls if real thickness."""
        if 'Walls' in self.main.wVisual.annotate_texts():
            if self.main.gui.calibration_factor is not None:
                self.main.walls_tab.update_wall_annotations()

    def reset_hover_pick(self):
        """Reset to neither hovered nor picked artists."""
        index_handles = []
        for i, patch in enumerate(self.ax.patches):
            if 'handle' in patch.get_gid():
                index_handles.append(i)
            elif patch == self.hovered_artist:
                patch.set_linewidth(self.main.gui.annotations_linethick)
        if len(index_handles):
            index_handles.reverse()
            for i in index_handles:
                self.ax.patches[i].remove()
        if self.hovered_artist:
            if self.main.gui.current_tab == 'Areas':
                self.hovered_artist.set_picker(True)
            else:
                self.hovered_artist.set_picker(self.main.gui.picker)
            self.hovered_artist = None
        self.current_artist = None
        self.handles_visible = False
        self.drag_handle = False
        self.info_text.set_text('')
        self.info_text.set_visible(False)

        self.draw_idle()

    def finish_drag(self):
        """Update parameters when drag finished."""
        active_row = self.main.tabs.currentWidget().active_row
        # update table
        if self.main.gui.current_tab == 'Areas':
            [x0, y0], [x1, y1] = self.hovered_artist.get_bbox().get_points()
            pos_string = f'{x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f}'
        elif self.main.gui.current_tab == 'Walls':
            [x0, x1], [y0, y1] = self.hovered_artist.get_data()
            pos_string = f'{x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f}'
        else:
            pos_string = f'{self.main.gui.x1:.0f}, {self.main.gui.y1:.0f}'

        self.main.tabs.currentWidget().table_list[active_row][2] = pos_string
        w = self.main.tabs.currentWidget().table.cellWidget(active_row, 2)
        w.setText(pos_string)

        if self.main.gui.current_tab == 'Areas':
            self.main.areas_tab.update_occ_map()
        elif self.main.gui.current_tab == 'Walls':
            self.main.walls_tab.update_wall_annotations()
        elif ('source' in self.main.gui.current_tab
              or 'point' in self.main.gui.current_tab):
            self.sourcepos_highlight()
        self.main.reset_dose()

        self.reset_hover_pick()

    def add_scale_highlight(self, x0, y0, x1, y1):
        """Highlight floor plan scale.

        Parameters
        ----------
        x0 : int
        y0 : int
        x1 : int
        y1 : int
        """
        for i, p in enumerate(self.ax.lines):
            if p.get_gid() == 'scale':
                self.ax.lines[i].remove()
        self.ax.plot([x0, x1], [y0, y1],
                     'b', marker='|', linewidth=2., picker=self.main.gui.picker,
                     gid='scale')
        if self.main.gui.scale_length > 0:
            if hasattr(self, 'scale_text'):
                self.scale_text.set_position(
                    [x0+self.main.gui.annotations_delta[0],
                     y0+self.main.gui.annotations_delta[1]])
                self.scale_text.set_text(
                    f'{self.main.gui.scale_length:.3f} m')
            else:
                self.scale_text = self.ax.text(
                    x0+self.main.gui.annotations_delta[0],
                    y0+self.main.gui.annotations_delta[1],
                    f'{self.main.gui.scale_length:.3f} m',
                    fontsize=self.main.gui.annotations_fontsize, color='b',
                    picker=self.main.gui.picker)
            if hasattr(self, 'measured_text'):
                self.measured_text.set_text('')
        self.draw_idle()

    def remove_scale(self):
        """Remove scale from display."""
        for i, p in enumerate(self.ax.lines):
            if p.get_gid() == 'scale':
                self.ax.lines[i].remove()
        if hasattr(self, 'scale_text'):
            self.scale_text.set_text('')

    def add_measured_length(self):
        """Show measured length of line."""
        if self.main.gui.scale_length > 0:
            lineLen = self.main.gui.calibration_factor * np.sqrt(
                (self.main.gui.x1-self.main.gui.x0)**2 +
                (self.main.gui.y1-self.main.gui.y0)**2)
            lineTxt = f'{lineLen:.3f} m'
        else:
            lineTxt = 'NB - scale not defined'

        if hasattr(self, 'measured_text'):
            self.measured_text.set_position(
                [self.main.gui.x0+self.main.gui.annotations_delta[0],
                 self.main.gui.y0+self.main.gui.annotations_delta[1]])
            self.measured_text.set_text(lineTxt)
        else:
            self.measured_text = self.ax.text(
                self.main.gui.x0+self.main.gui.annotations_delta[0],
                self.main.gui.y0+self.main.gui.annotations_delta[1],
                lineTxt, fontsize=self.main.gui.annotations_fontsize, color='k')
        self.draw_idle()

    def add_area_highlight(self, x0, y0, width, height):
        """Add self.area_highlight when area selected in table.

        Parameters
        ----------
        x0 : int
        y0 : int
        width : int
        height : int
        """
        self.area_highlight = patches.Rectangle(
            (x0, y0), width, height,
            edgecolor='red', fill=False, gid='area_highlight',
            linewidth=self.main.gui.annotations_linethick + 2,
            linestyle='dotted')
        if len(self.ax.patches) > 0:
            for i, p in enumerate(self.ax.patches):
                if p.get_gid() == 'area_highlight':
                    self.ax.patches[i].remove()
        self.ax.add_patch(self.area_highlight)
        self.draw()

    def wall_highlight(self):
        """Highlight wall selected in table."""
        for i, p in enumerate(self.ax.lines):
            try:
                gid = int(p.get_gid())
                if gid == self.main.walls_tab.active_row:
                    p.set_markeredgewidth(3)
                else:
                    p.set_markeredgewidth(0)
            except ValueError:
                pass
        print('wall hightlight')
        self.draw_idle()

    def sourcepos_highlight(self):
        """Highlight source selected in table."""
        w = self.main.tabs.currentWidget()
        for i, p in enumerate(self.ax.lines):
            try:
                temp_gid = f'{w.modality}_{w.active_row}'
                if p.get_gid() == temp_gid:
                    p.set_markeredgewidth(3)
                elif p.get_gid() == 'point_release':
                    pass
                else:
                    p.set_markeredgewidth(0)
            except AttributeError:
                pass
        self.draw_idle()

    def CT_marker(self, rotation):
        """Add marker formed as a CT footprint rotated as stated."""
        verts = np.array([
           (0.45, 0.15), (0.45, -0.15), (0.15, -0.15), (0.15, -1.0),
           (-0.15, -1.0), (-0.15, -0.15), (-0.45, -0.15), (-0.45, 0.15),
           (0.45, 0.15)
        ])
        codes = [Path.MOVETO] + [Path.LINETO]*(len(verts) - 2) + [Path.CLOSEPOLY]
        marker = Path(verts, codes)

        correction_factor = 1.
        if rotation != 0:
            marker = marker.transformed(Affine2D().rotate_deg(-rotation))
            bbox = marker.get_extents().get_points()
            correction_factor = np.max(np.abs(bbox))

        return (marker, correction_factor)

    def set_CT_marker_properties(
            self, index=None, marker=None, highlight=False, hover=False):
        """Set CT marker properties of ax.lines[index].

        Parameters
        ----------
        index : int, optional
            index of CT marker in ax.lines. The default is None.
        marker : matplotlib 2Dline, optional
            the marker to change properties on. The default is None.
        highlight : bool, optional
            set properties on hightlight. The default is False.
        hover : TYPE, optional
            set properties on hover. The default is False.
        """
        if self.main.gui.calibration_factor is not None:
            size = (2.5 / self.main.gui.calibration_factor)
            # calibration factor = meters/pixel, assume iso to end of table CT 2.5m
        else:
            size = 30
        if marker is None:
            marker = self.ax.lines[index]

        gid = marker.get_gid()
        gid_split = gid.split('_')
        row = int(gid_split[1])
        rotation = self.main.CTsources_tab.table_list[row][5]
        if rotation != 0:
            _, correction_factor = self.CT_marker(rotation)
            size = size * correction_factor

        if hover:
            size = 1.1*size
        marker.set_markersize(size)
        marker.set_markerfacecolor('gray')
        marker.set_markeredgecolor('k')
        if highlight:
            marker.set_alpha(0.8)
        else:
            marker.set_alpha(0.5)

    def update_info_text(self, event):
        """Update self.info_text on hover."""
        self.info_text.set_position((event.xdata+20, event.ydata-20))
        row_txt = self.hovered_artist.get_gid()
        if '_' in row_txt:
            row_txt = row_txt.split('_')[1]
        try:
            row = int(row_txt)
        except ValueError:
            row = None
        if row is not None:
            text = ''
            table_list = self.main.tabs.currentWidget().table_list
            text = (
                f'Name: {table_list[row][1]}\n'
                f'Row: {row}\n'
                )
            if self.main.gui.current_tab == 'Areas':
                text = text + f'Occupancy: {table_list[row][-1]:.2f}'
            elif self.main.gui.current_tab == 'Walls':
                text = text + (
                    f'Material: {table_list[row][3]}\n'
                    f'Thickness: {table_list[row][-1]:.2f}mm'
                    )
            elif self.main.gui.current_tab == 'NM sources':
                text = text + (
                    f'Isotope: {table_list[row][3]}\n'
                    f'Activity: {table_list[row][5]}\n'
                    f'# per day: {table_list[row][-1]}'
                    )
            elif self.main.gui.current_tab == 'CT sources':
                text = text + (
                    f'kV source: {table_list[row][3]}\n'
                    f'kV correction: {table_list[row][-3]}\n'
                    f'mAs pr patient: {table_list[row][-2]}\n'
                    f'# per day: {table_list[row][-1]}'
                    )
            if text != '':
                self.info_text.set_text(text)
                self.info_text.set_visible(True)
                self.draw_idle()

    def update_annotations_fontsize(self, fontsize):
        """Refresh all annotation text elements with input fontsize."""
        for text in self.ax.texts:
            text.set_fontsize(fontsize)
        self.draw()

    def update_annotations_linethick(self, linethick):
        """Refresh all annotation line elements with input line thickness."""
        for line in self.ax.lines:
            line.set_linewidth(linethick)
        for patch in self.ax.patches:
            gid = patch.get_gid()
            if 'handle' not in gid:
                patch.set_linewidth(linethick)
        self.draw()

    def update_area_on_drag(self):
        """Update GUI when area dragged either by handles or not."""
        width = round(self.main.gui.x1 - self.main.gui.x0)
        height = round(self.main.gui.y1 - self.main.gui.y0)
        if self.drag_handle:
            gid_handle = self.current_artist.get_gid()
            half = self.main.gui.handle_size // 2
            row = int(self.hovered_artist.get_gid())
            x0, y0, w0, h0 = self.main.areas_tab.get_area_from_text(
                self.main.areas_tab.table_list[row][2])
            if gid_handle == 'handle_right':
                w0 = w0 + width
                self.current_artist.set_xy((x0 + w0 - half, y0 + h0 // 2 - half))
            elif gid_handle == 'handle_left':
                w0 = w0 - width
                x0 = x0 + width
                self.current_artist.set_xy((x0 - half, y0 + h0 // 2 - half))
            elif gid_handle == 'handle_top':
                h0 = h0 - height
                y0 = y0 + height
                self.current_artist.set_xy((x0 + w0 // 2 - half, y0 - half))
            else:
                h0 = h0 + height
                self.current_artist.set_xy((x0 + w0 // 2 - half, y0 + h0 - half))
            self.hovered_artist.set_xy((x0, y0))
            self.hovered_artist.set_width(w0)
            self.hovered_artist.set_height(h0)
        else:
            self.area_temp.set_width(np.abs(width))
            self.area_temp.set_height(np.abs(height))
            self.area_temp.set_xy((
                min(self.main.gui.x0, self.main.gui.x1),
                min(self.main.gui.y0, self.main.gui.y1)))
        self.draw_idle()

    def update_wall_on_drag(self):
        """Update GUI when picked wall handles dragged."""
        if self.drag_handle:
            gid_handle = self.current_artist.get_gid()
            half = self.main.gui.handle_size // 2
            xnow = round(self.main.gui.x1)
            ynow = round(self.main.gui.y1)
            row = int(self.hovered_artist.get_gid())
            x0, y0, x1, y1 = self.main.walls_tab.get_wall_from_text(
                self.main.walls_tab.table_list[row][2])
            start = True if 'start' in gid_handle else False
            if start:
                x0, y0 = xnow, ynow
            else:
                x1, y1 = xnow, ynow
            if self.main.gui.rectify:
                diff_x = abs(x0 - x1)
                diff_y = abs(y0 - y1)
                if diff_x > diff_y:  # keep y
                    if start:
                        y0 = y1
                    else:
                        y1 = y0
                else:  # keep x
                    if start:
                        x0 = x1
                    else:
                        x1 = x0
            if start:
                self.main.gui.x0, self.main.gui.y0 = x0, y0
                self.current_artist.set_xy((x0 - half, y0 - half))
            else:
                self.main.gui.x1, self.main.gui.y1 = x1, y1
                self.current_artist.set_xy((x1 - half, y1 - half))
            self.hovered_artist.set_data([x0, x1], [y0, y1])

            self.draw_idle()

    def update_source_on_drag(self):
        """Update GUI when picked point source dragged."""
        self.current_artist.set_data(
            round(self.main.gui.x1),
            round(self.main.gui.y1)
            )
        self.draw_idle()

    def floor_draw(self):
        """Draw or redraw all elements."""
        # reset
        #self.fig.clear()
        #if hasattr(self, 'ax'):
        self.ax.cla()
        #self.ax = self.fig.add_subplot(111)

        props = dict(boxstyle='round', facecolor='wheat', alpha=0.6, pad=1)
        self.info_text = self.ax.text(
            0, 0, '', fontsize=self.main.gui.annotations_fontsize, bbox=props)
        self.info_text.set_visible(False)
        self.image = self.ax.imshow(self.main.image, cmap='gray')
        self.ax.axis('off')

        self.image_overlay = self.ax.imshow(
            np.zeros(self.main.image.shape[0:2]), alpha=0)
        self.main.wVisual.overlay_selections_changed()
        self.draw_idle()


class FloorWidget(QWidget):
    """Class holding the widget containing the FloorCanvas with toolbars."""

    def __init__(self, main):
        super().__init__()

        self.main = main
        self.canvas = FloorCanvas(self.main)
        tbimg = NavToolBar(self.canvas, self)
        tbimgPos = PositionToolBar(self.canvas, self.main)
        tbimg.addWidget(tbimgPos)

        act_edit_annotations = QAction(
            QIcon(f'{os.environ[ENV_ICON_PATH]}edit.png'),
            'Edit annotations', self)
        act_edit_annotations.triggered.connect(self.edit_annotations)
        self.tool_imgsize = QToolButton()
        self.tool_imgsize.setToolTip('Maximize image')
        self.tool_imgsize.setIcon(QIcon(
            f'{os.environ[ENV_ICON_PATH]}layout_maximg.png'))
        self.tool_imgsize.clicked.connect(self.clicked_imgsize)
        self.tool_imgsize.setCheckable(True)
        tbimg.addAction(act_edit_annotations)
        tbimg.addWidget(self.tool_imgsize)

        vlo = QVBoxLayout()
        vlo.addWidget(tbimg)
        vlo.addWidget(self.canvas)
        self.setLayout(vlo)

    def edit_annotations(self):
        """Pop up dialog to edit annotations settings."""
        dlg = EditAnnotationsDialog(
            annotations=self.main.gui.annotations,
            annotations_linethick=self.main.gui.annotations_linethick,
            annotations_fontsize=self.main.gui.annotations_fontsize,
            canvas=self.canvas)
        res = dlg.exec()
        if res:
            ann, linethick, fontsize = dlg.get_data()
            self.main.gui.annotations = ann
            self.main.gui.annotations_linethick = linethick
            self.main.gui.annotations_fontsize = fontsize
        else:
            self.canvas.update_annotations_fontsize(
                self.main.gui.annotations_fontsize)
            self.canvas.update_annotations_linethick(
                self.main.gui.annotations_linethick)

    def clicked_imgsize(self):
        """Maximize or reset image size."""
        if self.tool_imgsize.isChecked():
            self.tool_imgsize.setIcon(QIcon(
                f'{os.environ[ENV_ICON_PATH]}layout_resetimg.png'))
            self.main.set_split_max_img()
        else:
            self.tool_imgsize.setIcon(QIcon(
                f'{os.environ[ENV_ICON_PATH]}layout_maximg.png'))
            self.main.reset_split_sizes()


class NavToolBar(NavigationToolbar2QT):
    """Matplotlib navigation toolbar with less buttons and no text."""

    def __init__(self, canvas, parent):
        super().__init__(canvas, parent)
        self.main = parent.main
        for x in self.actions():
            if x.text() in ['Back', 'Forward', 'Subplots']:#, 'Customize']:
                self.removeAction(x)

    def set_message(self, event):
        """Hide cursor position and value text."""
        pass

    def zoom(self, *args):
        """Override super zoom to set zoom flag."""
        if self.main.gui.zoom_active:
            self.main.gui.zoom_active = False
        else:
            self.main.gui.zoom_active = True
        super().zoom(*args)

    def release_zoom(self, event):
        """Override super().release_zoom to update wall-thickness."""
        super().release_zoom(event)
        self.canvas.on_zoom_changed()

    def home(self, *args):
        """Override super().home to update wall thickness."""
        super().home(*args)
        self.canvas.on_zoom_changed()

    def save_figure(self, *args):
        """Fix to avoid crash on self.canvas.parent() TypeError.

        from https://github.com/matplotlib/matplotlib/blob/main/lib/matplotlib/backends/backend_qt.py
        """
        filetypes = self.canvas.get_supported_filetypes_grouped()
        sorted_filetypes = sorted(filetypes.items())
        default_filetype = self.canvas.get_default_filetype()

        # startpath = os.path.expanduser(mpl.rcParams['savefig.directory'])
        # start = os.path.join(startpath, self.canvas.get_default_filename())
        filters = []
        selectedFilter = None
        for name, exts in sorted_filetypes:
            exts_list = " ".join(['*.%s' % ext for ext in exts])
            filter = f'{name} ({exts_list})'
            if default_filetype in exts:
                selectedFilter = filter
            filters.append(filter)
        filters = ';;'.join(filters)

        fname, filter = QFileDialog.getSaveFileName(
            self, 'Choose a filename to save to', '',
            filters, selectedFilter)
        if fname:
            try:
                self.canvas.figure.savefig(fname)
            except Exception as e:
                QMessageBox.critical(
                    self, "Error saving file", str(e))


class PositionToolBar(QWidget):
    """Toolbar for showing cursor position (x, y)."""

    def __init__(self, canvas, main):
        super().__init__()
        self.main = main
        hlo = QHBoxLayout()
        self.setLayout(hlo)
        self.lbl_xypos = QLabel('')
        hlo.addWidget(self.lbl_xypos)
        canvas.mpl_connect('motion_notify_event', self.on_move)

    def on_move(self, event):
        """When mouse cursor is moving in the canvas."""
        if event.inaxes and len(event.inaxes.get_images()) > 0:
            xpos = round(event.xdata)
            ypos = round(event.ydata)
            self.lbl_xypos.setText(f'xy = ({xpos}, {ypos})')
        else:
            self.lbl_xypos.setText('')


class InfoToolBar(QWidget):
    """Toolbar for showing cursor position and values."""

    def __init__(self, canvas, main):
        super().__init__()
        vlo = QVBoxLayout()
        self.main = main
        self.setLayout(vlo)
        self.lbl_occ = QLabel('Occupancy factor =')
        self.lbl_dose_total = QLabel('Total dose = - mSv')
        self.lbl_dose_nm = QLabel('NM dose = - mSv')
        self.lbl_doserate_nm = QLabel('NM doserate = - ' + '\u03bc' + 'Sv/h')
        self.lbl_dose_ct = QLabel('CT dose = - mSv')
        vlo.addWidget(self.lbl_occ)
        vlo.addWidget(self.lbl_dose_total)
        vlo.addWidget(self.lbl_dose_nm)
        vlo.addWidget(self.lbl_doserate_nm)
        vlo.addWidget(self.lbl_dose_ct)
        vlo.addStretch()

        canvas.mpl_connect('motion_notify_event', self.on_move)

    def on_move(self, event):
        """When mouse cursor is moving in the canvas."""
        if event.inaxes and len(event.inaxes.get_images()) > 0:
            xpos = round(event.xdata)
            ypos = round(event.ydata)
            self.lbl_occ.setText(
                f'Occupancy factor = {self.main.occ_map[ypos, xpos]:.2f}')
            fix = 'not implemented'
            self.lbl_dose_total.setText('Total dose = {fix} mSv')
            self.lbl_dose_nm.setText('NM dose = {fix} mSv')
            self.lbl_doserate_nm.setText('NM doserate = {fix} ' + '\u03bc' + 'Sv/h')
            self.lbl_dose_ct.setText('CT dose = {fix} mSv')
        else:
            self.lbl_occ.setText('Occupancy factor =')
            self.lbl_dose_total.setText('Total dose = - mSv')
            self.lbl_dose_nm.setText('NM dose = - mSv')
            self.lbl_doserate_nm.setText('NM doserate = - ' + '\u03bc' + 'Sv/h')
            self.lbl_dose_ct.setText('CT dose = - mSv')


class VisualizationWidget(QWidget):
    """GUI for settings on how to visualize data."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        self.hlo = QHBoxLayout()
        self.setLayout(self.hlo)

        self.gb_annotate = QGroupBox('Annotate...')
        self.gb_annotate.setFont(uir.FontItalic())
        self.gb_annotate.setMinimumWidth(round(0.15*self.main.gui.panel_width))
        self.btns_annotate = QButtonGroup()
        self.btns_annotate.setExclusive(False)
        vlo = QVBoxLayout()
        for i, txt in enumerate(ANNOTATION_OPTIONS):
            chbx = QCheckBox(txt)
            self.btns_annotate.addButton(chbx, i)
            chbx.setChecked(True)
            vlo.addWidget(chbx)
            chbx.clicked.connect(self.annotate_selections_changed)
        self.gb_annotate.setLayout(vlo)
        self.hlo.addWidget(self.gb_annotate)

        self.overlay_options = ['None', 'Occupancy factors', 'Dose', 'Max dose rate NM']
        self.gb_overlay = QGroupBox('Color overlay...')
        self.gb_overlay.setFont(uir.FontItalic())
        self.gb_overlay.setMinimumWidth(round(0.15*self.main.gui.panel_width))
        self.btns_overlay = QButtonGroup()
        vlo = QVBoxLayout()
        for i, txt in enumerate(self.overlay_options):
            rbtn = QRadioButton(txt)
            self.btns_overlay.addButton(rbtn, i)
            vlo.addWidget(rbtn)
            rbtn.clicked.connect(self.overlay_selections_changed)
        self.gb_overlay.setLayout(vlo)
        self.btns_overlay.button(0).setChecked(True)
        self.hlo.addWidget(self.gb_overlay)

        self.gb_dose = QGroupBox('Dose...')
        self.gb_dose.setFont(uir.FontItalic())
        self.gb_dose.setMinimumWidth(round(0.15*self.main.gui.panel_width))
        self.btns_dose = QButtonGroup()
        vlo = QVBoxLayout()
        for i, txt in enumerate([
                'Total dose',
                'NM dose',
                'CT dose',
                'Fluoro dose']):
            rbtn = QRadioButton(txt)
            self.btns_dose.addButton(rbtn, i)
            vlo.addWidget(rbtn)
            rbtn.clicked.connect(self.dose_selections_changed)
        self.gb_dose.setLayout(vlo)
        self.btns_dose.button(0).setChecked(True)
        self.hlo.addWidget(self.gb_dose)

        vlo_alpha = QVBoxLayout()
        self.hlo.addLayout(vlo_alpha)
        self.alpha_overlay = QSlider(Qt.Horizontal)
        self.alpha_overlay_value = QLabel(
            f'{100*self.main.gui.alpha_overlay:.0f} %')
        self.alpha_overlay.setRange(0, 100)
        self.alpha_overlay.setValue(50)
        self.alpha_overlay.valueChanged.connect(self.update_alpha_overlay)
        self.alpha_image = QSlider(Qt.Horizontal)
        self.alpha_image_value = QLabel(
            f'{100*self.main.gui.alpha_image:.0f} %')
        self.alpha_image.setRange(0, 100)
        self.alpha_image.setValue(100)
        self.alpha_image.valueChanged.connect(self.update_alpha_image)
        vlo_alpha.addWidget(uir.LabelItalic('Opacity image'))
        vlo_alpha.addWidget(self.alpha_image)
        vlo_alpha.addWidget(self.alpha_image_value)
        vlo_alpha.addSpacing(5)
        vlo_alpha.addWidget(uir.LabelItalic('Opacity overlay'))
        vlo_alpha.addWidget(self.alpha_overlay)
        vlo_alpha.addWidget(self.alpha_overlay_value)
        vlo_alpha.addStretch()

    def overlay_text(self):
        """Get selected overlay text."""
        return self.overlay_options[self.btns_overlay.checkedId()]

    def annotate_texts(self):
        """Get selected annotation options as list of str."""
        return [btn.text() for btn in self.btns_annotate.buttons() if btn.isChecked()]

    def annotate_selections_changed(self):
        """Update display when annotation selections change."""
        txts = self.annotate_texts()
        #TODO
        #['Scale', 'Areas', 'Walls', 'Wall thickness',
        #                   'NM sources', 'CT sources', 'FL sources']
        if 'Scale' in txts:
            try:
                self.main.wFloorDisplay.canvas.add_scale_highlight(
                    self.main.gui.scale_start[0], self.main.gui.scale_start[1],
                    self.main.gui.scale_end[0], self.main.gui.scale_end[1])
            except IndexError:
                pass
        else:
            self.main.wFloorDisplay.canvas.remove_scale()

        if 'Areas' in txts:
            self.main.areas_tab.update_occ_map()
        else:
            if len(self.main.wFloorDisplay.canvas.ax.patches) > 0:
                for patch in self.main.wFloorDisplay.canvas.ax.patches:
                    patch.remove()
            self.main.wFloorDisplay.canvas.draw_idle()

        if 'Walls' in txts:
            self.main.walls_tab.update_wall_annotations()
        else:
            for line in self.main.wFloorDisplay.canvas.ax.lines:
                try:
                    int_id = int(line.get_gid())
                except ValueError:
                    int_id = None
                if int_id is not None:
                    line.remove()
            self.main.wFloorDisplay.canvas.draw_idle()

        remove_modalities = []
        if 'NM sources' in txts:
            self.main.NMsources_tab.update_source_annotations()
            self.main.wFloorDisplay.canvas.draw_idle()
        else:
            remove_modalities.append('NM')

        if len(remove_modalities):
            for line in self.main.wFloorDisplay.canvas.ax.lines:
                for mod in remove_modalities:
                    if mod in line.get_gid():
                        line.remove()
            self.main.wFloorDisplay.canvas.draw_idle()

    def overlay_selections_changed(self):
        """Update display when Overlay selections change."""
        cmap = 'rainbow'
        vmin = 0.
        vmax = 1.
        if self.overlay_text() == 'None':
            overlay = np.zeros(self.main.image.shape)
        elif self.overlay_text() == 'Occupancy factors':
            self.main.areas_tab.update_occ_map()
            overlay = self.main.occ_map
            cmap = 'rainbow'
            vmin = 0.
            vmax = 1.
        elif self.overlay_text() == 'Dose':
            self.main.wFloorDisplay.canvas.update_dose_overlay()
            overlay = None
        else:  # Doserate max NM
            #TODO overlay = self.main.dose_dict[]
            pass
        if overlay is not None:
            self.main.wFloorDisplay.canvas.image_overlay.set_data(overlay)
            self.main.wFloorDisplay.canvas.image_overlay.set(cmap=cmap)
            self.main.wFloorDisplay.canvas.image_overlay.set_clim(vmin=vmin, vmax=vmax)
        self.main.wFloorDisplay.canvas.draw_idle()

    def dose_selections_changed(self):
        """Update display when Dose selections change."""
        pass  #TODO

    def set_alpha_overlay(self, value):
        """Set opacity (alpha) overlay value and update related parameters/gui."""
        self.main.gui.alpha_overlay = value
        self.alpha_overlay.setValue(100*value)
        self.alpha_overlay_value.setText(f'{100*value:.0f} %')
        self.main.wFloorDisplay.canvas.image_overlay.set(
            alpha=self.main.gui.alpha_overlay)
        self.main.wFloorDisplay.canvas.draw()

    def update_alpha_overlay(self):
        """Set opacity (alpha) overlay from slider and update floor display."""
        self.alpha_overlay_value.setText(f'{self.alpha_overlay.value():.0f} %')
        self.main.gui.alpha_overlay = 0.01 * self.alpha_overlay.value()
        self.main.wFloorDisplay.canvas.image_overlay.set(
            alpha=self.main.gui.alpha_overlay)
        self.main.wFloorDisplay.canvas.draw()

    def update_alpha_image(self):
        """Set opacity (alpha) image from slider and update floor display."""
        self.alpha_image_value.setText(f'{self.alpha_image.value():.0f} %')
        self.main.gui.alpha_image = 0.01 * self.alpha_image.value()
        self.main.wFloorDisplay.canvas.image.set(
            alpha=self.main.gui.alpha_image)
        self.main.wFloorDisplay.canvas.draw()


class CalculateWidget(QWidget):
    """GUI for calculation options."""

    def __init__(self, main):
        super().__init__()
        self.main = main
        hlo = QHBoxLayout()
        self.setLayout(hlo)
        vlo_image_values = QVBoxLayout()
        hlo.addLayout(vlo_image_values)
        vlo_image_values.addWidget(uir.LabelHeader('Values at cursor position', 4))
        info_tb = InfoToolBar(self.main.wFloorDisplay.canvas, self.main)
        vlo_image_values.addWidget(info_tb)

        hlo.addSpacing(10)
        hlo.addWidget(uir.VLine())
        hlo.addSpacing(10)

        vlo = QVBoxLayout()
        hlo.addLayout(vlo)
        vlo.addWidget(uir.LabelHeader("Calculate", 4))

        self.gb_floor = QGroupBox('Calculate dose for floor...')
        self.gb_floor.setFont(uir.FontItalic())
        self.btns_floor = QButtonGroup()
        vlo_gb = QVBoxLayout()
        for i, txt in enumerate([
                'Floor above',
                'This floor',
                'Floor below']):
            rbtn = QRadioButton(txt)
            self.btns_floor.addButton(rbtn, i)
            vlo_gb.addWidget(rbtn)
            rbtn.clicked.connect(self.main.calculate_dose)
        self.gb_floor.setLayout(vlo_gb)
        self.btns_floor.button(1).setChecked(True)

        self.working_days = QSpinBox(minimum=1, maximum=1000,
                                     value=self.main.general_values.working_days)
        self.working_days.editingFinished.connect(
            self.main.update_dose_days)
        hlo_working_days = QHBoxLayout()
        hlo_working_days.addWidget(QLabel('Sum dose (mSv) for '))
        hlo_working_days.addWidget(self.working_days)
        hlo_working_days.addWidget(QLabel(' working days'))
        hlo_working_days.addStretch()
        vlo.addLayout(hlo_working_days)
        self.chk_correct_thickness_geometry = QCheckBox(
            'Correct geometrically for material thickness.')
        self.chk_correct_thickness_geometry.setChecked(
            self.main.general_values.correct_thickness)
        hlo_correct = QHBoxLayout()
        vlo.addLayout(hlo_correct)
        hlo_correct.addWidget(self.chk_correct_thickness_geometry)
        hlo_correct.addWidget(uir.InfoTool(
            'Correct wall thickness geometrically as the rays actually have a longer '
            'path through the material when oblique to the wall.<br>'
            'NB might underestimate path length of scattered photons.<br>'
            'These corrections are ignored for oblique walls.',
            parent=self))

        vlo.addSpacing(20)
        btn_calculate = QPushButton('Calculate dose')
        btn_calculate.toggled.connect(self.main.calculate_dose)
        hlo_calc = QHBoxLayout()
        vlo.addLayout(hlo_calc)
        hlo_calc.addWidget(self.gb_floor)
        hlo_calc.addWidget(btn_calculate)
