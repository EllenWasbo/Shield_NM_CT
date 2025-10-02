# v2.1.0
_02 Oct, 2025_

Upgrade to python version 3.11-3.13 and packages (upgrade from PyQt5 to PyQt6, numpy 2.0+ and more).

Bugfixes:
- Fixed error/crash when editing color settings, leaving only one color and trying to save the change.

Changes that affect usage of Shield_NM_CT:
- Dark mode now follow the system settings for this. Dark mode setting of user preferences removed.
- Import of projects from IDL version of Shield_NM_CT removed as IDL-users assumed to already have converted.


# v2.0.10
_08 Jul, 2025_

New functionalities:
- More (and fixed) options for color settings. Now possible to set named matplotlib-colormaps, and also setting colormap for occupancy factors.
- CT model with options smooth and flatten used to be ignored for floor above and below. Now included.

Bugfixes:
- IMPORTANT! Occupancy-factor for CT doses have until now not had any effect on the dose. This is now corrected. 
	- Apologies, if this have had effect on decisions.
	- Validation for CT, similar to NM is now added to the Wiki and to the automatic tests (pytest).
- IMPORTANT 2! Rotation of CT ignored for floor above/below. Now fixed.
- Zoom and pan now better handled.
- Fixed quite a few issues in settings (adding/editing isotopes, materials, shield_data, color settings)
- Fixed issues with user interface and calculations after visiting settings:
	- List of isotopes were updated in case of changes in settings, but without visually selecting the correct inital value for the current project.
	- Issues with missing isotopes, kV sources, CT models and materials if renaming in Settings.
	- Please validate changes in settings with simple calculations f.x. with the simple project available in tests using the sources or materials you have added or edited.
- Avoiding default shielding for the floors being set to 200mm Lead. Now correctly set default 200mm Concrete.

# v2.0.9
_21 May, 2025_

Bugfixes:
- Accepting more when manually editing positions (accurate use of space after comma no longer important)
- Avoiding crash when no config folder created yet.
- Fixed ZeroDivision error when adding new isotopes.

# v2.0.8
_10 Feb, 2025_

- More user friendly on drawing and adding elements:
	- For areas and walls: Rightclick hovered element to display drag handles (avoid confusion between editing and adding new element)
	- When adding new element - the coordinates of the currently drawn temporary object is added.
- Accepting missing space when editing coordinates
- Fixed error on oblique walls - under some circumstances the affected sector was claerly miscalculated.

# v2.0.7
_06 Feb, 2025_
- bugfixes to prevent crashes related to matplotlib set_xdata no longer accept single positions, now packed into list

# v2.0.6
_05 Feb, 2025_
- bugfixes to prevent crashes related to alpha_overlay and add_measured_length

# v2.0.5
_04 Sep, 2024_
- fixes to user interface (image annotations on hover)
- bugfixes to prevent crashes

# v2.0.4
_03 Sep, 2024_
- fixed remaining error with walls at left of source (if fully above or below source)
- removed option to delete rows by delete key (causing trouble if actually deleting text)
- small fixes to user interface on hover after settings window have been open
- small bug-fixes

# v2.0.3
_23 Aug, 2024_
- fixed error with walls at left of source

# v2.0.2
_07 May, 2024_
- upgraded dependency of matplotlib from >=3.5.2 to >=3.7.1 due to issue with incorrect behavior of colorbar
- fixed error when starting config using older package PyQt5 versions

# v2.0.1
_05 Feb, 2024_
- updated dependencies
- changed way of setting the cmaps as the register int matplotlib did not work on all systems
- changed default gamma ray constants for Lu-177. See Wiki.

# v2.0.0_b4
_01 Feb 2024_
Small fixes:
- probably different versions of PyQt5 require int values where others accept also float. Fixed to int values.

# v2.0.0_b3
_22 Dec 2023_
Small fixes:
- avoiding confusing behaviour selecting several areas at once
- adding option to deselect area or wall by clicking once more
- text and layout fixes

# v2.0.0_b2
_21 Dec 2023_
First functional version ready for validation.

# v2.0.0_b1_1..6
_Nov - Dec, 2023_
Initiation Python version - Not functional, just backing up files