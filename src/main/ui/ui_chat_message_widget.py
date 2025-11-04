# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'chat_message_widget.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QSizePolicy, QSpacerItem,
    QTextEdit, QWidget)

class Ui_ChatMessageWidget(object):
    def setupUi(self, ChatMessageWidget):
        if not ChatMessageWidget.objectName():
            ChatMessageWidget.setObjectName(u"ChatMessageWidget")
        ChatMessageWidget.resize(400, 50)
        ChatMessageWidget.setStyleSheet(u"/* Ensure the base widget is transparent */\n"
"                QWidget {\n"
"                background-color: transparent;\n"
"                }\n"
"\n"
"                QTextEdit {\n"
"                border: 1px solid #444;\n"
"                border-radius: 8px;\n"
"                padding: 8px;\n"
"                font-size: 14px;\n"
"                /* We'll set the background color in the .py file */\n"
"                }\n"
"            ")
        self.mainLayout = QHBoxLayout(ChatMessageWidget)
        self.mainLayout.setObjectName(u"mainLayout")
        self.mainLayout.setContentsMargins(0, 2, 0, 2)
        self.leftSpacer = QSpacerItem(10, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainLayout.addItem(self.leftSpacer)

        self.messageContent = QTextEdit(ChatMessageWidget)
        self.messageContent.setObjectName(u"messageContent")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.messageContent.sizePolicy().hasHeightForWidth())
        self.messageContent.setSizePolicy(sizePolicy)
        self.messageContent.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.messageContent.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.mainLayout.addWidget(self.messageContent)

        self.rightSpacer = QSpacerItem(10, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.mainLayout.addItem(self.rightSpacer)


        self.retranslateUi(ChatMessageWidget)

        QMetaObject.connectSlotsByName(ChatMessageWidget)
    # setupUi

    def retranslateUi(self, ChatMessageWidget):
        ChatMessageWidget.setWindowTitle(QCoreApplication.translate("ChatMessageWidget", u"Form", None))
    # retranslateUi

