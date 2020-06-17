
import sys                          # for parsing command line args
import os                           # for handling paths
import unittest                     # for unit testing modules
import io                           # for file handles testing


sys.path.append(os.getcwd())

import v5_file_info as v5         # module under test


class v5_DIDSON_FILE_TEST(unittest.TestCase):
    test_param = {
        "filePath": {
            "name": "sample.aris",
            "good": os.path.join("file_handlers", "v5", "sample.aris"),
            "bad": "nosample.aris",
            "absGood": os.path.abspath(
                os.path.join(
                    "file_handlers",
                    "v5",
                    "sample.aris"
                )
            )
        },
        "corruptedFilePath": os.path.join("file_handlers", "v5", "corruptedSample.aris"),
        "version": 88491076,
        "frameCount": 6,
        "frameRate": 0,
        "highResolution": 0,
        "numRawBeams": 48,
        "sampleRate": 0.0,
        "samplesPerChannel": 2000,
        "receiverGain": 0,
        "windowStart": 0.0,
        "windowLength": 0.0,
        "reverse": 0,
        "serialNumber": 1098,
        "strDate": b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        "strHeaderID": b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00',
        "userID1": 0,
        "userID2": 0,
        "userID3": 0,
        "userID4": 0,
        "startFrame": 0,
        "endFrame": 0,
        "timelapse": 0,
        "recordInterval": 0,
        "radioSecond": 0,
        "frameInterval": 0,
        "flags": 1174406144,
        "auxFlags": 0,
        "soundVelocity": 0,
        "flags3D": 0,
        "softwareVersion": 5891,
        "waterTemp": 0,
        "salinity": 0,
        "pulseLength": 0,
        "TxMode": 0,
        "versionFPGA": 0,
        "versionPSuC": 0,
        "thumbnailFI": 0,
        "fileSize": 583168,
        "optionalHeaderSize": 0,
        "optionalTailSize": 0,
        "versionMinor": 0,
        "largeLens": 360181532

    }

    def testFileOpened(self):
        """
        testFileOpened 

        Test that file is opened correctly and all information checked.

        """
        f = v5.v5_File(self.test_param["filePath"]["good"])
        self.assertIsInstance(f, v5.v5_File)
        return

    def testFileNotOpened(self):
        """
        testFileNotOpened

        providing wrong path and checking for FileNotFoundError exception

        """
        with self.assertRaises(FileNotFoundError) as cm:
            v5.v5_File(self.test_param["filePath"]["bad"])
        return

    def testCorruptedFile(self):
        with self.assertRaises(TypeError) as cm:
            v5.v5_File(self.test_param["corruptedFilePath"])
        return

    def testFrameCount(self):
        f = v5.v5_File(self.test_param["filePath"]["good"])
        self.assertEqual(
            self.test_param["frameCount"],
            len(f)
        )
        return

    def testFilePath(self):
        f = v5.v5_File(self.test_param["filePath"]["good"])
        self.assertEqual(
            self.test_param["filePath"]["absGood"],
            repr(f)
        )
        return

    def testFileName(self):
        f = v5.v5_File(self.test_param["filePath"]["good"])
        self.assertEqual(
            self.test_param["filePath"]["name"],
            f.getFileName()
        )
        return

    def testReadFrame(self):
        return

    def testGetFileHeader(self):
        return

    def testGetInfo(self):
        return


def main():
    try:
        unittest.main()
    finally:
        return


if __name__ == "__main__":
    main()
