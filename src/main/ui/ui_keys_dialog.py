# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'keys_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractButton, QApplication, QDialog, QDialogButtonBox,
    QFormLayout, QLabel, QSizePolicy, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_KeysDialog(object):
    def setupUi(self, KeysDialog):
        if not KeysDialog.objectName():
            KeysDialog.setObjectName(u"KeysDialog")
        KeysDialog.resize(450, 200)
        KeysDialog.setModal(True)
        self.verticalLayout = QVBoxLayout(KeysDialog)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label = QLabel(KeysDialog)
        self.label.setObjectName(u"label")

        self.verticalLayout.addWidget(self.label)

        self.keyFormLayout = QFormLayout()
        self.keyFormLayout.setObjectName(u"keyFormLayout")

        self.verticalLayout.addLayout(self.keyFormLayout)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.buttonBox = QDialogButtonBox(KeysDialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)

        self.verticalLayout.addWidget(self.buttonBox)


        self.retranslateUi(KeysDialog)
        self.buttonBox.accepted.connect(KeysDialog.accept)
        self.buttonBox.rejected.connect(KeysDialog.reject)

        QMetaObject.connectSlotsByName(KeysDialog)
    # setupUi

    def retranslateUi(self, KeysDialog):
        KeysDialog.setWindowTitle(QCoreApplication.translate("KeysDialog", u"API Key Management", None))
        self.label.setText(QCoreApplication.translate("KeysDialog", u"Enter your API keys for the LLM providers:", None))
    # retranslateUi

