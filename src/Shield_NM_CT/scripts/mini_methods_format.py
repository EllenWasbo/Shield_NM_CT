#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Collection of small functions used in Shield_NM_CT.

@author: Ellen Wasbo
"""
import os
from time import time
from pathlib import Path
import re


def time_diff_string(seconds):
    """Return time difference as string from input epoch time.

    Parameters
    ----------
    seconds : int
        epoch time

    Returns
    -------
    time_string : str
        xx seconds/minutes/hours/days ago
    """
    time_string = "?"
    diff = time() - seconds
    if diff < 60:
        time_string = str(round(diff)) + ' seconds'
    elif diff < 3600:
        time_string = str(round(diff/60)) + ' minutes'
    elif diff < 3600 * 24:
        time_string = str(round(diff/60/60)) + ' hours'
    else:
        time_string = str(round(diff/60/60/24)) + ' days'

    return ' '.join([time_string, 'ago'])


def get_format_strings(format_string):
    """Extract parts of format_string from list_format of TagPatternFormat.

    Parameters
    ----------
    format_string : str
        '' or prefix|format_string|suffix

    Returns
    -------
    prefix : str
        text before value
    format_part : st
        :.. to place behind {val:...} in an f-string
    suffix : str
        text after value
    """
    prefix = ''
    format_part = ''
    suffix = ''
    if format_string != '':
        try:
            prefix, format_part, suffix = format_string.split('|')
            if len(format_part) > 0:
                if format_part[0] == ':':
                    format_part = format_part[1:]
        except ValueError:
            pass

    return (prefix, format_part, suffix)


def format_val(val, format_string):
    """Format a value or list of values using a format string."""
    val_text = val
    if format_string != '':
        if '|' in format_string:
            prefix, format_string, suffix = get_format_strings(format_string)
        try:
            if not isinstance(val, str):
                if len(val) > 1:
                    val = list(val)  # in case pydicom.multival.MultiValue
                else:
                    val = val[0]
        except TypeError:
            pass

        if isinstance(val, list):
            last_format = format_string[-1]
            if not isinstance(val[0], float) and last_format == 'f':
                try:
                    val = [float(str(x)) for x in val]
                    val_text = [
                        f'{x:{format_string}}' for x in val]
                except ValueError:
                    val_text = [f'{x}' for x in val]
                except TypeError:
                    val_text = [f'{x}' for x in val]
            else:
                val_text = [f'{x:{format_string}}' for x in val]
        else:
            if isinstance(val, str) and format_string[-1] == 'f':
                try:
                    val = float(val)
                    val_text = f'{val:{format_string}}'
                except ValueError:
                    pass
            elif isinstance(val, str) and format_string[0] == '0':
                n_first = int(format_string)
                val_text = f'{val[:n_first]}'
            else:
                try:
                    val_text = f'{val:{format_string}}'
                except TypeError:
                    val_text = '-'
                    pass

    return val_text


def valid_path(input_string, folder=False):
    """Replace non-valid characters for filenames.

    Parameters
    ----------
    input_string : str
        string to become path (filename)
    folder : bool, optional
        avoid . in name if folder = True, default is False

    Returns
    -------
    valid_string : str

    """
    valid_string = re.sub(r'[^\.\w]', '_', input_string)
    if folder:
        valid_string = re.sub(r'[\.]', '_', valid_string)

    return valid_string


def generate_uniq_filepath(input_filepath, max_attempts=1000):
    """Generate new filepath_XXX.ext if already exists.

    Parameters
    ----------
    input_filepath : str
        path to check whether uniq
    max_attempts : int, optional
        _999 is max. The default is 1000.

    Returns
    -------
    uniq_path : str
        unique path based on input, empty string if failed
    """
    uniq_path = input_filepath
    p = Path(input_filepath)
    if os.path.exists(input_filepath):
        for i in range(max_attempts):
            new_p = p.parent / f'{p.stem}_{i:03}.{p.suffix}'
            if new_p.exists() is False:
                uniq_path = new_p.resolve()
                break
        if uniq_path == input_filepath:
            uniq_path = ''  # = failed
    return uniq_path


def valid_template_name(text):
    """No slash or space in template names (confuse automation)."""
    return re.sub(r'[\s/]+', '_', text)
