#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Functions used for configuration settings.

@author: Ellen Wasbo
"""
import os
from pathlib import Path
from time import time, ctime
from dataclasses import asdict

import yaml
from PyQt6.QtWidgets import QMessageBox, QFileDialog

# Shield_NM_CT block block start
from Shield_NM_CT.config.Shield_NM_CT_constants import (
    USERNAME, APPDATA, TEMPDIR, ENV_USER_PREFS_PATH, ENV_CONFIG_FOLDER,
    CONFIG_FNAMES, USER_PREFS_FNAME, VERSION
    )
import Shield_NM_CT.config.config_classes as cfc
from Shield_NM_CT.ui import messageboxes
# Shield_NM_CT block block end


def verify_config_folder(widget):
    """Test whether config folder exist, ask to create if not.

    Parameters
    ----------
    widget : QWidget
        calling widget

    Returns
    -------
    proceed : bool
        continue to save - config folder is ready
    """
    proceed = True
    if get_config_folder() == '':
        proceed = False
        quest = '''Config folder not specified.
        Do you want to locate or initate a config folder now?'''
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            'Proceed?', quest,
            buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            parent=widget
            )
        res = msg_box.exec()
        if res == QMessageBox.StandardButton.Yes:
            proceed = True
        if proceed:
            dlg = QFileDialog()
            dlg.setFileMode(QFileDialog.FileMode.Directory)
            if dlg.exec():
                fname = dlg.selectedFiles()
                os.environ[ENV_CONFIG_FOLDER] = fname[0]
                _, user_path, user_prefs = load_user_prefs()
                if user_path != '':
                    user_prefs.config_folder = os.environ[ENV_CONFIG_FOLDER]
                    _, _ = save_user_prefs(user_prefs, parentwidget=widget)

    return proceed


def get_active_users():
    """Get list of active usernames sharing the config folder."""
    path = get_config_filename('active_users')
    active_users = {}

    if path != '':
        with open(path, 'r') as file:
            active_users = yaml.safe_load(file)

    return active_users


def add_user_to_active_users():
    """Add current user to yaml holding active users of the config folder."""
    path = os.environ[ENV_CONFIG_FOLDER]
    if path != '':
        active_users = {}
        path = get_config_filename('active_users', force=True)
        if os.path.exists(path):
            with open(path, 'r') as file:
                active_users = yaml.safe_load(file)

        active_users[USERNAME] = ctime()

        if os.access(Path(path).parent, os.W_OK):
            with open(path, 'w') as file:
                yaml.safe_dump(
                    active_users, file,
                    default_flow_style=None, sort_keys=False)


def remove_user_from_active_users():
    """Remove current user from yaml holding active users."""
    path = get_config_filename('active_users')
    if path != '':
        active_users = {}
        with open(path, 'r') as file:
            active_users = yaml.safe_load(file)

        active_users.pop(USERNAME, None)

        if os.access(Path(path).parent, os.W_OK):
            with open(path, 'w') as file:
                yaml.safe_dump(
                    active_users, file,
                    default_flow_style=None, sort_keys=False)


def init_user_prefs(path=APPDATA, config_folder=''):
    """Initiate empty local folder/file optionally with config_folder set.

    Returns
    -------
    status: bool
        False if failed initiating user preferences and config folder
    path_out: str
        path (or '' if failed)
    errmsg: str
        error message
    """
    status = False
    errmsg = ''
    path_out = ''

    # initiate APPDATA or TEMPDIR Shield_NM_CT if missing
    if os.path.exists(path) is False:
        if os.access(Path(path).parent, os.W_OK):
            os.mkdir(path)
        else:
            errmsg = '\n'.join(['Missing writing permission:',
                                Path(path).parent])

    if errmsg == '':
        userpref = cfc.UserPreferences()
        userpref.config_folder = config_folder

        path_out = os.path.join(path, USER_PREFS_FNAME)

        if os.access(path, os.W_OK):
            with open(path_out, 'w') as file:
                yaml.safe_dump(
                    asdict(userpref), file,
                    default_flow_style=None, sort_keys=False)
            status = True
        else:
            errmsg = '\n'.join(['Missing writing permission:', path_out])
            path_out = ''

    if errmsg != '':
        errmsg = '\n'.join([errmsg,
                            'Saving settings is not possible.'])

    return (status, path_out, errmsg)


def verify_input_dict(dict_input, default_object):
    """Verify input from yaml if config classes change on newer versions.

    Remove old keywords from input.
    """
    default_dict = asdict(default_object)
    actual_keys = [*default_dict]
    updated_dict = {k: v for k, v in dict_input.items() if k in actual_keys}

    return updated_dict


def save_user_prefs(userpref, parentwidget=None):
    """Save user preferences to user_preferences.yaml file.

    Parameters
    ----------
    userpref : object of class UserPreferences

    Returns
    -------
    bool
        False if failed saving user preferences
    str
        file path to save to
    """
    status = False
    try:
        path = os.environ[ENV_USER_PREFS_PATH]
    except KeyError:
        if parentwidget is not None:
            quest = 'Save user_preferences.yaml in:'
            res = messageboxes.QuestionBox(
                parentwidget, title='Save as', msg=quest,
                yes_text=f'{APPDATA}', no_text=f'{TEMPDIR}')
            res.exec()
            if res.clickedButton() == res.yes:
                path_local = APPDATA
            else:
                path_local = TEMPDIR
            _, path, userpref = init_user_prefs(
                    path=path_local, config_folder=os.environ[ENV_CONFIG_FOLDER])
        else:
            path = ''

    if path != '':
        if os.access(Path(path).parent, os.W_OK):
            with open(path, 'w') as file:
                yaml.safe_dump(
                    asdict(userpref), file,
                    default_flow_style=None, sort_keys=False)
            status = True
            os.environ[ENV_CONFIG_FOLDER] = userpref.config_folder

    return (status, path)


def load_user_prefs():
    """Load yaml file.

    Returns
    -------
    bool
        True if yaml file found
    str
        file path where tried to load from
    UserPreferences
    """
    status = True
    userprefs = None
    path = ''
    try:
        path = os.environ[ENV_USER_PREFS_PATH]
    except KeyError:
        path = os.path.join(APPDATA, USER_PREFS_FNAME)
        if os.path.exists(path) is False:
            path = os.path.join(TEMPDIR, USER_PREFS_FNAME)  # try with TEMPDIR

    if os.path.exists(path):
        with open(path, 'r') as file:
            doc = yaml.safe_load(file)
            updated_doc = verify_input_dict(doc, cfc.UserPreferences())
            userprefs = cfc.UserPreferences(**updated_doc)

    if userprefs is None:
        status = False
        path = ''
        userprefs = cfc.UserPreferences()

    return (status, path, userprefs)


def get_config_folder():
    """Get config folder.

    Returns
    -------
    str
        Config folder if exists else empty string.
    """
    try:
        path = os.environ[ENV_CONFIG_FOLDER]
        config_folder = path if os.path.exists(path) else ''
    except KeyError:
        config_folder = ''

    return config_folder


def get_config_filename(fname, force=False):
    """Verify if yaml file exists.

    Parameters
    ----------
    fname : str
        filename as defined in CONFIG_FNAMES (or + _<modality> if paramsets)
    force : bool
        force return filename even though it does not exist

    Returns
    -------
    str
        full path to yaml file if it exist, empty if not verified
    """
    path = ''
    if os.environ[ENV_CONFIG_FOLDER] != '':
        path_temp = os.path.join(
            os.environ[ENV_CONFIG_FOLDER], fname + '.yaml')
        path_temp = os.path.normpath(path_temp)
        if os.path.exists(path_temp):
            path = path_temp
        else:
            if force:
                path = path_temp

    return path


def load_settings(fname='', temp_config_folder=''):
    """Load settings from yaml file in config folder.

    Parameters
    ----------
    fname : str
        yaml filename without folder and extension
    temp_config_folder : str
        temporary config folder e.g. when import. Default is '' (ignored)

    Returns
    -------
    bool
        True if success
    str
        full path of file tried to load from
    object
        structured objects defined by the corresponding dataclass
    """
    status = False
    path = ''
    settings = None

    if fname != '':
        return_default = False
        if temp_config_folder == '':
            path = get_config_filename(fname)
        else:
            path = str(Path(temp_config_folder) / f'{fname}.yaml')

        if path != '':
            if CONFIG_FNAMES[fname]['saved_as'] == 'object_list':
                try:
                    with open(path, 'r') as file:
                        docs = yaml.safe_load_all(file)
                        settings = []
                        for doc in docs:
                            if fname == 'isotopes':
                                updated_doc = verify_input_dict(doc, cfc.Isotope())
                                settings.append(cfc.Isotope(**updated_doc))
                            elif fname == 'ct_models':
                                updated_doc = verify_input_dict(doc, cfc.CT_model())
                                settings.append(cfc.CT_model(**updated_doc))
                            elif fname == 'materials':
                                updated_doc = verify_input_dict(doc, cfc.Material())
                                settings.append(cfc.Material(**updated_doc))
                            elif fname == 'shield_data':
                                updated_doc = verify_input_dict(doc, cfc.ShieldData())
                                settings.append(cfc.ShieldData(**updated_doc))
                            elif fname == 'colormaps':
                                updated_doc = verify_input_dict(doc, cfc.ColorMap())
                                settings.append(cfc.ColorMap(**updated_doc))
                except OSError as error:
                    print(f'config_func.py load_settings {fname}: {str(error)}')
                    return_default = True

                status = True

            else:  # settings as one object
                try:
                    with open(path, 'r') as file:
                        doc = yaml.safe_load(file)
                        if fname == 'general_values':
                            upd = verify_input_dict(doc, cfc.GeneralValues())
                            settings = cfc.GeneralValues(**upd)
                        elif fname == 'last_modified':
                            upd = verify_input_dict(doc, cfc.LastModified())
                            settings = cfc.LastModified(**upd)
                    status = True
                except OSError as error:
                    print(f'config_func.py load_settings {fname}: {str(error)}')
                    return_default = True
        else:
            return_default = True

        if return_default:
            settings = CONFIG_FNAMES[fname]['default']

    return (status, path, settings)


def check_save_conflict(fname, lastload):
    """Check if config file modified (by others) after last load.

    Parameters
    ----------
    fname : str
        yaml filename to check
    lastload : float
        epoch time of last load of the yaml file before trying to save.

    Returns
    -------
    proceed : bool
        proceed to save
    errmsg : str
        Errormessage if proceed False
    """
    status = True
    errmsg = ''
    path = get_config_filename(fname)
    if os.path.exists(path):
        if os.path.getmtime(path) > lastload:
            _, path, last_mod = load_settings(fname='last_modified')
            res = getattr(last_mod, fname)
            if len(res) == 2:
                user, modtime = res
                version_string = ''
            else:
                user, modtime, version_string = res

            if user != USERNAME:
                if modtime > lastload:
                    errmsg = f'It seems that {user} is also editing this config file.'
                else:
                    errmsg = 'It seems that this file has been edited recently.'

                errmsg = (
                    errmsg +
                    '\nProceed saving and possibly overwrite changes done by others?')
            if errmsg != '':
                status = False

    return status, errmsg


def update_last_modified(fname=''):
    """Update last_modified.yaml."""
    # path = get_config_filename(fname, force=True)
    _, _, last_mod = load_settings(fname='last_modified')
    setattr(last_mod, fname, [USERNAME, time(), VERSION])
    _, _ = save_settings(last_mod, fname='last_modified')


def save_settings(settings, fname='', temp_config_folder=''):
    """Save settings to yaml file.

    Parameters
    ----------
    settings : object
        object of a settings dataclass
    fname : str
        filename without folder and extension
    temp_config_folder : str, Optional
        path to save settings to if other than config folder

    Returns
    -------
    bool
        False if failed saving
    str
        filepath where tried to save
    """
    status = False
    path = ''

    def try_save(input_data):
        status = False
        try_again = False
        try:
            with open(path, 'w') as file:
                if isinstance(input_data, list):
                    yaml.safe_dump_all(
                        input_data, file, default_flow_style=None, sort_keys=False)
                else:
                    yaml.safe_dump(
                        input_data, file, default_flow_style=None, sort_keys=False)
            status = True
        except yaml.YAMLError:
            # try once more with eval(str(input_data))
            try_again = True
        except IOError as io_error:
            QMessageBox.warning(None, "Failed saving",
                                f'Failed saving to {path} {io_error}')
        if try_again:
            try:
                input_data = eval(str(input_data))
                with open(path, 'w') as file:
                    if isinstance(input_data, list):
                        yaml.safe_dump_all(
                            input_data, file, default_flow_style=None, sort_keys=False)
                    else:
                        yaml.safe_dump(
                            input_data, file, default_flow_style=None, sort_keys=False)
                status = True
            except yaml.YAMLError as yaml_error:
                QMessageBox.warning(None, 'Failed saving',
                                    f'Failed saving to {path} {yaml_error}')
        return status

    if fname != '':
        proceed = False
        if temp_config_folder:
            path = Path(temp_config_folder) / f'{fname}.yaml'
        else:
            path = get_config_filename(fname, force=True)
        if os.access(Path(path).parent, os.W_OK):
            proceed = True

        if proceed:
            if CONFIG_FNAMES[fname]['saved_as'] == 'object_list':
                listofdict = [asdict(temp) for temp in settings]
                status = try_save(listofdict)
            else:
                status = try_save(asdict(settings))

        if fname != 'last_modified' and temp_config_folder=='':
            update_last_modified(fname)

    return (status, path)


def import_settings(import_main):
    """Import config settings."""
    any_same_name = False

    lists = [fname for fname, item in CONFIG_FNAMES.items()
             if item['saved_as'] == 'object_list']
    for fname in lists:
        new_temps = getattr(import_main, fname, [])
        if len(new_temps) > 0:
            _, _, temps = load_settings(fname=fname)
            if len(new_temps) > 0:
                old_labels = [temp.label for temp in temps]
                new_labels = [temp.label for temp in new_temps]
                if old_labels == ['']:
                    temps = new_temps
                else:
                    for new_id in range(len(new_temps)):
                        if new_labels[new_id] in old_labels:
                            new_temps[new_id].label = (
                                new_labels[new_id] + '_import')
                            any_same_name = True
                        temps.append(new_temps[new_id])

            _, _ = save_settings(temps, fname=fname)

    return any_same_name


def get_icon_path(dark_mode):
    """Get path for icons depending on darkmode settings."""
    path_icons = ':/icons/'
    if dark_mode:
        path_icons = ':/icons_darkmode/'

    return path_icons
