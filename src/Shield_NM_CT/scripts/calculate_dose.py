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
                nonzero_columns = [7, 8, 9]
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
                main.CTsources_tab.table_list, nonzero_columns=[7, 8, 9],
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

        main.areas_tab.update_occ_map(update_overlay=False, update_patches=False)

        nNM = 0
        if 'NM' in sources:
            dose_NM = calculate_dose_NM(
                sources['NM'], main.isotopes, walls, main.shield_data,
                main.occ_map.shape, calibration_factor, main.general_values,
                progress_modal, current_progress_value, step, msgs
                )
            nNM = len(sources['NM'])
            current_progress_value = 100 * nNM
        else:
            dose_NM = None

        nCT = 0
        if 'CT' in sources and progress_modal.wasCanceled() is False:
            dose_CT = calculate_dose_kV(
                sources['CT'], main.ct_models, walls, main.shield_data,
                main.occ_map.shape, calibration_factor, main.general_values,
                progress_modal, current_progress_value, step, msgs
                )
            nCT = len(sources['CT'])
            current_progress_value = 100 * (nNM + nCT)
        else:
            dose_CT = None

        if 'OT' in sources and progress_modal.wasCanceled() is False:
            dose_OT = calculate_dose_kV(
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
                dd = dose_NM
                param = 'doserate_max_factors'
                main.dose_dict['dose_NM'][param][source_number] = dd[param][0]
            elif modality == 'CT':
                dd = dose_CT
            else:
                dd = dose_OT
            for param in [
                    'dist_maps', 'dose_factors', 'transmission_maps']:
                main.dose_dict[f'dose_{modality}'][param][source_number] = dd[param][0]

        else:
            main.dose_dict = {
                'dose_NM': dose_NM,
                'dose_CT': dose_CT,
                'dose_OT': dose_OT,
                }
    else:
        if modality:  # not valid dose (e.g. zero and specific source)
            if modality == 'NM':
                main.dose_dict['dose_NM']['doserate_max_factors'][source_number] = None
            for param in [
                    'dist_maps', 'dose_factors', 'transmission_maps']:
                main.dose_dict[f'dose_{modality}'][param][source_number] = None

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
    """
    sz_y, sz_x = shape
    x, y = xy
    xs, ys = np.meshgrid(np.arange(sz_x), np.arange(sz_y))
    distance_map = np.sqrt((xs-x) ** 2 + (ys-y) ** 2)
    distance_map = calibration_factor * distance_map
    distance_map[distance_map < 0.1] = 0.1  # ignore doses closer than 0.5m

    return distance_map


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
            if data.material == material and data.kV_source == kV_source:
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

    half_life = isotope.half_life
    if isotope.half_life_unit == 'minutes':  # must match choises in settings Isotope
        half_life = half_life / 60
    elif isotope.half_life_unit == 'days':
        half_life = half_life * 24

    # doseconstant - decay and gammaray constant or damping in patient
    act_at_t1 = A0 * np.exp(-np.log(2) * t1 / half_life)
    gamma_ray_constant = (
        isotope.patient_constant if in_patient
        else isotope.gamma_ray_constant)

    # unshielded doserate factor at t1
    doserate_max_factor = act_at_t1 * gamma_ray_constant * rest_void

    # unshielded dose in uSv pr workday
    integral_duration = (
        (1./np.log(2)) * half_life
        * (1-np.exp(-np.log(2) * duration/half_life))
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
        'dist_maps': [],  # list of np.array, distances in floor 1
        'dose_factors': [],  # list of floats - unshielded dose uSv @ 1 m pr day
        'doserate_max_factors': [],  # list of floats - max doserate uSv/h @ 1m
        'transmission_maps': [],  # list of list of transmission map pr floor pr source
        }

    isotope_labels = [x.label for x in isotopes]
    progress_modal.setLabelText("Calculating NM dose...")

    for i, source in enumerate(sources):
        if source:
            isotope = isotopes[isotope_labels.index(source[3])]
            dist_map = get_distance_source(
                map_shape, source[2], calibration_factor)
            dose_factor, doserate_max_factor = get_dose_factors_NM(
                source, isotope)

            transmission_map = np.ones(map_shape)
            if any(walls):
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
                            msgs.append(errmsg)
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
                msgs.append(errmsg)
            transmission_floor_2, errmsg = calculate_transmission(
                shield_data, wall_affect_map=thickness_corr_2,
                thickness=general_values.shield_mm_above,
                material=general_values.shield_material_above,
                isotope=isotope)
            if errmsg:
                msgs.append(errmsg)

            transmission_maps = [
                transmission_floor_0, transmission_map, transmission_floor_2]

            dose_NM['dist_maps'].append(dist_map)
            dose_NM['dose_factors'].append(dose_factor)
            dose_NM['doserate_max_factors'].append(doserate_max_factor)
            dose_NM['transmission_maps'].append(transmission_maps)
        else:
            dose_NM['dist_maps'].append(None)
            dose_NM['dose_factors'].append(None)
            dose_NM['doserate_max_factors'].append(None)
            dose_NM['transmission_maps'].append(None)

        if progress_modal.wasCanceled():
            dose_NM = None
            break
    return dose_NM


def generate_CT_doseratemap(template,
                            rotation=0., map_shape=(0, 0), source_xy=(0, 0),
                            resolution=0.1, all_floors=True, general_values=None,
                            factor=1.0):
    """Generate array with doserates based on values from config_classes.CT_model.

    Parameters
    ----------
    template : config_classes.CT_model
        doserate values at defined positions
    rotation : float, optional
        rotation of CT in degrees
    map_shape : tuple of ints, optional
        shape of output map
    source_xy : tuple of ints
        (x, y) pix position of source in map
    resolution : float, optional
        resolution of returnd array in meters/pixel. The default is 0.1.
    all_floors : bool, optional
        calculate one np.array per floor. If False only floor 1. Default is True.
    general_values : cfc.GeneralValues, optional
        Used for heights if all_floors is True. Default is None.
    factor : float, optional
        Multiply all doseratemaps with this factor. Default is 1.0.

    Returns
    -------
    doseratemap : np.array or list of np.array if all_floors True
    """
    # y along CT table at iso
    doseratemap = np.zeros(map_shape)
    ny, nx = map_shape
    cx, cy = source_xy
    xs, ys = np.meshgrid(np.arange(nx) - cx, np.arange(ny) - cy)
    ys = -ys
    dists_sq = resolution ** 2 * (xs ** 2 + ys ** 2)
    rot = - rotation * np.pi / 180.
    ys_rotated = -np.sin(rot)*xs + np.cos(rot)*ys
    sin_angles = np.divide(resolution * ys_rotated, np.sqrt(dists_sq),
                           out=np.zeros_like(dists_sq),
                           where=dists_sq > 0)

    if template.scatter_factor_front > 0:
        sin_rear = np.sin(template.rear_stop_angle * np.pi / 180.)
        sin_front = np.sin(template.front_stop_angle * np.pi / 180.)
        doseratemap = np.divide(
            template.scatter_factor_gantry, dists_sq,
            out=np.zeros_like(dists_sq),
            where=dists_sq > 0.6**2)
        doseratemap = np.divide(
            template.scatter_factor_front, dists_sq,
            out=doseratemap,
            where=(sin_angles < sin_front) & (dists_sq > 0.6**2))
        doseratemap = np.divide(
            template.scatter_factor_rear, dists_sq,
            out=doseratemap,
            where=(sin_angles > sin_rear) & (dists_sq > 0.6**2))
        factors = np.ones(map_shape)
        if template.angle_flatten_front != -90:
            rot_f = template.angle_flatten_front
            sin_flatten = np.sin(rot_f * np.pi / 180.)
            factors = np.subtract(1, np.abs(sin_angles - sin_flatten),
                                  out=factors, where=sin_angles < sin_flatten)
        if template.angle_flatten_rear != 90:
            rot_f = template.angle_flatten_rear
            sin_flatten = np.sin(rot_f * np.pi / 180.)
            factors = np.subtract(1, np.abs(sin_angles - sin_flatten),
                                  out=factors, where=sin_angles > sin_flatten)
        factors = factors ** template.flatten_power
        doseratemap = factor * factors * doseratemap

        if all_floors and general_values is not None:
            doseratemap = [doseratemap]
            for floor in [0, 2]:
                floor_dist = get_floor_distance(floor, general_values)
                dists_sq = resolution ** 2 * (xs ** 2 + ys ** 2) + floor_dist ** 2
                sin_angles = resolution * ys / np.sqrt(dists_sq)
                doseratemap_this = template.scatter_factor_gantry / dists_sq
                doseratemap_this = np.divide(
                    template.scatter_factor_front, dists_sq,
                    out=doseratemap_this,
                    where=(sin_angles < sin_front))
                doseratemap_this = np.divide(
                    template.scatter_factor_rear, dists_sq,
                    out=doseratemap_this,
                    where=(sin_angles > sin_rear))
                # TODO flatten to reduce currently ignored
                doseratemap_this = factor * doseratemap_this
                doseratemap.insert(floor, doseratemap_this)

    return doseratemap


def get_dose_factors_CT(source_row, ct_model, map_shape, general_values,
                        calibration_factor):
    """Calculate dose distribution from source (unshielded, pr workday).

    Parameters
    ----------
    source_row : list
        row from table_list source['CT']
    ct_model : config_classes.CT_model
        info to generate current doseratemap
    map_shape : tuple of ints
        shape of map in pixels (y, x)
    general_values : config_classes.GeneralValues
        to get floor heights
    calibration_factor : float
        meters/pixel

    Returns
    -------
    dose_factors : list of np.array
        dose in mikroSv pr workday for current source (unshielded) per floor (0,1,2)
    """
    _, _, pos, rotation, _, _, _, units, correction, n_pr_workday = source_row

    general_factor = correction * units * n_pr_workday

    dose_factors = generate_CT_doseratemap(
        ct_model, rotation=rotation, map_shape=map_shape, source_xy=pos,
        resolution=calibration_factor, general_values=general_values,
        factor=general_factor)

    return dose_factors


def calculate_dose_kV(
        sources, ct_models, walls, shield_data,
        map_shape, calibration_factor, general_values,
        progress_modal, progress_value, step, msgs):
    """Calculate parameters for kV sources, isotropic (OT) or non-isotropic (CT)."""
    dose_dict = {  # calculated values and arrays listed pr source
        'dist_maps': [],  # not used for CT
        'dose_factors': [],
        # list of float (OT) or lists of dose pr day pr floor (CT) pr source
        'transmission_maps': [],  # list of transmission_map list of 3 floors pr source
        }
    mod = 'kV' if ct_models is None else 'CT'

    progress_modal.setLabelText(f'Calculating dose for {mod} sources...')

    for i, source in enumerate(sources):
        if source:
            dist_map = get_distance_source(
                map_shape, source[2], calibration_factor)
            if mod == 'CT':
                ct_models_label = source[5]
                try:
                    idx = [c.label for c in ct_models].index(ct_models_label)
                    dose_factor = get_dose_factors_CT(
                        source, ct_models[idx], map_shape, general_values,
                        calibration_factor)
                except ValueError:
                    name = str(i) if source[1] == '' else source[1]
                    msgs.append(f'Failed finding CT doseratemap ({source[5]}) '
                                f'for CT source ({name})')
                    dose_factor = None
                kV_source = source[4]
            else:
                dose_factor = source[4] * source[5]
                kV_source = source[3]

            if dose_factor is None:  # doseratemap CT not found
                transmission_maps = None
            else:
                transmission_map = np.ones(map_shape)
                if any(walls):
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
                                material=material, kV_source=kV_source)
                            if errmsg:
                                msgs.append(errmsg)
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
                    kV_source=kV_source)
                if errmsg:
                    msgs.append(errmsg)
                transmission_floor_2, errmsg = calculate_transmission(
                    shield_data, wall_affect_map=thickness_corr_2,
                    thickness=general_values.shield_mm_above,
                    material=general_values.shield_material_above,
                    kV_source=kV_source)
                if errmsg:
                    msgs.append(errmsg)

                transmission_maps = [
                    transmission_floor_0, transmission_map, transmission_floor_2]

            dose_dict['dist_maps'].append(dist_map)
            dose_dict['dose_factors'].append(dose_factor)
            dose_dict['transmission_maps'].append(transmission_maps)
        else:
            dose_dict['dist_maps'].append(None)
            dose_dict['dose_factors'].append(None)
            dose_dict['transmission_maps'].append(None)

        if progress_modal.wasCanceled():
            dose_dict = None
            break
    return dose_dict
