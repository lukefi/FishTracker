"""
Python Module for functions that is used by the UI
that is available in all windows

"""
import os
from PyQt5.QtWidgets import QFileDialog
from FViewer import FViewer                         # UI/FViewer
# for the about section in the help menu
import webbrowser
#for exporting results
from jinja2 import Environment, FileSystemLoader
import file_handler as FH

def FOpenFile(QT_Dialog):
        ## DEBUG : remove filePathTuple and uncomment filePathTuple
        # homeDirectory = str(Path.home())
        homeDirectory = str(os.path.expanduser("~"))
        # filePathTuple = ('/home/mghobria/Documents/work/data/data.aris',) # laptop
        # filePathTuple = ('data.aris',) # Home PC & windows Laptop
        # filePathTuple = ('/home/mghobria/Documents/work/data/data 1/data.aris',) # work PC
        # filePathTuple = ("C:\\Users\\mghobria\\Downloads\\data.aris",) # Home PC windows
        filePathTuple = QFileDialog.getOpenFileName(QT_Dialog,
                                                    "Open File",
                                                    homeDirectory,
                                                    "Sonar Files (*.aris *.ddf)")
        if filePathTuple[0] != "" : 
            # if the user has actually chosen a specific file.
            QT_Dialog.FFilePath = filePathTuple[0]
            QT_Dialog.FCentralScreen = FViewer(QT_Dialog)
            QT_Dialog.setCentralWidget(QT_Dialog.FCentralScreen)
            QT_Dialog.setWindowTitle("Fisher - " + QT_Dialog.FFilePath)

def loadTemplate(QT_Dialog, default=False):
    """Loads an analysis template from disk from the following path 
    "/fish-tracking/file_handlers/analysis_presets".
    It calls 'loadJSON()' function from 'file_handler'
    module, which returns a dictionary that has the following keys:
    {
        "morphStruct": {string} -- indicates type of kernel,
        "morphStructDim": {list} -- [{int} -- width, {int} -- height],
        "startFrame": {int} -- frame to start analysis from,
        "blurVal": {list} -- [{int} -- width, {int} -- height],
        "bgTh": {int} -- background threshold,
        "maxApp": {int} -- appearance frames,
        "maxDis": {int} -- disappearance frames,
        "radius": {int} -- search radius,
        "showImages" : {bool} -- whether to show process or not
    }
    
    Arguments:
        QT_Dialog {PyQt5.Widget.QDialog()} -- Pop-up QtDialog to start
                        the analysis.
    
    Keyword Arguments:
        default {bool} -- determines whether to load the default template
                or another predefined template. (default: {False})
    """             
    config = None

    if default:
        # load the default template
        defaultTemplatePath = FH.pathFromList(QT_Dialog._MAIN_CONTAINER._CONFIG["analyzerTemplate"])
        config = FH.loadJSON(defaultTemplatePath)

    else:
        # load a preset from disk
        homeDirectory = str(
            os.path.expanduser(
                FH.pathFromList(
                    QT_Dialog._MAIN_CONTAINER._CONFIG["templatesFolder"]
                )
            )
        )
        filePathTuple = QFileDialog.getOpenFileName(QT_Dialog,
                                                    "Load Template",
                                                    homeDirectory,
                                                    "JSON (*.json)")
        if filePathTuple[0] != "" :
            # if the user has actually chosen a specific file.
            config = FH.loadJSON(filePathTuple[0])
    
    if config:
        # if the file was read successfully
        QT_Dialog.morphStruct.setCurrentText(config['morphStruct'])
        QT_Dialog.morphStructDimInp.setText(
            "({w},{h})".format(
                w=config['morphStructDim'][0],
                h=config['morphStructDim'][1]
            )
        )
        QT_Dialog.startFrameInp.setText(config['startFrame'])
        QT_Dialog.blurValInp.setText(
            "({w},{h})".format(
                w=config['blurVal'][0],
                h=config['blurVal'][1]
            )
        )
        QT_Dialog.bgThInp.setText(config['bgTh'])
        QT_Dialog.maxAppInp.setText(config['maxApp'])
        QT_Dialog.maxDisInp.setText(config['maxDis'])
        QT_Dialog.radiusInput.setText(config['radius'])
        QT_Dialog.showImages.setChecked(config['showImages'])
        QT_Dialog.update()
    return

def exportAsJPGActionFunction(self):
    name = QFileDialog.getSaveFileName(self, 'Save all frames')[0]
    if not os.path.exists(name):
        os.makedirs(name)
    file = FOpenSonarFile(self.FFilePath)
    numberOfImagesToSave = file.frameCount
    numOfDigits = str(len(str(numberOfImagesToSave)))
    fileName = os.path.splitext(os.path.basename(file.FILE_PATH))[0]
    
    for i in range(numberOfImagesToSave):
    
        frame = file.getFrame(i)
        imgNmbr = format(i, "0"+numOfDigits+"d")
        cv2.imwrite((os.path.join( name,  fileName+ "_"+imgNmbr+".jpg")), frame)
        print("Saving : ", str(i))

    return

def export_BGS_AsJPGActionFunction(self):
    ## TODO _ : change the non-generic export path
    ## allow the user to enter their specific paths.
    file = FOpenSonarFile(self.FFilePath)
    numberOfImagesToSave = file.frameCount
    imagesExportDirectory = "/home/mghobria/Pictures/SONAR_Images"
    BGS_Threshold = 25
    fgbg = cv2.createBackgroundSubtractorMOG2(varThreshold = BGS_Threshold)
    for i in range(numberOfImagesToSave):
        frame = file.getFrame(i)
        frame = fgbg.apply(frame)
        cv2.imwrite((os.path.join( imagesExportDirectory, "IMG_BGS_"+str(i)+".jpg")), frame)
        print("Saving : ", str(i))

    return

def lukeInfo():
    """Opens a new tab in the default webbrowser to show LUKE homepage.
    """
    url = "https://www.luke.fi/en/"
    return webbrowser.open_new_tab(url)

def uniOuluInfo():
    """Opens a new tab in the default webbrowser to show University
    of Oulu homepage.
    """
    url = "https://www.oulu.fi/university/"
    return webbrowser.open_new_tab(url)

def fisherInfo():
    """Opens a new tab in the default webbrowser to show project's
    homepage.
    """
    url = "https://minamaged113.github.io/fish-tracking/#"
    return webbrowser.open_new_tab(url)

def exportResult(type, detectedFish):    
    """Function used to export results of the program to well-known
    file formats {CSV, JSON, TXT}, according to the choice of the user.
    
    Keyword Arguments:
        type {string} -- The specified output format chosen by the user.
                         it has 3 values {CSV, JSON, TXT}.
                         CSV: Comma-Separated Value,
                         JSON: JavaScript Object Notation,
                         TXT: text.
        detectedFish {list} -- Ouput of the analysis process.
    """
    templatesPath = os.path.join( os.getcwd(), "file_handlers","output_templates")
    file_loader = FileSystemLoader(templatesPath)
    env = Environment(loader = file_loader)
    items = []
    textTemp = env.get_template("textTemplate.txt")
    for i in range(10):
        an_item = dict(frame=i, dir=i, R=i, theta=i, L=i, dR=i, aspect=i, time=i, date=i, speed=i, comments="")
        items.append(an_item)

    output = textTemp.render(fishes=items)
    
    return

def loadFrameList():
    """Function that loads frames before and after the current
    Frame into the memory for faster processing.
    Every time the user presses `Next` or `Previous` it modifies
    the list to maintain the number of loaded frames.

        range: {integer} -- defines number of frames loaded into
                the memory.

    """
    ## TODO _
    framesIndices = list()
    range = 10
    if range > (self.File.FRAME_COUNT+1):
        range = self.File.FRAME_COUNT
    for i in range(range):
        framesIndices.append()
        
    pass

def getAvgLength():
    return "N/A"

def print_stat_msg(text):
    ## TODO _ : delete this function
    print(text)