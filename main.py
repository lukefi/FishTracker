from ui_manager import launch_ui
import multiprocessing

if __name__ == "__main__":
    # Freezing is required by PyInstaller
    multiprocessing.freeze_support()
    launch_ui()