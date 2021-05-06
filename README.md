# LUKE
LUKE Fish Tracking

## Run with Python
The easiest way to run the code is by installing Anaconda. Dependencies include opencv and filterpy. Tested with Python 3.7.6 and 3.8.5.
In the path, run:
```
python main.py
```

## Build and create installer (Windows)
The source code can be built with all the required dependecies using PyInstaller. The following command does exactly this based on the configuration file "fish_tracker.spec". Navigate to the path and run:
```
pyinstaller fish_tracker.spec
```
The build can be found in the "dist" folder. It includes an executable, "fish_tracker.exe", which can be used to run the program.
For easier distribution, an installer can be created using NSIS or similar.