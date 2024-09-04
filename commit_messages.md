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