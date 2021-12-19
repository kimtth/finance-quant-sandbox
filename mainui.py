# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pyside.ui'
##
## Created by: Qt User Interface Compiler version 5.15.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide2.QtCore import *
from PySide2.QtGui import *
from PySide2.QtWidgets import *


class Ui_mainWindow(object):
    def setupUi(self, mainWindow):
        if not mainWindow.objectName():
            mainWindow.setObjectName(u"mainWindow")
        mainWindow.resize(426, 543)
        self.centralwidget = QWidget(mainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.mainTab = QTabWidget(self.centralwidget)
        self.mainTab.setObjectName(u"mainTab")
        self.mainTab.setGeometry(QRect(0, 0, 421, 521))
        self.ledgerTab = QWidget()
        self.ledgerTab.setObjectName(u"ledgerTab")
        self.tableView = QTableView(self.ledgerTab)
        self.tableView.setObjectName(u"tableView")
        self.tableView.setGeometry(QRect(10, 30, 401, 211))
        self.tableView.setSortingEnabled(True)
        self.tableView_2 = QTableView(self.ledgerTab)
        self.tableView_2.setObjectName(u"tableView_2")
        self.tableView_2.setGeometry(QRect(10, 270, 401, 221))
        self.tableView_2.setSortingEnabled(True)
        self.label_2 = QLabel(self.ledgerTab)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(10, 10, 56, 12))
        self.label_3 = QLabel(self.ledgerTab)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setGeometry(QRect(10, 250, 56, 12))
        self.loadButton = QPushButton(self.ledgerTab)
        self.loadButton.setObjectName(u"loadButton")
        self.loadButton.setGeometry(QRect(250, 0, 75, 23))
        self.quantityButton = QPushButton(self.ledgerTab)
        self.quantityButton.setObjectName(u"quantityButton")
        self.quantityButton.setGeometry(QRect(330, 0, 75, 23))
        self.mainTab.addTab(self.ledgerTab, "")
        self.transactionTtab = QWidget()
        self.transactionTtab.setObjectName(u"transactionTtab")
        self.PathButton = QPushButton(self.transactionTtab)
        self.PathButton.setObjectName(u"PathButton")
        self.PathButton.setGeometry(QRect(10, 10, 75, 23))
        self.sellButton = QPushButton(self.transactionTtab)
        self.sellButton.setObjectName(u"sellButton")
        self.sellButton.setGeometry(QRect(90, 10, 75, 23))
        self.buyButton = QPushButton(self.transactionTtab)
        self.buyButton.setObjectName(u"buyButton")
        self.buyButton.setGeometry(QRect(170, 10, 75, 23))
        self.label = QLabel(self.transactionTtab)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 42, 71, 20))
        self.lineEdit = QLineEdit(self.transactionTtab)
        self.lineEdit.setObjectName(u"lineEdit")
        self.lineEdit.setGeometry(QRect(90, 40, 151, 20))
        self.textEdit = QTextEdit(self.transactionTtab)
        self.textEdit.setObjectName(u"textEdit")
        self.textEdit.setGeometry(QRect(10, 80, 401, 411))
        self.textEdit.setReadOnly(True)
        self.mainTab.addTab(self.transactionTtab, "")
        self.accountTab = QWidget()
        self.accountTab.setObjectName(u"accountTab")
        self.tableView_3 = QTableView(self.accountTab)
        self.tableView_3.setObjectName(u"tableView_3")
        self.tableView_3.setGeometry(QRect(10, 40, 401, 451))
        self.pushButton = QPushButton(self.accountTab)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(330, 10, 75, 23))
        self.mainTab.addTab(self.accountTab, "")
        mainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(mainWindow)
        self.statusbar.setObjectName(u"statusbar")
        mainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(mainWindow)

        self.mainTab.setCurrentIndex(2)


        QMetaObject.connectSlotsByName(mainWindow)
    # setupUi

    def retranslateUi(self, mainWindow):
        mainWindow.setWindowTitle(QCoreApplication.translate("mainWindow", u"KiwoomOpenAPI", None))
        self.label_2.setText(QCoreApplication.translate("mainWindow", u"Buy", None))
        self.label_3.setText(QCoreApplication.translate("mainWindow", u"Sell", None))
        self.loadButton.setText(QCoreApplication.translate("mainWindow", u"Load", None))
        self.quantityButton.setText(QCoreApplication.translate("mainWindow", u"Quantity", None))
        self.mainTab.setTabText(self.mainTab.indexOf(self.ledgerTab), QCoreApplication.translate("mainWindow", u"Ledger", None))
        self.PathButton.setText(QCoreApplication.translate("mainWindow", u"Input Path", None))
        self.sellButton.setText(QCoreApplication.translate("mainWindow", u"Sell", None))
        self.buyButton.setText(QCoreApplication.translate("mainWindow", u"Buy", None))
        self.label.setText(QCoreApplication.translate("mainWindow", u"Account No.", None))
        self.textEdit.setPlaceholderText(QCoreApplication.translate("mainWindow", u"Log ...", None))
        self.mainTab.setTabText(self.mainTab.indexOf(self.transactionTtab), QCoreApplication.translate("mainWindow", u"Transaction", None))
        self.pushButton.setText(QCoreApplication.translate("mainWindow", u"Inquiry", None))
        self.mainTab.setTabText(self.mainTab.indexOf(self.accountTab), QCoreApplication.translate("mainWindow", u"AccountInfo", None))
    # retranslateUi

