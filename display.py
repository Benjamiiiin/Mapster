# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'gui/display.ui'
#
# Created by: PyQt5 UI code generator 5.10.1
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_DisplayDialog(object):
    def setupUi(self, DisplayDialog):
        DisplayDialog.setObjectName("DisplayDialog")
        DisplayDialog.resize(400, 300)
        self.horizontalLayout = QtWidgets.QHBoxLayout(DisplayDialog)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.scroll_display = QtWidgets.QScrollArea(DisplayDialog)
        self.scroll_display.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll_display.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.scroll_display.setLineWidth(0)
        self.scroll_display.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_display.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll_display.setWidgetResizable(True)
        self.scroll_display.setObjectName("scroll_display")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 400, 300))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scroll_display.setWidget(self.scrollAreaWidgetContents)
        self.horizontalLayout.addWidget(self.scroll_display)

        self.retranslateUi(DisplayDialog)
        QtCore.QMetaObject.connectSlotsByName(DisplayDialog)

    def retranslateUi(self, DisplayDialog):
        _translate = QtCore.QCoreApplication.translate
        DisplayDialog.setWindowTitle(_translate("DisplayDialog", "Dialog"))

