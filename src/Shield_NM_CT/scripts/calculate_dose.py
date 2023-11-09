#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of small functions used in ImageQC.

@author: Ellen Wasbo
"""
import numpy as np

# Shield_NM_CT block start

# Shield_NM_CT block end


def calculate_dose(main):
    """Calculate dose based on parameters in main updating dose_dict of main.

    Parameters
    ----------
    main : ui_main.MainWindow

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
        # any sources with # patients or dose-values > 0?
        sources_NM = get_valid_rows(
            main.NMsources_tab.table_list, nonzero_columns=[5, 7, 8, 9],
            n_coordinates=2)
        if sources_NM:
            sources['NM'] = sources_NM
        '''
        sources_CT = get_valid_rows(
            main.CTsources_tab.table_list, nonzero_columns=[], n_coordinates=2)
        if sources_CT:
            sources['CT'] = sources_CT
        FL...
        '''
        if not sources:
            proceed = False
            msgs.append(
                'Found no valid sources (either not defined, not active '
                'or values zero that causes zero dose.')

    walls = []
    if proceed:
        # any walls to consider (thickness > 0)
        walls = get_valid_rows(
            main.walls_tab.table_list, nonzero_columns=[4], n_coordinates=4)

        isotopes = main.isotopes
        materials = main.materials
        shield_data = main.shield_data
        general_values = main.general_values

        main.areas_tab.update_occ_map()
        occ_map = main.occ_map

        dose_NM = {  # calculated values and arrays listed pr source
            'dose_pr_workday': np.zeros(occ_map.shape),
            # np.array shielded and summed [uSv]
            'doserate_max_pr_workday': np.zeros(occ_map.shape),
            # np.array shielded and summed [uSv/h]
            'dist_maps': [],  # dist_factors not saved, easily from 1/(dist_map**2)
            'dose_factors': [],
            'doserate_max_factors': [],
            }
        if 'NM' in sources:
            isotope_labels = [x.label for x in isotopes]
            for source in sources['NM']:
                isotope = isotopes[isotope_labels.index(source[3])]
                dist_map, dist_factors = get_distance_source(
                    occ_map.shape, source[1], calibration_factor=calibration_factor)
                dose_factor, doserate_max_factor = get_dose_factors_NM(source, isotope)
                transmission = calculate_transmission_NM(
                    occ_map.shape, calibration_factor, source[2], walls, shield_data)

                dose_NM['dist_maps'].append(dist_map)
                dose_NM['dose_factors'].append(dose_factor)
                dose_NM['doserate_max_factors'].append(doserate_max_factor)
                dose_NM['transmission_maps'].append(transmission)

                dose_pr_workday = dose_factor * dist_factors * transmission

                dose_NM['dose_pr_workday'] += dose_pr_workday

    main.dose_dict = {
        'dose_NM': dose_NM,
        #'dose_CT': dose_CT,
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
    valid_table_list = []
    for row in table_list:
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
                    row[2] = coord_list
                    valid_table_list.append(row)
                except ValueError:
                    pass

    return valid_table_list


def get_distance_source(shape, xy, calibration_factor):
    """Calculate distance factors 1/dist^2 for (x,y) in image.

    Parameters
    ----------
    shape : tuple
        shape of array to generate
    xy: tuple of int
        Position of point in map
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
    distance_map[distance_map < 0.5] = 0.5  # ignore doses closer than 0.5m
    distance_factors = 1. / (distance_map ** 2)

    return (distance_map, distance_factors)


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
    if in_patient:
        gamma_ray_constant = (isotope.patient_constant if in_patient
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

def calculate_transmission_NM(shape, calibration_factor,
                              source_pos_xy, walls, shield_data):
    """Calculate transmission factors as map.

    Parameters
    ----------
    shape : TYPE
        DESCRIPTION.
    calibration_factor : TYPE
        DESCRIPTION.
    source_pos_xy : tuple or array
        x,y position of source
    walls : TYPE
        DESCRIPTION.
    shield_data : ShieldData
        for the selected source type

    Returns
    -------
    transmission_map : TYPE
        DESCRIPTION.

    """
    transmission_map = np.ones(shape)

    for wall in walls:
        # Find sector where wall affect the dose and correct transmission in this area.
        
        # horizontal, vertical or oblique wall?
        pass  #TODO
    
    return transmission_map
'''
  wallAffectSector=FLTARR(sizeMap)
  IF N_ELEMENTS(strucWalls) GT 0 THEN BEGIN  ;for each wall
    FOR i=0, N_TAGS(strucWalls)-1 DO BEGIN
      ; horisontal, vertical or oblique wall?
      IF strucWalls.(i).pos(0) EQ strucWalls.(i).pos(2) THEN dir=1 ELSE dir=0; dir 1 = vertical
      ;  define sector affected by wall set to dist else 0
      yposW=[strucWalls.(i).pos(1),strucWalls.(i).pos(3)]
      xposW=[strucWalls.(i).pos(0),strucWalls.(i).pos(2)]

      IF dir EQ 1 THEN BEGIN; vertical
        y1=MIN(yposW) & y2=MAX(yposW)
        xposW=xposW(0)
        IF xposW GT pos(0) THEN xxStartEnd=[CEIL(xposW), sizeMap(0)-1] ELSE xxStartEnd=[0, FLOOR(xposW)]
        FOR xx= xxStartEnd(0), xxStartEnd(1) DO BEGIN
          geomFac=(xx-pos(0))/(xposW(0)-pos(0))
          yy1=ROUND(pos(1))+ROUND((y1-pos(1))*geomFac)
          yy2=ROUND(pos(1))+ROUND((y2-pos(1))*geomFac)
          IF yy1 LT 0 THEN yy1=0
          IF yy2 GT sizeMap(1)-1 THEN yy2=sizeMap(1)-1
          IF yy1 LE sizeMap(1)-1 AND yy2 GE 0 THEN wallAffectSector[xx,yy1:yy2]=distSource[xx,yy1:yy2]/(cFactor(0)*ABS(xx-pos(0)));thickness corr
        ENDFOR
      ENDIF ELSE BEGIN
        x1=MIN(xposW) & x2=MAX(xposW)
        yposW=yposW(0)
        IF yposW GT pos(1) THEN yyStartEnd=[CEIL(yposW), sizeMap(1)-1] ELSE yyStartEnd=[0, FLOOR(yposW)]
        FOR yy= yyStartEnd(0), yyStartEnd(1) DO BEGIN
          geomFac=(yy-pos(1))/(yposW-pos(1))
          xx1=ROUND(pos(0))+ROUND((x1-pos(0))*geomFac)
          xx2=ROUND(pos(0))+ROUND((x2-pos(0))*geomFac)
          IF xx1 LT 0 THEN xx1=0
          IF xx2 GT sizeMap(0)-1 THEN xx2=sizeMap(0)-1
          IF xx1 LE sizeMap(0)-1 AND xx2 GE 0 THEN wallAffectSector[xx1:xx2,yy]=distSource[xx1:xx2,yy]/(cFactor(0)*ABS(yy-pos(1)));thickness corr
        ENDFOR
      ENDELSE

      IF corrThick NE 1 THEN BEGIN
        idinSector=WHERE(wallAffectSector NE 0)
        wallAffectSector(idinSector)=1.
      ENDIF

      ;  calculate B for all pixels in sector based on eff.thickness and isotope
      dataNames=TAG_NAMES(thisData)
      IF strucWalls.(i).std EQ 1 THEN BEGIN
        matId=stdW.material
        thickn=stdW.thickness
      ENDIF ELSE BEGIN
        matId=strucWalls.(i).material
        thickn=strucWalls.(i).thickness
      ENDELSE
      IF dataNames.HasValue('ABG') THEN BEGIN
        abg=thisData.abg[*,matId]
        B=((1+(abg(1)/abg(0)))*exp(abg(0)*abg(2)*thickn*wallAffectSector)-(abg(1)/abg(0)))^(-1./abg(2))
      ENDIF ELSE BEGIN
        B=0.1^(thickn*wallAffectSector/thisData.tvl(matId))
      ENDELSE
      idnoSector=WHERE(wallAffectSector EQ 0)
      B(idnoSector)=1.
      doseMapThis=B*doseMapThis
      doseRateMaxThis=B*doseRateMaxThis

      wallAffectSector=0.*wallAffectSector
    ENDFOR

  ENDIF

  return, CREATE_STRUCT('doseMap',doseMapThis,'maxDoseRate',doseRateMaxThis)
end

    # calculate transmission for pixels in sector based on material/thickness/isotope
    IF corrThick THEN thickCorr=1./floorDist*distSource ELSE thickCorr=1.;correctionfactor floorthickness in direction from source
    dataNames=TAG_NAMES(thisData)
    ;concrete
    matId=1
    thickn=floorThickCon*thickCorr
    IF dataNames.HasValue('ABG') THEN BEGIN
      abg=thisData.abg[*,matId]
      B=((1+(abg(1)/abg(0)))*exp(abg(0)*abg(2)*thickn)-(abg(1)/abg(0)))^(-1./abg(2))
    ENDIF ELSE BEGIN
      B=0.1^(thickn/thisData.tvl(matId))
    ENDELSE
    doseMapThis=B*doseMapThis
    doseRateMaxThis=B*doseRateMaxThis
    ;lead
    IF floorThickLead GT 0. THEN BEGIN
      matID=0
      thickn=floorThickLead*thickCorr
      IF dataNames.HasValue('ABG') THEN BEGIN
        abg=thisData.abg[*,matId]
        B=((1+(abg(1)/abg(0)))*exp(abg(0)*abg(2)*thickn)-(abg(1)/abg(0)))^(-1./abg(2))
      ENDIF ELSE BEGIN
        B=0.1^(thickn/thisData.tvl(matId))
      ENDELSE
      doseMapThis=B*doseMapThis
      doseRateMaxThis=B*doseRateMaxThis
    ENDIF
'''