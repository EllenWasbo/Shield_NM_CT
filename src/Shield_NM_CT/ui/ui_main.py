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

from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QTimer, QFile, QItemSelectionModel
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QButtonGroup, QFormLayout,
    QScrollArea, QTabWidget, QTableWidget,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
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
    VERSION, ENV_ICON_PATH, ENV_CONFIG_FOLDER, ENV_USER_PREFS_PATH)
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
    map_density = 0.5
    occ_density = 0.2
    dose_density = 0.7
    show = [True]*7
    x0 = 0.0
    x1 = 0.0
    y0 = 0.0
    y1 = 0.0
    currentTab = 'Scale'
    wall_materials = ['Lead', 'Concrete']  #TODO from settings
    annotations = True
    annotations_font_size = 15
    annotations_line_thick = 3
    annotations_delta = (20, 20)
    panel_width = 400
    panel_height = 700
    char_width = 7


class MainWindow(QMainWindow):
    """Class main window of ShieldNMCT."""

    def __init__(self, scX=1400, scY=700, char_width=7,
                 developer_mode=False, warnings=[]):
        super().__init__()

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
        self.gui.annotations_line_thick = self.user_prefs.annotations_line_thick
        self.gui.annotations_font_size = self.user_prefs.annotations_font_size

        self.occ_map = np.zeros(2)
        self.ct_dose_map = np.zeros(2)

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
        self.wVisualization = VisualizationWidget(self)
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
        lo_btm.addWidget(self.wVisualization)

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

    def reset_dose(self, floor=2):
        #TODO reset if current floor is floor
        pass

    def calculate_dose(self):
        pass

    def update_dose_days(self):
        #TODO - number of working days changed - update dose if exists
        #self.wCalculate.working_days.value()
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
        if hasattr(self.tabs.currentWidget(), 'label'):
            self.gui.currentTab = self.tabs.currentWidget().label
            if hasattr(self.wFloorDisplay.FloorCanvas, 'ax'):
                if len(self.wFloorDisplay.FloorCanvas.ax.patches) > 0:
                    for i, p in enumerate(
                            self.wFloorDisplay.FloorCanvas.ax.patches):
                        if p.get_gid() == 'area_temp':
                            self.wFloorDisplay.FloorCanvas.ax.patches[i].remove()
                            break
                if len(self.wFloorDisplay.FloorCanvas.ax.lines) > 0:
                    for i, p in enumerate(
                            self.wFloorDisplay.FloorCanvas.ax.lines):
                        if p.get_gid() in [
                                'line_temp',
                                'wall_selected',
                                'source_selected']:
                            try:
                                self.wFloorDisplay.FloorCanvas.ax.lines[i].remove()
                            except IndexError:
                                pass
                self.wFloorDisplay.FloorCanvas.draw()

    def load_floor_plan_image(self):
        """Open image and update GUI."""
        fname = QFileDialog.getOpenFileName(
            self, 'Load floor plan image',
            os.path.join(self.user_prefs.default_path, 'floorplan.png'),
            "PNG files (*.png);;All files (*)")

        if len(fname[0]) > 0:
            self.gui.image_path = fname[0]
            self.refresh_floor_display()

    def refresh_floor_display(self):
        """Refresh floor display - generally only once - else only updated."""
        if len(self.gui.image_path) > 0:
            self.wFloorDisplay.FloorCanvas.floor_draw()
            # and the overlays

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
        self.areas_tab.table.setRowCount(0)
        self.areas_tab.add_cell_widgets(0)
        self.areas_tab.table_list.append(
            copy.deepcopy(self.areas_tab.empty_row))
        self.wFloorDisplay.FloorCanvas.floor_draw()

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
                self.wFloorDisplay.FloorCanvas.floor_draw()
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
        self.fig = Figure()#figsize=(1.5, 1.5))
        self.fig.subplots_adjust(0., 0., 1., 1.)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.main = main
        self.setParent(main)

        self.font = {
            'family': 'serif',
            'color': 'darkred',
            'weight': 'normal',
            'size': 16
        }
        self.area_temp = Rectangle((0, 0), 1, 1)
        self.area_highlight = Rectangle((0, 0), 1, 1)

        self.mouse_pressed = False

        self.mpl_connect("button_press_event", self.on_press)
        self.mpl_connect("button_release_event", self.on_release)
        self.mpl_connect("motion_notify_event", self.on_motion)

    def on_press(self, event):
        """When mouse button pressed."""
        if hasattr(self, 'ax'):
            self.mouse_pressed = True
            self.main.gui.x0, self.main.gui.y0 = event.xdata, event.ydata
            self.main.gui.x1, self.main.gui.y1 = event.xdata, event.ydata

            if self.main.gui.currentTab == 'Areas':
                self.area_temp = Rectangle((0, 0), 1, 1,
                                           edgecolor='k', linestyle='--',
                                           linewidth=2., fill=False,
                                           gid='area_temp')
                if len(self.ax.patches) > 0:
                    for i, p in enumerate(self.ax.patches):
                        if p.get_gid() == 'area_temp':
                            self.ax.patches[i].remove()
                self.ax.add_patch(self.area_temp)
                self.draw()
            elif self.main.gui.currentTab in ['Scale', 'Walls']:
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
                if self.main.gui.currentTab == 'Areas':
                    width = np.abs(self.main.gui.x1 - self.main.gui.x0)
                    height = np.abs(self.main.gui.y1 - self.main.gui.y0)
                    self.area_temp.set_width(width)
                    self.area_temp.set_height(height)
                    self.area_temp.set_xy((
                        min(self.main.gui.x0, self.main.gui.x1),
                        min(self.main.gui.y0, self.main.gui.y1)))

                elif self.main.gui.currentTab in ['Scale', 'Walls']:
                    for p in self.ax.lines:
                        if p.get_gid() == 'line_temp':
                            p.set_data(
                                [self.main.gui.x0, self.main.gui.x1],
                                [self.main.gui.y0, self.main.gui.y1])
                            break
                    if self.main.gui.currentTab == 'Scale':
                        self.add_measured_length()

                self.draw()

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
        if (width + height) > 20:
            if self.main.gui.currentTab == 'Areas':
                self.area_temp.set_width(width)
                self.area_temp.set_height(height)
                self.area_temp.set_xy((
                    min(self.main.gui.x0, self.main.gui.x1),
                    min(self.main.gui.y0, self.main.gui.y1)))
            elif self.main.gui.currentTab in ['Scale', 'Walls']:
                for p in self.ax.lines:
                    if p.get_gid() == 'line_temp':
                        p.set_data(
                            [self.main.gui.x0, self.main.gui.x1],
                            [self.main.gui.y0, self.main.gui.y1])
                        break
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
            edgecolor='red', fill=False, gid='area_highlight')
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
                     'b', marker='|', linewidth=2., gid='scale')
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
                    fontsize=self.main.gui.annotations_font_size, color='b')
            if hasattr(self, 'measured_text'):
                self.measured_text.set_text('')
        self.draw()

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
                lineTxt, fontsize=self.main.gui.annotations_font_size, color='k')
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

    def floor_draw(self):
        """Refresh image."""
        da = self.main.gui
        self.fig.clear()
        self.ax = self.fig.add_subplot(111)

        if da.image_path == '':
            self.img = self.main.default_floorplan
        else:
            self.img = mpimg.imread(da.image_path)
        self.img_show = self.ax.imshow(self.img, cmap='gray')
        self.ax.axis('off')
        # initiate maps
        if self.main.occ_map.size < 3:
            self.main.occ_map = np.ones(self.img.shape[0:2], dtype=float)
            self.main.ct_dose_map = np.zeros(self.img.shape[0:2], dtype=float)

        if da.currentTab == 'Areas':  # draw occ_map
            self.img_show = self.ax.imshow(
                self.main.occ_map, alpha=0.3, cmap='rainbow',
                vmin=0., vmax=1.)

        self.draw()


class FloorWidget(QWidget):
    """Class holding the widget containing the FloorCanvas with toolbars."""

    def __init__(self, parent):
        super().__init__()

        self.main = parent
        self.FloorCanvas = FloorCanvas(self.main)
        tbimg = NavToolBar(self.FloorCanvas, self)
        tbimgPos = PositionToolBar(self.FloorCanvas, self.main)
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
        #vlo.addWidget(tbimg2)
        vlo.addWidget(self.FloorCanvas)
        self.setLayout(vlo)
        self.FloorCanvas.floor_draw()

    def edit_annotations(self):
        """Pop up dialog to edit annotations settings."""
        dlg = EditAnnotationsDialog(
            annotations=self.main.gui.annotations,
            annotations_line_thick=self.main.gui.annotations_line_thick,
            annotations_font_size=self.main.gui.annotations_font_size)
        res = dlg.exec()
        if res:
            ann, line_thick, font_size = dlg.get_data()
            self.main.gui.annotations = ann
            self.main.gui.annotations_line_thick = line_thick
            self.main.gui.annotations_font_size = font_size
            if self.main.gui.active_img_no > -1:
                self.canvas.img_draw()

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
        self.lbl_dose_total = QLabel('Total dose = xxxx mSv')
        self.lbl_dose_nm = QLabel('NM dose = xxxx mSv')
        self.lbl_doserate_nm = QLabel('NM doserate = xxxx ' + '\u03bc' + 'Sv/h')
        self.lbl_dose_ct = QLabel('CT dose = xxxx mSv')
        vlo.addWidget(self.lbl_occ)
        vlo.addWidget(self.lbl_dose_total)
        vlo.addWidget(self.lbl_dose_nm)
        vlo.addWidget(self.lbl_doserate_nm)
        vlo.addWidget(self.lbl_dose_ct)
        #self.calibration_factor = self.main.gui.calibration_factor

        canvas.mpl_connect('motion_notify_event', self.on_move)

    def on_move(self, event):
        """When mouse cursor is moving in the canvas."""
        if event.inaxes and len(event.inaxes.get_images()) > 0:
            xpos = round(event.xdata)
            ypos = round(event.ydata)
            self.lbl_occ.setText(
                f'Occupancy factor = {self.main.occ_map[ypos, xpos]:.2f}')
            self.lbl_dose_total.setText('Total dose = xxxx mSv')
            self.lbl_dose_nm.setText('NM dose = xxxx mSv')
            self.lbl_doserate_nm.setText('NM doserate = xxxx ' + '\u03bc' + 'Sv/h')
            self.lbl_dose_ct.setText('CT dose = xxxx mSv')
        else:
            self.lbl_occ.setText('')
            self.lbl_dose_total.setText('')
            self.lbl_dose_nm.setText('')
            self.lbl_doserate_nm.setText('')
            self.lbl_dose_ct.setText('')


class VisualizationWidget(QWidget):
    """GUI for settings on how to visualize data."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.hlo = QHBoxLayout()
        self.setLayout(self.hlo)

        self.gb_display = QGroupBox('Display...')
        self.gb_display.setFont(uir.FontItalic())
        self.gb_display.setMinimumWidth(round(0.15*self.parent.gui.panel_width))
        self.btns_display = QButtonGroup()
        vlo = QVBoxLayout()
        for i, txt in enumerate([
                'Floor map',
                'Scale',
                'Walls',
                'Wall thickness',
                'Sources']):
            chbx = QCheckBox(txt)
            self.btns_display.addButton(chbx, i)
            chbx.setChecked(True)
            vlo.addWidget(chbx)
            chbx.clicked.connect(self.display_selections_changed)
        self.gb_display.setLayout(vlo)
        self.hlo.addWidget(self.gb_display)

        self.gb_overlay = QGroupBox('Color overlay...')
        self.gb_overlay.setFont(uir.FontItalic())
        self.gb_overlay.setMinimumWidth(round(0.15*self.parent.gui.panel_width))
        self.btns_overlay = QButtonGroup()
        vlo = QVBoxLayout()
        for i, txt in enumerate([
                'Occupancy factors',
                'Dose',
                'Max dose rate NM']):
            rbtn = QRadioButton(txt)
            self.btns_overlay.addButton(rbtn, i)
            vlo.addWidget(rbtn)
            rbtn.clicked.connect(self.overlay_selections_changed)
        self.gb_overlay.setLayout(vlo)
        self.btns_overlay.button(0).setChecked(True)
        self.hlo.addWidget(self.gb_overlay)

        self.gb_dose = QGroupBox('Dose...')
        self.gb_dose.setFont(uir.FontItalic())
        self.gb_dose.setMinimumWidth(round(0.15*self.parent.gui.panel_width))
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

        vlo_transparency = QVBoxLayout()
        self.hlo.addLayout(vlo_transparency)
        self.transparency = QSlider(Qt.Horizontal)
        lbl_min = QLabel('0 %')
        lbl_max = QLabel('100 %')
        self.transparency.setRange(0, 100)
        self.transparency.setValue(50)
        self.transparency.sliderReleased.connect(
            self.parent.wFloorDisplay.FloorCanvas.floor_draw)
        vlo_transparency.addWidget(uir.LabelItalic('Transparency overlay'))
        vlo_transparency.addWidget(self.transparency)
        hlo_0_100 = QHBoxLayout()
        vlo_transparency.addLayout(hlo_0_100)
        hlo_0_100.addWidget(lbl_min)
        hlo_0_100.addStretch()
        hlo_0_100.addWidget(lbl_max)

    def display_selections_changed(self):
        """Update display when Display selections change."""
        pass  #TODO

    def overlay_selections_changed(self):
        """Update display when Overlay selections change."""
        pass  #TODO

    def dose_selections_changed(self):
        """Update display when Dose selections change."""
        pass  #TODO


class CalculateWidget(QWidget):
    """GUI for calculation options."""

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        hlo = QHBoxLayout()
        self.setLayout(hlo)
        vlo_image_values = QVBoxLayout()
        hlo.addLayout(vlo_image_values)
        vlo_image_values.addWidget(uir.LabelHeader('Values at cursor position', 4))
        info_tb = InfoToolBar(self.parent.wFloorDisplay.FloorCanvas, self.parent)
        vlo_image_values.addWidget(info_tb)

        hlo.addWidget(uir.VLine())
        hlo.addSpacing(5)

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
            rbtn.clicked.connect(self.parent.calculate_dose)
        self.gb_floor.setLayout(vlo_gb)
        self.btns_floor.button(1).setChecked(True)

        self.working_days = QSpinBox(minimum=0, maximum=1000,
                                     value=self.parent.general_values.working_days)
        self.working_days.editingFinished.connect(
            self.parent.update_dose_days)
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
        hlo_correct.addSpacing(2)
        hlo_correct.addWidget(uir.InfoTool(
            'Correct wall thickness geometrically as the rays actually have a longer '
            'path through the material when oblique to the wall.<br>'
            'NB might underestimate path length of scattered photons.<br>'
            'These corrections are ignored for oblique walls.',
            parent=self))

        vlo.addSpacing(20)
        btn_calculate = QPushButton('Calculate dose')
        btn_calculate.toggled.connect(self.parent.calculate_dose)
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
        act_delete.setToolTip('Delete selected row')
        act_delete.triggered.connect(table.delete_row)

        act_add = QAction('Add', self)
        act_add.setIcon(QIcon(f'{os.environ[ENV_ICON_PATH]}add.png'))
        act_add.setToolTip('Add new row after selected row')
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


class TextCell(QLineEdit):
    """Text inputs as QLineEdit to trigger action on input changes."""

    def __init__(self, parent, initial_text=''):
        super().__init__(initial_text)
        self.textEdited.connect(parent.cell_changed)
        self.parent = parent

    def focusInEvent(self, event):
        self.parent.cell_selection_changed()
        super().focusInEvent(event)


class CellSpinBox(QDoubleSpinBox):
    """Spinbox for cell widgets. Default is ratio 0.-1."""

    def __init__(self, parent,
                 initial_value=0., min_val=0., max_val=1.,
                 step=0.05, decimals=2):
        """Initialize CellSpinBox.

        Parameters
        ----------
        parent : InputTab
        initial_value : float, optional
            Initial value. The default is 0..
        min_val : float, optional
            Minumum value. The default is 0..
        max_val : float, optional
            Maximum value. The default is 1..
        step : float, optional
            Single step when using arrows. The default is 0.05.
        decimals : int, optional
            Number of decimals. The default is 2.
        """
        super().__init__()
        self.setRange(min_val, max_val)
        self.setSingleStep(step)
        self.setDecimals(decimals)
        self.setValue(initial_value)
        self.valueChanged.connect(parent.cell_changed)
        self.parent = parent

    def focusInEvent(self, event):
        self.parent.cell_selection_changed()
        super().focusInEvent(event)


class InputCheckBox(QCheckBox):
    """Checkbox with left margin for InputTab."""

    def __init__(self, parent, initial_value=True):
        super().__init__()
        self.setStyleSheet("QCheckBox { padding-left: 15px }")
        self.setChecked(initial_value)
        self.toggled.connect(parent.cell_changed)
        self.parent = parent

    def focusInEvent(self, event):
        self.parent.cell_selection_changed()
        super().focusInEvent(event)


class CellCombo(QComboBox):
    """Checkbox with left margin for InputTab."""

    def __init__(self, parent, strings):
        super().__init__()
        self.addItems(strings)
        self.currentIndexChanged.connect(parent.cell_changed)
        self.parent = parent

    def focusInEvent(self, event):
        self.parent.cell_selection_changed()
        super().focusInEvent(event)


class InputTab(QWidget):
    """Common GUI for input tabs."""

    def __init__(self, header='', info='', btn_get_pos_text='Get pos from figure'):
        super().__init__()

        self.vlo = QVBoxLayout()
        self.setLayout(self.vlo)
        self.vlo.addWidget(uir.LabelHeader(header, 4))
        self.btn_get_pos = QPushButton(f'   {btn_get_pos_text}   ')
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

        self.table_list = []  # table as list for easy access for computations, import/export
        self.active_row = -1

        self.tb = TableToolBar(self)
        self.hlo.addWidget(self.tb)
        self.hlo.addWidget(self.table)

    def select_row_col(self, row, col):
        """Set focus on selected row and col."""
        index = self.table.model().index(row, col)
        self.table.selectionModel().select(
            index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)

    def get_row_col(self):
        """Get selected row in table."""
        row = -1
        col = -1
        for i in range(self.table.rowCount()):
            for j in range(self.table.columnCount()):
                if self.table.cellWidget(i, j) == self.table.focusWidget():
                    row = i
                    col = j
        if row == -1:  # if no focusWidget, try selected row
            sel = self.table.selectedIndexes()
            if len(sel) > 0:
                row = sel[0].row()
                col = sel[0].column()

        return (row, col)

    def cell_selection_changed(self):
        """Cell widget got focus. Change active row and highlight."""
        row, col = self.get_row_col()
        if row != self.active_row:
            self.active_row = row
            self.highlight_selected_in_image()

    def delete_row(self):
        """Delete selected row.

        Returns
        -------
        rowPosition : int
            index of the deleted row
        """
        rowPosition = self.active_row
        if self.active_row > -1:
            self.table.removeRow(self.active_row)
            self.table_list.pop(self.active_row)
            if len(self.table_list) == 0:
                self.add_cell_widgets(0)
                self.table_list.append(copy.deepcopy(self.empty_row))
            self.table.setFocus()
        return rowPosition

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        newrow : int
            index of the new row
        """
        row, col = self.get_row_col()
        newrow = -1
        if row == -1:
            newrow = self.table.rowCount()
        else:
            newrow = row + 1
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

    def __init__(self, parent):
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

        self.c0 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c0.editingFinished.connect(lambda: self.parent.reset_dose(floor=0))
        self.c1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c1.editingFinished.connect(lambda: self.parent.reset_dose(floor=1))
        self.c2 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.c2.editingFinished.connect(lambda: self.parent.reset_dose(floor=2))
        self.h0 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h0.editingFinished.connect(lambda: self.parent.reset_dose(floor=1))
        self.h1 = QDoubleSpinBox(minimum=0, maximum=10, decimals=3)
        self.h1.editingFinished.connect(lambda: self.parent.reset_dose(floor=2))

        self.shield_mm_above = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_above.editingFinished.connect(
            lambda: self.parent.reset_dose(floor=2))
        self.shield_material_above = QComboBox()
        self.shield_material_above.currentTextChanged.connect(
            lambda: self.parent.reset_dose(floor=2))
        self.shield_mm_below = QDoubleSpinBox(minimum=0, maximum=500, decimals=1)
        self.shield_mm_below.editingFinished.connect(
            lambda: self.parent.reset_dose(floor=0))
        self.shield_material_below = QComboBox()
        self.shield_material_below.currentTextChanged.connect(
            lambda: self.parent.reset_dose(floor=0))

        self.label = 'Scale'
        self.parent = parent
        self.tb.setVisible(False)
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(
            ['Line positions x0,y0,x1,y1', 'Actual length (m)'])
        self.empty_row = ['', 0.0]
        self.table_list.append(copy.deepcopy(self.empty_row))
        self.active_row = 0
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 40*self.parent.gui.char_width)
        self.table.setColumnWidth(1, 25*self.parent.gui.char_width)
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
        self.table.setCellWidget(row, 0, TextCell(self))
        self.table.setCellWidget(row, 1, CellSpinBox(
            self, max_val=200., step=1.0, decimals=3))

    def get_pos(self):
        """Get line positions as defined in figure."""
        if self.parent.gui.x1 + self.parent.gui.y1 > 0:
            text = (
                f'{self.parent.gui.x0:.0f}, '
                f'{self.parent.gui.y0:.0f}, '
                f'{self.parent.gui.x1:.0f}, '
                f'{self.parent.gui.y1:.0f}'
                )
            tabitem = self.table.cellWidget(0, 0)
            tabitem.setText(text)
            self.parent.gui.scale_start = (
                self.parent.gui.x0, self.parent.gui.y0)
            self.parent.gui.scale_end = (
                self.parent.gui.x1, self.parent.gui.y1)
            if self.parent.gui.calibration_factor > 0.:
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
        self.parent.gui.calibration_factor = (
            self.parent.gui.scale_length / lineLen)
        self.parent.wFloorDisplay.FloorCanvas.add_scale_highlight(
            x0, y0, x1, y1)
        # TODO self.parent.update_dose()

    def update_heights(self):
        """Update floor heights."""
        self.blockSignals(True)
        self.c0.setValue(self.parent.general_values.c0)
        self.c1.setValue(self.parent.general_values.c1)
        self.c2.setValue(self.parent.general_values.c2)
        self.h0.setValue(self.parent.general_values.h0)
        self.h1.setValue(self.parent.general_values.h1)
        self.shield_mm_above.setValue(self.parent.general_values.shield_mm_above)
        self.shield_mm_below.setValue(self.parent.general_values.shield_mm_below)
        self.blockSignals(False)

    def update_material_lists(self, first=False):
        """Update selectable lists."""
        self.material_strings = [x.label for x in self.parent.materials]
        if first:
            prev_above = self.parent.general_values.shield_material_above
            prev_below = self.parent.general_values.shield_material_below
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

    def cell_changed(self):
        """Value changed by user input."""
        value = self.get_cell_value(0, 1)
        self.parent.gui.scale_length = value
        self.update_scale()

    def delete_row(self):
        pass

    def add_row(self):
        pass

    def duplicate_row(self):
        pass


class AreasTab(InputTab):
    """GUI for adding/editing areas to define occupancy factors."""

    def __init__(self, parent):
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
        self.parent = parent
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Area name', 'x0,y0,x1,y1', 'Occupancy factor'])
        self.empty_row = [True, '', '', 1.]
        self.table_list.append(copy.deepcopy(self.empty_row))
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.parent.gui.char_width)
        self.table.setColumnWidth(1, 30*self.parent.gui.char_width)
        self.table.setColumnWidth(2, 30*self.parent.gui.char_width)
        self.table.setColumnWidth(3, 30*self.parent.gui.char_width)
        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, InputCheckBox(self))
        self.table.setCellWidget(row, 1, TextCell(self))
        self.table.setCellWidget(row, 2, TextCell(self))
        self.table.setCellWidget(row, 3, CellSpinBox(self))

    def get_pos(self):
        """Get positions for element as defined in figure."""
        self.active_row, col = super().get_row_col()
        text = (
            f'{self.parent.gui.x0:.0f}, '
            f'{self.parent.gui.y0:.0f}, '
            f'{self.parent.gui.x1:.0f}, '
            f'{self.parent.gui.y1:.0f}'
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
            self.parent.wFloorDisplay.FloorCanvas.add_area_highlight(
                x0, y0, width, height)

    def update_occ_map(self):
        """Update array containing occupation factors and redraw."""
        self.parent.occ_map = np.ones(self.parent.occ_map.shape)
        for i in range(self.table.rowCount()):
            if self.table_list[i][0]:  # if active
                tabitem = self.table.cellWidget(i, 2)
                x0, y0, width, height = self.get_area_from_text(tabitem.text())
                self.parent.occ_map[y0:y0+height, x0:x0+width] = self.table_list[i][3]
        self.parent.wFloorDisplay.FloorCanvas.floor_draw()
        """
        self.parent.wFloorDisplay.FloorCanvas.img_show.set_data(
            self.parent.wFloorDisplay.FloorCanvas.img)
        self.parent.wFloorDisplay.FloorCanvas.img_show.set_data(
            self.parent.occ_map, alpha=0.3, cmap='rainbow',
            vmin=0., vmax=1.)
        """

    def cell_changed(self):
        """Value changed by user input."""
        self.active_row, col = self.get_row_col()
        value = self.get_cell_value(self.active_row, col)
        self.table_list[self.active_row][col] = value
        if col > 1:
            self.update_occ_map()

    def delete_row(self):
        """Delete selected row."""
        removedRow = super().delete_row()
        if removedRow > -1:
            pass
            # TODO: update floor display

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        addedRow : int
            index of the new row
        """
        addedRow = super().add_row()
        if addedRow > -1:
            self.add_cell_widgets(addedRow)
            # TODO: update floor display
        return addedRow

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        addedRow = self.add_row()
        if addedRow > -1:
            values_above = self.table_list[addedRow - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(True)

            self.table.cellWidget(addedRow, 0).setChecked(values_above[0])
            self.table.cellWidget(addedRow, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(addedRow, 2).setText(values_above[2])
            self.table.cellWidget(addedRow, 3).setValue(float(values_above[3]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(False)

            self.select_row_col(addedRow, 1)
            self.table_list[addedRow] = copy.deepcopy(values_above)


class WallsTab(InputTab):
    """GUI for adding/editing walls."""

    def __init__(self, parent):
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
        self.parent = parent
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Wall name', 'x0,y0,x1,y1', 'Material', 'Thickness (mm)'])
        self.empty_row = [True, '', '', 'Lead', 0.0]
        self.material_strings = [x.label for x in self.parent.materials]
        self.table_list.append(copy.deepcopy(self.empty_row))
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.parent.gui.char_width)
        self.table.setColumnWidth(1, 30*self.parent.gui.char_width)
        self.table.setColumnWidth(2, 30*self.parent.gui.char_width)
        self.table.setColumnWidth(3, 30*self.parent.gui.char_width)
        self.table.setColumnWidth(4, 30*self.parent.gui.char_width)
        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, InputCheckBox(self))
        self.table.setCellWidget(row, 1, TextCell(self))
        self.table.setCellWidget(row, 2, TextCell(self))
        self.table.setCellWidget(row, 3, CellCombo(
            self, self.material_strings))
        self.table.setCellWidget(row, 4, CellSpinBox(
            self, max_val=400., step=1.0))

    def update_materials(self):
        """Update ComboBox of all rows when list of materials changed in settings."""
        self.material_strings = [x.label for x in self.parent.materials]
        warnings = []
        self.blockSignals(True)
        for row in range(self.table.rowCount()):
            prev_val = self.get_cell_value(row, 3)
            self.table.setCellWidget(row, 3, CellCombo(self, self.material_strings))
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
        self.active_row, col = super().get_row_col()
        if self.active_row > -1:
            text = (
                f'{self.parent.gui.x0:.0f}, '
                f'{self.parent.gui.y0:.0f}, '
                f'{self.parent.gui.x1:.0f}, '
                f'{self.parent.gui.y1:.0f}'
                )
            tabitem = self.table.cellWidget(self.active_row, 2)
            tabitem.setText(text)
            self.table_list[self.active_row][2] = text
            self.highlight_selected_in_image()
            # TODO: self.parent.update_doses()

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
            self.parent.wFloorDisplay.FloorCanvas.add_wall_highlight(
                x0, y0, x1, y1)

    def cell_changed(self):
        """Value changed by user input."""
        self.active_row, col = self.get_row_col()
        value = self.get_cell_value(self.active_row, col)
        self.table_list[self.active_row][col] = value
        if col > 2:
            pass
            # TODO:self.parent.update_dose()

    def delete_row(self):
        """Delete selected row."""
        removedRow = super().delete_row()
        if removedRow > -1:
            pass
            # TODO:self.parent.update_dose()

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        addedRow : int
            index of the new row
        """
        addedRow = super().add_row()
        if addedRow > -1:
            self.add_cell_widgets(addedRow)
            # TODO: if not duplicate_row calling: self.parent.update_dose()
        return addedRow

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        addedRow = self.add_row()
        if addedRow > -1:
            values_above = self.table_list[addedRow - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(True)

            self.table.cellWidget(addedRow, 0).setChecked(values_above[0])
            self.table.cellWidget(addedRow, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(addedRow, 2).setText(values_above[2])
            self.table.cellWidget(addedRow, 3).setCurrentText(values_above[3])
            self.table.cellWidget(addedRow, 3).setValue(float(values_above[3]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(False)
            self.select_row_col(addedRow, 1)
            self.table_list[addedRow] = copy.deepcopy(values_above)


class NMsourcesTab(InputTab):
    """GUI for adding/editing NM sources."""

    def __init__(self, parent):
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

        self.label = 'NMsources'
        self.parent = parent
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(
            ['Active', 'Source name', 'x,y', 'Isotope', 'In patient',
             'A0 (MBq)', 't1 (hours)', 'duration (hours)', 'Rest void',
             '# pr workday'])
        self.empty_row = [True, '', '', 'F-18', True, '0.0', '0.0', '0.0',
                          '1.0', '0']
        self.isotope_strings = [x.label for x in self.parent.isotopes]
        self.table_list.append(copy.deepcopy(self.empty_row))
        self.active_row = 0
        self.table.setColumnWidth(0, 10*self.parent.gui.char_width)
        self.table.setColumnWidth(1, 25*self.parent.gui.char_width)
        self.table.setColumnWidth(2, 15*self.parent.gui.char_width)
        self.table.setColumnWidth(3, 13*self.parent.gui.char_width)
        self.table.setColumnWidth(4, 13*self.parent.gui.char_width)
        self.table.setColumnWidth(5, 13*self.parent.gui.char_width)
        self.table.setColumnWidth(6, 13*self.parent.gui.char_width)
        self.table.setColumnWidth(7, 17*self.parent.gui.char_width)
        self.table.setColumnWidth(8, 13*self.parent.gui.char_width)
        self.table.setColumnWidth(9, 15*self.parent.gui.char_width)

        self.table.verticalHeader().setVisible(False)
        self.add_cell_widgets(0)
        self.select_row_col(0, 1)

    def add_cell_widgets(self, row):
        """Add cell widgets to the selected row (new row, default values)."""
        self.table.setCellWidget(row, 0, InputCheckBox(self))
        self.table.setCellWidget(row, 1, TextCell(self))
        self.table.setCellWidget(row, 2, TextCell(self))
        self.table.setCellWidget(row, 3, CellCombo(self, self.isotope_strings))
        self.table.setCellWidget(row, 4, InputCheckBox(self))
        self.table.setCellWidget(row, 5, CellSpinBox(
            self, max_val=100000, step=10, decimals=0))
        self.table.setCellWidget(row, 6, CellSpinBox(
            self, max_val=1000, step=0.1, decimals=1))
        self.table.setCellWidget(row, 7, CellSpinBox(
            self, max_val=100, step=0.1, decimals=1))
        self.table.setCellWidget(row, 8, CellSpinBox(
            self, initial_value=1.))
        self.table.setCellWidget(row, 9, CellSpinBox(
            self, max_val=100, step=1, decimals=0))

    def update_isotopes(self):
        """Update ComboBox of all rows when list of isotopes changed in settings."""
        self.isotope_strings = [x.label for x in self.parent.isotopes]
        for row in range(self.table.rowCount()):
            self.table.setCellWidget(row, 3, CellCombo(self, self.isotope_strings))

    def get_pos(self):
        """Get positions for element as defined in figure."""
        self.active_row, col = super().get_row_col()
        if self.active_row > -1:
            text = (
                f'{self.parent.gui.x1:.0f}, '
                f'{self.parent.gui.y1:.0f}'
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
            self.parent.wFloorDisplay.FloorCanvas.add_sourcepos_highlight(x, y)

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
        self.parent.wFloorDisplay.FloorCanvas.floor_draw()

    def cell_changed(self):
        """Value changed by user input."""
        self.active_row, col = self.get_row_col()
        value = self.get_cell_value(self.active_row, col)
        self.table_list[self.active_row][col] = value
        if col > 1:
            self.update_NM_dose()

    def delete_row(self):
        """Delete selected row."""
        removedRow = super().delete_row()
        if removedRow > -1:
            pass
            # TODO: update floor display

    def add_row(self):
        """Add row after selected row (or as last row if none selected).

        Returns
        -------
        addedRow : int
            index of the new row
        """
        addedRow = super().add_row()
        if addedRow > -1:
            self.add_cell_widgets(addedRow)
            # TODO: update floor display
        return addedRow

    def duplicate_row(self):
        """Duplicate selected row and add as next."""
        addedRow = self.add_row()
        if addedRow > -1:
            values_above = self.table_list[addedRow - 1]
            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(True)

            self.table.cellWidget(addedRow, 0).setChecked(values_above[0])
            self.table.cellWidget(addedRow, 1).setText(values_above[1] + '_copy')
            self.table.cellWidget(addedRow, 2).setText(values_above[2])
            self.table.cellWidget(addedRow, 3).setCurrentText(values_above[3])
            self.table.cellWidget(addedRow, 4).setChecked(values_above[4])
            self.table.cellWidget(addedRow, 5).setValue(float(values_above[5]))
            self.table.cellWidget(addedRow, 6).setValue(float(values_above[6]))
            self.table.cellWidget(addedRow, 7).setValue(float(values_above[7]))
            self.table.cellWidget(addedRow, 8).setValue(float(values_above[8]))
            self.table.cellWidget(addedRow, 9).setValue(int(values_above[9]))

            for i in range(self.table.columnCount()):
                self.table.cellWidget(addedRow, i).blockSignals(False)
            self.select_row_col(addedRow, 1)
            self.table_list[addedRow] = copy.deepcopy(values_above)
            # TODO: change label to one not used yet
            # TODO: update floor display