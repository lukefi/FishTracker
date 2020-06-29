from file_handler import FOpenSonarFile
import os
import psutil

"""
Experimental result: A FSONAR_File takes around 1.5 Mb of memory.
7000 such objects would require almost 11 Gb of buffer space.
"""
if __name__ == "__main__":
    process = psutil.Process(os.getpid())

    path = "D:/Projects/VTT/FishTracking/Teno1_2019-07-02_153000.aris"
    sonar = FOpenSonarFile(path)
    array = []

    for i in range(sonar.frameCount):
        if i % 100 == 0:
            print(i, process.memory_info()[0])  # in bytes 

        array.append(sonar.getFrame(i))
