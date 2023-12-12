#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of small functions used in ImageQC.

@author: Ellen Wasbo
"""
import copy
import numpy as np
from skimage.transform import resize

# Shield_NM_CT block start
from Shield_NM_CT.ui import reusable_widgets as uir
# Shield_NM_CT block end


def calculate_dose(main, source_number=None, modality=None):
    """Calculate dose based on parameters in main updating dose_dict of main.

    Parameters
    ----------
    main : ui_main.MainWindow
    source_number : int, Optional
        source number to calculate/update. Default is None = all.
    modality: str, Optional
        modality of source_number to update. Default is None = all

    Returns
    -------
    status : bool
        True if calculation succeeded.
    msgs : list of str
        Info and warning messages to display after this process finished.
    """
    msgs = []
    status = False
    proceed = False
    # calibrated scale?
    calibration_factor = main.gui.calibration_factor
    if calibration_factor:
        proceed = True
    else:
        msgs.append(
            'Calibration factor for scaling number of pixels pr meter is missing.')
        msgs.append(
            'Dose calculation not possible. '
            'Please define the scale from the Scale tab.')

    sources = {}
    if proceed:
        if source_number is not None and modality is not None:
            if modality == 'NM':
                nonzero_columns = [5, 7, 8, 9]
            elif modality == 'CT':
                nonzero_columns = [6, 7, 8]
            elif modality == 'OT':
                nonzero_columns = [4, 5]
            this_source = get_valid_rows(
                [main.tabs.currentWidget().table_list[source_number]],
                nonzero_columns=nonzero_columns,
                n_coordinates=2)
            if any(this_source):
                sources[modality] = this_source
                n_sources = 1
            else:
                proceed = False
        else:
            # any sources with # patients or dose-values > 0?
            n_sources = 0
            sources_NM = get_valid_rows(
                main.NMsources_tab.table_list, nonzero_columns=[5, 7, 8, 9],
                n_coordinates=2)
            if any(sources_NM):
                sources['NM'] = sources_NM
                n_sources += len(sources_NM)
            sources_CT = get_valid_rows(
                main.CTsources_tab.table_list, nonzero_columns=[6, 7, 8],
                n_coordinates=2)
            if any(sources_CT):
                sources['CT'] = sources_CT
                n_sources += len(sources_CT)
            sources_OT = get_valid_rows(
                main.OTsources_tab.table_list, nonzero_columns=[4, 5],
                n_coordinates=2)
            if any(sources_OT):
                sources['OT'] = sources_OT
                n_sources += len(sources_OT)

        if not sources and source_number is None:
            proceed = False
            msgs.append(
                'Found no valid sources (either not defined, not active '
                'or values zero that causes zero dose.')

    walls = []
    if proceed:
        # any walls to consider (thickness > 0)
        walls = get_valid_rows(
            main.walls_tab.table_list, nonzero_columns=[4], n_coordinates=4)

    if proceed:
        max_progress = 100 * n_sources  # 0-100 within each source
        step = 100 if len(walls) == 0 else 100 // len(walls)
        progress_modal = uir.ProgressModal(
            "Calculating...", "Cancel", 0, max_progress, main, minimum_duration=0)

        progress_modal.setLabelText("Preparing data...")
        progress_modal.setValue(1)
        current_progress_value = 1

        main.areas_tab.update_occ_map()

        if 'NM' in sources:
            dose_NM = calculate_dose_NM(
                sources['NM'], main.isotopes, walls, main.shield_data,
                main.occ_map.shape, calibration_factor, main.general_values,
                progress_modal, current_progress_value, step, msgs
                )
            current_progress_value = 100 * len(sources['NM'])
        else:
            dose_NM = None

        if 'CT' in sources and progress_modal.wasCanceled() is False:
            pass  #TODO
            current_progress_value = 100 * (len(sources['NM']) + len(sources['CT']))

        if 'OT' in sources and progress_modal.wasCanceled() is False:
            dose_OT = calculate_dose_OT(
                sources['OT'], walls, main.shield_data,
                main.occ_map.shape, calibration_factor, main.general_values,
                progress_modal, current_progress_value, step, msgs
                )
        else:
            dose_OT = None

        if progress_modal.wasCanceled() is False:
            status = True

        progress_modal.setValue(max_progress)
        if modality:
            if modality == 'NM':
                main.dose_dict[
                    'dose_NM']['dist_maps'][source_number] = dose_NM['dist_maps'][0]

        else:
            main.dose_dict = {
                'dose_NM': dose_NM,
                'dose_CT': None,
                'dose_OT': dose_OT,
                }

    return status, msgs


def get_valid_rows(table_list, nonzero_columns=None, n_coordinates=0):
    """Get rows from table_list where active and specific columns are not zero.

    Also concert position-string to list of ints.

    Parameters
    ----------
    table_list : list of list
        as defined in ui_main for each tab.
    nonzero_columns : list of int, optional
        Columns that cannot be zero to be valid. The default is None.
    n_coordinates: int
        number of coordinate values [x1, y1, x2, y2] = 4 numbers

    Returns
    -------
    valid_table_list : list of list
        table_list with valid rows.
    """
    valid_table_list = [None for row in table_list]
    for rowno, row in enumerate(table_list):
        add = True
        if len(row[2]):
            if row[0]:  # active
                for i in nonzero_columns:
                    if row[i] == 0:
                        add = False
                        break
            else:
                add = False
        else:
            add = False  # position(s) not given

        if add:
            coords = row[2].split(', ')
            if len(coords) == n_coordinates:
                try:
                    coord_list = [int(coord) for coord in coords]
                    valid_table_list[rowno] = copy.deepcopy(row)
                    valid_table_list[rowno][2] = coord_list
                except ValueError:
                    pass

    return valid_table_list


def get_distance_source(shape, xy, calibration_factor):
    """Calculate distance factors 1/dist^2 for (x,y) in image.

    Parameters
    ----------
    shape : tuple
        shape of array to generate
    xy: str
        x, y position of point in map
    calibration_factor: float
        m/pixel

    Returns
    -------
    distance_map : ndarray
        distances to source
    distance_factor_map : ndarray
        distance factors (1/dist*2) to source
    """
    sz_y, sz_x = shape
    x, y = xy
    xs, ys = np.meshgrid(np.arange(sz_x), np.arange(sz_y))
    distance_map = np.sqrt((xs-x) ** 2 + (ys-y) ** 2)
    distance_map = calibration_factor * distance_map
    distance_map[distance_map < 0.1] = 0.1  # ignore doses closer than 0.5m
    distance_factors = 1. / (distance_map ** 2)

    return (distance_map, distance_factors)


def generate_CT_doseratemap_cor(template,
                                meters_lateral=1.5, meters_rear=2., meters_front=3.5,
                                resolution=0.1):
    """Generate array with doserates based on values from config_classes.CT_doserates.

    Parameters
    ----------
    template : config_classes.CT_doserates
        doserate values at defined positions
    meters_lateral : float, optional
        extract values to the given number of meters laterally. The default is 1.5.
    meters_rear : float, optional
        extract values to the given number of meters rear of CT iso. The default is 2..
    meters_front : TYPE, optional
        extract values to the given number of meters front of CT iso. The default is 2..
    resolution : float, optional
        resolution of returnd array in meters/pixel. The default is 0.1.

    Returns
    -------
    doseratemap : np.array
    offset xy: tuple center position of output
    """
    # start with 50cm resolution (same as values from doserate table)
    nx50 = round(np.ceil(meters_lateral / 0.5)) + 1
    # left side calculated and duplicated
    ny50 = round(np.ceil((meters_rear + meters_front) / 0.5)) + 1
    doseratemap = np.zeros((ny50, nx50))

    cy = np.ceil((meters_rear) / 0.5)  # center x and y
    xs, ys = np.meshgrid(np.arange(nx50), np.arange(ny50) - cy)
    ys = -ys
    dists_sq = 0.5 ** 2 * (xs ** 2 + ys ** 2)
    dists_sq[dists_sq < 0.5**2] = 0.5**2
    sin_angles = 0.5*ys / np.sqrt(dists_sq)

    tables_len = 0
    try:
        tables_len = len(template.tables)
    except TypeError:
        tables_len = 0
    if tables_len:
        # edge values distances and angles
        x_edge = 0.5 * np.array([0, 1, 2] + [3]*12 + [2, 1, 0])
        y_edge = 0.5 * np.array([4]*3 + list(range(4, -8, -1)) + [-7]*3)
        dists_edge_sq = x_edge ** 2 + y_edge ** 2
        sin_angles_edge = y_edge / np.sqrt(dists_edge_sq)

        for i in range(nx50):  # left side
            for j in range(ny50):
                diff_angle = sin_angles_edge - sin_angles[j, i]
                idx = np.where(np.abs(diff_angle) == np.min(np.abs(diff_angle)))
                dose_factor = dists_edge_sq[idx[0][0]] / dists_sq[j, i]
                doseratemap[j, i] = dose_factor * template.tables[0][idx[0][0]]
    else:
        sin_rear = np.sin(template.rear_stop_angle * np.pi() / 180.)
        sin_front = np.sin(template.front_stop_angle * np.pi() / 180.)
        doseratemap = template.scatter_factor_gantry / dists_sq
        doseratemap[sin_angles < sin_front] = template.scatter_factor_front / dists_sq
        doseratemap[sin_angles > sin_rear] = template.scatter_factor_rear / dists_sq

    if resolution != 0.5:
        nx = np.ceil(meters_lateral / resolution)
        ny = np.ceil((meters_rear + meters_front) / resolution)
        # assure odd number pixels (central is central)
        if nx % 2 == 0:
            nx += 1
        if ny % 2 == 0:
            ny += 1
        doseratemap = resize(doseratemap, (ny, nx))
    else:
        nx = nx50

    # duplicate and flip in x-dir
    right_side = np.fliplr(doseratemap[:, 1:])
    doseratemapfull = np.concatenate((right_side, doseratemap), axis=1)

    x_offset = round(nx // 2)
    y_offset = round(np.ceil((meters_rear) / resolution))

    return (doseratemapfull, (x_offset, y_offset))


def generate_CT_doseratemap_sag(template,
                                meters_rear=2., meters_front=3.5,
                                meters_z=1.5, above=True,
                                resolution=0.1):
    """Generate array with doserates based on values from config_classes.CT_doserates.

    Parameters
    ----------
    values : array like
        doserate values at defined positions
    meters_rear : float, optional
        extract values to the given number of meters rear of CT iso. The default is 2..
    meters_front : float, optional
        extract values to the given number of meters front of CT iso. The default is 2..
    meters_z: float, optional
        extract values to the given number of meters front of CT iso. The default is 1.5
        above tells if z is above or below
    above: bool, optional
        Calculate doses above or below iso (floor above or below). The default True.
    resolution : float, optional
        resolution of returnd array in meters/pixel. The default is 0.1.

    Returns
    -------
    doseratemap : np.array
    offset zy: tuple center position of output
    """
    # start with 50cm resolution (same as values from doserate table)
    nz50 = round(np.ceil(meters_z / 0.5)) + 1
    ny50 = round(np.ceil((meters_rear + meters_front) / 0.5)) + 1
    doseratemap = np.zeros((ny50, nz50))

    cy = np.ceil(meters_rear / 0.5)  # center y
    zs, ys = np.meshgrid(np.arange(nz50), np.arange(ny50) - cy)
    ys = -ys
    dists_sq = 0.5 ** 2 * (zs ** 2 + ys ** 2)
    dists_sq[dists_sq < 0.5**2] = 0.5**2
    sin_angles = 0.5*ys / np.sqrt(dists_sq)

    # edge values distances and angles
    if above:
        edge_values = edge_values[:18]
        z_edge = 0.5 * np.array([0, 1, 2] + [3]*12 + [2, 1, 0])
        y_edge = 0.5 * np.array([4]*3 + list(range(4, -8, -1)) + [-7]*3)
    else:
        edge_values = edge_values[17:] + [edge_values[0]]
        edge_values = edge_values[::-1]
        z_edge = 0.5 * np.array([0, 1] + [3]*12 + [1, 0])
        y_edge = 0.5 * np.array([4]*2 + list(range(4, -8, -1)) + [-7]*2)

    dists_edge_sq = z_edge ** 2 + y_edge ** 2
    sin_angles_edge = y_edge / np.sqrt(dists_edge_sq)

    for i in range(nz50):
        for j in range(ny50):
            diff_angle = sin_angles_edge - sin_angles[j, i]
            idx = np.where(np.abs(diff_angle) == np.min(np.abs(diff_angle)))
            dose_factor = dists_edge_sq[idx[0][0]] / dists_sq[j, i]
            doseratemap[j, i] = dose_factor * edge_values[idx[0][0]]

    if resolution != 0.5:
        nz = np.ceil(meters_z / resolution)
        ny = np.ceil((meters_rear + meters_front) / resolution)
        # assure odd number pixels (central is central)
        if ny % 2 == 0:
            ny += 1
        doseratemap = resize(doseratemap, (ny, nz))
    else:
        nz = nz50

    z_offset = 0
    y_offset = round(np.ceil((meters_rear) / resolution))

    return (doseratemap, (z_offset, y_offset))


def calculate_wall_affect_sector(shape, source_pos, wall_pos):
    """Return matrix zeros except for sector where source is shielded by wall.

    Where shielded by wall = relative thickness of wall
    """
    sx, sy = source_pos
    wx0, wy0, wx1, wy1 = wall_pos
    dx0, dy0 = (wx0 - sx), (wy0 - sy)
    dx1, dy1 = (wx1 - sx), (wy1 - sy)
    angle0 = np.arctan2(dy0, dx0)
    angle1 = np.arctan2(dy1, dx1)
    angle_min = np.min([angle0, angle1])
    angle_max = np.max([angle0, angle1])

    # convert cartesian --> polar coordinates
    y, x = np.ogrid[:shape[0], :shape[1]]
    theta0 = np.arctan2(y-sy, x-sx)
    theta = np.arctan2(y-sy, x-sx) - angle_min
    theta %= (2*np.pi)  # force values between 0 and 2*pi
    anglemask = theta < (angle_max - angle_min)

    if wx0 == wx1:  # vertical wall
        wall_affect_sector = anglemask * np.abs(1/np.cos(theta0))
        if sx > wx0:
            wall_affect_sector[:, wx0:] = 0
        elif sx < wx0:
            wall_affect_sector[:, :wx0] = 0
    elif wy0 == wy1:  # horizontal wall
        wall_affect_sector = anglemask * np.abs(1/np.cos(theta0 + np.pi/2))
        if sy > wy0:
            wall_affect_sector[wy0:, :] = 0
        elif sy < wy0:
            wall_affect_sector[:wy0, :] = 0
    else:  # oblique wall
        wall_affect_sector = anglemask  # geometric correction of thickness ignored
        if wx0 > wx1:
            xmax, ymax = wx0, wy0
            xmin, ymin = wx1, wy1
        else:
            xmax, ymax = wx1, wy1
            xmin, ymin = wx0, wy0
        slope = (ymax-ymin)/(xmax-xmin)
        y0 = - (slope * xmin - ymin)
        y_at_source = slope*sx + y0
        for xx in range(shape[0]):
            if xx > xmax:
                if xx > sx:
                    break
                else:
                    wall_affect_sector[:, xx] = 0
            elif sx < xx < xmin:
                wall_affect_sector[:, xx] = 0
            elif xx >= xmin:
                ythis = int(slope * xx + y0)
                if y_at_source > sy:
                    wall_affect_sector[:ythis, xx] = 0
                else:
                    wall_affect_sector[ythis:, xx] = 0
    mask = np.copy(wall_affect_sector)
    mask[wall_affect_sector != 0] = 1
    return wall_affect_sector, mask


def calculate_transmission(shield_data, wall_affect_map=1, thickness=0.,
                           material='', isotope='', kV_source=''):
    """Calculate transmission factors, if floor 1 or correct thickness - as map.

    Parameters
    ----------
    shield_data : list of ShieldData
    wall_affect_map : np.array or 1
        0 or 1 if thickness correction not performed else thickness correction
        1 (int) if floor 0 or 2 and thickness correction is False
    thickness : float
        wall thickness in mm
    material : str
        Material name
    isotope : str, Optional
        Isotope name. Default is ''
    kV_source : str, Optional
        kV_source name. Default is ''

    Returns
    -------
    transmission : float or np array
    errmsg : str
    """
    sd = None
    transmission = None
    errmsg = ''
    for data in shield_data:
        if isotope:
            if data.material == material and data.isotope == isotope.label:
                sd = data
                break
        elif kV_source:
            if data.material == material and data.kV_source == kV_source.label:
                sd = data
                break

    if sd:
        if all([sd.alpha, sd.beta, sd.gamma]):
            transmission = (
                (1 + (sd.beta/sd.alpha))
                * np.exp(sd.alpha*sd.gamma*thickness*wall_affect_map)
                - (sd.beta/sd.alpha)) ** (-1./sd.gamma)
        elif sd.hvl1 or sd.tvl1:
            thickness_map = thickness * wall_affect_map
            if thickness < sd.hvl1:
                transmission = 2 ** -(thickness_map / sd.hvl1)
            elif thickness < sd.tvl1 and sd.hvl2 > 0:
                transmission = 0.5 * 2 ** -(
                    (thickness_map - sd.hvl1)/sd.hvl2)
            elif thickness > sd.tvl1:
                transmission = 0.1 * 10 ** -(
                    (thickness_map - sd.tvl1)/sd.tvl2)
            if not isinstance(wall_affect_map, int):
                transmission[wall_affect_map == 0] = 1.
        else:
            errmsg = f'Found no shield data for {material} and {isotope}'
    return (transmission, errmsg)


def get_floor_distance(floor, general_values):
    """Calculate distance from floor 1 to floor != 1."""
    floor_dist = 0.
    if floor == 0:
        floor_dist = (
            general_values.h0 + general_values.c1 - general_values.c0)
    elif floor == 2:
        floor_dist = (
            general_values.h1 + general_values.c2 - general_values.c1)

    return floor_dist


def get_dose_factors_NM(source_row, isotope):
    """Calculate dose and maximum dose rate @ 1m from source (unshielded, pr workday).

    Parameters
    ----------
    source_row : list
        row from table_list source['NM']
    isotope: config_classes.Isotope
        isotope info for current isotope

    Returns
    -------
    dose_factor : float
        dose in mikroSv pr workday for current source @1m (unshielded)
    doserate_max_factor : float
        array og maximum doserate for current source unshielded
    """
    _, _, _, _, in_patient, A0, t1, duration, rest_void, n_pr_workday = source_row

    # doseconstant - decay and gammaray constant or damping in patient
    act_at_t1 = A0 * np.exp(-np.log(2) * t1 / isotope.half_life)
    gamma_ray_constant = (
        isotope.patient_constant if in_patient
        else isotope.gamma_ray_constant)

    # unshielded doserate factor at t1
    doserate_max_factor = act_at_t1 * gamma_ray_constant * rest_void

    # unshielded dose in uSv pr workday
    integral_duration = (
        (1./np.log(2)) * isotope.half_life
        * (1-np.exp(-np.log(2) * duration/isotope.half_life))
        )
    dose_factor = (
        act_at_t1 * integral_duration * gamma_ray_constant *
        rest_void * n_pr_workday)

    return (dose_factor, doserate_max_factor)


def calculate_dose_NM(
        sources, isotopes, walls, shield_data,
        map_shape, calibration_factor, general_values,
        progress_modal, progress_value, step, msgs):
    """Calculate parameters for NM sources."""
    dose_NM = {  # calculated values and arrays listed pr source
        'dose_pr_workday': np.zeros(map_shape),
        # np.array shielded and summed [uSv]
        'doserate_max_pr_workday': np.zeros(map_shape),
        # np.array shielded and summed [uSv/h]
        'dist_maps': [],  # dist_factors not saved, easily from 1/(dist_map**2)
        'dose_factors': [],
        'doserate_max_factors': [],
        'transmission_maps': [],
        'transmission_floor_0': [],
        'transmission_floor_2': [],
        }

    isotope_labels = [x.label for x in isotopes]
    progress_modal.setLabelText("Calculating NM dose...")

    for i, source in enumerate(sources):
        if source:
            isotope = isotopes[isotope_labels.index(source[3])]
            dist_map, dist_factors = get_distance_source(
                map_shape, source[2], calibration_factor)
            dose_factor, doserate_max_factor = get_dose_factors_NM(
                source, isotope)

            transmission_map = np.ones(map_shape)
            errmsgs = None
            for wall in walls:
                progress_value += step
                progress_modal.setValue(progress_value)
                if wall:
                    wall_affect_map, mask = calculate_wall_affect_sector(
                        map_shape, source[2], wall[2])
                    if general_values.correct_thickness is False:
                        wall_affect_map = np.ones(map_shape) * mask

                    material = wall[3]
                    transmission_map_this, errmsg = calculate_transmission(
                        shield_data, wall_affect_map, thickness=wall[4],
                        material=material, isotope=isotope)
                    if errmsg:
                        errmsgs.append(errmsg)
                    else:
                        transmission_map = (
                            transmission_map * transmission_map_this)

            thickness_corr_0 = 1
            thickness_corr_2 = 1
            if general_values.correct_thickness:
                dist = get_floor_distance(0, general_values)
                thickness_corr_0 = np.sqrt(dist_map ** 2 + dist ** 2) / dist
                dist = get_floor_distance(2, general_values)
                thickness_corr_2 = np.sqrt(dist_map ** 2 + dist ** 2) / dist
            transmission_floor_0, errmsg = calculate_transmission(
                shield_data, wall_affect_map=thickness_corr_0,
                thickness=general_values.shield_mm_below,
                material=general_values.shield_material_below,
                isotope=isotope)
            if errmsg:
                errmsgs.append(errmsg)
            transmission_floor_2, errmsg = calculate_transmission(
                shield_data, wall_affect_map=thickness_corr_2,
                thickness=general_values.shield_mm_above,
                material=general_values.shield_material_above,
                isotope=isotope)
            if errmsg:
                errmsgs.append(errmsg)

            if errmsgs:
                msgs.extend(errmsgs)

            dose_NM['dist_maps'].append(dist_map)
            dose_NM['dose_factors'].append(dose_factor)
            dose_NM['doserate_max_factors'].append(doserate_max_factor)
            dose_NM['transmission_maps'].append(transmission_map)
            dose_NM['transmission_floor_0'].append(transmission_floor_0)
            dose_NM['transmission_floor_2'].append(transmission_floor_2)
        else:
            dose_NM['dist_maps'].append(None)
            dose_NM['dose_factors'].append(None)
            dose_NM['doserate_max_factors'].append(None)
            dose_NM['transmission_maps'].append(None)
            dose_NM['transmission_floor_0'].append(None)
            dose_NM['transmission_floor_2'].append(None)

        if progress_modal.wasCanceled():
            dose_NM = None
            break
    return dose_NM


def calculate_dose_OT(
        sources, walls, shield_data,
        map_shape, calibration_factor, general_values,
        progress_modal, progress_value, step, msgs):
    """Calculate parameters for OT (kV isotropic) sources."""
    dose_OT = {  # calculated values and arrays listed pr source
        'dose_pr_workday': np.zeros(map_shape),
        # np.array shielded and summed [uSv]
        'dist_maps': [],  # dist_factors not saved, easily from 1/(dist_map**2)
        'dose_factors': [],
        'transmission_maps': [],
        'transmission_floor_0': [],
        'transmission_floor_2': [],
        }

    progress_modal.setLabelText("Calculating dose for other kV sources...")

    for i, source in enumerate(sources):
        if source:
            dist_map, dist_factors = get_distance_source(
                map_shape, source[2], calibration_factor)
            dose_factor = source[4] * source[5]

            transmission_map = np.ones(map_shape)
            errmsgs = None
            for wall in walls:
                progress_value += step
                progress_modal.setValue(progress_value)
                if wall:
                    wall_affect_map, mask = calculate_wall_affect_sector(
                        map_shape, source[2], wall[2])
                    if general_values.correct_thickness is False:
                        wall_affect_map = np.ones(map_shape) * mask

                    material = wall[3]
                    transmission_map_this, errmsg = calculate_transmission(
                        shield_data, wall_affect_map, thickness=wall[4],
                        material=material, kV_source=source[3])
                    if errmsg:
                        errmsgs.append(errmsg)
                    else:
                        transmission_map = (
                            transmission_map * transmission_map_this)

            thickness_corr_0 = 1
            thickness_corr_2 = 1
            if general_values.correct_thickness:
                dist = get_floor_distance(0, general_values)
                thickness_corr_0 = np.sqrt(dist_map ** 2 + dist ** 2) / dist
                dist = get_floor_distance(2, general_values)
                thickness_corr_2 = np.sqrt(dist_map ** 2 + dist ** 2) / dist
            transmission_floor_0, errmsg = calculate_transmission(
                shield_data, wall_affect_map=thickness_corr_0,
                thickness=general_values.shield_mm_below,
                material=general_values.shield_material_below,
                kV_source=source[3])
            if errmsg:
                errmsgs.append(errmsg)
            transmission_floor_2, errmsg = calculate_transmission(
                shield_data, wall_affect_map=thickness_corr_2,
                thickness=general_values.shield_mm_above,
                material=general_values.shield_material_above,
                kV_source=source[3])
            if errmsg:
                errmsgs.append(errmsg)

            if errmsgs:
                msgs.extend(errmsgs)

            dose_OT['dist_maps'].append(dist_map)
            dose_OT['dose_factors'].append(dose_factor)
            dose_OT['transmission_maps'].append(transmission_map)
            dose_OT['transmission_floor_0'].append(transmission_floor_0)
            dose_OT['transmission_floor_2'].append(transmission_floor_2)
        else:
            dose_OT['dist_maps'].append(None)
            dose_OT['dose_factors'].append(None)
            dose_OT['transmission_maps'].append(None)
            dose_OT['transmission_floor_0'].append(None)
            dose_OT['transmission_floor_2'].append(None)

        if progress_modal.wasCanceled():
            dose_OT = None
            break
    return dose_OT
