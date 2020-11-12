# LUKE
LUKE Fish Tracking

## Build and create installer
The source code can be built with all the required dependecies using PyInstaller. The following command does exactly this based on the configuration file "fish_tracker.spec". Navigate to the path and run:
```
pyinstaller fish_tracker.spec
```
The build can be found in the "dist" folder.

An installer can be created using NSIS or similar, although it is not necessary.