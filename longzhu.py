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
                            QFontDialog, QHeaderView, QInputDialog, QMenuBar)

from PyQt5.QtWebSockets import QWebSocket
from os import path, mkdir, remove, getenv
import locale
import requests
import time
import json
from functools import partial

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

def get_longzhu_url(roomid):
    url = 'https://livestream.longzhu.com/live/GetLivePlayUrl?appId=5001&app_t='+str(int(time.time()))+'&device=2&packageId=1&roomId='+str(roomid)+'&version=4.3.0'
    print(url)
    r = requests.get(url, timeout=5)
	
    json_value = json.loads(r.text)
    print(json.dumps(json_value, indent=4, sort_keys=True))
    if json_value['playLines']:
        for url in json_value['playLines'][0]['urls']:
            if url['ext'] == 'flv':
                return url['securityUrl'], url['resolution'].split('x')

    return None, None

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

def switch_live(roomid, mpv):
    url, resolution = get_longzhu_url(roomid)
    print(url)
    if url and url != 'null':
        mp.command("loadfile", url, "replace")

def setup_live_menu(live_menu, mpv):
    with open('live.json',encoding='utf-8') as f:
        live_list = json.loads(f.read())
        for live in live_list['streamlist']:
            action = live_menu.addAction(live['name'])
            roomid = live['roomid']
            action.triggered.connect(partial(switch_live, roomid, mpv))
            print(action, live['roomid'])

if __name__ == '__main__':
    v = "longzhu 0.1.0"
    
    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, "C")

    #horizontal splitter
    main_splitter = QSplitter(Qt.Horizontal)
    #mpv(left)
    mpvwidget = MpvWidget(main_splitter)
    #right splitter
    right_splitter = QSplitter(Qt.Vertical, main_splitter)
    #menubar
    menubar_widget = QMenuBar(right_splitter)
    live_menu = menubar_widget.addMenu("live")

    #text
    textwidget = QTextEdit(right_splitter)
    textwidget.setReadOnly(True)
    qfont = QFont('Microsoft YaHei')
    qfont.setPointSize(10)
    textwidget.setFont(qfont)

    #fill layout
    main_splitter.addWidget(mpvwidget)
    main_splitter.addWidget(right_splitter)
    main_splitter.setStretchFactor(0, 1)
    main_splitter.setStretchFactor(1, 0)
    right_splitter.addWidget(menubar_widget)
    right_splitter.addWidget(textwidget)
    right_splitter.setStretchFactor(0, 0)
    right_splitter.setStretchFactor(1, 1)

    mp = mpv.MPV(
        wid=str(int(mpvwidget.winId())),
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
    main_splitter.resize(int(resolution[0]), int(resolution[1]))
    #main_splitter.resize(300, 300)
    mp.command("loadfile", url, "replace")
    mp.pause = False

    setup_live_menu(live_menu, mpv)

    ws_thread = ListenWebsocket(2185, textwidget)

    main_splitter.show()
    app.exec_()