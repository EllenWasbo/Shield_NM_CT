# Help for programmers

## Starting virt env from scratch
- conda create --name vShield
- conda activate vShield
- cd folder above 'src'
- pip install -e .

For using pytest:
- pip install pytest
- pip install pytest-qt

using virt env later
- conda activate vShield
- cd folder above 'src'
- python -m Shield_NM_CT.Shield_NM_CT # to run the program
- python -m pytest tests\test_....py # example to test

To be able to plot during pytest:
- import matplotlib.pyplot as plt
- plt.plot([x,y])
- plt.pause(.1)

## Update resources.py after changes
- add to resouces.qrc if needed
- with PySide6 installed (in a separate virtual environment):
	- cd C:\...\Shield_NM_CT\src\Shield_NM_CT
	- pyside6-rcc resources.qrc -o resources.py
- open the resources.py file and replace the PySide6 import to PyQt6
 
## Update requirements.txt
- cd to src-folder
- pipreqs 
- requirements will now be in the src-folder. Move it to folder above src.
- remove skimage...?
- remove charset_normalizer (only for pyinstaller)
- Copy also new content to setup.cfg

## Update pdf version of Wiki
- download wikidoc code from https://github.com/jobisoft/wikidoc
	- Replace wikidoc.py in wikidoc-master with the one in helper_scripts folder where the code is updated for python3 and some fixes for linking pages
- install exe files: 
	- pandoc https://pandoc.org/installing.html 
	- wkhtmltopdf https://wkhtmltopdf.org

- conda install -c anaconda git
Clone git from github
- git clone https://github.com/EllenWasbo/Shield_NM_CT/wiki.git &lt;some path&gt;\Shield_NM_CT_wiki
- or update with Pull and GitHub Desktop

- cd to wikidoc-master
- python wikidoc.py C:\Programfiler\wkhtmltopdf\bin\wkhtmltopdf.exe &lt;some path&gt;\\Shield_NM_CT_wiki\

Note that code used by wikidoc are within the .md files of Shield_NM_CT/wiki

## For building .exe
This method reduces the output files considerably compared to doing this in conda environment:
- Install python 3.9.7 and choose to add path
- Create an empty folder (somewhere) called Shield_NM_CT. This folder should hold the input and output for pyinstaller.
- Copy into the empty folder src and all files directly from folder above src except .gitignore/.pylintrc
- Delete these folders in src: icons, config_defaults + all pycache/eggs folders
- Delete also resources.qrc
- In cmd.exe (not from Anaconda):
	- cd ....path...to...\Shield_NM_CT (the new stripped folder)
- pip install -e . 
	- (if error on cwd None, try this: pip install --upgrade pip setuptools wheel --user)
- pip install pyinstaller (or pip list to see if its already installed)
- maybe: pip uninstall pathlib (have had some troubles and this solved it)

pyinstaller -i="logo.ico" -w --clean --paths=src\Shield_NM_CT src\Shield_NM_CT\Shield_NM_CT.py

- Add latest pdf user manual to dist.

- zip content of folder dist to distribute Shield_NM_CT_versionXXX.zip

To run the exe file from cmd.exe:
- cd .....\dist\Shield_NM_CT
- Shield_NM_CT
