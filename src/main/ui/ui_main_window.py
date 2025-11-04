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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QMenuBar, QPushButton,
    QSizePolicy, QSplitter, QStatusBar, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1134, 747)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.mainSplitter = QSplitter(self.centralwidget)
        self.mainSplitter.setObjectName(u"mainSplitter")
        self.mainSplitter.setOrientation(Qt.Orientation.Horizontal)
        self.leftPanelWidget = QWidget(self.mainSplitter)
        self.leftPanelWidget.setObjectName(u"leftPanelWidget")
        self.leftPanelLayout = QVBoxLayout(self.leftPanelWidget)
        self.leftPanelLayout.setSpacing(6)
        self.leftPanelLayout.setObjectName(u"leftPanelLayout")
        self.leftPanelLayout.setContentsMargins(0, 0, 0, 0)
        self.keysButton = QPushButton(self.leftPanelWidget)
        self.keysButton.setObjectName(u"keysButton")

        self.leftPanelLayout.addWidget(self.keysButton)

        self.searchBar = QLineEdit(self.leftPanelWidget)
        self.searchBar.setObjectName(u"searchBar")

        self.leftPanelLayout.addWidget(self.searchBar)

        self.newButtonsLayout = QHBoxLayout()
        self.newButtonsLayout.setObjectName(u"newButtonsLayout")
        self.newChatButton = QPushButton(self.leftPanelWidget)
        self.newChatButton.setObjectName(u"newChatButton")

        self.newButtonsLayout.addWidget(self.newChatButton)

        self.newProjectButton = QPushButton(self.leftPanelWidget)
        self.newProjectButton.setObjectName(u"newProjectButton")

        self.newButtonsLayout.addWidget(self.newProjectButton)


        self.leftPanelLayout.addLayout(self.newButtonsLayout)

        self.line = QFrame(self.leftPanelWidget)
        self.line.setObjectName(u"line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.leftPanelLayout.addWidget(self.line)

        self.chatHistoryTree = QTreeWidget(self.leftPanelWidget)
        self.chatHistoryTree.setObjectName(u"chatHistoryTree")
        self.chatHistoryTree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chatHistoryTree.setHeaderHidden(True)

        self.leftPanelLayout.addWidget(self.chatHistoryTree)

        self.mainSplitter.addWidget(self.leftPanelWidget)
        self.rightPanelWidget = QWidget(self.mainSplitter)
        self.rightPanelWidget.setObjectName(u"rightPanelWidget")
        self.rightPanelLayout = QVBoxLayout(self.rightPanelWidget)
        self.rightPanelLayout.setObjectName(u"rightPanelLayout")
        self.rightPanelLayout.setContentsMargins(0, 0, 0, 0)
        self.chatAreaSplitter = QSplitter(self.rightPanelWidget)
        self.chatAreaSplitter.setObjectName(u"chatAreaSplitter")
        self.chatAreaSplitter.setOrientation(Qt.Orientation.Vertical)
        self.chatDisplay = QListWidget(self.chatAreaSplitter)
        self.chatDisplay.setObjectName(u"chatDisplay")
        self.chatDisplay.setFrameShape(QFrame.NoFrame)
        self.chatDisplay.setSelectionMode(QAbstractItemView.NoSelection)
        self.chatDisplay.setSpacing(5)
        self.chatAreaSplitter.addWidget(self.chatDisplay)
        self.inputContainer = QWidget(self.chatAreaSplitter)
        self.inputContainer.setObjectName(u"inputContainer")
        self.inputContainerLayout = QVBoxLayout(self.inputContainer)
        self.inputContainerLayout.setObjectName(u"inputContainerLayout")
        self.messageInput = QTextEdit(self.inputContainer)
        self.messageInput.setObjectName(u"messageInput")
        self.messageInput.setMaximumSize(QSize(16777215, 120))

        self.inputContainerLayout.addWidget(self.messageInput)

        self.bottomControlsLayout = QHBoxLayout()
        self.bottomControlsLayout.setObjectName(u"bottomControlsLayout")
        self.modelComboBox = QComboBox(self.inputContainer)
        self.modelComboBox.setObjectName(u"modelComboBox")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.modelComboBox.sizePolicy().hasHeightForWidth())
        self.modelComboBox.setSizePolicy(sizePolicy)

        self.bottomControlsLayout.addWidget(self.modelComboBox)

        self.sendButton = QPushButton(self.inputContainer)
        self.sendButton.setObjectName(u"sendButton")

        self.bottomControlsLayout.addWidget(self.sendButton)


        self.inputContainerLayout.addLayout(self.bottomControlsLayout)

        self.chatAreaSplitter.addWidget(self.inputContainer)

        self.rightPanelLayout.addWidget(self.chatAreaSplitter)

        self.mainSplitter.addWidget(self.rightPanelWidget)

        self.verticalLayout.addWidget(self.mainSplitter)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"AnyChat", None))
        self.keysButton.setText(QCoreApplication.translate("MainWindow", u"Keys", None))
        self.searchBar.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Search chats...", None))
        self.newChatButton.setText(QCoreApplication.translate("MainWindow", u"New Chat", None))
        self.newProjectButton.setText(QCoreApplication.translate("MainWindow", u"New Project", None))
        ___qtreewidgetitem = self.chatHistoryTree.headerItem()
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", u"Chat History", None));
        self.messageInput.setPlaceholderText(QCoreApplication.translate("MainWindow", u"Ask anything...", None))
        self.sendButton.setText(QCoreApplication.translate("MainWindow", u"Send", None))
    # retranslateUi

