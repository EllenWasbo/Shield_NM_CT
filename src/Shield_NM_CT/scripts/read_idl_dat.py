# -*- coding: utf-8 -*-
"""
Convert config.dat from IDL version of imageQC to config_classes of py version.

@author: EllenWasbo
"""
import pandas as pd
import numpy as np
from PIL import Image
from pathlib import Path

from PyQt5.QtWidgets import QMessageBox, QFileDialog

# Shield_NM_CT block start
import Shield_NM_CT.scripts.modified_scipy_io_idl as mod_scipy_io_idl
from Shield_NM_CT.config.config_classes import GeneralValues
from Shield_NM_CT.config import config_func as cff
# Shield_NM_CT block end

IDL_MATERIALS = ['Lead', 'Concrete']  # indexed materials converted to py-names
IDL_ISOTOPES = [['F18', 'Tc99m', 'I123', 'I131', 'Lu177'],
                ['F-18', 'Tc-99m', 'I-123', 'I-131', 'Lu-177']]


def try_decode(bytestr):
    """Decode and handle attributeError when empty input string."""
    try:
        return_string = bytestr.decode('utf-8')
    except AttributeError:
        return_string = ''

    return return_string


class ReadDat():
    """Class to read IDL .dat-file."""

    def __init__(self, main, fname):

        self.errmsgs = []
        self.main = main

        self.read_config_dat(fname)

    def read_config_dat(self, fname):
        """Read .dat from IDL version of this software.

        Parameters
        ----------
        fname : str
            full path of config.dat
        """
        dat_dict = {}
        self.folder = ''
        try:
            dat_dict = mod_scipy_io_idl.readsav(fname)
        except ValueError:
            self.errmsgs.append(
                ('Error reading .dat file.'))
        if dat_dict:
            QMessageBox.information(
                self.main, 'Locate project folder',
                'Now you will be asked to locate or create a folder to place '
                'the generated project files.')
            dlg = QFileDialog(self.main,
                              directory=r'C:\Users\ellen\Documents\GitHub\Shield_NM_CT\tests\testdat_output')
            dlg.setFileMode(QFileDialog.Directory)
            if dlg.exec():
                fname = dlg.selectedFiles()
                self.folder = fname[0]

        if self.folder:
            # TODO ask to override files?
            any_res = False
            if 'im' in dat_dict.keys():
                # save image as png
                imagenp = dat_dict['im']
                imagenp = np.flipud(imagenp)
                im = Image.fromarray(imagenp)
                im = im.convert('L')  # grayscale
                path = Path(self.folder) / 'floorplan.png'
                im.save(path)
                any_res = True
                self.shape = imagenp.shape
                if 'swalls' in dat_dict.keys():
                    if str(dat_dict['swalls'].dtype) != 'int16':
                        self.convert_struct(
                            self.as_dict(dat_dict['swalls']), fname='walls')
                if 'sareas' in dat_dict.keys():
                    if str(dat_dict['sareas'].dtype) != 'int16':
                        self.convert_struct(
                            self.as_dict(dat_dict['sareas']), fname='areas')
                if 'ssources' in dat_dict.keys():
                    if str(dat_dict['ssources'].dtype) != 'int16':
                        self.convert_struct(
                            self.as_dict(dat_dict['ssources']), fname='NMsources')
                if 'ssourcesct' in dat_dict.keys():
                    if str(dat_dict['ssourcesct'].dtype) != 'int16':
                        self.convert_struct(
                            self.as_dict(dat_dict['ssourcesct']), fname='CTsources')
                    if 'sagtab' in dat_dict.keys() or 'cortab' in dat_dict.keys():
                        QMessageBox.warning(
                            self.main, 'CT dose maps not imported',
                            'The CT dose maps will not be imported. '
                            'Transfer this information manually if other than '
                            'default needed.')
                if 'startmap' in dat_dict.keys():
                    self.add_scale(
                        dat_dict['startmap'], dat_dict['endmap'], dat_dict['lencalib'])
                if 'workdays' in dat_dict.keys():
                    self.add_general_values(
                        dat_dict['workdays'], dat_dict['h0'], dat_dict['h1'],
                        dat_dict['conceil'], dat_dict['confloor'],
                        dat_dict['leadceil'], dat_dict['leadfloor']
                        )

            if not any_res:
                self.errmsgs.append(
                    'Could not find the expected content in the selected file.')

        return self.folder

    def as_dict(self, rec):
        """Turn a numpy recarray record into a dict."""
        return {name: rec[name] for name in rec.dtype.names}

    def convert_pos(self, pos, area=False):
        """Convert to integers and comma separated string."""
        pos_string = ''
        pos_list = [int(val) for val in pos]
        for i, val in enumerate(pos_list):
            if i % 2:  # y values
                pos_list[i] = self.shape[0] - val
        if area:
            xs = [pos_list[0], pos_list[2]]
            ys = [pos_list[1], pos_list[3]]
            pos_list = [min(xs), min(ys), max(xs), max(ys)]
        pos_list = [str(val) for val in pos_list]
        pos_string = ', '.join(pos_list)
        return pos_string

    def save_csv(self, datalist, path=''):
        """Save table to csv."""
        df = pd.DataFrame(datalist[1:], columns=datalist[0])
        df.to_csv(path, sep=self.main.general_values.csv_separator,
                  decimal=self.main.general_values.csv_decimal)

    def convert_struct(self, d, fname='walls'):
        """Convert structure into csv table.

        Parameters
        ----------
        d : dict
            structure in .dat converted to dictionary
        """
        keys = [key for key, val in d.items()]

        table_list = []
        for key in keys:
            dict_this = self.as_dict(d[key][0])
            name = try_decode(dict_this['ID'][0])
            pos = self.convert_pos(dict_this['POS'][0], area=(fname == 'areas'))

            if fname == 'areas':
                factor = dict_this['OCC'][0]
                table_list.append([True, name, pos, factor])
            elif fname == 'walls':
                material = IDL_MATERIALS[dict_this['MATERIAL'][0]]
                thickness = 10. * dict_this['THICKNESS'][0]
                table_list.append([True, name, pos, material, thickness])
            elif fname == 'NMsources':
                isotope_idl = try_decode(dict_this['ISOTOPE'][0])
                if isotope_idl in IDL_ISOTOPES[0]:
                    idx = IDL_ISOTOPES[0].index(isotope_idl)
                    isotope = IDL_ISOTOPES[1][idx]
                else:
                    isotope = 'F18'
                    self.errmsgs.append(
                        f'Isotope {isotope_idl} not recognized. Set to F-18.')
                in_patient = True if dict_this['INPATIENT'][0] else False
                A0 = dict_this['A0'][0]
                t1 = dict_this['T1'][0]
                duration = dict_this['T2'][0]
                rest_void = dict_this['RESTVOID'][0]
                n_pr_workday = dict_this['NPRWORKDAY'][0]
                table_list.append([True, name, pos, isotope, in_patient,
                                   A0, t1, duration, rest_void, n_pr_workday])
            elif fname == 'CTsources':
                kVp = dict_this['KVP'][0]
                kV_source = f'CT {kVp} kVp'
                rotation = - dict_this['ROT'][0]
                kVp_correction = dict_this['KVCORR'][0]
                mAs = dict_this['MASPRPAT'][0]
                n_pr_workday = dict_this['NPRWORKDAY'][0]
                table_list.append([True, name, pos,
                                   rotation,
                                   kV_source, 'Siemens140', 'mAs', mAs,
                                   kVp_correction, n_pr_workday])

        if len(table_list) == 0:
            if fname == 'areas':
                table_list = [[True, '', '', 1.]]
            elif fname == 'walls':
                material = self.main.materials[0]
                table_list = [[True, '', '', material.label,
                               material.default_thickness]]
            elif fname == 'NMsources':
                table_list = [
                    [True, '', '', 'F-18', True, 0.0, 0.0, 0.0, 1.0, 0.0]]
            elif fname == 'CTsources':
                table_list = [
                    [True, '', '', 0., self.main.general_values.kV_sources[0],
                     'Siemens140', 'mAs', 4000, 1.0, 0.0]]

        headers = []
        if fname == 'areas':
            headers = ['Active', 'Area name', 'x0,y0,x1,y1',
                       'Occupancy factor']
            self.empty_row = [True, '', '', 1.]
        elif fname == 'walls':
            headers = ['Active', 'Wall name', 'x0,y0,x1,y1',
                       'Material', 'Thickness (mm)']
        elif fname == 'NMsources':
            headers = ['Active', 'Source name', 'x,y', 'Isotope', 'In patient',
                       'A0 (MBq)', 't1 (hours)', 'Duration (hours)', 'Rest void',
                       '# pr workday']
        elif fname == 'CTsources':
            headers = ['Active', 'Source name', 'x,y', 'Rotation', 'kV source',
                       'Doserate map', 'Workload unit', 'Workload pr patient',
                       'Correction', '# pr workday']

        if headers:
            table_list.insert(0, headers)
            path = Path(self.folder) / f'{fname}.csv'
            self.save_csv(table_list, path=path)

    def add_scale(self, startmap, endmap, lencalib):
        """Get scale settings and save as .csv."""
        pos = ', '.join([self.convert_pos(startmap), self.convert_pos(endmap)])
        length = float(try_decode(lencalib[0]))
        table_list = [['Line positions x0,y0,x1,y1', 'Actual length (m)'],
                      [pos, length]]
        path = Path(self.folder) / 'scale.csv'
        self.save_csv(table_list, path=path)

    def add_general_values(self, working_days, h0, h1, conceil, confloor,
                           leadceil, leadfloor):
        """Get general values and save as yaml."""
        general_values = GeneralValues(working_days=working_days)
        try:
            general_values.h0 = float(try_decode(h0[0]))
        except ValueError:
            self.errmsgs.append('Failed reading H0.')
        try:
            general_values.h1 = float(try_decode(h1[0]))
        except ValueError:
            self.errmsgs.append('Failed reading H1.')
        try:
            concrete_above = float(try_decode(conceil[0]))
            lead_above = float(try_decode(leadceil[0]))
            if concrete_above > 0 and lead_above > 0:
                self.errmsgs.append(
                    'Combination of lead and concrete between floors '
                    'no longer accepted.')
            else:
                if lead_above > 0:
                    general_values.shield_material_above = 'Lead'
                    general_values.shield_mm_above = 10 * lead_above
                else:
                    general_values.shield_mm_above = 10 * concrete_above
        except ValueError:
            self.errmsgs.append('Failed reading shielding floor above.')
        try:
            concrete_below = float(try_decode(confloor[0]))
            lead_below = float(try_decode(leadfloor[0]))
            if concrete_below > 0 and lead_below > 0:
                self.errmsgs.append(
                    'Combination of lead and concrete between floors '
                    'no longer accepted.')
            else:
                if lead_below > 0:
                    general_values.shield_material_below = 'Lead'
                    general_values.shield_mm_below = 10 * lead_below
                else:
                    general_values.shield_mm_below = 10 * concrete_below
        except ValueError:
            self.errmsgs.append('Failed reading shielding floor below.')

        _, _ = cff.save_settings(
            general_values, fname='general_values', temp_config_folder=self.folder)
