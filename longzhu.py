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
from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineView
from PyQt5.QtNetwork import QNetworkCookieJar

from os import path, mkdir, remove, getenv
import locale
import requests
import time
import json
from functools import partial
import time
from pyquery import PyQuery as pq

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
    def __init__(self, roomid, textwidget):
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
            #print(json_value['IsBroadcasting'])
            if json_value['IsBroadcasting']:
                self.longzhu.actions[i].setIcon(QIcon('online.png'))
            else:
                self.longzhu.actions[i].setIcon(QIcon('offline.png'))

class LongZhu():
    def __init__(self, main_window, mp):
        self.main_window = main_window
        self.mp = mp
        self.roomid = None
        self.chatroom = None

    def get_longzhu_url(self, roomid):
        url = 'https://livestream.longzhu.com/live/GetLivePlayUrl?appId=5001&app_t='+str(int(time.time()))+'&device=2&packageId=1&roomId='+str(roomid)+'&version=4.3.0'
        #print(url)
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
                action = self.main_window.live_menu.addAction(live['name'])
                self.actions = self.actions + [action]
                action.triggered.connect(partial(self.switch_live, live['roomid']))

    def setup_chatroom(self):
        if self.chatroom:
            self.chatroom.close()

        roomid = self.get_roomid()
        if roomid:
            self.chatroom = ChatRoom(roomid, self.main_window.textwidget)

    def play(self):
        roomid = self.get_roomid()
        if roomid:        
            url, resolution = self.get_longzhu_url(roomid)
            if url and resolution:
                self.mp.command("loadfile", url, "replace")
                self.mp.pause = False        
                self.main_window.resize(int(resolution[0]), int(resolution[1]))
                return True

        return False

    def get_roomid(self):
        if self.roomid:
            return self.roomid
        elif self.live_list and self.live_list['streamlist']:
            self.roomid = self.live_list['streamlist'][0]['roomid']
            return self.roomid

        return None

    def switch_live(self, newroomid):
        self.roomid = newroomid
        if self.play():
            self.setup_chatroom()

class InputEditor(QTextEdit):
    def __init__(self, login_window, parent = None):
        super().__init__(parent)
        self.textChanged.connect(self.listen_input)
        self.s = requests.Session()
        self.login_window = login_window

    def listen_input(self):
        if self.toPlainText().endswith('\n'):
            print(self.toPlainText())
            self.send_input()
            

    def send_input(self):
        url = 'http://mbgo.plu.cn/chatroom/sendmsg?group={}&content={}&color=0xffffff&style=1'.format(self.login_window.main_window.longzhu.roomid, self.toPlainText()[:-1])
        cookies = {}
        for cookie in self.login_window.cookiejar.cookiesForUrl(QUrl('http://login.longzhu.com/enter')):
            cookies[str(cookie.name(), encoding='ascii')] = str(cookie.value(), encoding='ascii')
        print(url)
        print(cookies)
        self.s.get(url, cookies=cookies)
        self.clear()

class MainWindow(QSplitter):
    def __init__(self):
        super().__init__()

        #longzhu obj
        self.longzhu = None

        #add login window
        self.login_window = LoginWindow()
        self.login_window.set_main_window(self)

        #horizontal splitter
        self.setOrientation(Qt.Horizontal)

        #mpv(left)
        mpvwidget = MpvWidget(self)
        #right splitter
        right_splitter = QSplitter(Qt.Vertical, self)
        #login splitter
        login_splitter = QSplitter(Qt.Horizontal, right_splitter)
        #menubar
        menubar_widget = QMenuBar(right_splitter)
        live_menu = menubar_widget.addMenu("live")

        #text
        textwidget = QTextEdit(right_splitter)
        textwidget.setReadOnly(True)
        qfont = QFont('Microsoft YaHei')
        qfont.setPointSize(10)
        textwidget.setFont(qfont)

        #login button
        login_button = QPushButton("登陆")
        login_button.clicked.connect(self.login_window.show)
        #user info
        user_info = QLineEdit(right_splitter)
        user_info.setFrame(False)
        user_info.setReadOnly(True)
        #input
        inputwidget = InputEditor(self.login_window, right_splitter)
        inputwidget.setFont(qfont)

        #fill layout
        self.addWidget(mpvwidget)
        self.addWidget(right_splitter)
        self.setStretchFactor(0, 1)
        right_splitter.addWidget(menubar_widget)
        right_splitter.addWidget(textwidget)
        right_splitter.addWidget(login_splitter)
        right_splitter.addWidget(inputwidget)
        right_splitter.setStretchFactor(right_splitter.indexOf(textwidget), 1)
        login_splitter.addWidget(login_button)
        login_splitter.addWidget(user_info)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 0)

        self.right_splitter = right_splitter
        self.login_splitter = login_splitter
        self.menubar_widget = menubar_widget
        self.live_menu = live_menu
        self.textwidget = textwidget
        self.login_button = login_button
        self.user_info = user_info
        self.mpvwidget = mpvwidget

    def show_login_window(self):
        self.login_window.show()

    def set_longzhu(self, longzhu):
        self.longzhu = longzhu

class LoginWindow(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.loadFinished.connect(self.process_load_finish)
        self.main_window = None
        self.is_login = False
        cookie_store = self.page().profile().cookieStore()
        print(cookie_store)
        cookie_store.cookieAdded.connect(self.cookie_added);
        self.cookiejar = QNetworkCookieJar()

    def set_main_window(self, main_window):
        self.main_window = main_window

    def show(self):
        self.load(QUrl('http://login.longzhu.com/enter'))
        super().show()

    def process_load_finish(self):
        if self.url().host() == 'www.longzhu.com' and self.url().path() == '/':
            print('after login')
            self.page().toHtml(self.tohtml_cb)

    def tohtml_cb(self, data):
        self.login_html = data
        user_menu = pq(data)('#topbar-user-menu')
        self.level = user_menu.find('i.user-lv').attr['class'].split('-')[-1]
        self.uid = user_menu.find('a.report-rbi-click').attr['data-label'].split(':')[-1]
        self.username = user_menu.find('span.topbar-username').text()
        self.is_login = True
        print(self.level)
        print(self.uid)
        print(self.username)
        self.main_window.user_info.setText('{} {}级'.format(self.username, self.level))
        for cookie in self.cookiejar.cookiesForUrl(QUrl('http://login.longzhu.com/enter')):
            print('name = {}, value = {}'.format(str(cookie.name(), encoding='ascii'), str(cookie.value(), encoding='ascii')))
        self.hide()

    def cookie_added(self, cookie):
        if cookie.name() == b'p1u_id' or cookie.name() == b'PLULOGINSESSID':
            print('name = {}, domain = {}, value = {}, path = {}, date = {}'.format(cookie.name(), cookie.domain(), cookie.value(), cookie.path(), cookie.expirationDate().date()))
            self.cookiejar.setCookiesFromUrl([cookie], QUrl('http://login.longzhu.com/enter'))

if __name__ == '__main__':
    v = "longzhu 0.1.0"
    
    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, "C")

    main_window = MainWindow()

    mp = mpv.MPV(
        wid=str(int(main_window.mpvwidget.winId())),
        keep_open="yes",
        idle="yes",
        osc="yes",
        cursor_autohide="no",
        input_cursor="no",
        input_default_bindings="no",
        config="yes",
        ytdl="yes",
        )

    longzhu = LongZhu(main_window, mp)
    main_window.set_longzhu(longzhu)
    longzhu.setup_live_menu()
    longzhu.setup_chatroom()
    longzhu.play()


    decect_thread = DetectThread(longzhu)
    decect_thread.start()

    main_window.show()
    app.exec_()

    '''
    online https://roomapicdn.longzhu.com/room/RoomAppStatusV2?device=2&packageId=1&roomid=397449&version=4.3.0
    login http://login.longzhu.com/enter
    send msg http://mbgo.plu.cn/chatroom/sendmsg?group=16215&content=666&color=0xffffff&style=1&callback=_callbacks_._1hgl4h8jbjcp6rb
    http://mbgo.plu.cn/chatroom/sendmsg?group=16215&content=%E4%B8%80%E5%8F%B0%E5%9C%A8%E4%BF%AE%E5%90%A7&color=0xffffff&style=1&callback=_callbacks_._uygzjzjbjcqg4b
    '''