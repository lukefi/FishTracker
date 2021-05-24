# LUKE
LUKE Fish Tracking

## Run with Python
The easiest way to run the code is by using Anaconda and a provided yml file to create an environment. At the project root, run:
```
conda env create --file environment.yml --name fish_tracking
```
Activate environment:
```
conda activate fish_tracking
```
And run the program:
```
python main.py
```
The program has been tested in Windows (Python 3.7.6 and 3.8.5) and Ubuntu 20.04 (Python 3.8.8).

## Bundle and create installer (Windows)
PyInstaller can be used to bundle the source code into a single package with all the required dependecies. The following command does this based on the configuration file "fish_tracker.spec". At the project root, run:
```
pyinstaller fish_tracker.spec
```
or
```
pyinstaller fish_tracker.spec --noconfirm
```
so the removal of the previous bundle does not have to be confirmed.

The resulting bundle can be found in the "dist" folder. It includes an executable, "fish_tracker.exe", which can be used to run the program.
For easier distribution, an installer can be created using NSIS or similar.