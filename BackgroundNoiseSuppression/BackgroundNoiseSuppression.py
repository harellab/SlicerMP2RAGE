import logging
import os
import numpy as np
from typing import Annotated, Optional

import vtk

import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.parameterNodeWrapper import (
    parameterNodeWrapper,
    WithinRange,
)

from slicer import vtkMRMLScalarVolumeNode


#
# BackgroundNoiseSuppression
#

class BackgroundNoiseSuppression(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "BackgroundNoiseSuppression"  # TODO: make this more human readable by adding spaces
        self.parent.categories = ["Filtering"]  # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["Sam Brenny UMN CMRR)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#BackgroundNoiseSuppression">module documentation</a>.
"""
        # TODO: replace with organization, grant and thanks
        self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

#
# BackgroundNoiseSuppressionParameterNode
#

@parameterNodeWrapper
class BackgroundNoiseSuppressionParameterNode:
    """
    The parameters needed by module.

    UNI_Image - The volume to suppress background noise.
    INV1_Image - The volume of the first inversion.
    INV2_Image - The volume of the second inversion.
    Output_Image - The output volume of the background-filtered UNI volume.
    """
    UNIInputVolume: vtkMRMLScalarVolumeNode
    INV1InputVolume: vtkMRMLScalarVolumeNode
    INV2InputVolume: vtkMRMLScalarVolumeNode
    OutputVolume: vtkMRMLScalarVolumeNode

#
# BackgroundNoiseSuppressionWidget
#

class BackgroundNoiseSuppressionWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath('UI/BackgroundNoiseSuppression.ui'))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = BackgroundNoiseSuppressionLogic()

        # Connections

        # These connections ensure that we update parameter node when scene is closed
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
        self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

        # Buttons
        self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

        # Make sure parameter node is initialized (needed for module reload)
        self.initializeParameterNode()

    def cleanup(self) -> None:
        """
        Called when the application closes and the module widget is destroyed.
        """
        self.removeObservers()

    def enter(self) -> None:
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        self.initializeParameterNode()

    def exit(self) -> None:
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI will be updated when the user enters into the module)
        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self._parameterNodeGuiTag = None
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)

    def onSceneStartClose(self, caller, event) -> None:
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        self.setParameterNode(None)

    def onSceneEndClose(self, caller, event) -> None:
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        if self.parent.isEntered:
            self.initializeParameterNode()

    def initializeParameterNode(self) -> None:
        """
        Ensure parameter node exists and observed.
        """
        # Parameter node stores all user choices in parameter values, node selections, etc.
        # so that when the scene is saved and reloaded, these settings are restored.

        self.setParameterNode(self.logic.getParameterNode())

        # Removed code to Select default input nodes if nothing is selected yet

    def setParameterNode(self, inputParameterNode: Optional[BackgroundNoiseSuppressionParameterNode]) -> None:
        """
        Set and observe parameter node.
        Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
        """

        if self._parameterNode:
            self._parameterNode.disconnectGui(self._parameterNodeGuiTag)
            self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
        self._parameterNode = inputParameterNode
        if self._parameterNode:
            # Note: in the .ui file, a Qt dynamic property called "SlicerParameterName" is set on each
            # ui element that needs connection.
            self._parameterNodeGuiTag = self._parameterNode.connectGui(self.ui)
            self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self._checkCanApply)
            self._checkCanApply()

    def _checkCanApply(self, caller=None, event=None) -> None:
        if all([self._parameterNode,
                self._parameterNode.UNIInputVolume,
                self._parameterNode.INV1InputVolume,
                self._parameterNode.INV2InputVolume,
                self._parameterNode.OutputVolume]): 
            self.ui.applyButton.toolTip = "Apply background suppression"
            self.ui.applyButton.enabled = True
        else:
            self.ui.applyButton.toolTip = "Select input and output volume nodes"
            self.ui.applyButton.enabled = False

    def onApplyButton(self) -> None:
        """
        Run processing when user clicks "Apply" button.
        """
        with slicer.util.tryWithErrorDisplay("Failed to compute results.", waitCursor=True):

            # Compute output
            self.logic.process(self.ui.UNI_Image.currentNode(), self.ui.INV1_Image.currentNode(), self.ui.INV2_Image.currentNode(),
                               self.ui.Output_Image.currentNode(), self.ui.checkBox.checked)

#
# BackgroundNoiseSuppressionLogic
#

class BackgroundNoiseSuppressionLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """
        Called when the logic class is instantiated. Can be used for initializing member variables.
        """
        ScriptedLoadableModuleLogic.__init__(self)

    def getParameterNode(self):
        return BackgroundNoiseSuppressionParameterNode(super().getParameterNode())

    def process(self,
                UNI_Image: vtkMRMLScalarVolumeNode, #UNI image
                INV1_Image: vtkMRMLScalarVolumeNode, #INV1 image
                INV2_Image: vtkMRMLScalarVolumeNode, #INV2 image
                Output_Image: vtkMRMLScalarVolumeNode, #output image
                invert: bool = False,
                showResult: bool = True) -> None:
        """
        Run the processing algorithm.
        Can be used without GUI widget.
        :param inputVolume: volume to be thresholded
        :param outputVolume: thresholding result
        :param imageThreshold: values above/below this threshold will be set to 0
        :param invert: if True then values above the threshold will be set to 0, otherwise values below are set to 0
        :param showResult: show output volume in slice viewers
        """
        # add mp2rage_contras

        logging.info(f'UNI_Image is {UNI_Image.GetName()}')
        logging.info(f'INV1_Image is {INV1_Image.GetName()}')
        logging.info(f'INV2_Image is {INV2_Image.GetName()}')
        for check_val in [UNI_Image, INV1_Image, INV2_Image, Output_Image]:
            if not check_val:
                raise ValueError(f"input or output argument volume is invalid")

        import time
        startTime = time.time()
        logging.info('Processing started')

        # Run background suppression
        from mp2rage_contrasts import make_mp2rage_from_unsigned
        # Calculate ouput voxel data
        out_array = make_mp2rage_from_unsigned(
            slicer.util.arrayFromVolume(INV1_Image),
            slicer.util.arrayFromVolume(INV2_Image),
            slicer.util.arrayFromVolume(UNI_Image),
            beta=10000 #TODO fix hardcoding
        )
        
        # Store result in output volume
        slicer.util.updateVolumeFromArray(Output_Image, out_array.astype(np.int16))
        # Copy orientation affine from UNI image to ouput volume
        ijkToRas = vtk.vtkMatrix4x4()
        UNI_Image.GetIJKToRASMatrix(ijkToRas)
        Output_Image.SetIJKToRASMatrix(ijkToRas)
        #TODO make sure IJK to RAS direction matrix is correct for all orientations

        stopTime = time.time()
        logging.info(f'Processing completed in {stopTime-startTime:.2f} seconds')


#
# BackgroundNoiseSuppressionTest
#

class BackgroundNoiseSuppressionTest(ScriptedLoadableModuleTest):
    """
    This is the test case for your scripted module.
    Uses ScriptedLoadableModuleTest base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough.
        """
        slicer.mrmlScene.Clear()
    
    def runTest(self):
        """Run as few or as many tests as needed here.
        """
        self.setUp()
        
        self.test_BackgroundNoiseSuppression1()
        
   
    def test_BackgroundNoiseSuppression1(self):
        logic = BackgroundNoiseSuppressionLogic()
        
        TestPath = os.path.join(os.path.dirname(__file__), 'Resources/Tests/')

        UNI_Img = slicer.util.loadVolume(os.path.join(TestPath,'UNI_Test.nrrd'))
        INV1_Img = slicer.util.loadVolume(os.path.join(TestPath,'INV1_Test.nrrd'))
        INV2_Img = slicer.util.loadVolume(os.path.join(TestPath,'INV2_Test.nrrd'))
        outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        outputVolume.SetName("Test_Output")
        logic.process(UNI_Img,INV1_Img,INV2_Img,outputVolume)