# Fish Tracking
LUKE Fish Tracking

## Run with Python
The easiest way to run the source code is by using Anaconda and a provided yml file to create an environment. At the project root, run:
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

## Quickstart guide
1. Open &ast;.aris file by choosing "File"&#8594;"Open...". Previously saved results (&ast;.fish files) can be opened by choosing "File"&#8594;"Load..."
2. The application computes a background model for background subtraction and an echogram. The progress of the application is printed on the "Log" tab.
3. A vertical line seen in the echogram indicates the currently selected frame, which can be freely selected. The view can be zoomed with the scroll wheel and panned with the left mouse button.
4. The quality of the background subtraction can be inspected by choosing the "Background subtraction" icon (topmost icon on the left-hand side of the sonar view).
5. If fish seem to disappear from the view, it is recommended to lower the value of the "MOG var threshold" parameter. To confirm the changes, press "Apply Values".
6. ”Calculate all” computes all detections for the entire data. "Log" tab can be used to follow the progress.
7. "Detections" tab lists all detections in the currently selected frame.
8. Detections are combined into counted fish at the "Tracker" tab by choosing "Primary Track". "Log" tab can be used to follow the progress.
9. "Tracks" tab lists all the tracked fish from the entire file. The fish list can be edited if needed (change lengths, remove fish, combine paths, etc.)
10. Final results can be saved to a file by choosing "File"&#8594;"Save as...".
11. Detections and tracks can be exported to separate &ast;.csv files by choosing "File"&#8594;"Export detections..." and "File"&#8594;"Export tracks...".

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
For easier distribution, an installer can be created using a program called NSIS or similar.