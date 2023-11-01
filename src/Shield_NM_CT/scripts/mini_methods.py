#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of small functions used in ImageQC.

@author: Ellen Wasbo
"""
import os
from fnmatch import fnmatch
from pathlib import Path
from PyQt5.QtWidgets import QMessageBox

# Shield_NM_CT block start
from Shield_NM_CT.ui import messageboxes
# Shield_NM_CT block end


def string_to_float(string_value):
    """Convert string to float, accept comma as decimal-separator.

    Parameters
    ----------
    string_value : str

    Returns
    -------
    output : float or None
    """
    output = None
    if isinstance(string_value, str):
        string_value = string_value.replace(',', '.')
        try:
            output = float(string_value)
        except ValueError:
            pass
    return output


def get_uniq_ordered(input_list):
    """Get uniq elements of a group in same order as first appearance."""
    output_list = []
    for elem in input_list:
        if elem not in output_list:
            output_list.append(elem)
    return output_list


def get_all_matches(input_list, value, wildcards=False):
    """Get all matches of value in input_list.

    Parameters
    ----------
    input_list : list of object
    value : object
        Same type as input_list elements
    wildcards : bool, optional
        If true, use fnmatch to include wildcards */?. The default is False.

    Returns
    -------
    index_list : list of int
        list of indexes in input_list where value is found

    """
    index_list = []
    if wildcards and isinstance(value, str):
        index_list = [idx for idx, val in enumerate(input_list) if fnmatch(val, value)]
    else:
        index_list = [idx for idx, val in enumerate(input_list) if val == value]

    return index_list


def find_value_in_sublists(input_list, value):
    """Get all matches of value in nested input_list.

    Parameters
    ----------
    input_list : list of object
    value : str or number
        Same type as input_list elements

    Returns
    -------
    sublist_ids : list of int
        list of indexes of sublist in input_list where value is found

    """
    sublist_ids = []
    for i, sub in enumerate(input_list):
        if value in sub:
            sublist_ids.append(i)

    return sublist_ids


def create_empty_file(filepath, parent_widget, proceed_info_txt='', proceed=False):
    """Ask to create empty file if not existing path."""
    if not os.path.exists(filepath):
        if proceed is False:
            proceed = messageboxes.proceed_question(
                parent_widget, f'{proceed_info_txt} Proceed creating an empty file?')
        if proceed:
            try:
                with open(filepath, "w") as file:
                    file.write('')
            except (OSError, IOError) as error:
                QMessageBox.warning(
                    parent_widget, 'Error',
                    f'Failed creating the file {error}.')


def create_empty_folder(folderpath, parent_widget, proceed_info_txt=''):
    """Ask to create empty folder if not existing path."""
    if not os.path.exists(folderpath):
        proceed = messageboxes.proceed_question(
            parent_widget, f'{proceed_info_txt} Proceed creating an empty folder?')
        if proceed:
            try:
                Path(folderpath).mkdir(parents=True)
            except (NotADirectoryError, FileNotFoundError, OSError) as error:
                QMessageBox.warning(
                    parent_widget, 'Error',
                    f'Failed creating the folder {error}.')
