#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import mpv
from PyQt5.QtCore import Qt, QObject, QTimer, QEvent, QPoint, QTranslator, QThread, QUrl
from PyQt5.QtGui import (QStandardItemModel, QStandardItem, QCursor, QIcon,
                        QFont, QColor, QPalette, QFontDatabase, QFontMetrics,
                        QTextOption)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget,
                            QAbstractItemView, QTableView, QStyledItemDelegate,
                            QVBoxLayout, QHBoxLayout, QDialog, QMessageBox,
                            QLabel, QLineEdit, QTextEdit, QTextBrowser,
                            QPushButton, QTabWidget, QGroupBox, QSpinBox,
                            QSplitter, QDesktopWidget, QFileDialog, QMenu,
                            QAction, QActionGroup, QStyleFactory, QFrame,
                            QFontDialog, QHeaderView, QInputDialog)

from PyQt5.QtWebSockets import QWebSocket
from os import path, mkdir, remove, getenv
import locale
import requests
import time
import json

def hideCursor():
    if mainwindow.isFullScreen():
        app.setOverrideCursor(QCursor(Qt.BlankCursor))

class MpvWidget(QFrame):

    def __init__(self, parent=None):
        super(MpvWidget, self).__init__(parent)
        # Make the frame black, so that the video frame
        # is distinguishable from the rest when no
        # video is loaded yet
        self.setStyleSheet("background-color:black;")
        self.setMouseTracking(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.cursortimer = QTimer(self)
        self.cursortimer.setSingleShot(True)
        self.cursortimer.timeout.connect(hideCursor)

    def contextMenu(self, pos=None):
        contextMenu(pos)

def mpvLogHandler(loglevel, component, message):
    print("[{}] {}: {}".format(loglevel, component, message))


def get_longzhu_url(roomid):
    url = 'https://livestream.longzhu.com/live/GetLivePlayUrl?appId=5001&app_t='+str(int(time.time()))+'&device=2&packageId=1&roomId='+str(roomid)+'&version=4.3.0'
    print(url)
    r = requests.get(url, timeout=5)
	
    json_value = json.loads(r.text)
    print(json.dumps(json_value, indent=4, sort_keys=True))
    for url in json_value['playLines'][0]['urls']:
        if url['ext'] == 'flv':
            return url['securityUrl'], url['resolution'].split('x')

class ListenWebsocket(QThread):
    def __init__(self, roomid, textwidget, parent=None):
        super(ListenWebsocket, self).__init__(parent)

        self.textwidget = textwidget
        self.WS = QWebSocket()

        self.WS.open(QUrl('ws://mbgows.plu.cn:8805/?room_id='+str(roomid)+'&batch=1&group=0&connType=1'))

        self.WS.textMessageReceived.connect(self.on_message)
        self.WS.connected.connect(self.signal_connected_process)
        self.WS.disconnected.connect(self.signal_disconnected_process)
        self.WS.error.connect(self.signal_error_process)
        self.WS.readChannelFinished.connect(self.signal_readChannelFinished_process)

    def on_message(self, message):
        print(message)
        json_msg = json.loads(message)
        print(type(json_msg))
        if type(json_msg) == list:
            msg = json_msg[0]
        else:
            msg = json_msg

        self.textwidget.insertHtml('<font color="Blue">{}</font> <font color="Black">{}</font><br>'.format(msg['msg']['user']['username'], msg['msg']['content']))
        sb = self.textwidget.verticalScrollBar();
        sb.setValue(sb.maximum());

    def signal_connected_process(self):
        print('signal_connected_process')

    def signal_disconnected_process(self):
        print('signal_disconnected_process')

    def signal_error_process(self, error):
        print('signal_error_process')

    def signal_readChannelFinished_process(self):
        print('signal_readChannelFinished_process')


if __name__ == '__main__':
    v = "longzhu 0.1.0"
    
    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, "C")

    mainwindow = QMainWindow()

    #add centralwidget
    centralwidget = QWidget(mainwindow)
    mainwindow.setCentralWidget(centralwidget)

    #setup layout
    mainlayout = QHBoxLayout()
    mainlayout.setContentsMargins(0, 0, 0, 0)
    centralwidget.setLayout(mainlayout)

    #splitter for centralwidget
    mainwindowsplitter = QSplitter(centralwidget)
    mainwindowsplitter.setOrientation(Qt.Horizontal)
    leftwidget = MpvWidget()
    rigthwidget = QTextEdit()
    rigthwidget.setReadOnly(True)
    qfont = QFont('Microsoft YaHei')
    qfont.setPointSize(10)
    rigthwidget.setFont(qfont)
    mainwindowsplitter.addWidget(leftwidget)
    mainwindowsplitter.addWidget(rigthwidget)
    mainwindowsplitter.setStretchFactor(0, 1)
    mainwindowsplitter.setStretchFactor(1, 0)    
    mainlayout.addWidget(mainwindowsplitter)

    mp = mpv.MPV(
        wid=str(int(leftwidget.winId())),
        keep_open="yes",
        idle="yes",
        osc="yes",
        cursor_autohide="no",
        input_cursor="no",
        input_default_bindings="no",
        config="yes",
        ytdl="yes",
        )
    url, resolution = get_longzhu_url(2185)
    mainwindow.resize(int(resolution[0]), int(resolution[1]))
    mp.command("loadfile", url, "replace")
    mp.pause = False

    ws_thread = ListenWebsocket(2185, rigthwidget)

    mainwindow.show()
    app.exec_()