#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys
import mpv
from PyQt5.QtCore import (Qt, QObject, QTimer, QEvent, QPoint, QTranslator, QThread, QUrl, QSettings)
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
from PyQt5.QtNetwork import QNetworkCookieJar, QNetworkCookie

from os import path, mkdir, remove, getenv
import locale
import requests
import time
import json
from functools import partial
import time
from pyquery import PyQuery as pq
import pickle
import os

app_name = 'longzhu starcraft'
version = '0.1.0'
app_icon = 'longzhu.ico'
cookie_file = 'cookie'
longzhu_login_url = 'http://login.longzhu.com/enter'
longzhu_main_url = 'http://www.longzhu.com'

class TextFont(QFont):
    def __init__(self):
        super().__init__()
        self.setFamily('Microsoft YaHei')
        self.setPointSize(10)
textfont = TextFont()

#parameters
#LongZhu.roomid
#LoginWindow.is_login
#LoginWindow.level
#LoginWindow.uid
#LoginWindow.username

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

class ChatRoom(QTextEdit):
    def __init__(self, parent = None):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(textfont)

        self.WS = QWebSocket()
        self.WS.textMessageReceived.connect(self.signal_textMessageReceived_process)
        self.WS.connected.connect(self.signal_connected_process)
        self.WS.disconnected.connect(self.signal_disconnected_process)
        self.WS.error.connect(self.signal_error_process)
        self.WS.readChannelFinished.connect(self.signal_readChannelFinished_process)

    def close(self):
        if self.WS:
            self.WS.close()

    def set_roomid(self, roomid):
        self.roomid = roomid
        self.WS.close()

        print(roomid)
        self.WS.open(QUrl('ws://mbgows.plu.cn:8805/?room_id='+str(roomid)+'&batch=1&group=0&connType=1'))
    def signal_textMessageReceived_process(self, message):
        print(message)
        json_msg = json.loads(message)
        print(type(json_msg))
        if type(json_msg) == list:
            msg = json_msg[0]
        else:
            msg = json_msg

        self.insertHtml('<font color="Blue">{}</font> <font color="Black">{}</font><br>'.format(msg['msg']['user']['username'], msg['msg']['content']))
        #auto scroll
        sb = self.verticalScrollBar();
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
    def __init__(self, main_window):
        self.main_window = main_window
        self.roomid = None
        self.chatroom = None
        self.setup_live_menu()
        self.setup_chatroom()

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
        if self.main_window.chatroom:
            self.main_window.chatroom.close()

        roomid = self.get_roomid()
        print('chat room id = {}'.format(roomid))
        print(self.main_window.chatroom)
        if roomid and self.main_window.chatroom:
            print('set chat room id = {}'.format(roomid))
            self.main_window.chatroom.set_roomid(roomid)

    def play(self):
        roomid = self.get_roomid()
        if roomid:        
            url, resolution = self.get_longzhu_url(roomid)
            if url and resolution:
                self.main_window.mp.command("loadfile", url, "replace")
                self.main_window.mp.pause = False        
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
        print('switch to new room id = {}'.format(newroomid))
        self.roomid = newroomid
        if self.play():
            print('switch chat room')
            self.setup_chatroom()

class InputEditor(QTextEdit):
    def __init__(self, login_window, parent = None):
        super().__init__(parent)
        self.textChanged.connect(self.listen_input)
        self.s = requests.Session()
        self.login_window = login_window
        self.setReadOnly(True)

    def listen_input(self):
        if self.toPlainText().endswith('\n'):
            print(self.toPlainText())
            self.send_input()

    def send_input(self):
        url = 'http://mbgo.plu.cn/chatroom/sendmsg?group={}&content={}&color=0xffffff&style=1'.format(self.login_window.main_window.longzhu.roomid, self.toPlainText()[:-1])
        cookies = {}
        for cookie in self.login_window.cookiejar.cookiesForUrl(QUrl(longzhu_login_url)):
            cookies[str(cookie.name(), encoding='ascii')] = str(cookie.value(), encoding='ascii')
        print(url)
        print(cookies)
        self.s.get(url, cookies=cookies)
        self.clear()

    def focusInEvent(self, event):
        print('input editor get focus')
        if not self.login_window.is_login:
            self.login_window.show()

class MainWindow(QSplitter):
    def __init__(self):
        super().__init__()

        #title and icon
        self.setWindowIcon(QIcon(app_icon))
        self.setWindowTitle('{} {}'.format(app_name, version))

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

        #dummy chatroom with roomid = 0
        chatroom = ChatRoom(right_splitter)

        #login button
        login_button = QPushButton("登陆")
        login_button.clicked.connect(self.login_logout_process)
        #user info
        user_info = QLineEdit(right_splitter)
        user_info.setFrame(False)
        user_info.setReadOnly(True)
        #input
        inputwidget = InputEditor(self.login_window, right_splitter)
        inputwidget.setFont(textfont)

        #fill layout
        self.addWidget(mpvwidget)
        self.addWidget(right_splitter)
        self.setStretchFactor(0, 1)
        right_splitter.addWidget(menubar_widget)
        right_splitter.addWidget(chatroom)
        right_splitter.addWidget(login_splitter)
        right_splitter.addWidget(inputwidget)
        right_splitter.setStretchFactor(right_splitter.indexOf(chatroom), 1)
        login_splitter.addWidget(login_button)
        login_splitter.addWidget(user_info)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 0)

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

        self.right_splitter = right_splitter
        self.login_splitter = login_splitter
        self.inputwidget = inputwidget
        self.menubar_widget = menubar_widget
        self.live_menu = live_menu
        self.chatroom = chatroom
        self.login_button = login_button
        self.user_info = user_info
        self.mpvwidget = mpvwidget
        self.mp = mp

    def show_login_window(self):
        self.login_window.show()

    def set_longzhu(self, longzhu):
        self.longzhu = longzhu
        self.login_window.longzhu = longzhu
        self.chatroom.set_roomid(longzhu.roomid)

    def login(self, username, level):
        self.user_info.setText('{} {}级'.format(username, level))
        self.inputwidget.setReadOnly(False)
        self.login_button.setText("登出")

    def logout(self):
        self.user_info.setText('')
        self.inputwidget.setReadOnly(True)
        self.login_button.setText("登陆")        

    def login_logout_process(self):
        if self.login_window.is_login:
            print("logout button click")
            self.login_window.logout()
            self.logout()
        else:
            print("login button click")
            self.login_window.show()

class LoginWindow(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(app_icon))
        self.setWindowTitle('login')
        self.loadFinished.connect(self.process_load_finish)
        self.main_window = None
        self.is_login = False
        cookie_store = self.page().profile().cookieStore()
        print(cookie_store)
        self.cookiejar = QNetworkCookieJar()
        cookie_store.cookieAdded.connect(self.cookie_added)
        self.login_on_startup()

    def set_main_window(self, main_window):
        self.main_window = main_window

    def show(self):
        self.load(QUrl(longzhu_login_url))
        super().show()

    def process_load_finish(self):
        if self.url().host() == 'www.longzhu.com' and self.url().path() == '/':
            print('after login')
            self.page().toHtml(self.login)

    def login(self, data):
        self.login_html = data
        user_menu = pq(data)('#topbar-user-menu')
        self.level = user_menu.find('i.user-lv').attr['class'].split('-')[-1]
        self.uid = user_menu.find('a.report-rbi-click').attr['data-label'].split(':')[-1]
        self.username = user_menu.find('span.topbar-username').text()
        self.is_login = True
        print(self.level)
        print(self.uid)
        print(self.username)
        for cookie in self.cookiejar.cookiesForUrl(QUrl(longzhu_login_url)):
            print('name = {}, value = {}'.format(str(cookie.name(), encoding='ascii'), str(cookie.value(), encoding='ascii')))
        self.main_window.login(self.username, self.level)
        self.load(QUrl(''))
        self.hide()
        self.save_cookie()

    def logout(self):
        self.level = ''
        self.uid = ''
        self.username = ''
        self.is_login = False
        self.cookiejar.setAllCookies([])
        self.page().profile().cookieStore().deleteAllCookies();
        self.delete_cookie()

    def login_on_startup(self):
        if self.load_cookie():
            self.load(QUrl('http://www.longzhu.com'))


    def cookie_added(self, cookie):
        if cookie.name() == b'p1u_id' or cookie.name() == b'PLULOGINSESSID':
            print('name = {}, domain = {}, value = {}, path = {}, date = {}'.format(cookie.name(), cookie.domain(), cookie.value(), cookie.path(), cookie.expirationDate().date()))
        self.cookiejar.setCookiesFromUrl([cookie], QUrl(longzhu_login_url))

    def save_cookie(self):
        with open(cookie_file, 'wb') as f:
            for cookie in self.cookiejar.allCookies():
                f.write(cookie.toRawForm() + b'\n')

    def delete_cookie(self):
        try:
            os.remove(cookie_file)
        except OSError:
            pass

    def load_cookie(self):
        cookies = []
        with open(cookie_file, 'rb') as f:
            for line in f:
                cookie = QNetworkCookie.parseCookies(line)
                self.cookiejar.setCookiesFromUrl(cookie, QUrl(longzhu_login_url))
                self.page().profile().cookieStore().setCookie(cookie[0])
            return True

        return False

if __name__ == '__main__':
    
    app = QApplication(sys.argv)
    locale.setlocale(locale.LC_NUMERIC, "C")

    main_window = MainWindow()

    longzhu = LongZhu(main_window)
    longzhu.play()

    decect_thread = DetectThread(longzhu)
    decect_thread.start()

    main_window.set_longzhu(longzhu)
    main_window.show()

    app.exec_()

    '''
    online https://roomapicdn.longzhu.com/room/RoomAppStatusV2?device=2&packageId=1&roomid=397449&version=4.3.0
    login http://login.longzhu.com/enter
    send msg http://mbgo.plu.cn/chatroom/sendmsg?group=16215&content=666&color=0xffffff&style=1&callback=_callbacks_._1hgl4h8jbjcp6rb
    http://mbgo.plu.cn/chatroom/sendmsg?group=16215&content=%E4%B8%80%E5%8F%B0%E5%9C%A8%E4%BF%AE%E5%90%A7&color=0xffffff&style=1&callback=_callbacks_._uygzjzjbjcqg4b
    '''