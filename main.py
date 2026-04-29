import ast
import asyncio
import configparser
import copy
import glob
import io
import logging
import os
import random
import re
import string
import sys
import threading
import time
import traceback
from random import choices

from PIL import Image

from EASLogger import EASloggerSingleton
from workflow.ReceiveReward import receiveReward
from workflow.StartApp import StartApp, runStartApp
from workflow.MainMaterial import mainMaterial

import yaml
from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import Qt, QIcon

import ADBClass
import numpy as np
from PySide6.QtCore import QRunnable, Slot, QThreadPool, Signal, QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel, QPushButton, \
    QPlainTextEdit, QTextEdit, QHBoxLayout, QLineEdit, QCheckBox, QSizePolicy
import OCRClass
import OctoUtil
from Flows.TestFlow import StartAppFlow, TestFlowOcto, DailyMaterialFlow
from adb_profile import Adb_profile
from workflow.WeekTower import weeklyTower

sys.argv += ['-platform', 'windows:darkmode=2']

# Paddleocr supports Chinese, English, French, German, Korean and Japanese.
# You can set the parameter `lang` as `ch`, `en`, `french`, `german`, `korean`, `japan`
# to switch the language model in order.
# ocr = PaddleOCR(use_angle_cls=True, lang='ch') # need to run only once to download and load model into memory
class Signals(QtCore.QObject):
    finished = QtCore.Signal()
class scheduleMission:
    @classmethod
    def ConfigInit(cls, fullId, auto, freeAuto, characterList, autoDeploy=False, defaultDifficulty=False, highRewardFirst=False):
        allMissionList = []
        missionId = None
        difficulty = None
        midMission = None
        if characterList == ['']:
            characterList = []
        with open('app_config.yaml', 'r', encoding='utf-8') as keyconfigfile:
            keyconfig_data = yaml.safe_load(keyconfigfile)
            allMissionList = keyconfig_data[4]["missionInfo"]
        for mission in allMissionList:
             if mission["id"] in fullId:
                missionId = mission["id"]
                missionName = mission["name"]
                allMiddleMission = mission["middleLevel"]
                allDifficulty = mission["difficultyCount"]
                missionArrIndex = allMissionList.index(mission)

                difficulty = fullId.replace(mission["id"], "")
                if OctoUtil.OctoUtil.check_string(difficulty) is True:
                    full_suffix = difficulty.split("_")
                    midMission = full_suffix[0]
                    # midMission = OctoUtil.OctoUtil.map_char_num(midMission)
                    difficulty = int(full_suffix[1])
                else:
                    difficulty = int(difficulty.lstrip("_"))
                    midMission = None

                if difficulty not in allDifficulty:
                    difficulty = allDifficulty[-1]
                difficultyInfoArrIndex = allDifficulty.index(difficulty)
                allDifficultyCharCount = mission["difficultyAutoCharCount"]
                if len(allDifficultyCharCount) == 1:
                    maxCharCount = allDifficultyCharCount[0]
                else:
                    maxCharCount = allDifficultyCharCount[difficultyInfoArrIndex]
                _id = random.randint(0, 100000)

        return cls(missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMiddleMission, missionArrIndex)

    @classmethod
    def UIInit(cls, missionParam, missionBtn: QPushButton = None, missionRow: QWidget = None):
        allMissionList = []
        allDifficultyCharCount = []
        allDifficulty = []
        allMidMission = []
        missionArrIndex = None
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                allMissionList = config_data[4]["missionInfo"]
        if missionParam is not None:
            print("missionParam: ", type(missionParam))
            if isinstance(missionParam, str):
                # Handle integer parameter
                missionName = missionParam
                for mission in allMissionList:
                    if mission["name"] == missionParam:
                        missionId = mission["id"]
                        missionArrIndex = allMissionList.index(mission)
                        allDifficultyCharCount = mission["difficultyAutoCharCount"]
                        allDifficulty = mission["difficultyCount"]
                        allMidMission = mission["middleLevel"]
            elif isinstance(missionParam, int):
                # Handle string parameter
                missionId = allMissionList[missionParam]['id']
                missionArrIndex = missionParam
                missionName = allMissionList[missionParam]['name']
                allDifficultyCharCount = allMissionList[missionParam]["difficultyAutoCharCount"]
                allDifficulty = allMissionList[missionParam]["difficultyCount"]
                allMidMission = allMissionList[missionParam]["middleLevel"]
            else:
                # Handle other parameter types
                print("Unsupported parameter type")
        else:
            missionName = "None"
            missionId = -1
        missionBtn = missionBtn
        missionRow = missionRow
        difficulty = 1
        midMission = ""
        maxCharCount = 1
        if missionName != "None":
            maxCharCount = allDifficultyCharCount[allDifficulty.index(difficulty)]
        characterList = []
        auto = True
        freeAuto = False
        autoDeploy = False
        defaultDifficulty = False
        highRewardFirst = False
        _id = random.randint(0, 100000)
        return cls(missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMidMission, missionArrIndex, missionBtn,missionRow)

    def __init__(self, missionId, missionName, midMission, difficulty, auto, freeAuto, autoDeploy, defaultDifficulty, highRewardFirst, _id, characterList, maxCharCount, allMissionList, allDifficultyCharCount, allDifficulty, allMidMission, missionArrIndex, missionBtn: QPushButton = None, missionRow: QWidget = None):
        self.missionId = missionId
        self.missionName = missionName
        self.midMission = midMission
        self.difficulty = int(difficulty)
        self.auto = auto
        self.freeAuto = freeAuto
        self.autoDeploy = autoDeploy
        self.defaultDifficulty = defaultDifficulty
        self.highRewardFirst = highRewardFirst
        self.id = _id
        self.characterList = characterList
        self.maxCharCount = maxCharCount
        self.missionArrIndex = missionArrIndex
        self.missionBtn = missionBtn
        self.missionRow = missionRow
        self.allMissionList = allMissionList
        self.allDifficultyCharCount = allDifficultyCharCount
        self.allDifficulty = allDifficulty
        self.allMidMission = allMidMission



    def setDifficulty(self, difficulty):
        self.difficulty = int(difficulty)
        difficultyIndex = self.allDifficulty.index(self.difficulty)
        if len(self.allDifficultyCharCount) == 1:
            self.maxCharCount = self.allDifficultyCharCount[0]
        else:
            self.maxCharCount = self.allDifficultyCharCount[difficultyIndex]
        if self.maxCharCount >= 0 and len(self.characterList) > self.maxCharCount:
            self.characterList = self.characterList[:self.maxCharCount]

    def setMidMission(self, midMission):
        self.midMission = midMission

    def setMission(self, missionParam):
        if missionParam is not None:
            print("missionParam: ", type(missionParam))
            if isinstance(missionParam, str):
                # Handle integer parameter
                self.missionName = missionParam
                for mission in self.allMissionList:
                    if mission["name"] == missionParam:
                        self.missionId = mission["id"]
                        self.missionArrIndex = self.allMissionList.index(mission)
                        self.allDifficultyCharCount = mission["difficultyAutoCharCount"]
                        self.allDifficulty = mission["difficultyCount"]
                        self.allMidMission = mission["middleLevel"]
            elif isinstance(missionParam, int):
                # Handle string parameter
                self.missionId = self.allMissionList[missionParam]['id']
                self.missionArrIndex = missionParam
                self.missionName = self.allMissionList[missionParam]['name']
                self.allDifficultyCharCount = self.allMissionList[missionParam]["difficultyAutoCharCount"]
                self.allDifficulty = self.allMissionList[missionParam]["difficultyCount"]
                self.allMidMission = self.allMissionList[missionParam]["middleLevel"]

            else:
                print("Unsupported parameter type")
                # Handle other parameter types
                return "Unsupported parameter type"
            if self.difficulty in self.allDifficulty:
                difficultyIndex = self.allDifficulty.index(self.difficulty)
                self.difficulty = self.allDifficulty[difficultyIndex]
                if len(self.allDifficultyCharCount) == 1:
                    self.maxCharCount = self.allDifficultyCharCount[0]
                else:
                    self.maxCharCount = self.allDifficultyCharCount[difficultyIndex]
            else:
                self.difficulty = self.allDifficulty[0]
                if len(self.allDifficultyCharCount) == 1:
                    self.maxCharCount = self.allDifficultyCharCount[0]
                else:
                    self.maxCharCount = self.allDifficultyCharCount[self.allDifficulty.index(self.difficulty)]

            if self.midMission in self.allMidMission:
                midMissionIndex = self.allMidMission.index(self.midMission)
                self.midMission = self.allMidMission[midMissionIndex]
            else:
                if len(self.allMidMission) > 0:
                    self.midMission = self.allMidMission[0]
                else:
                    self.midMission = ""


class FlowRunnable(QRunnable):
    def __init__(self, flow):
        super().__init__(self)
        self.signal = Signals()
        self.flow = flow

    def run(self):
        self.flow.run()

        self.signal.finished.emit()

class FlowThread(QThread):
    finished = Signals()

    def __init__(self, flow):
        super().__init__()
        self.flow = flow

    def run(self):
        try:
            for fw in self.flow:
                if self.isInterruptionRequested() or ADBClass.AdbSingleton.getInstance().stop_requested:
                    EASloggerSingleton.getInstance().info('./logs/log_test.txt', "流程已停止")
                    break
                result = fw.run()
                if result is False:
                    EASloggerSingleton.getInstance().info('./logs/log_test.txt', "流程因前置步骤失败已停止")
                    break
        except RuntimeError as exc:
            if str(exc) == "流程已停止":
                EASloggerSingleton.getInstance().info('./logs/log_test.txt', "流程已停止")
            else:
                traceback.print_exc()
                EASloggerSingleton.getInstance().info('./logs/log_test.txt', f"流程异常停止：{exc}")
        except Exception as exc:
            traceback.print_exc()
            EASloggerSingleton.getInstance().info('./logs/log_test.txt', f"流程异常停止：{exc}")
        self.finished.emit()

class Monitor:
    def __init__(self, filename, last_read_ptr=0):
        self.filename = filename
        self.last_read_ptr = last_read_ptr

    def check(self):
        with open("./logs/log_test.txt") as f:
            f.seek(0, 2)
            f.seek(max(self.last_read_ptr, 0), 0)  # Move file pointer to the end of the file

            content_lines = f.read().split("\n")
            new_content = ""
            for line in content_lines:
                if line != "":
                    new_content += ast.literal_eval(line).decode()
                    if line != content_lines[-2]:
                        new_content += '\n'

            self.last_read_ptr = f.tell()  # Save the current position of the file pointer
            return (new_content, self.last_read_ptr)

        # with open("./logs/log_test.txt", "rb") as f:
        #     new_content = ast.literal_eval(f.read()).decode()
        #     f.seek(0, 2)
        #     f.seek(max(self.last_read_ptr, 0), 0)  # Move file pointer to the end of the file
        #     self.last_read_ptr = f.tell()  # Save the current position of the file pointer
        #     return (new_content, self.last_read_ptr)

class OctoUI(QtWidgets.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAA - 铃兰")
        self.selectedFiles = []
        self.setMinimumSize(1200, 800)
        self.runProg = True
        self.lastReadPtr = 0
        self.editingMission = scheduleMission.UIInit(None)




        # Create tabs
        self.recList = [[],[]]
        self.scheduleMissionList = []
        self.missionNameList = []
        self.missionInfoList = []
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                self.missionInfoList = config_data[4]["missionInfo"]
                for mission in config_data[4]["missionInfo"]:
                    self.missionNameList.append(mission['name'])
                print("missionNameList: ", config_data[2]['missionList'])

                print("missionList: ", config_data[3]['characterList'])
                self.characterNameList = config_data[3]['characterList']

        self.OctoBotThread = None;



        self.tabs = QtWidgets.QTabWidget()
        # self.recThread = threading.Thread(target=StripchatRecorder.startRecording, args=(self.recList,))
        # Create Tab 1
        self.tab1 = QtWidgets.QWidget()
        self.tab1Layout = QtWidgets.QHBoxLayout(self.tab1)
        # self.Config = configparser.ConfigParser()
        # Create Left Panel
        self.leftPanel = QtWidgets.QVBoxLayout()
        self.mainDir = sys.path[0]
        # self.Config.read(self.mainDir + '/config.conf')
        self.wanted_model = []

        # Create the layout and add the first QLineEdit widget
        self.lineEditsLayout = QtWidgets.QVBoxLayout()
        self.lineEdits = [QtWidgets.QLineEdit() for _ in range(len(self.wanted_model)+1)]
        self.mission = []
        # print(len(self.wanted_model))

        self.lineEditsWidget = QtWidgets.QWidget()
        self.lineEditsVbox = QtWidgets.QVBoxLayout()
        self.lineEditsWidget.setLayout(self.lineEditsVbox)
        self.lineEditsScrollArea = QtWidgets.QScrollArea()
        self.lineEditsScrollArea.setWidget(self.lineEditsWidget)
        self.lineEditsScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.lineEditsScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.lineEditsScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.lineEditsScrollArea.setWidgetResizable(True)
        self.lineEditsScrollArea.setStyleSheet("QWidget {border: 1px solid gray; border-radius: 5px;}")


        # Create the button to add new QLineEdit widgets
        self.addButton = QtWidgets.QPushButton("Add Model")
        # self.addButton.setAlignment(Qt.AlignmentFlag.AlignBottom)
        # Create a widget to hold the line edits layout
        # Create a scroll area to hold the line edits widget

        # Add the scroll area to the left panel

        for i in (range(len(self.lineEdits))):
            if i < len(self.wanted_model):
                # print(i)
                self.lineEdits[i].setText(self.wanted_model[i])
            self.lineEditsVbox.addWidget(self.lineEdits[i])


        # Add the button to the left panel
        # self.leftPanel.addWidget(self.addButton, alignment=QtCore.Qt.AlignBottom)
        # Create TextInput Box
        self.inputStream = QtWidgets.QLineEdit()
        self.inputStream.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        # Create Start Button
        self.startButton = QtWidgets.QPushButton("Start")

        # Create Stop Button
        self.stopButton = QtWidgets.QPushButton("Stop")

        self.applyModelsButton = QtWidgets.QPushButton("Apply Changes")
        # self.stopButton.clicked.connect(self.stopRecording)

        # Add TextInput Box and Start Button to Left Panel
        # self.leftPanel.addWidget(self.inputStream, 2)
        self.startAppOptionWidget = QtWidgets.QWidget()
        self.startAppOptionLayout = QtWidgets.QHBoxLayout(self.startAppOptionWidget)
        self.startAppOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.startAppCheckbox = QCheckBox('开始唤醒', self)
        self.startAppCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.startAppSetting = QtWidgets.QPushButton("设置")

        self.startAppOptionLayout.addWidget(self.startAppCheckbox)
        self.startAppOptionLayout.addStretch()
        self.startAppOptionLayout.addWidget(self.startAppSetting)


        self.farmResOptionWidget = QtWidgets.QWidget()
        self.farmResOptionLayout = QtWidgets.QHBoxLayout(self.farmResOptionWidget)
        self.farmResOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.farmResCheckbox = QCheckBox('自动刷图', self)
        self.farmResCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.farmResSetting = QtWidgets.QPushButton("设置")

        self.farmResOptionLayout.addWidget(self.farmResCheckbox)
        self.farmResOptionLayout.addStretch()
        self.farmResOptionLayout.addWidget(self.farmResSetting)

        self.receiveRewardOptionWidget = QtWidgets.QWidget()
        self.receiveRewardOptionLayout = QtWidgets.QHBoxLayout(self.receiveRewardOptionWidget)
        self.receiveRewardOptionLayout.setAlignment(QtCore.Qt.AlignTop)

        self.receiveRewardCheckbox = QCheckBox('领取奖励', self)
        self.receiveRewardCheckbox.stateChanged.connect(self.saveTaskSelection)
        self.receiveRewardSetting = QtWidgets.QPushButton("设置")

        self.receiveRewardOptionLayout.addWidget(self.receiveRewardCheckbox)
        self.receiveRewardOptionLayout.addStretch()
        self.receiveRewardOptionLayout.addWidget(self.receiveRewardSetting)

        self.taskBox = QtWidgets.QGroupBox()
        self.taskBox.setStyleSheet("QGroupBox {border: 1px solid gray; border-radius: 5px; padding: 20px; margin:50px; margin-right: 0px; margin-left: 20px;}")

        self.StartBtn = QtWidgets.QPushButton("启动")
        self.StartBtn.connect(self.StartBtn, QtCore.SIGNAL("clicked()"), lambda: self.startMainFlow([self.startAppCheckbox.isChecked(), self.farmResCheckbox.isChecked(), self.receiveRewardCheckbox.isChecked()]))

        self.StopBtn = QtWidgets.QPushButton("停止")
        self.StopBtn.connect(self.StopBtn, QtCore.SIGNAL("clicked()"), lambda: self.stopMainFlow())
        # self.startButton.connect()

        # self.addFileBtn = QtWidgets.QPushButton("Select Files")
        # Add Label to Bordered Textbox
        self.taskLabelLayout = QtWidgets.QVBoxLayout(self.taskBox)
        self.taskLabelLayout.addWidget(self.startAppOptionWidget)
        self.taskLabelLayout.addWidget(self.farmResOptionWidget)
        self.taskLabelLayout.addWidget(self.receiveRewardOptionWidget)
        self.taskLabelLayout.addStretch()
        self.taskLabelLayout.addWidget(self.StartBtn)
        self.taskLabelLayout.addWidget(self.StopBtn)


        self.leftPanel.addWidget(self.taskBox, 1)
        # self.leftPanel.addWidget(self.startButton, 1)

        # Create Right Panel
        self.middlePanel = QtWidgets.QVBoxLayout()

        self.settingBox = QtWidgets.QGroupBox()
        self.settingBox.setStyleSheet("QGroupBox {border: 1px solid gray; border-radius: 5px; padding: 0px; margin:10px; margin-top:50px; margin-bottom: 50px;}")

        self.middlePanel.addWidget(self.settingBox, 1)


        # Create Right Panel
        self.rightPanel = QtWidgets.QVBoxLayout()

        # Create Bordered Textbox
        self.streamerBox = QtWidgets.QGroupBox("Recording Streamer")
        self.streamerBox.setStyleSheet("QGroupBox {border: 1px solid gray; border-radius: 5px; padding-top: 10px}")

        # Create Label
        self.streamerLabel = QtWidgets.QLabel("No streamer selected")
        self.streamerLabel.setAlignment(QtCore.Qt.AlignTop)

        # Create Label


        self.recordingBox = QtWidgets.QWidget()
        self.recordingBox.setStyleSheet("QWidget {border: 1px solid gray; border-radius: 5px; padding-top: 10px}")
        self.recordingBoxLayout = QtWidgets.QVBoxLayout()
        self.recordingBox.setLayout(self.recordingBoxLayout)

        # self.recordingHistory = QtWidgets.QLabel("Recording History")
        # self.recordingHistory.setAlignment(QtCore.Qt.AlignTop)

        self.streamerDisplayWidget = QtWidgets.QWidget()
        self.streamerDisplayVbox = QtWidgets.QVBoxLayout()
        self.streamerDisplayWidget.setLayout(self.streamerDisplayVbox)
        self.recordingScrollArea = QtWidgets.QScrollArea(self.recordingBox)
        self.recordingScrollArea.setWidget(self.streamerDisplayWidget)
        self.recordingScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.recordingScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # self.recordingScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.recordingScrollArea.setWidgetResizable(True)
        self.recordingScrollArea.setStyleSheet("QWidget {border: 1px solid gray; border-radius: 5px;}")

        self.logText = QtWidgets.QTextEdit()
        self.logText.setReadOnly(True)
        self.logText.setText("")
        self.streamerDisplayVbox.addWidget(self.logText)
        # Add Bordered Textbox to Right Panel
        self.rightPanel.addWidget(self.recordingScrollArea, 1)

        # Add Left and Right Panel to Tab 1
        self.tab1Layout.addLayout(self.leftPanel, 1)
        self.tab1Layout.addLayout(self.middlePanel, 1)
        self.tab1Layout.addLayout(self.rightPanel, 1)

        self.fixVideoTabWidget = QtWidgets.QWidget()
        self.fixVideoTabLayout = QtWidgets.QHBoxLayout()
        self.fixVideoTabWidget.setLayout(self.fixVideoTabLayout)

        self.addFileBtn = QtWidgets.QPushButton("Select Files")
        # self.btn.clicked.connect(self.getfile)

        self.flineEditsWidget = QtWidgets.QWidget()
        self.flineEditsVbox = QtWidgets.QVBoxLayout()
        self.flineEditsVbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.flineEditsWidget.setLayout(self.flineEditsVbox)
        self.flineEditsScrollArea = QtWidgets.QScrollArea()
        self.flineEditsScrollArea.setWidget(self.flineEditsWidget)
        self.flineEditsScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.flineEditsScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.flineEditsScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.flineEditsScrollArea.setWidgetResizable(True)
        self.flineEditsScrollArea.setStyleSheet("QWidget {border: 1px solid gray; border-radius: 5px;}")

        self.saveSettingBtn = QtWidgets.QPushButton("保存文件")
        self.saveSettingBtn.clicked.connect(
            lambda: self.save_preset(self.missionPresetDropdown.currentText())
        )

        self.loadSettingBtn = QtWidgets.QPushButton("加载文件")
        self.loadSettingBtn.clicked.connect(
            lambda: self.onLoadMissionPreset(self.missionPresetDropdown.currentText())
        )

        # self.fAddButton.clicked.connect(self.add_empty_mission)

        self.fAddButton = QtWidgets.QPushButton("新增任务")
        self.fAddButton.clicked.connect(self.add_empty_mission)

        self.missionRemoveButton = QtWidgets.QPushButton("删除任务")
        self.missionRemoveButton.connect(self.missionRemoveButton, QtCore.SIGNAL("clicked()"), self.remove_missions)
        # --------------------------------------------------------------------------------------------------------------
        self.newPresetButton = QtWidgets.QPushButton("另存為")

        self.newPresetTextEdit = QtWidgets.QLineEdit()

        self.newPresetButton.clicked.connect(
            lambda: self.save_as_new_preset(self.newPresetTextEdit.text())
        )
        # --------------------------------------------------------------------------------------------------------------
        self.missionPresetDropdownWidget = QtWidgets.QWidget()
        self.missionPresetDropdownLayout = QtWidgets.QHBoxLayout()
        self.missionPresetDropdownWidget.setLayout(self.missionPresetDropdownLayout)

        self.missionPresetDropdownLabel = QtWidgets.QLabel("任務列表")
        self.missionPresetDropdown = QtWidgets.QComboBox()
        self.missionPresetDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        directory_path = "./configs/*.yaml"
        conf_files = glob.glob(directory_path)

        for file_path in conf_files:
            print(file_path)
            self.missionPresetDropdown.addItem(file_path)
            self.missionPresetDropdown.setCurrentIndex(0)
                # dropdown.setCurrentIndex(0)
        # self.missionPresetDropdown.currentIndexChanged.connect(
        #     lambda: self.onMissionPresetChanged(self.missionPresetDropdown.currentText()))
        self.missionPresetDropdownLayout.addWidget(self.missionPresetDropdownLabel)
        self.missionPresetDropdownLayout.addStretch()
        self.missionPresetDropdownLayout.addWidget(self.missionPresetDropdown)
        # --------------------------------------------------------------------------------------------------------------

        self.missionSaveButton = QtWidgets.QPushButton("启用当前流程")
        self.missionSaveButton.connect(self.missionSaveButton, QtCore.SIGNAL("clicked()"), self.save_missions)

        self.missionSettingSLWidget = QtWidgets.QWidget()
        self.missionSettingSLLayout = QtWidgets.QHBoxLayout()
        self.missionSettingSLWidget.setLayout(self.missionSettingSLLayout)
        self.missionSettingSLLayout.addWidget(self.loadSettingBtn)
        self.missionSettingSLLayout.addWidget(self.saveSettingBtn)

        # --------------------------------------------------------------------------------------------------------------
        self.missionSettingSaveAsWidget = QtWidgets.QWidget()
        self.missionSettingSaveAsLayout = QtWidgets.QHBoxLayout()
        self.missionSettingSaveAsWidget.setLayout(self.missionSettingSaveAsLayout)
        self.missionSettingSaveAsLayout.addWidget(self.newPresetButton)
        self.missionSettingSaveAsLayout.addWidget(self.newPresetTextEdit)
        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDifficultyWidget.setLayout(self.missionSettingDifficultyLayout)

        self.missionSettingDifficultyLabel = QtWidgets.QLabel("难度")
        self.missionSettingDifficultyDropdown = QtWidgets.QComboBox()
        self.missionSettingDifficultyDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for difficulty in mission.difficulty:
                    self.missionSettingDifficultyDropdown.addItem(difficulty)
                self.missionSettingDifficultyDropdown.setCurrentIndex(0)
                break
                # dropdown.setCurrentIndex(0)
        self.missionSettingDifficultyDropdown.currentIndexChanged.connect(
            lambda : self.onMissionDifficultyChanged(self.missionSettingDifficultyDropdown.currentText()))
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyLabel)
        self.missionSettingDifficultyLayout.addStretch()
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyDropdown)
        #--------------------------------------------------------------------------------------------------------------

        self.missionSettingButtonWidget = QtWidgets.QWidget()
        self.missionSettingButtonLayout = QtWidgets.QHBoxLayout()
        self.missionSettingButtonWidget.setLayout(self.missionSettingButtonLayout)
        self.missionSettingButtonLayout.addWidget(self.fAddButton)
        self.missionSettingButtonLayout.addWidget(self.missionRemoveButton)
        # self.label_1.setStyleSheet("background-color: rgb(255,0,0); margin:5px; border:1px solid rgb(0, 255, 0); ")
        self.missionSettingApplyWidget = QtWidgets.QWidget()
        self.missionSettingApplyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingApplyWidget.setLayout(self.missionSettingApplyLayout)
        self.missionSettingApplyLayout.addWidget(self.missionSaveButton)

        self.PPLeftPanelWidget = QtWidgets.QWidget()
        self.PPLeftPanelLayout = QtWidgets.QVBoxLayout()
        self.PPLeftPanelLayout.addWidget(self.flineEditsScrollArea)
        self.PPLeftPanelLayout.addWidget(self.missionSettingSLWidget)
        self.PPLeftPanelLayout.addWidget(self.missionSettingSaveAsWidget)

        self.PPLeftPanelLayout.addWidget(self.missionPresetDropdownWidget)
        self.PPLeftPanelLayout.addWidget(self.missionSettingButtonWidget)
        self.PPLeftPanelLayout.addWidget(self.missionSettingApplyWidget)
        # self.PPLeftPanelWidget.setStyleSheet("background-color: yellow")
        self.PPLeftPanelWidget.setLayout(self.PPLeftPanelLayout)

        self.heroListText = QtWidgets.QLabel("Hero List")

        self.heroListWidget = QtWidgets.QWidget()
        self.heroListGrid = QtWidgets.QGridLayout()
        self.heroListGrid.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.heroListWidget.setLayout(self.heroListGrid)
        self.heroListScrollArea = QtWidgets.QScrollArea()
        self.heroListScrollArea.setWidget(self.heroListWidget)
        self.heroListScrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.heroListScrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.heroListScrollArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.heroListScrollArea.setWidgetResizable(True)
        self.heroListScrollArea.setStyleSheet("QWidget {border: 1px solid gray; border-radius: 5px;}")

        self.charSelectionList = []
        self.selectedCharacterName = None
        # initializ a array with 9 empty buttons
        # for i in range(len(self.characterNameList)):
        #     charBtn = QtWidgets.QPushButton(self.characterNameList[i])
        #     self.heroListGrid.addWidget(charBtn, int(i/3), i%3)
        #     self.charSelectionList.append(charBtn)
        #     charBtn.connect(charBtn, QtCore.SIGNAL("clicked()"), lambda: self.selectMissionEdit(i))
        self.heroListGridTitle = QtWidgets.QLabel("Character Selection: ")
        for characterName in self.characterNameList:
            self.add_character_button(characterName)
        self.updateCharacterGridStatus()
        self.heroSettingAddButton = QtWidgets.QPushButton("新增角色")
        self.heroSettingAddButton.clicked.connect(self.add_empty_character)

        self.heroSettingClearButton = QtWidgets.QPushButton("清除选择")
        self.heroSettingClearButton.clicked.connect(self.clear_current_character_selection)

        #--------------------------------------------------------------------------------------------------------------
        self.heroSettingButtonWidget = QtWidgets.QWidget()
        self.heroSettingButtonLayout = QtWidgets.QHBoxLayout()
        self.heroSettingButtonWidget.setLayout(self.heroSettingButtonLayout)
        self.heroSettingButtonLayout.addWidget(self.heroSettingAddButton)
        self.heroSettingButtonLayout.addWidget(self.heroSettingClearButton)

        self.missionSettingLabel = QtWidgets.QLabel("关卡设置")

        self.missionSettingWidget = QtWidgets.QWidget()
        self.missionSettingWidget.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.missionSettingWidget.setObjectName("missionSetting")
        self.missionSettingWidget.setStyleSheet("QWidget#missionSetting{border: 1px solid gray; border-radius: 5px;}")
        self.missionSettingLayout = QtWidgets.QVBoxLayout()
        self.missionSettingWidget.setLayout(self.missionSettingLayout)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingAutoOrManuelWidget = QtWidgets.QWidget()
        self.missionSettingAutoOrManuelLayout = QtWidgets.QHBoxLayout()
        self.missionSettingAutoOrManuelWidget.setLayout(self.missionSettingAutoOrManuelLayout)

        self.missionSettingAutoOrManuelLabelWidget = QtWidgets.QLabel("代行模式")
        self.missionSettingAutoOrManuelSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingAutoOrManuelSwitchWidget.clicked.connect(self.updateAutoOrManuelStatus)

        self.missionSettingAutoOrManuelLayout.addWidget(self.missionSettingAutoOrManuelLabelWidget)
        self.missionSettingAutoOrManuelLayout.addStretch()
        self.missionSettingAutoOrManuelLayout.addWidget(self.missionSettingAutoOrManuelSwitchWidget)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingFreeAutoWidget = QtWidgets.QWidget()
        self.missionSettingFreeAutoLayout = QtWidgets.QHBoxLayout()
        self.missionSettingFreeAutoWidget.setLayout(self.missionSettingFreeAutoLayout)

        self.missionSettingFreeAutoLabelWidget = QtWidgets.QLabel("使用免費代行")
        self.missionSettingFreeAutoSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingFreeAutoSwitchWidget.clicked.connect(self.updateFreeAutoStatus)

        self.missionSettingFreeAutoLayout.addWidget(self.missionSettingFreeAutoLabelWidget)
        self.missionSettingFreeAutoLayout.addStretch()
        self.missionSettingFreeAutoLayout.addWidget(self.missionSettingFreeAutoSwitchWidget)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingAutoDeployWidget = QtWidgets.QWidget()
        self.missionSettingAutoDeployLayout = QtWidgets.QHBoxLayout()
        self.missionSettingAutoDeployWidget.setLayout(self.missionSettingAutoDeployLayout)

        self.missionSettingAutoDeployLabelWidget = QtWidgets.QLabel("自动上阵")
        self.missionSettingAutoDeploySwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingAutoDeploySwitchWidget.clicked.connect(self.updateAutoDeployStatus)

        self.missionSettingAutoDeployLayout.addWidget(self.missionSettingAutoDeployLabelWidget)
        self.missionSettingAutoDeployLayout.addStretch()
        self.missionSettingAutoDeployLayout.addWidget(self.missionSettingAutoDeploySwitchWidget)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingDefaultDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDefaultDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDefaultDifficultyWidget.setLayout(self.missionSettingDefaultDifficultyLayout)

        self.missionSettingDefaultDifficultyLabelWidget = QtWidgets.QLabel("默认难度")
        self.missionSettingDefaultDifficultySwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingDefaultDifficultySwitchWidget.clicked.connect(self.updateDefaultDifficultyStatus)

        self.missionSettingDefaultDifficultyLayout.addWidget(self.missionSettingDefaultDifficultyLabelWidget)
        self.missionSettingDefaultDifficultyLayout.addStretch()
        self.missionSettingDefaultDifficultyLayout.addWidget(self.missionSettingDefaultDifficultySwitchWidget)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingHighRewardWidget = QtWidgets.QWidget()
        self.missionSettingHighRewardLayout = QtWidgets.QHBoxLayout()
        self.missionSettingHighRewardWidget.setLayout(self.missionSettingHighRewardLayout)

        self.missionSettingHighRewardLabelWidget = QtWidgets.QLabel("高额优先")
        self.missionSettingHighRewardSwitchWidget = QtWidgets.QCheckBox()
        self.missionSettingHighRewardSwitchWidget.clicked.connect(self.updateHighRewardFirstStatus)

        self.missionSettingHighRewardLayout.addWidget(self.missionSettingHighRewardLabelWidget)
        self.missionSettingHighRewardLayout.addStretch()
        self.missionSettingHighRewardLayout.addWidget(self.missionSettingHighRewardSwitchWidget)

        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingDifficultyWidget = QtWidgets.QWidget()
        self.missionSettingDifficultyLayout = QtWidgets.QHBoxLayout()
        self.missionSettingDifficultyWidget.setLayout(self.missionSettingDifficultyLayout)

        self.missionSettingDifficultyLabel = QtWidgets.QLabel("难度")
        self.missionSettingDifficultyDropdown = QtWidgets.QComboBox()
        self.missionSettingDifficultyDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for difficulty in mission.difficulty:
                    self.missionSettingDifficultyDropdown.addItem(difficulty)
                self.missionSettingDifficultyDropdown.setCurrentIndex(0)
                break
                # dropdown.setCurrentIndex(0)
        self.missionSettingDifficultyDropdown.currentIndexChanged.connect(
            lambda : self.onMissionDifficultyChanged(self.missionSettingDifficultyDropdown.currentText()))
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyLabel)
        self.missionSettingDifficultyLayout.addStretch()
        self.missionSettingDifficultyLayout.addWidget(self.missionSettingDifficultyDropdown)
        #--------------------------------------------------------------------------------------------------------------
        self.missionSettingMidMissionWidget = QtWidgets.QWidget()
        self.missionSettingMidMissionLayout = QtWidgets.QHBoxLayout()
        self.missionSettingMidMissionWidget.setLayout(self.missionSettingMidMissionLayout)

        self.missionSettingMidMissionLabel = QtWidgets.QLabel("分页")
        self.missionSettingMidMissionDropdown = QtWidgets.QComboBox()
        self.missionSettingMidMissionDropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for mission in self.missionInfoList:
            if mission["id"] == self.editingMission.missionId:
                for midMission in mission.midMission:
                    self.missionSettingMidMissionDropdown.addItem(midMission)
                self.missionSettingMidMissionDropdown.setCurrentIndex(0)
                break
                # dropdown.setCurrentIndex(0)
        self.missionSettingMidMissionDropdown.currentIndexChanged.connect(
            lambda: self.onMissionMidMissionChanged(self.missionSettingMidMissionDropdown.currentText()))
        self.missionSettingMidMissionLayout.addWidget(self.missionSettingMidMissionLabel)
        self.missionSettingMidMissionLayout.addStretch()
        self.missionSettingMidMissionLayout.addWidget(self.missionSettingMidMissionDropdown)
        # --------------------------------------------------------------------------------------------------------------

        self.missionSettingFreeAutoSwitchWidget.setEnabled(False)
        self.missionSettingAutoOrManuelSwitchWidget.setEnabled(False)
        self.missionSettingAutoDeploySwitchWidget.setEnabled(False)
        self.missionSettingDefaultDifficultySwitchWidget.setEnabled(False)
        self.missionSettingHighRewardSwitchWidget.setEnabled(False)

        self.missionSettingLayout.addWidget(self.missionSettingAutoOrManuelWidget)
        self.missionSettingLayout.addWidget(self.missionSettingFreeAutoWidget)
        self.missionSettingLayout.addWidget(self.missionSettingAutoDeployWidget)
        self.missionSettingLayout.addWidget(self.missionSettingDefaultDifficultyWidget)
        self.missionSettingLayout.addWidget(self.missionSettingHighRewardWidget)
        self.missionSettingLayout.addWidget(self.missionSettingDifficultyWidget)
        self.missionSettingLayout.addWidget(self.missionSettingMidMissionWidget)
        self.missionSettingLayout.addStretch()

        self.PPMiddlePanelWidget = QtWidgets.QWidget()
        self.PPMiddlePanelLayout = QtWidgets.QVBoxLayout()
        self.PPMiddlePanelLayout.addWidget(self.heroListText)
        self.PPMiddlePanelLayout.addWidget(self.heroListGridTitle)
        self.PPMiddlePanelLayout.addWidget(self.heroListScrollArea)
        self.PPMiddlePanelLayout.addWidget(self.heroSettingButtonWidget)
        # self.PPRightPanelWidget.setStyleSheet("background-color: red")
        self.PPMiddlePanelWidget.setLayout(self.PPMiddlePanelLayout)

        self.PPRightPanelWidget = QtWidgets.QWidget()
        self.PPRightPanelLayout = QtWidgets.QVBoxLayout()
        self.PPRightPanelWidget.setLayout(self.PPRightPanelLayout)
        self.PPRightPanelLayout.addWidget(self.missionSettingLabel)
        self.PPRightPanelLayout.addWidget(self.missionSettingWidget)

        self.fixVideoTabLayout.addWidget(self.PPLeftPanelWidget, 1)
        self.fixVideoTabLayout.addWidget(self.PPMiddlePanelWidget, 1)
        self.fixVideoTabLayout.addWidget(self.PPRightPanelWidget, 1)



        self.tabSetting = QtWidgets.QWidget()
        self.tabSettingLayout = QtWidgets.QVBoxLayout()
        self.tabFormLayout = QtWidgets.QFormLayout()
        self.tabSetting.setLayout(self.tabSettingLayout)

        self.adbDirTextEdit = QtWidgets.QLineEdit()
        self.connectionPortTextEdit = QtWidgets.QLineEdit()
        self.controlModeDropdown = QtWidgets.QComboBox()
        self.controlModeDropdown.addItems(["window", "adb"])
        self.windowTitleTextEdit = QtWidgets.QLineEdit()
        self.processNameTextEdit = QtWidgets.QLineEdit()
        self.baseResolutionTextEdit = QtWidgets.QLineEdit()
        self.ocrLanguageDropdown = QtWidgets.QComboBox()
        self.ocrLanguageDropdown.addItems(["ch_sim,en", "ch_tra,en"])

        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                config_data = yaml.safe_load(file)
                config_lookup = {}
                for item in config_data:
                    if isinstance(item, dict):
                        config_lookup.update(item)
                print(config_lookup.get('adbDir', ''))
                print(config_lookup.get('connectionPort', ''))
                self.adbDirTextEdit.setText(config_lookup.get('adbDir', ''))
                self.connectionPortTextEdit.setText(config_lookup.get('connectionPort', ''))
                self.controlModeDropdown.setCurrentText(config_lookup.get('controlMode', 'window'))
                self.windowTitleTextEdit.setText(config_lookup.get('windowTitle', '铃兰'))
                self.processNameTextEdit.setText(config_lookup.get('processName', 'SoC.exe'))
                base_resolution = config_lookup.get('baseResolution', [1280, 720])
                self.baseResolutionTextEdit.setText(f"{base_resolution[0]}x{base_resolution[1]}")
                ocr_languages = config_lookup.get('ocrLanguages', ['ch_sim', 'en'])
                self.ocrLanguageDropdown.setCurrentText(",".join(ocr_languages))
                task_selection = config_lookup.get('taskSelection', {})
                self.startAppCheckbox.setChecked(task_selection.get('startApp', False))
                self.farmResCheckbox.setChecked(task_selection.get('farmResources', False))
                self.receiveRewardCheckbox.setChecked(task_selection.get('receiveReward', False))


        self.tabFormLayout.addRow("控制模式", self.controlModeDropdown)
        self.tabFormLayout.addRow("窗口标题", self.windowTitleTextEdit)
        self.tabFormLayout.addRow("进程名", self.processNameTextEdit)
        self.tabFormLayout.addRow("基准分辨率", self.baseResolutionTextEdit)
        self.tabFormLayout.addRow("OCR语言", self.ocrLanguageDropdown)
        self.tabFormLayout.addRow("ADB路径", self.adbDirTextEdit)
        self.tabFormLayout.addRow("连接地址", self.connectionPortTextEdit)

        self.applySetting = QtWidgets.QPushButton("Apply")
        self.applySetting.clicked.connect(self.applySettingAction)
        self.settingActionRow = QtWidgets.QHBoxLayout();
        self.settingActionRow.addWidget(self.applySetting)
        self.tabSettingLayout.addLayout(self.tabFormLayout)
        self.tabSettingLayout.addLayout(self.settingActionRow)
        # Add Tab 1 to the tabs
        self.tabs.addTab(self.tab1, "一鍵刷資源")
        self.tabs.addTab(self.fixVideoTabWidget, "刷图流程")
        self.tabs.addTab(self.tabSetting, "设置")


        # Add tabs to the main window
        self.setCentralWidget(self.tabs)

        # Set window properties
        self.setWindowTitle("MAA Assistance SS - 铃兰")
        self.setGeometry(100, 100, 800, 600)

        self.initMissions()
        # Update the text every second
        self.timer = QtCore.QTimer()
        self.timer.start(1000)

        self.timer_log = QTimer()
        self.timer_log.timeout.connect(self.monitor_log)
        self.timer_log.start(1000)  # 1000 milliseconds = 1 second

    def monitor_log(self):
        file_path = 'logs\\log_test.txt'
        monitor = Monitor(file_path, self.lastReadPtr)
        newText = monitor.check()
        self.lastReadPtr = newText[1]
        if len(newText[0]) > 0:
            self.logText.append(newText[0])
            print("".join(newText[0]))

    def initMissionCheckRepeated(self, config_data, missionId, past_mission):
        for mission in list(config_data[0]['LevelAutomation'].keys()):
            if (missionId in mission) and (mission not in past_mission):
                missionId = mission
                break
            if mission == list(config_data[0]['LevelAutomation'].keys())[-1]:
                print(
                    "ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR")
                # ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR--ERROR
                return (False, missionId)
        return (True, missionId)
    def initMissions(self):
        self.loadMissionsPreset('.\\active_config.yaml')
        self.updateCharacterGridStatus()
        # with open('active_config.yaml', 'r', encoding='utf-8') as configfile:
        #     config_data = yaml.safe_load(configfile)
        #     print(config_data)
        #     past_mission = []
        #
        #     for missionId in config_data[1]['Material_Mission']['mission'].split(','):
        #         original_mission = missionId
        #         if missionId not in list(config_data[0]['LevelAutomation'].keys()):
        #             if not self.initMissionCheckRepeated(config_data, missionId, past_mission)[0]:
        #                 continue
        #             else:
        #                 missionId = self.initMissionCheckRepeated(config_data, missionId, past_mission)[1]
        #         past_mission.append(missionId)
        #         characters = config_data[0]['LevelAutomation'][missionId]["characters"]
        #         isAuto = config_data[0]['LevelAutomation'][missionId]["isAuto"]
        #         isFreeAuto = config_data[0]['LevelAutomation'][missionId]["isFreeAuto"]
        #         mission = scheduleMission.ConfigInit(original_mission, isAuto, isFreeAuto, characters.split(','))
        #         #-----------------------------------------------------------------------------------------------------
        #         newMissionRowWidget = QtWidgets.QWidget()
        #         newMissionRowLayout = QtWidgets.QHBoxLayout()
        #         newMissionRowWidget.setLayout(newMissionRowLayout)
        #
        #         dropdown = QtWidgets.QComboBox()
        #         dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        #
        #         for missionName in self.missionNameList:
        #             dropdown.addItem(missionName)
        #         dropdown.setCurrentIndex(mission.missionArrIndex)
        #
        #         setting_button = QPushButton()
        #         setting_button.setProperty("list-button", True)
        #         setting_button.setIcon(QIcon("setting_icon.png"))
        #         setting_button.setStyleSheet("QPushButton {background-color: #0E2369;}")
        #         print("added mission:", dropdown.currentIndex())
        #         mission.missionBtn = setting_button
        #         mission.missionRow = newMissionRowWidget
        #
        #         self.scheduleMissionList.append(mission)
        #         dropdown.currentIndexChanged.connect(
        #             lambda _targetMissionId=dropdown.currentText(), _mission=mission: self.onMissionIdChanged(
        #                 _targetMissionId, _mission))
        #         setting_button.connect(setting_button, QtCore.SIGNAL("clicked()"),
        #                                lambda _missionId=mission.id: self.selectMissionEdit(_missionId))
        #
        #         # setting_button.setStyleSheet("QPushButton {border: 0px solid gray;}")
        #
        #         newMissionRowLayout.addWidget(dropdown)
        #         newMissionRowLayout.addWidget(setting_button)
        #         self.mission.append(newMissionRowWidget)
        #         self.flineEditsVbox.addWidget(newMissionRowWidget)
        #         self.updateCharacterGridStatus()
        #         #-----------------------------------------------------------------------------------------------------

    def loadMissionsPreset(self, presetFileName):
        with open(presetFileName, 'r', encoding='utf-8') as configfile:
            config_data = yaml.safe_load(configfile)
            print(config_data)
            self.scheduleMissionList.clear()
            self.mission.clear()
            while self.flineEditsVbox.count():
                child = self.flineEditsVbox.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
            # self.flineEditsVbox.removeWidget(self.missionSettingWidget)
            for shortFormMissionId, missionId, missionConfig in self.resolvePresetMissionEntries(config_data):
                characters = missionConfig.get("characters", "")
                isAuto = missionConfig.get("isAuto", True)
                isFreeAuto = missionConfig.get("isFreeAuto", False)
                autoDeploy = missionConfig.get("autoDeploy", False)
                defaultDifficulty = missionConfig.get("defaultDifficulty", False)
                highRewardFirst = missionConfig.get("highRewardFirst", False)
                mission = scheduleMission.ConfigInit(shortFormMissionId, isAuto, isFreeAuto, characters.split(','), autoDeploy, defaultDifficulty, highRewardFirst)
                # -----------------------------------------------------------------------------------------------------
                newMissionRowWidget = QtWidgets.QWidget()
                newMissionRowLayout = QtWidgets.QHBoxLayout()
                newMissionRowWidget.setLayout(newMissionRowLayout)

                dropdown = QtWidgets.QComboBox()
                dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

                for missionName in self.missionNameList:
                    dropdown.addItem(missionName)
                dropdown.setCurrentIndex(mission.missionArrIndex)

                setting_button = QPushButton()
                setting_button.setProperty("list-button", True)
                setting_button.setIcon(QIcon("setting_icon.png"))
                setting_button.setStyleSheet("QPushButton {background-color: #0E2369;}")
                print("added mission:", dropdown.currentIndex())
                mission.missionBtn = setting_button
                mission.missionRow = newMissionRowWidget

                self.scheduleMissionList.append(mission)
                dropdown.currentIndexChanged.connect(
                    lambda _targetMissionId=dropdown.currentText(), _mission=mission: self.onMissionIdChanged(
                        _targetMissionId, _mission))
                setting_button.connect(setting_button, QtCore.SIGNAL("clicked()"),
                                       lambda _missionId=mission.id: self.selectMissionEdit(_missionId))

                # setting_button.setStyleSheet("QPushButton {border: 0px solid gray;}")

                newMissionRowLayout.addWidget(dropdown)
                newMissionRowLayout.addWidget(setting_button)
                self.mission.append(newMissionRowWidget)
                self.flineEditsVbox.addWidget(newMissionRowWidget)
                self.updateCharacterGridStatus()
                # -----------------------------------------------------------------------------------------------------

        if self.scheduleMissionList:
            self.selectMissionEdit(self.scheduleMissionList[0].id)
        else:
            self.editingMission = scheduleMission.UIInit(None)
            self.updateCharacterGridStatus()

        print(self.scheduleMissionList)

    def stripDuplicateMissionSuffix(self, missionId):
        match = re.match(r'^(.*_\d{2})_\d+$', missionId)
        if match:
            return match.group(1)
        return missionId

    def resolvePresetMissionEntries(self, config_data):
        levelAutomation = config_data[0].get('LevelAutomation', {})
        missionText = config_data[1].get('Material_Mission', {}).get('mission', '')
        missionOrder = [mission for mission in missionText.split(',') if mission]
        usedMissionIds = set()
        resolvedEntries = []

        for shortFormMissionId in missionOrder:
            missionId = None
            if shortFormMissionId in levelAutomation and shortFormMissionId not in usedMissionIds:
                missionId = shortFormMissionId
            else:
                duplicatePrefix = shortFormMissionId + "_"
                for candidateMissionId in levelAutomation.keys():
                    if candidateMissionId in usedMissionIds:
                        continue
                    if candidateMissionId.startswith(duplicatePrefix):
                        duplicateSuffix = candidateMissionId[len(duplicatePrefix):]
                        if duplicateSuffix.isdigit():
                            missionId = candidateMissionId
                            break

            if missionId is None:
                continue

            usedMissionIds.add(missionId)
            resolvedEntries.append((shortFormMissionId, missionId, levelAutomation[missionId]))

        for missionId, missionConfig in levelAutomation.items():
            if missionId in usedMissionIds:
                continue
            resolvedEntries.append((self.stripDuplicateMissionSuffix(missionId), missionId, missionConfig))

        return resolvedEntries

    def onFlowFinished(self):
        # Get the result of the flow from the sender object

        # Print the result to the console
        print("completedFlow")
        self.thread_pool = []
    def startMainFlow(self, taskCheckBoxArray):
        self.saveTaskSelection()
        for thread in getattr(self, "thread_pool", []):
            if thread.isRunning():
                EASloggerSingleton.getInstance().info('./logs/log_test.txt', "已有流程正在运行，请先停止或等待结束")
                return

        file_path = 'logs\\log_test.txt'

        # Open the file in write mode
        with open(file_path, 'w') as file:
            # Use the truncate() method to clear the file content
            file.truncate(0)
        self.lastReadPtr = 0
        ADBClass.AdbSingleton.getInstance().resetStop()
        EASloggerSingleton.getInstance().info('./logs/log_test.txt', "开始执行流程")

        thread_pool = QThreadPool.globalInstance()
        thread_pool.setMaxThreadCount(1)
        self.thread_pool = []
        self.MainFlow = self.constructFlow(taskCheckBoxArray)
        # for flow in self.MainFlow:
        flowThread = FlowThread(self.MainFlow)
        flowThread.finished.connect(self.onFlowFinished)  # Connect to the finished signal
        flowThread.start()  # Start the thread
        # runnable = FlowRunnable(flow)
        # # Connect the finished signal of the QRunnable to a slot that prints the result
        # runnable.signal.finished.connect(self.onFlowFinished)
        # # Add the QRunnable to the thread pool
        # thread_pool.start(runnable)
        self.thread_pool.append(flowThread)

        # self.MainFlow = self.constructFlow(taskCheckBoxArray)
        # for flow in self.MainFlow:
        #     flow.executeFlow()

    def stopMainFlow(self):
        if not getattr(self, "thread_pool", None):
            print("停止：当前没有运行中的流程")
            EASloggerSingleton.getInstance().info('./logs/log_test.txt', "停止：当前没有运行中的流程")
            return
        print("停止：已请求停止流程")
        EASloggerSingleton.getInstance().info('./logs/log_test.txt', "停止：已请求停止流程")
        ADBClass.AdbSingleton.getInstance().requestStop()
        for thread in self.thread_pool:
            if thread.isRunning():
                thread.requestInterruption()
                if not thread.wait(1000):
                    EASloggerSingleton.getInstance().info('./logs/log_test.txt', "正在停止流程，请稍候")
                    return
        self.thread_pool = []
        print("停止：流程已结束")
        EASloggerSingleton.getInstance().info('./logs/log_test.txt', "停止：流程已结束")

    def saveTaskSelection(self):
        if not hasattr(self, "startAppCheckbox"):
            return
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or []
        else:
            data = []

        runtime_config = None
        for item in data:
            if isinstance(item, dict) and 'controlMode' in item:
                runtime_config = item
                break
        if runtime_config is None:
            runtime_config = {}
            data.append(runtime_config)

        runtime_config['taskSelection'] = {
            'startApp': self.startAppCheckbox.isChecked(),
            'farmResources': self.farmResCheckbox.isChecked(),
            'receiveReward': self.receiveRewardCheckbox.isChecked(),
        }

        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    def updateFreeAutoStatus(self):
        self.editingMission.freeAuto = self.missionSettingFreeAutoSwitchWidget.isChecked()
    def updateAutoOrManuelStatus(self):
        self.editingMission.auto = self.missionSettingAutoOrManuelSwitchWidget.isChecked()
    def updateAutoDeployStatus(self):
        self.editingMission.autoDeploy = self.missionSettingAutoDeploySwitchWidget.isChecked()
    def updateDefaultDifficultyStatus(self):
        self.editingMission.defaultDifficulty = self.missionSettingDefaultDifficultySwitchWidget.isChecked()
        self.missionSettingDifficultyDropdown.setEnabled(not self.editingMission.defaultDifficulty)
        self.missionSettingMidMissionDropdown.setEnabled(True)
    def updateHighRewardFirstStatus(self):
        self.editingMission.highRewardFirst = self.missionSettingHighRewardSwitchWidget.isChecked()
    def constructFlow(self, taskCheckBoxArray):
        self.MainFlow = []
        if taskCheckBoxArray[0]:
            StartAppWf = runStartApp(self.adbDirTextEdit.text(),self.connectionPortTextEdit.text())
            self.MainFlow.append(StartAppWf)
        if taskCheckBoxArray[1]:
            mainMaterialWf = mainMaterial(self.adbDirTextEdit.text(),self.connectionPortTextEdit.text())
            # StartAppWf = StartAppFlow(self.adbDirTextEdit.text(), self.connectionPortTextEdit.text())
            self.MainFlow.append(mainMaterialWf)
        if taskCheckBoxArray[2]:
            receiveRewardWf = receiveReward(self.adbDirTextEdit.text(),self.connectionPortTextEdit.text())
            # StartAppWf = StartAppFlow(self.adbDirTextEdit.text(), self.connectionPortTextEdit.text())
            self.MainFlow.append(receiveRewardWf)
        return self.MainFlow

    def applySettingAction(self):
        print("applySettingAction")
        if os.path.exists('app_config.yaml'):
            with open('app_config.yaml', 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file) or []
        else:
            data = []

        if len(data) < 1 or not isinstance(data[0], dict):
            data.insert(0, {})
        if len(data) < 2 or not isinstance(data[1], dict):
            data.insert(1, {})

        data[0]['adbDir'] = self.adbDirTextEdit.text()
        data[1]['connectionPort'] = self.connectionPortTextEdit.text()

        runtime_config = None
        for item in data:
            if isinstance(item, dict) and 'controlMode' in item:
                runtime_config = item
                break
        if runtime_config is None:
            runtime_config = {}
            data.append(runtime_config)

        base_resolution_text = self.baseResolutionTextEdit.text().lower().replace(" ", "")
        try:
            base_width, base_height = [int(value) for value in base_resolution_text.split("x", 1)]
        except ValueError:
            base_width, base_height = 1280, 720
            self.baseResolutionTextEdit.setText("1280x720")

        runtime_config['controlMode'] = self.controlModeDropdown.currentText()
        runtime_config['windowTitle'] = self.windowTitleTextEdit.text()
        runtime_config['processName'] = self.processNameTextEdit.text()
        runtime_config['baseResolution'] = [base_width, base_height]
        runtime_config['ocrLanguages'] = self.ocrLanguageDropdown.currentText().split(',')
        runtime_config['taskSelection'] = {
            'startApp': self.startAppCheckbox.isChecked(),
            'farmResources': self.farmResCheckbox.isChecked(),
            'receiveReward': self.receiveRewardCheckbox.isChecked(),
        }

        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(data, file, allow_unicode=True, sort_keys=False)

    def add_empty_mission(self):
        # newMission = QtWidgets.QLineEdit()

        newMissionRowWidget = QtWidgets.QWidget()
        newMissionRowLayout = QtWidgets.QHBoxLayout()
        newMissionRowWidget.setLayout(newMissionRowLayout)

        dropdown = QtWidgets.QComboBox()
        dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for missionName in self.missionNameList:
            dropdown.addItem(missionName)
        dropdown.setCurrentIndex(0)

        setting_button = QPushButton()
        setting_button.setProperty("list-button", True)
        setting_button.setIcon(QIcon("setting_icon.png"))
        setting_button.setStyleSheet("QPushButton {background-color: #0E2369;}")
        newMission = scheduleMission.UIInit(dropdown.currentText(), setting_button, newMissionRowWidget)
        print("added mission:" , dropdown.currentIndex())
        self.scheduleMissionList.append(newMission)
        dropdown.currentIndexChanged.connect(lambda _targetMissionId=dropdown.currentText(), _mission=newMission: self.onMissionIdChanged(
                             _targetMissionId, _mission))
        for mission in self.scheduleMissionList:
            print(mission.id)
        setting_button.connect(setting_button, QtCore.SIGNAL("clicked()"), lambda _missionId=newMission.id: self.selectMissionEdit(_missionId))

        # setting_button.setStyleSheet("QPushButton {border: 0px solid gray;}")


        newMissionRowLayout.addWidget(dropdown)
        newMissionRowLayout.addWidget(setting_button)
        self.mission.append(newMissionRowWidget)
        self.flineEditsVbox.addWidget(newMissionRowWidget)
        self.updateCharacterGridStatus()

    def onMissionIdChanged(self, _missionId, _mission):
        print("onMissionIdChanged")
        print("fromMission", _mission.missionName)
        print("targetMissionId",_missionId)
        print("targetMissionName",self.missionNameList[_missionId])

        _mission.setMission(_missionId)
        self.selectMissionEdit(_mission.id)
        self.updateCharacterGridStatus()

        # _mission.missionName = self.missionNameList[_missionId]

    def onMissionDifficultyChanged(self, _targetDifficulty):
        print("onMissionDifficultyChanged")
        print("_targetDifficulty", _targetDifficulty)
        print("editingMission",self.editingMission)

        self.editingMission.setDifficulty(_targetDifficulty)
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                mission.setDifficulty(int(_targetDifficulty))

        self.updateCharacterGridStatus()
    def onLoadMissionPreset(self, _targetPreset):
        print("onMissionPresetChanged")
        print("_targetDifficulty", _targetPreset)

        self.loadMissionsPreset(_targetPreset)

        self.updateCharacterGridStatus()

    def onMissionMidMissionChanged(self, _targetMidMission):
        print("onMissionMidMissionChanged")
        print("_targetDifficulty", _targetMidMission)
        print("editingMission",self.editingMission)

        self.editingMission.setMidMission(_targetMidMission)
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                mission.setMidMission(_targetMidMission)

        self.updateCharacterGridStatus()

    def add_character_button(self, character):
        row = int(len(self.charSelectionList) / 3)
        col = len(self.charSelectionList) % 3
        print(row, col, character)
        charBtn = QtWidgets.QPushButton(character)
        self.heroListGrid.addWidget(charBtn, row, col)
        self.charSelectionList.append(charBtn)
        charBtn.clicked.connect(lambda checked=False, _character=character, _btn=charBtn: self.selectCharacter(_character, _btn))
        charBtn.setStyleSheet("QPushButton {background-color: #0E2369;}")
        return charBtn

    def save_character_list(self):
        if not os.path.exists('app_config.yaml'):
            return
        with open('app_config.yaml', 'r', encoding='utf-8') as file:
            config_data = yaml.safe_load(file) or []
        for item in config_data:
            if isinstance(item, dict) and "characterList" in item:
                item["characterList"] = self.characterNameList
                break
        with open('app_config.yaml', 'w', encoding='utf-8') as file:
            yaml.safe_dump(config_data, file, allow_unicode=True, sort_keys=False)

    def add_empty_character(self):
        character, ok = QtWidgets.QInputDialog.getText(self, "新增角色", "角色名称")
        character = character.strip()
        if not ok or character == "":
            return
        if character in self.characterNameList:
            return
        self.characterNameList.append(character)
        self.add_character_button(character)
        self.save_character_list()
        self.updateCharacterGridStatus()

    def clear_current_character_selection(self):
        if self.editingMission.missionName == "None":
            return
        self.editingMission.characterList.clear()
        self.selectedCharacterName = None
        self.updateCharacterGridStatus()

    def selectMissionEdit(self, missionId):
        print("selectMissionEdit: ", missionId)
        for mission in self.scheduleMissionList:

            if mission.id == missionId:
                self.editingMission = mission
                print("editingMission missionName: ", self.editingMission.missionName)
                print("characterList: ", self.editingMission.characterList)
                self.updateCharacterGridStatus()

                for missionInfo in self.missionInfoList:
                    if missionInfo['id'] == self.editingMission.missionId:
                        self.missionSettingDifficultyDropdown.blockSignals(True)
                        self.missionSettingDifficultyDropdown.clear()

                        for difficulty in missionInfo["difficultyCount"]:
                            self.missionSettingDifficultyDropdown.addItem(str(difficulty))
                        self.missionSettingDifficultyDropdown.setCurrentIndex(mission.allDifficulty.index(mission.difficulty))
                        self.missionSettingDifficultyDropdown.blockSignals(False)

                        #-----------------------------------------------------------------------------------------------
                        self.missionSettingMidMissionDropdown.blockSignals(True)
                        self.missionSettingMidMissionDropdown.clear()

                        for middleLevel in missionInfo["middleLevel"]:
                            self.missionSettingMidMissionDropdown.addItem(str(middleLevel))
                        if len(mission.allMidMission) > 0:
                            self.missionSettingMidMissionDropdown.setCurrentIndex(
                                mission.allMidMission.index(mission.midMission)
                            )
                        self.missionSettingMidMissionDropdown.blockSignals(False)
                        break
                        # dropdown.setCurrentIndex(0)

                break
        # self.editingMission = mission
        #
        # self.updateCharacterGridStatus()
        # print(self.editingMission.missionName)
        # print(mission.missionName)
        # for mis in self.scheduleMissionList:
        #     print(mis.characterList)


    def selectCharacter(self, character, btn: QPushButton):
        print("selectCharacter: ", character)
        self.selectedCharacterName = character
        if character not in self.editingMission.characterList:
            self.editingMission.characterList.append(character)
            btn.setStyleSheet("QPushButton {background-color: #991B00;}")
        else:
            self.editingMission.characterList.remove(character)
            btn.setStyleSheet("QPushButton {background-color: #0E2369;}")
        print(self.editingMission.characterList)
        self.updateCharacterGridStatus()
    def updateCharacterGridStatus(self):
        if self.editingMission.missionName == "None":
            for btn in self.charSelectionList:
                btn.setEnabled(False)
            self.missionRemoveButton.setEnabled(False)
            if hasattr(self, "heroSettingClearButton"):
                self.heroSettingClearButton.setEnabled(False)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setEnabled(False)
            if hasattr(self, "missionSettingDifficultyDropdown"):
                self.missionSettingDifficultyDropdown.setEnabled(False)
            if hasattr(self, "missionSettingMidMissionDropdown"):
                self.missionSettingMidMissionDropdown.setEnabled(False)
        else:
            isFull = self.editingMission.maxCharCount >= 0 and len(self.editingMission.characterList) >= self.editingMission.maxCharCount
            maxCharCountText = str(self.editingMission.maxCharCount) if self.editingMission.maxCharCount >= 0 else "不限"
            self.heroListGridTitle.setText("Character Selection: " + str(len(self.editingMission.characterList)) + "/"+ maxCharCountText)
            self.missionRemoveButton.setEnabled(True)
            for btn in self.charSelectionList:
                btn.setEnabled(True)
                if btn.text() in self.editingMission.characterList:
                    btn.setStyleSheet("QPushButton {background-color: #991B00;}")
                else:
                    btn.setStyleSheet("QPushButton {background-color: #0E2369;}")
                    if isFull:
                        btn.setEnabled(False)
                for mission in self.scheduleMissionList:
                    # print(mission.characterList)
                    if mission.id != self.editingMission.id:
                        if btn.text() in mission.characterList:
                            btn.setEnabled(False)
            for mission in self.scheduleMissionList:
                if mission.id == self.editingMission.id:
                    mission.missionBtn.setStyleSheet("QPushButton {background-color: #991B00;}")
                else:
                    mission.missionBtn.setStyleSheet("QPushButton {background-color: #0E2369;}")
            self.missionSettingFreeAutoSwitchWidget.setEnabled(True)
            self.missionSettingAutoOrManuelSwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setEnabled(True)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setEnabled(True)
            if hasattr(self, "heroSettingClearButton"):
                self.heroSettingClearButton.setEnabled(True)
            self.missionSettingFreeAutoSwitchWidget.setChecked(self.editingMission.freeAuto)
            self.missionSettingAutoOrManuelSwitchWidget.setChecked(self.editingMission.auto)
            if hasattr(self, "missionSettingAutoDeploySwitchWidget"):
                self.missionSettingAutoDeploySwitchWidget.setChecked(self.editingMission.autoDeploy)
            if hasattr(self, "missionSettingDefaultDifficultySwitchWidget"):
                self.missionSettingDefaultDifficultySwitchWidget.setChecked(self.editingMission.defaultDifficulty)
            if hasattr(self, "missionSettingHighRewardSwitchWidget"):
                self.missionSettingHighRewardSwitchWidget.setChecked(self.editingMission.highRewardFirst)
            if hasattr(self, "missionSettingDifficultyDropdown"):
                self.missionSettingDifficultyDropdown.setEnabled(not self.editingMission.defaultDifficulty)
            if hasattr(self, "missionSettingMidMissionDropdown"):
                self.missionSettingMidMissionDropdown.setEnabled(True)
    def remove_missions(self):
        print("remove_missions")
        for mission in self.scheduleMissionList:
            if mission.id == self.editingMission.id:
                self.editingMission.missionRow.deleteLater()
                self.scheduleMissionList.remove(mission)
                if len(self.scheduleMissionList) > 0:
                    self.editingMission = self.scheduleMissionList[0]
                else:
                    self.editingMission = scheduleMission.UIInit(None)
                self.updateCharacterGridStatus()
                break
    def save_missions(self):
        print("save_preset")
        print("--------------------------------------------------------")
        for mission in self.scheduleMissionList:
            print("missionName: ", mission.missionName)
            print("characterList: ", mission.characterList)
            print("id: ", mission.id)
            print("missionId: ", mission.missionId)
            print("difficulty: ", mission.difficulty)
            print("midMission: ", mission.midMission)
            print("maxCharCount: ", mission.maxCharCount)
            print("auto: ", mission.auto)
            print("freeAuto: ", mission.freeAuto)
            print("autoDeploy: ", mission.autoDeploy)
            print("defaultDifficulty: ", mission.defaultDifficulty)
            print("highRewardFirst: ", mission.highRewardFirst)
            print("--------------------------------------------------------")
        filename = f'.\\active_config.yaml'
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, filename)
    def save_preset(self, fileName):
        print("save_preset")
        print("--------------------------------------------------------")
        for mission in self.scheduleMissionList:
            print("missionName: ",mission.missionName)
            print("characterList: ",mission.characterList)
            print("id: ",mission.id)
            print("missionId: ",mission.missionId)
            print("difficulty: ",mission.difficulty)
            print("midMission: ",mission.midMission)
            print("maxCharCount: ", mission.maxCharCount)
            print("auto: ", mission.auto)
            print("freeAuto: ", mission.freeAuto)
            print("autoDeploy: ", mission.autoDeploy)
            print("defaultDifficulty: ", mission.defaultDifficulty)
            print("highRewardFirst: ", mission.highRewardFirst)
            print("--------------------------------------------------------")
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, fileName)

    def save_as_new_preset(self, filename):
        print("save_preset")
        print("--------------------------------------------------------")
        for mission in self.scheduleMissionList:
            print("missionName: ", mission.missionName)
            print("characterList: ", mission.characterList)
            print("id: ", mission.id)
            print("missionId: ", mission.missionId)
            print("difficulty: ", mission.difficulty)
            print("midMission: ", mission.midMission)
            print("maxCharCount: ", mission.maxCharCount)
            print("auto: ", mission.auto)
            print("freeAuto: ", mission.freeAuto)
            print("autoDeploy: ", mission.autoDeploy)
            print("defaultDifficulty: ", mission.defaultDifficulty)
            print("highRewardFirst: ", mission.highRewardFirst)
            print("--------------------------------------------------------")
        filename = f'.\\configs\\{filename}.yaml'
        OctoUtil.OctoUtil.parse_mission_to_preset_yaml(self.scheduleMissionList, filename)
# BTN_LOC_ACCEPT_PERMISSION = [875,420]

# m_config = Config("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555", [1280, 720], 240)
# m_profile = Adb_profile("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555")
# ADBClass.AdbSingleton.getInstance().connectDevice(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# if not os.path.exists('config.yaml'):
#     with open('config.ini', 'w', encoding='utf-8') as configfile:
#         data = [
#             {'LevelAutomation': [{'level': 'EXP_07', 'characters': '澤維爾,迪塔利奧', 'times': '1'}]},
#         ]
#
#         # Write the list of dictionaries to a YAML file
#         with open('config.yaml', 'w') as file:
#             yaml.dump(data, file)
# else:
# with open('config.ini', 'w', encoding='utf-8') as configfile:
#     data =  [
#                 {'LevelAutomation':
#                     [
#                         {'EXP_07': {'characters': '澤維爾,迪塔利奧', 'times': '1'}},
#                         {'SRD_04': {'characters': 'Auto', 'times': '1'}}
#                     ]
#                 }
#             ]
#
#     # Write the list of dictionaries to a YAML file
#     with open('config.yaml', 'w') as file:
#         yaml.dump(data, file)
#
# ocr = PaddleOCR(rec_model_dir ="./res/chinese_cht_PP-OCRv3_rec_infer/", det_model_dir="./res/ch_PP-OCRv3_det_infer/", use_angle_cls=True, lang="ch")
# ocr = CnOcr(rec_model_name='chinese_cht_PP-OCRv3')
# result = ocr.ocr('./img/autoRunScreenshot_FOR_OCR_TEST.png')
# for line in result:
#     # print(line)
#     text = line['text']
#     confidence = line['score']
#     positionRect = line['position']
#     center = [(positionRect[0][0] + positionRect[1][0]) / 2, (positionRect[1][1] + positionRect[2][1]) / 2]
#     print(text, confidence > 0.8, center)

# Create an instance of the EasyOCR reader
# reader = easyocr.Reader(['ch_tra'])
#
# # Load the image file
# image_path = './Icons/CharOCRImg.png'
#
# # Perform OCR on the image
# results = reader.readtext(image_path)
#
# # Print the recognized text
# for result in results:
#     print(result)
# OCRClass.OCRSingleton.getInstance().findTextPosition('./img/levelCapture.png', '實戰訓練')
# # Load the YAML file
# with open('config.yaml', 'r') as file:
#     config_data = yaml.safe_load(file)
#     print(config_data[1]['Material_Mission']['mission'].split(','))
#     level_character = config_data[0]['LevelAutomation'][0]['EXP_07']['characters'].split(',')
#     # config_data['LevelAutomation'][0]['level'] = 'EXP_07'
#     for char in level_character:
#         print(char)
#         print(OCRClass.OCRSingleton.getInstance().findTextPosition('./img/loginCapture.png', char))

#         ADBClass.AdbSingleton().getInstance().tap([(line[0][2][0] + line[0][3][0])/2, (line[0][1][1] + line[0][2][1])/2])
# m_adb = ADBClass.AdbSingleton().connectDevice("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555")# print(m_profile.adb_connect())

# Define the Python function that will be called from the HTML UI
# @eel.expose
# def say_hello():
#     return "Hello, World!"
# @eel.expose
# def print_test(text):
#     return text + " From PY"
# # Set the web files folder and optionally specify which file types to check for
# eel.init('web')
# # Start the Eel application
# eel.start('index.html', size=(1080, 720))
# image_one = Image.open("./img/ScrollCharacterBeforeCroppedScreenshot.png").convert('RGB')
# image_two = Image.open("./img/ScrollCharacterBeforeCroppedScreenshot.png").convert('RGB')
#
# diff = ImageChops.difference(image_one, image_two)
#
# diff.getbbox()
# startFlow = TestFlowOcto("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555",5)
# MainFlow = DailyMaterialFlow("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555", 5)
# MainFlow.executeFlow()

# startFlow = StartAppFlow("D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", "127.0.0.1:7555",5)
#
# startFlow.executeFlow()

# m_dataset = [
#   {
#     "filename": "trainingData/ScrollCharacter0.png",
#     "dataset": [{"transcription": "歌洛莉亞", "points": [[324, 159], [409, 159], [409, 181], [324, 181]]}, {"transcription": "泰登", "points": [[547, 158], [591, 158], [591, 183], [547, 183]]}, {"transcription": "志願者", "points": [[166, 422], [221, 422], [221, 448], [166, 448]]}, {"transcription": "紅隼", "points": [[384, 423], [424, 423], [424, 445], [384, 445]]}, {"transcription": "神閃", "points": [[585, 423], [624, 422], [623, 445], [585, 445]]}, {"transcription": "迪塔利奥", "points": [[120, 157], [207, 157], [207, 181], [120, 181]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter1.png",
#     "dataset": [{"transcription": "兵蜂", "points": [[176, 169], [219, 169], [219, 192], [176, 192]]}, {"transcription": "炎之魔女", "points": [[347, 169], [424, 169], [424, 193], [347, 193]]}, {"transcription": "魔禁", "points": [[585, 169], [625, 169], [625, 192], [585, 192]]}, {"transcription": "執劍者", "points": [[165, 433], [222, 433], [222, 459], [165, 459]]}, {"transcription": "蝴蝶", "points": [[366, 434], [410, 434], [410, 458], [366, 458]]}, {"transcription": "暗夜", "points": [[576, 433], [622, 433], [622, 458], [576, 458]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter2.png",
#     "dataset": [{"transcription": "銳眼", "points": [[183, 167], [221, 167], [221, 194], [183, 194]]}, {"transcription": "天使", "points": [[385, 171], [423, 171], [423, 191], [385, 191]]}, {"transcription": "黯心", "points": [[585, 169], [624, 169], [624, 191], [585, 191]]}, {"transcription": "怒風", "points": [[174, 433], [220, 433], [220, 459], [174, 459]]}, {"transcription": "鞭笞", "points": [[376, 433], [421, 433], [421, 459], [376, 459]]}, {"transcription": "神威", "points": [[587, 433], [624, 433], [624, 458], [587, 458]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter3.png",
#     "dataset": [{"transcription": "風暴神斧", "points": [[145, 169], [220, 169], [220, 194], [145, 194]]}, {"transcription": "利刃", "points": [[383, 169], [421, 169], [424, 191], [385, 191]]}, {"transcription": "法皇國投槍兵", "points": [[501, 169], [632, 169], [632, 194], [501, 194]]}, {"transcription": "王國軍長槍兵", "points": [[103, 434], [229, 434], [229, 457], [103, 457]]}, {"transcription": "騎士同盟長槍兵", "points": [[293, 434], [440, 434], [440, 457], [293, 457]]}, {"transcription": "薇爾德斥候", "points": [[514, 433], [622, 436], [621, 459], [513, 456]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter4.png",
#     "dataset": [{"transcription": "僱傭長槍兵", "points": [[113, 171], [219, 171], [219, 193], [113, 193]]}, {"transcription": "無法者長槍兵", "points": [[303, 169], [431, 169], [431, 192], [303, 192]]}, {"transcription": "無法者巨斧兵", "points": [[505, 171], [632, 171], [632, 195], [505, 195]]}, {"transcription": "僱傭刺客", "points": [[121, 433], [209, 433], [209, 461], [121, 461]]}, {"transcription": "無法者刺客", "points": [[312, 433], [421, 433], [421, 461], [312, 461]]}, {"transcription": "耀光", "points": [[583, 433], [624, 432], [626, 459], [586, 458]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter5.png",
#     "dataset": [{"transcription": "法皇國劍盾兵", "points": [[101, 169], [229, 169], [229, 193], [101, 193]]}, {"transcription": "王國軍劍盾兵", "points": [[304, 169], [431, 169], [431, 192], [304, 192]]}, {"transcription": "騎士同盟劍盾兵", "points": [[492, 168], [643, 171], [642, 195], [492, 192]]}, {"transcription": "王國軍火術士", "points": [[103, 435], [229, 435], [229, 458], [103, 458]]}, {"transcription": "黑暗之光冰術士", "points": [[293, 434], [440, 434], [440, 457], [293, 457]]}, {"transcription": "摧城", "points": [[578, 433], [622, 433], [622, 460], [578, 460]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter6.png",
#     "dataset": [{"transcription": "王國軍光術士", "points": [[103, 184], [229, 183], [229, 206], [103, 208]]}, {"transcription": "神恩", "points": [[383, 184], [422, 184], [422, 208], [383, 208]]}, {"transcription": "黑暗之光火術士", "points": [[493, 183], [643, 183], [643, 209], [493, 209]]}, {"transcription": "法皇國冰術師", "points": [[100, 449], [230, 446], [231, 470], [100, 473]]}, {"transcription": "王國軍弓箭手", "points": [[305, 450], [431, 450], [431, 472], [305, 472]]}, {"transcription": "無法者斧盾兵", "points": [[504, 449], [633, 447], [633, 471], [504, 473]]}]
#   },
#   {
#     "filename": "trainingData/ScrollCharacter7.png",
#     "dataset": [{"transcription": "王國軍光術士", "points": [[103, 184], [229, 183], [229, 206], [103, 208]]}, {"transcription": "神恩", "points": [[383, 184], [422, 184], [422, 208], [383, 208]]}, {"transcription": "黑暗之光火術士", "points": [[493, 183], [643, 183], [643, 209], [493, 209]]}, {"transcription": "法皇國冰術師", "points": [[100, 449], [230, 446], [231, 470], [100, 473]]}, {"transcription": "王國軍弓箭手", "points": [[305, 450], [431, 450], [431, 472], [305, 472]]}, {"transcription": "無法者斧盾兵", "points": [[504, 449], [633, 447], [633, 471], [504, 473]]}]
#   }
# ]
#
# for i in range(0, len(m_dataset)):
#     for j in range(0, len(m_dataset[i]['dataset'])):
#         left = m_dataset[i]['dataset'][j]['points'][0][0]
#         top = m_dataset[i]['dataset'][j]['points'][0][1]
#         right = m_dataset[i]['dataset'][j]['points'][2][0]
#         bottom = m_dataset[i]['dataset'][j]['points'][2][1]
#         inputImgPath = m_dataset[i]['filename']
#         dataScreenshot = Image.open(inputImgPath)
#         cropped_image = dataScreenshot.crop((left, top, right, bottom))
#         cropped_image.save('./autoSelectCharRecon/' + m_dataset[i]['dataset'][j]['transcription'] + '.png')

# runStartAppFlow = runStartApp(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# runStartAppFlow.run()

# ADBClass.AdbSingleton.getInstance().connectDevice(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# for i in range(0, 10):
#     ADBClass.AdbSingleton.getInstance().swipe((400, 600), (400, 225), 1000)
#     ADBClass.AdbSingleton.getInstance().screen_capture(f'./trainingData/ScrollCharacter{i}.png')
#     time.sleep(5)

# MatF = mainMaterial(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# MatF.run()
# logging.basicConfig(filename='example.log', encoding='utf-8', level=logging.DEBUG)
# logging.debug('This message should go to the log file')
# logging.info('So should this')
# logging.warning('And this, too')
# logging.error('And non-ASCII stuff, too, like Øresund and Malmö')
# SAFlow = runStartApp(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# SAFlow.run()

# RAFlow = receiveReward(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# RAFlow.run()

# WTFlow = weeklyTower(adb_path="D:\\mumu2\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe", adb_port="127.0.0.1:7555")
# WTFlow.run()

# left = 970
# top = 554
# right = 985
# bottom = 585
# OctoUtil.OctoUtil.checkSelectedCharNum( top, left, bottom, right)
# if os.path.exists('app_config.yaml'):
#     with open('app_config.yaml', 'r') as file:
#         config_data = yaml.safe_load(file)
#         print(config_data[4]["missioninfo"][0]["name"])
# OctoUtil.OctoUtil.check_pixel_color('./img/startMission.png', 751,35, (132,202,124,255))
# print(m_profile.screen_capture("./img/screenshot.png"))
# EASloggerSingleton.getInstance().info('./logs/log_test.txt', "正在連接模擬器")

log_path = 'logs\\log_test.txt'

    # Open the file in write mode
with open(log_path, 'w') as file:
    # Use the truncate() method to clear the file content
    file.truncate(0)

app = QtWidgets.QApplication([])
app.setStyle('Fusion')
ui = OctoUI()
ui.show()
app.exec_()





# app = QApplication(sys.argv)
# app.setStyle('Fusion')
# #app.setStyle('Material')
# window = MainWindow()
# window.show()
#
# # Start the event loop.
# app.exec()