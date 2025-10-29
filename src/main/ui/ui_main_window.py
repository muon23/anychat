# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QHBoxLayout,
    QHeaderView, QLineEdit, QMainWindow, QMenuBar,
    QPushButton, QSizePolicy, QSplitter, QStatusBar,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1069, 688)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout_3 = QVBoxLayout(self.centralwidget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.mainSplitter = QSplitter(self.centralwidget)
        self.mainSplitter.setObjectName(u"mainSplitter")
        self.mainSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.leftPanelWidget = QWidget(self.mainSplitter)
        self.leftPanelWidget.setObjectName(u"leftPanelWidget")
        self.leftPanelWidget.setBaseSize(QSize(200, 0))
        self.verticalLayout = QVBoxLayout(self.leftPanelWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.newChatButton = QPushButton(self.leftPanelWidget)
        self.newChatButton.setObjectName(u"newChatButton")

        self.verticalLayout.addWidget(self.newChatButton)

        self.searchBar = QLineEdit(self.leftPanelWidget)
        self.searchBar.setObjectName(u"searchBar")

        self.verticalLayout.addWidget(self.searchBar)

        self.keysButton = QPushButton(self.leftPanelWidget)
        self.keysButton.setObjectName(u"keysButton")

        self.verticalLayout.addWidget(self.keysButton)

        self.line = QFrame(self.leftPanelWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout.addWidget(self.line)

        self.chatHistoryTree = QTreeWidget(self.leftPanelWidget)
        __qtreewidgetitem = QTreeWidgetItem()
        __qtreewidgetitem.setText(0, u"1");
        self.chatHistoryTree.setHeaderItem(__qtreewidgetitem)
        self.chatHistoryTree.setObjectName(u"chatHistoryTree")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(self.chatHistoryTree.sizePolicy().hasHeightForWidth())
        self.chatHistoryTree.setSizePolicy(sizePolicy)

        self.verticalLayout.addWidget(self.chatHistoryTree)

        self.settingsButton = QPushButton(self.leftPanelWidget)
        self.settingsButton.setObjectName(u"settingsButton")

        self.verticalLayout.addWidget(self.settingsButton)

        self.mainSplitter.addWidget(self.leftPanelWidget)
        self.rightPanelWidget = QWidget(self.mainSplitter)
        self.rightPanelWidget.setObjectName(u"rightPanelWidget")
        self.rightPanelWidget.setBaseSize(QSize(600, 0))
        self.verticalLayout_2 = QVBoxLayout(self.rightPanelWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.chatAreaSplitter = QSplitter(self.rightPanelWidget)
        self.chatAreaSplitter.setObjectName(u"chatAreaSplitter")
        self.chatAreaSplitter.setOrientation(Qt.Orientation.Vertical)
        self.chatDisplay = QTextEdit(self.chatAreaSplitter)
        self.chatDisplay.setObjectName(u"chatDisplay")
        self.chatDisplay.setReadOnly(True)
        self.chatAreaSplitter.addWidget(self.chatDisplay)
        self.inputContainer = QWidget(self.chatAreaSplitter)
        self.inputContainer.setObjectName(u"inputContainer")
        self.inputContainerLayout = QVBoxLayout(self.inputContainer)
        self.inputContainerLayout.setObjectName(u"inputContainerLayout")
        self.messageInput = QTextEdit(self.inputContainer)
        self.messageInput.setObjectName(u"messageInput")
        sizePolicy.setHeightForWidth(self.messageInput.sizePolicy().hasHeightForWidth())
        self.messageInput.setSizePolicy(sizePolicy)

        self.inputContainerLayout.addWidget(self.messageInput)

        self.bottomControlsLayout = QHBoxLayout()
        self.bottomControlsLayout.setObjectName(u"bottomControlsLayout")
        self.modelComboBox = QComboBox(self.inputContainer)
        self.modelComboBox.setObjectName(u"modelComboBox")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(1)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.modelComboBox.sizePolicy().hasHeightForWidth())
        self.modelComboBox.setSizePolicy(sizePolicy1)

        self.bottomControlsLayout.addWidget(self.modelComboBox)

        self.sendButton = QPushButton(self.inputContainer)
        self.sendButton.setObjectName(u"sendButton")

        self.bottomControlsLayout.addWidget(self.sendButton)


        self.inputContainerLayout.addLayout(self.bottomControlsLayout)

        self.chatAreaSplitter.addWidget(self.inputContainer)

        self.verticalLayout_2.addWidget(self.chatAreaSplitter)

        self.mainSplitter.addWidget(self.rightPanelWidget)

        self.verticalLayout_3.addWidget(self.mainSplitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1069, 37))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"AnyChat", None))
        self.newChatButton.setText(QCoreApplication.translate("MainWindow", u"New Chat", None))
        self.searchBar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search chats...", None))
        self.keysButton.setText(QCoreApplication.translate("MainWindow", u"Keys", None))
        self.settingsButton.setText(QCoreApplication.translate("MainWindow", u"Settings", None))
        self.messageInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Ask anything...", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"Send", None))
    # retranslateUi

