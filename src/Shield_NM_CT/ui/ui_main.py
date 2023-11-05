# -*- coding: utf-8 -*-
"""User interface for main window of imageQC.

@author: EllenWasbo
"""
import sys
import os
from io import BytesIO
import numpy as np
import copy
from time import time
from dataclasses import dataclass
import pandas as pd
from pathlib import Path
import shutil
import webbrowser

from PyQt5.QtGui import QIcon, QPixmap, QKeyEvent
from PyQt5.QtCore import Qt, QTimer, QFile, QItemSelectionModel
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QButtonGroup, QFormLayout,
    QScrollArea, QTabWidget, QTableWidget,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
    QRadioButton, QCheckBox, QComboBox, QSlider, QToolButton,
    QMenu, QAction, QToolBar, QMessageBox, QFileDialog
    )
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg, NavigationToolbar2QT)
from matplotlib.figure import Figure
import matplotlib.image as mpimg
from matplotlib.patches import Rectangle
from matplotlib.widgets import RectangleSelector

# Shield_NM_CT block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    VERSION, ENV_ICON_PATH, ENV_CONFIG_FOLDER, ENV_USER_PREFS_PATH, ANNOTATION_OPTIONS)
from Shield_NM_CT.config import config_func as cff
from Shield_NM_CT.ui import messageboxes
from Shield_NM_CT.ui import settings
import Shield_NM_CT.ui.reusable_widgets as uir
from Shield_NM_CT.ui.ui_dialogs import AboutDialog, EditAnnotationsDialog
import Shield_NM_CT.resources
# Shield_NM_CT block end

#TODO these into userpref or config_folder
CSV_SEP = ';'
CSV_DEC = ','


@dataclass
class GuiData():
    """Class to keep variables."""

    image_path = ''
    load_path = ''
    scale_start = ()
    scale_end = ()
    scale_length = 0.
    calibration_factor = 1.  # meters/pixel
    x0 = 0.0  # mouse x coordinate FloorCanvas.on_press
    x1 = 0.0  # mouse x coordinate on_motion (if already pressed) and on_release
    y0 = 0.0  # same as above for y coordinate
    y1 = 0.0
    current_tab = 'Scale'
    annotations = True
    annotations_fontsize = 15
    annotations_linethick = 3
    annotations_delta = (20, 20)
    handle_size = 10
    alpha_image = 1.0
    alpha_overlay = 0.5
    panel_width = 400
    panel_height = 700
    char_width = 7


class MainWindow(QMainWindow):
    """Class main window of ShieldNMCT."""

    def __init__(self, scX=1400, scY=700, char_width=7,
                 developer_mode=False, warnings=[]):
        super().__init__()

        self.image = np.zeros(2)
        self.occ_map = np.zeros(2)
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
        self.tabs.currentChanged.connect(self.new_tab_selection)
        self.scale_tab = ScaleTab(self)
        self.areas_tab = AreasTab(self)
        self.walls_tab = WallsTab(self)
        self.NMsources_tab = NMsourcesTab(self)
        #TODO self.CTsources_tab = CTsources_tab(self)
        #TODO self.FLsources_tab = FLsources_tab(self)
        self.tabs.addTab(self.scale_tab, "Scale")
        self.tabs.addTab(self.areas_tab, "Areas")
        self.tabs.addTab(self.walls_tab, "Walls")
        self.tabs.addTab(self.NMsources_tab, "NM sources")
        #TODOself.tabs.addTab(self.CTsources_tab, "CT sources")
        #TODOself.tabs.addTab(self.FLsources_tab, "Fluoro sources")

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
        _, _, self.general_values = cff.load_settings(fname='general_values')

        if after_edit_settings:
            self.NMsources_tab.update_isotopes()
            self.walls_tab.update_materials()
            self.scale_tab.update_material_lists()

    def update_image(self):
        """Load image from file or default, reset related maps."""
        if self.gui.image_path == '':
            self.image = self.default_floorplan
        else:
            self.image = mpimg.imread(self.gui.image_path)

        # initiate maps
        if self.occ_map.size < 3:
            self.occ_map = np.ones(self.image.shape[0:2], dtype=float)
            try:
                self.areas_tab.update_occ_map()
            except AttributeError:
                pass
            self.ct_dose_map = np.zeros(self.image.shape[0:2], dtype=float)

    def reset_dose(self, floor=None):
        #TODO reset if floor = None, else reset if current floor is floor
        #also reset NM dose
        pass

    def calculate_dose(self):
        pass

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
                if self.tabs.currentWidget().cellwidget_is_text is False:
                    try:
                        self.tabs.currentWidget().add_row()
                    except AttributeError:
                        pass
            elif event.key() == Qt.Key_Delete:
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

    def new_tab_selection(self, i):
        """Remove temporary, tab-specific annotations + more settings."""
        if hasattr(self.tabs.currentWidget(), 'label'):
            self.gui.current_tab = self.tabs.currentWidget().label
            if hasattr(self.wFloorDisplay.canvas, 'ax'):
                if len(self.wFloorDisplay.canvas.ax.patches) > 0:
                    for i, p in enumerate(
                            self.wFloorDisplay.canvas.ax.patches):
                        if p.get_gid() == 'area_temp':
                            self.wFloorDisplay.canvas.ax.patches[i].remove()
                            break
                if len(self.wFloorDisplay.canvas.ax.lines) > 0:
                    for i, p in enumerate(
                            self.wFloorDisplay.canvas.ax.lines):
                        if p.get_gid() in [
                                'line_temp',
                                'wall_selected',
                                'source_selected']:
                            try:
                                self.wFloorDisplay.canvas.ax.lines[i].remove()
                            except IndexError:
                                pass
                self.blockSignals(True)
                if self.gui.current_tab in ANNOTATION_OPTIONS:
                    self.wVisual.btns_annotate.button(
                        ANNOTATION_OPTIONS.index(self.gui.current_tab)).setChecked(True)
                if self.gui.current_tab == 'Areas':
                    self.wVisual.set_alpha_overlay(0.2)
                    self.wVisual.btns_overlay.button(1).setChecked(True)
                    self.areas_tab.update_occ_map()
                else:  #TODO more options if dose
                    self.wVisual.btns_overlay.button(0).setChecked(True)
                self.blockSignals(False)
                self.wFloorDisplay.canvas.draw()

    def load_floor_plan_image(self):
        """Open image and update GUI."""
        fname = QFileDialog.getOpenFileName(
            self, 'Load floor plan image',
            os.path.join(self.user_prefs.default_path, 'floorplan.png'),
            "PNG files (*.png);;All files (*)")

        if len(fname[0]) > 0:
            self.gui.image_path = fname[0]
            self.update_image()
            self.wFloorDisplay.canvas.floor_draw()

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
        self.fig.subplots_adjust(0., 0., 1., 1.)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.main = main
        self.setParent(main)

        self.font = {
            'family': 'serif', 'color': 'darkred', 'weight': 'normal', 'size': 16}

        self.area_temp = Rectangle((0, 0), 1, 1)
        self.area_highlight = Rectangle((0, 0), 1, 1)
        self.current_artist = None  # picked artist
        self.hovered_artist = None  # artist detected on hover
        self.mouse_pressed = False
        self.info_text = None
        self.handles_activated = False  # True if handles for editing shown
        self.drag_handle = False  # True if handles for editing by drag picked
        # INFO gid used for different artists:
        '''
        'line_temp':	 dotted line for marked new line
        'scale': line for currently defined scale (line)
        'scale_text': text for currently defined length of scale line
        'measured_text': text for length of line_temp if scale set
        'area_temp': dotted Rectangle for marked area
        'area_highlight': red dottet Rectangle for selected row in Areas table
        'wall_selected':	
        'source_selected':
        'point_release'
        '{int}': row number in table for current tab
        'handle_?': pickable Rectangle to drag position of line (_start, _end)
                        or of area (_left, _right, _top, _bottom)
        '''

        self.mpl_connect("button_press_event", self.on_press)
        self.mpl_connect("button_release_event", self.on_release)
        self.mpl_connect("motion_notify_event", self.on_motion)
        self.mpl_connect("pick_event", self.on_pick)

    def on_press(self, event):
        """When mouse button pressed."""
        if hasattr(self, 'ax'):
            self.mouse_pressed = True
            self.main.gui.x0, self.main.gui.y0 = event.xdata, event.ydata
            self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata

            if self.main.gui.current_tab == 'Areas':
                self.area_temp = Rectangle(
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
                self.ax.plot([self.main.gui.x0, self.main.gui.x1],
                             [self.main.gui.y0, self.main.gui.y1],
                             'k--', linewidth=2., gid='line_temp')
            else:
                pass

    def on_motion(self, event):
        """When mouse pressed and moved."""
        if self.mouse_pressed:
            if self.main.gui.x0 is not None:
                self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata
                if self.main.gui.current_tab == 'Areas':
                    self.update_area_on_drag()
                elif self.main.gui.current_tab in ['Scale', 'Walls']:
                    for p in self.ax.lines:
                        if p.get_gid() == 'line_temp':
                            p.set_data(
                                [self.main.gui.x0, self.main.gui.x1],
                                [self.main.gui.y0, self.main.gui.y1])
                            break
                    if self.main.gui.current_tab == 'Scale':
                        self.add_measured_length()

                    self.draw_idle()
        else:  # on hover - make thicker + annotate with info_text
            if self.handles_activated == False and event.inaxes == self.ax:
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

                if prev_hovered_artist != self.hovered_artist:  # redraw
                    if prev_hovered_artist != None:  # reset linethickness
                        prev_hovered_artist.set_linewidth(
                            self.main.gui.annotations_linethick)
                        self.draw_idle()
                    if self.hovered_artist is None:
                        self.info_text.set_visible(False)
                        self.draw_idle()
                    else:
                        self.hovered_artist.set_linewidth(
                            self.main.gui.annotations_linethick + 2)
                        self.update_info_text(event)
                        self.draw_idle()

    def on_release(self, event):
        """When mouse button released."""
        self.mouse_pressed = False
        self.main.gui.x1, self.main.gui.y1 \
            = event.xdata, event.ydata

        if self.main.gui.x1 is not None:
            width = np.abs(self.main.gui.x1 - self.main.gui.x0)
            height = np.abs(self.main.gui.y1 - self.main.gui.y0)
        else:
            width = 0
            height = 0
        if self.main.gui.current_tab in ['Areas', 'Scale', 'Walls']:
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
                    self.ax.plot(event.xdata, event.ydata,
                                 'ko', markersize=10, gid='point_release')

        self.draw()

    def on_pick(self, event):
        """When mouse button picking objects."""
        if self.current_artist != event.artist:
            self.current_artist = event.artist
            gid = self.current_artist.get_gid()
            if 'handle' in gid:
                self.drag_handle = True
            else:
                try:
                    row = int(gid)
                except ValueError:
                    row = None
                if row is not None:
                    self.main.tabs.currentWidget().select_row_col(row, 1)
                    # Create handle_ to drag
                    if isinstance(self.current_artist, Rectangle):
                        self.current_artist.set_picker(False)
                        [xmin, ymin], [xmax, ymax] = (
                            self.current_artist.get_bbox().get_points())
                        xmid = (xmax + xmin) // 2
                        ymid = (ymax + ymin) // 2
                        half = self.main.gui.handle_size // 2
                        handles = [ # gid, pos
                            ('handle_left', (xmin-half, ymid-half)),
                            ('handle_top', (xmid-half, ymin-half)),
                            ('handle_right', (xmax-half, ymid-half)),
                            ('handle_bottom', (xmid-half, ymax-half))
                             ]
                    else:
                        data = self.current_artist.get_data()
                        print(f'data {gid} {data}')
                        handles = [ #gid, pos
                            ('handle_start', (100, 100)),
                            ('handle_end', (100, 100))
                            ]
                    print(f'add handles gid = {gid}')
                    for handle in handles:
                        self.ax.add_patch(
                            Rectangle(
                                handle[1],
                                self.main.gui.handle_size, self.main.gui.handle_size,
                                edgecolor='black', facecolor='white',
                                linewidth=2, fill=True,
                                picker=True, gid=handle[0])
                            )
                    self.handles_activated = True
                    self.draw_idle()

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
            print(index_handles)
            for i in index_handles:
                self.ax.patches[i].remove()
        if self.hovered_artist:
            self.hovered_artist.set_picker(True)
            self.hovered_artist = None
        self.current_artist = None
        self.handles_activated = False
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
            self.main.areas_tab.table_list[active_row][2] = pos_string
            w = self.main.areas_tab.table.cellWidget(active_row, 2)
            w.setText(pos_string)
            self.main.areas_tab.update_occ_map()

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
                     'b', marker='|', linewidth=2., gid='scale', picker=6)
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
                    picker=6)
            if hasattr(self, 'measured_text'):
                self.measured_text.set_text('')
        self.draw()

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
        self.draw()

    def add_area_highlight(self, x0, y0, width, height):
        """Add self.area_highlight when area selected in table.

        Parameters
        ----------
        x0 : int
        y0 : int
        width : int
        height : int
        """
        self.area_highlight = Rectangle(
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

    def add_wall_highlight(self, x0, y0, x1, y1):
        """Highlight wall selected in table.

        Parameters
        ----------
        x0 : int
        y0 : int
        x1 : int
        y1 : int
        """
        for i, p in enumerate(self.ax.lines):
            if p.get_gid() == 'wall_selected':
                self.ax.lines[i].remove()
        self.ax.plot([x0, x1], [y0, y1],
                     'r--', marker='.', linewidth=2., gid='wall_selected')
        self.draw()


    def add_sourcepos_highlight(self, x, y):
        """Highlight source selected in table.

        Parameters
        ----------
        x : int
        y : int
        """
        for i, p in enumerate(self.ax.lines):
            if p.get_gid() == 'source_selected':
                self.ax.lines[i].remove()
        self.ax.plot(x, y, 'ro', markersize=15,  gid='source_selected')
        self.draw()

    def update_info_text(self, event):
        """Update self.info_text on hover."""
        self.info_text.set_position((event.xdata+20, event.ydata-20))
        try:
            row = int(self.hovered_artist.get_gid())
        except ValueError:
            row = None
        if row is not None:
            text = ''
            if self.main.gui.current_tab == 'Areas':
                text = (
                    f'Name: {self.main.areas_tab.table_list[row][1]}\n'
                    f'Row: {row}\n'
                    f'Occupancy: {self.main.areas_tab.table_list[row][-1]:.2f}'
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
            print('---')
            print(x0, y0, w0, h0, width, height, gid_handle)
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
            print(x0, y0, w0, h0)
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

    def floor_draw(self, reload_image=False):
        """Draw or redraw all elements."""
        da = self.main.gui
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        props = dict(boxstyle='round', facecolor='wheat', alpha=0.6, pad=1)
        self.info_text = self.ax.text(
            0, 0, '', fontsize=self.main.gui.annotations_fontsize, bbox=props)
        self.info_text.set_visible(False)

        if reload_image:
            self.main.update_image()
        self.image = self.ax.imshow(self.main.image, cmap='gray')
        self.ax.axis('off')

        try:
            overlay_text = self.main.wVisual.overlay_text()
        except AttributeError:
            overlay_text = 'None'
        if overlay_text == 'Occupancy factors':
            self.image_overlay = self.ax.imshow(
                self.main.occ_map,
                alpha=self.main.gui.alpha_overlay,
                cmap='rainbow', vmin=0., vmax=1.)
        elif overlay_text == 'None':
            self.image_overlay = self.ax.imshow(np.zeros(self.main.image.shape))
        else:
            pass #TODO

        self.draw()


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
        self.canvas.floor_draw(reload_image=True)

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
        for x in self.actions():
            if x.text() in ['Back', 'Forward', 'Subplots', 'Customize']:
                self.removeAction(x)

    def set_message(self, event):
        """Hide cursor position and value text."""
        pass


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
        #self.calibration_factor = self.main.gui.calibration_factor

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
            self.main.wFloorDisplay.canvas.draw()

    def overlay_selections_changed(self):
        """Update display when Overlay selections change."""
        if self.overlay_text() == 'None':
            overlay = np.zeros(self.main.image.shape)
        elif self.overlay_text() == 'Occupancy factors':
            overlay = copy.deepcopy(self.main.occ_map)
            cmap = 'rainbow'
            vmin = 0.
            vmax = 1.
        elif self.overlay_text() == 'Dose':
            pass #TODO which dose
        self.main.wFloorDisplay.canvas.image_overlay.set_data(overlay)
        self.main.wFloorDisplay.canvas.image_overlay.set(
            cmap=cmap, vmin=vmin, vmax=vmax)
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

        self.working_days = QSpinBox(minimum=0, maximum=1000,
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
        except AttributeError: # Scale missing methods as toolbar hidden
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
            self.main.reset_dose()

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
                    print('table_list before pop')
                    print(self.table_list)
                    self.table.removeRow(row)
                    self.table_list.pop(row)
                    print('table_list after pop')
                    print(self.table_list)
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
            x = 0
            y = 0

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
                df.to_csv(path, sep=CSV_SEP, decimal=CSV_DEC)

    def import_csv(self, path='', ncols_expected=5):
        """Import table from csv."""
        if path == '':
            fname = QFileDialog.getOpenFileName(
                self, 'Import table', filter="CSV file (*.csv)")
            path = fname[0]

        if len(path) > 0:
            df = pd.read_csv(path, sep=CSV_SEP, decimal=CSV_DEC)
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
            if self.main.gui.calibration_factor > 0.:
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
        print('update_occ_map')
        self.main.occ_map = np.ones(self.main.occ_map.shape)
        if len(self.main.wFloorDisplay.canvas.ax.patches) > 0:
            index_patches = []
            for i, patch in enumerate(self.main.wFloorDisplay.canvas.ax.patches):
                index_patches.append(i)
            if len(index_patches) > 0:
                index_patches.reverse()
                for i in index_patches:
                    self.main.wFloorDisplay.canvas.ax.patches[i].remove()
                print(f'remove {index_patches}')
        self.main.wFloorDisplay.canvas.reset_hover_pick()
        print(f'table_list {self.table_list}')
        areas_this = []
        print('table widgets as list')
        print(self.get_table_as_list()[1:])
        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x0, y0, width, height = self.get_area_from_text(tabitem.text())
                print(x0, y0, width, height)
                self.main.occ_map[y0:y0+height, x0:x0+width] = self.table_list[i][3]
                areas_this.append(Rectangle(
                    (x0, y0), width, height, edgecolor='blue',
                    linewidth=self.main.gui.annotations_linethick, fill=False,
                    picker=True, gid=f'{i}'))
                print(f'add gid {i}')
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
            self, row=row, col=4, max_val=400., step=1.0))

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
            self.highlight_selected_in_image()
            # TODO: self.main.update_doses()

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

    def highlight_selected_in_image(self):
        """Highlight area in image if area positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x0, y0, x1, y1 = self.get_wall_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.add_wall_highlight(
                x0, y0, x1, y1)

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
                '   - # pr workday = number of procedures pr working day. '
                'Dose multiplied with number of working days specified above.'
                ),
            btn_get_pos_text='Get source coordinates as marked in image')

        self.label = 'NM sources'
        self.main = main
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Source name', 'x,y', 'Isotope', 'In patient',
             'A0 (MBq)', 't1 (hours)', 'duration (hours)', 'Rest void',
             '# pr workday'])
        self.empty_row = [True, '', '', 'F-18', True, '0.0', '0.0', '0.0',
                          '1.0', '0']
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
        self.table.setColumnWidth(7, 17*self.main.gui.char_width)
        self.table.setColumnWidth(8, 13*self.main.gui.char_width)
        self.table.setColumnWidth(9, 15*self.main.gui.char_width)

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
            self, row=row, col=9, max_val=100, step=1, decimals=0))

    def update_isotopes(self):
        """Update ComboBox of all rows when list of isotopes changed in settings."""
        self.isotope_strings = [x.label for x in self.main.isotopes]
        for row in range(self.table.rowCount()):
            self.table.setCellWidget(row, 3, uir.CellCombo(
                self, self.isotope_strings, row=row, col=3))

    def get_pos(self):
        """Get positions for element as defined in figure."""
        if self.active_row > -1:
            text = (
                f'{self.main.gui.x1:.0f}, '
                f'{self.main.gui.y1:.0f}'
                )
            tabitem = self.table.cellWidget(self.active_row, 2)
            tabitem.setText(text)
            self.table_list[self.active_row][2] = text
            self.highlight_selected_in_image()
            self.update_NM_dose()

    def highlight_selected_in_image(self):
        """Highlight source position in image if positions given."""
        if self.active_row > -1:
            tabitem = self.table.cellWidget(self.active_row, 2)
            x, y = self.get_pos_from_text(tabitem.text())
            self.main.wFloorDisplay.canvas.add_sourcepos_highlight(x, y)

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
            pass
            # TODO: update floor display

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