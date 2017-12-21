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
import time

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

    def contextMenu(self, pos=None):
        contextMenu(pos)

class ChatRoom():
    def __init__(self, roomid, textwidget, parent=None):

        self.textwidget = textwidget

        self.WS = QWebSocket()
        self.WS.open(QUrl('ws://mbgows.plu.cn:8805/?room_id='+str(roomid)+'&batch=1&group=0&connType=1'))
        self.WS.textMessageReceived.connect(self.signal_textMessageReceived_process)
        self.WS.connected.connect(self.signal_connected_process)
        self.WS.disconnected.connect(self.signal_disconnected_process)
        self.WS.error.connect(self.signal_error_process)
        self.WS.readChannelFinished.connect(self.signal_readChannelFinished_process)

    def close(self):
        if self.WS:
            self.WS.close()

    def signal_textMessageReceived_process(self, message):
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


class DetectThread(QThread):
    def __init__(self, longzhu):
        super().__init__()
        self.longzhu = longzhu
        self.stop = False

    def run(self):
        while not self.stop:
            self.detect()
            time.sleep(30)

    def detect(self):
        live_list = self.longzhu.live_list
        for i, live in enumerate(live_list['streamlist']):
            url = 'https://roomapicdn.longzhu.com/room/RoomAppStatusV2?device=2&packageId=1&roomid='+str(live['roomid'])+'&version=4.3.0'
            r = requests.get(url, timeout=5)
            json_value = json.loads(r.text)
            print(json_value['IsBroadcasting'])
            if json_value['IsBroadcasting']:
                self.longzhu.actions[i].setIcon(QIcon('online.png'))
            else:
                self.longzhu.actions[i].setIcon(QIcon('offline.png'))

class LongZhu():
    def __init__(self, live_menu, main_splitter, mpvwidget, textwidget, mp, roomid):
        self.main_splitter = main_splitter
        self.live_menu = live_menu
        self.mpvwidget = mpvwidget
        self.textwidget = textwidget
        self.mp = mp
        self.roomid = roomid
        self.chatroom = None

    def get_longzhu_url(self, roomid):
        url = 'https://livestream.longzhu.com/live/GetLivePlayUrl?appId=5001&app_t='+str(int(time.time()))+'&device=2&packageId=1&roomId='+str(roomid)+'&version=4.3.0'
        print(url)
        r = requests.get(url, timeout=5)
        
        json_value = json.loads(r.text)
        print(json.dumps(json_value, indent=4, sort_keys=True))
        if json_value['playLines']:
            for url in reversed(json_value['playLines'][0]['urls']):
                if url['ext'] == 'flv':
                    return url['securityUrl'], url['resolution'].split('x')

        return None, None

    def setup_live_menu(self):
        with open('live.json',encoding='utf-8') as f:
            live_list = json.loads(f.read())
            self.live_list = live_list
            print(type(self.live_list))
            self.actions = []
            for live in live_list['streamlist']:
                action = self.live_menu.addAction(live['name'])
                self.actions = [action] + self.actions
                roomid = live['roomid']
                action.triggered.connect(partial(self.switch_live, roomid))

    def setup_chatroom(self):
        if self.chatroom:
            self.chatroom.close()

        self.chatroom = ChatRoom(self.roomid, self.textwidget)

    def play(self):
        url, resolution = self.get_longzhu_url(self.roomid)
        if url and resolution:
            self.mp.command("loadfile", url, "replace")
            self.mp.pause = False        
            self.main_splitter.resize(int(resolution[0]), int(resolution[1]))
            return True

        return False

    def switch_live(self, newroomid):
        self.roomid = newroomid
        if longzhu.play():
            longzhu.setup_chatroom()

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

    longzhu = LongZhu(live_menu, main_splitter, mpvwidget, textwidget, mp, 2185)
    longzhu.setup_live_menu()
    longzhu.setup_chatroom()
    longzhu.play()

    decect_thread = DetectThread(longzhu)
    decect_thread.start()

    main_splitter.show()
    app.exec_()

    '''
    status https://roomapicdn.longzhu.com/room/RoomAppStatusV2?device=2&packageId=1&roomid=397449&version=4.3.0
    '''