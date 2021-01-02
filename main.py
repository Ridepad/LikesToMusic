# -*- coding: utf-8 -*-

TODO = '''
replace in grid vs creating new

dialog window if no playlist

dublicates in music

checkbox with text
or
checkbox -> icons
(likes = likesicons, other trashcan)

dl logo

sort_new disabled if empty

update vidname if changed
'''

from PyQt5 import QtCore, QtGui, QtWidgets
import os
import sys
import time
import yt_api
import pickle
import requests
import threading
import webbrowser
import urllib.request

if not os.path.exists('cached'):
    os.makedirs('cached')

for file_name in ('Errors', 'Ignored', 'Likes', 'Music'):
    open(f'_{file_name}.txt', 'a+').close()

NAMELEN = 150
MOUSECLICK = QtCore.QEvent.MouseButtonPress
LIKES_PLS = 'LL'
open('PUT_PLAYLIST_ID_INSIDE.txt', 'a+').close()
with open('PUT_PLAYLIST_ID_INSIDE.txt','r') as f:
    MUSIC_PLS = f.read()

class MainWindow(QtWidgets.QMainWindow):
    if 1: #hide all class variables
        THUMBNAIL_W = 320
        THUMBNAIL_H = 180
        TITLE_H = 23
        sizeChkBx = QtCore.QSize(16, TITLE_H)
        sizeTitle = QtCore.QSize(300, TITLE_H)
        sizeThumbnail = QtCore.QSize(THUMBNAIL_W, THUMBNAIL_H)
        fontMsgBox = QtGui.QFont("Lucida Console")
        fontTitle = QtGui.QFont("Calibri", 15)

        NewIDs = []
        LikesIDs = []
        MusicIDs = []
        IgnoredIDs = []
        ErrorsIDs = set()
        
        actionsList = [
            'Reconnect API',
            '',
            'Fetch Music',
            'Fetch Likes',
            '',
            'Sort New',
            '',
            'Delete From Music',
            'Delete From Ignored',
            '',
            'Exit App',
        ]
        
        menuChangeDict = {
            'enable' : 0,
            'actionNames' : []
        }
        MusicContents = []
        API_state = 'YouTube API IS UNAVAILABLE!'
        
        SPACING = 2
        menubarH = tabbarH = 21
        statusbarH = 29
        scrollbarW = 17
        thumbnails_dict = {}
        TABS = {}
        checkedBoxes = []
        uncheckedBoxes = []
    
    def __init__(self):
        super().__init__()
        threading.Thread(target=self.connect_yt_api).start()
        
        self.setup_logo()
        self.setup_size()
        self.setWindowTitle("Likes to Music")
        
        self.centralwidget = QtWidgets.QWidget(self)
        self.setCentralWidget(self.centralwidget)
        
        self.DL_daemon = CombineDicts()
        self.DL_daemon.start()
        
        self.setup_menuBar()
        self.setup_statusBar()
        self.setup_tabWidget()
        
    def setup_size(self):
        display = QtWidgets.QApplication.desktop().screenGeometry()
        
        _W = self.THUMBNAIL_W + self.SPACING
        self.MAX_COLLUMNS = (display.width() - self.scrollbarW - 4) // _W
        self.width = self.MAX_COLLUMNS * _W - self.SPACING + self.scrollbarW + 2
        
        usable_height = display.height() - self.menubarH - self.tabbarH - self.statusbarH - 30
        vid_height = self.THUMBNAIL_H + self.TITLE_H + self.SPACING*2
        max_rows = usable_height // vid_height
        self.height = max_rows * (self.THUMBNAIL_H + self.TITLE_H + self.SPACING * 2) + 2
        
        self.setFixedSize(
            4 + self.width, 
            4 + self.statusbarH + self.height + self.tabbarH + self.menubarH)

    def setup_logo(self):
        try:
            open('logo.ico', 'rb').close()
        except:
            url = 'https://raw.githubusercontent.com/Ridepad/LikesToMusic/master/logo.ico'
            icon = urllib.request.urlopen(url).read()
            with open('logo.ico', 'wb') as f:
                f.write(icon)
        self.setWindowIcon(QtGui.QIcon('logo.ico'))
    
    def setup_menuBar(self):
        self.menubar = QtWidgets.QMenuBar(self) 
        self.menu_Start = QtWidgets.QMenu(self.menubar, title="Menu")
        self.setMenuBar(self.menubar)
        for actionName in self.actionsList:
            if not actionName:
                self.menu_Start.addSeparator()
            else:
                action = QtWidgets.QAction(text=actionName)
                actionName = actionName.replace(" ","_")
                actionFunc = getattr(self, actionName, self.fetch_playlist)
                action.triggered.connect(actionFunc)
                setattr(self, f'action_{actionName}',  action)
                self.menu_Start.addAction(action)
        self.action_Delete_From_Music.setEnabled(False)
        self.menubar.addAction(self.menu_Start.menuAction())
    
    def setup_statusBar(self):
        self.statusbar = QtWidgets.QStatusBar(
            font=self.fontTitle,
            sizeGripEnabled=False,
        )
        self.setStatusBar(self.statusbar)
    
    def prefill_tabs(self):
        tab_geometry = QtCore.QRect(0, 0, self.width, self.height)
        for tabName in ('New', 'Music', 'Likes', 'Ignored'):
            _Tab = QtWidgets.QWidget()
            self.tabWidget.addTab(_Tab, tabName)
            _Tab_scrollArea = QtWidgets.QScrollArea(_Tab)
            _Tab_scrollArea.setGeometry(tab_geometry)

            self.TABS[tabName] = {
                'tab_scrollArea': _Tab_scrollArea,
                'PLS': {},
                'CBs': [],
                'IDs': []
            }
        
        for tabName in  ('Music', 'Likes', 'Ignored'):
            with open(f'_{tabName}.txt', 'r') as f:
                self.TABS[tabName]['IDs'] = f.read().splitlines()
            self.add_Tab(tabName)
        
        if self.TABS['Likes']['IDs']:
            self.fetch_playlist('New')
    
    def setup_tabWidget(self):
        self.tabWidget = QtWidgets.QTabWidget(self.centralwidget)
        tabWidget_W = self.width + 6
        tabWidget_H = self.height + self.tabbarH + 5
        tabWidget_geometry = QtCore.QRect(0, 0, tabWidget_W, tabWidget_H)
        self.tabWidget.setGeometry(tabWidget_geometry)
        
        self.prefill_tabs()

        self.tabWidget.currentChanged.connect(self.tabChanged)

    #rewrite checkbox=title
    def add_Tab(self, tabName):
        def add_Vid(row, col, vidID):
            _Thumbnail = QtWidgets.QLabel(
                objectName=vidID,
                minimumSize=self.sizeThumbnail,
                maximumSize=self.sizeThumbnail)
            _Thumbnail.installEventFilter(self)
            _scrollAreaContents_Grid.addWidget(_Thumbnail, row*2, col*2, 1, 2)
            
            _Title = QtWidgets.QLabel(
                minimumSize=self.sizeTitle,
                maximumSize=self.sizeTitle,
                font=self.fontTitle)
            _scrollAreaContents_Grid.addWidget(_Title, row*2+1, col*2, 1, 1)
            
            _checkBox = QtWidgets.QCheckBox(
                toolTip="Uncheck to remove",
                toolTipDuration=2000,
                checked=True)
            _checkboxes.append(_checkBox)
            _scrollAreaContents_Grid.addWidget(_checkBox, row*2+1, col*2+1, 1, 1)
            
            return _Thumbnail, _Title
        
        def add_row(cols):
            for col in range(cols):
                vidID = tmpIDs[row * self.MAX_COLLUMNS + col]
                thumbnails_dl_q[vidID] = add_Vid(row, col, vidID)
        
        _Tab_scrollArea = self.TABS[tabName]['tab_scrollArea']
        tmpIDs = self.TABS[tabName]['IDs']
        _checkboxes = self.TABS[tabName]['CBs']
        _checkboxes.clear()
        _scrollAreaContents = QtWidgets.QWidget()
        _scrollAreaContents_Grid = QtWidgets.QGridLayout(_scrollAreaContents)
        _scrollAreaContents_Grid.setSpacing(self.SPACING)
        _scrollAreaContents_Grid.setContentsMargins(0, 0, 0, 0)
        for x in range(4):
            _scrollAreaContents_Grid.setColumnStretch(x*2, 1)
        
        thumbnails_dl_q = {}
        rows, col_last_row = divmod(len(tmpIDs), self.MAX_COLLUMNS)
        row = -1
        for row in range(rows):
            add_row(self.MAX_COLLUMNS)
        row += 1
        add_row(col_last_row)
        _Tab_scrollArea.setWidget(_scrollAreaContents)
       
        self.DL_daemon.update_d_q(thumbnails_dl_q)
        
    def fetch_playlist(self, tabName=''):
        if not tabName:
            try:
                tabName = self.sender().text().split()[1]
            except AttributeError:
                tmp = self.tabWidget
                i = tmp.currentIndex()
                tabName = tmp.tabText(i)
        
        if tabName == 'New':
            tmpIDs = list(
                set(self.TABS['Likes']['IDs']) - 
                set(self.TABS['Music']['IDs']) - 
                set(self.TABS['Ignored']['IDs']))
            if tmpIDs == self.TABS['New'].get('IDs'):
                return
            self.TABS['New']['IDs'] = tmpIDs

        elif tabName in ('Music', 'Likes'):
            self.statusbar.showMessage(f'Fetching {tabName} Playlist...')
            QtWidgets.QApplication.processEvents()
            
            if tabName == 'Music':
                tmpContents = self.youtube.playlistContents(MUSIC_PLS)
                self.action_Delete_From_Music.setEnabled(True)
            elif tabName == 'Likes':
                tmpContents = self.youtube.playlistContents(LIKES_PLS)

            self.TABS[tabName]['PLS'] = tmpContents
            
            tmpIDs = list(tmpContents)
            if tmpIDs == self.TABS[tabName]['IDs']:
                return self.tabChanged()
            self.TABS[tabName]['IDs'] = tmpIDs
            with open(f'_{tabName}.txt', 'w') as f:
                f.write('\n'.join(tmpIDs))
        
        elif tabName == 'Ignored':
            with open(f'_Ignored.txt', 'w') as f:
                f.write('\n'.join(self.TABS['Ignored']['IDs']))
        self.add_Tab(tabName)
        self.tabChanged()
        if tabName != 'New' and self.TABS['Likes']['IDs']:
            self.fetch_playlist('New')
    
    def connect_yt_api(self):
        self.youtube = yt_api.YT()
        auth = bool(self.youtube.youtube)
        self.API_state = ('YouTube API IS UNAVAILABLE!', 'YouTube API Connected!')[auth]
        if not self.youtube.youtube:
            self.menuChangeDict['enable'] = 0
            self.menuChangeDict['actionNames'] = (
                'Fetch Music',
                'Fetch Likes',
                'Sort New',
            )
            self.menuChange()
        
    def Reconnect_API(self):
        self.youtube.youtube = self.youtube.main_auth_full()
        auth = self.youtube.auth_valid()
        self.API_state = ('YouTube API IS UNAVAILABLE!', 'YouTube API Connected!')[auth]
        self.menuChangeDict['enable'] = auth
        self.menuChangeDict['actionNames'] = (
            'Fetch Music',
            'Fetch Likes',
            'Sort New',
        )
        self.menuChange()
        self.tabChanged()

    def eventFilter(self, object, event):
        # Left mouse click opens vid url in browser
        if event.type() == MOUSECLICK and event.button() == 1:
            webbrowser.open(f'https://youtu.be/{object.objectName()}')
        return False
    
    def tabChanged(self):
        #self.tabWidget.setCurrentIndex(1)
        tabName = self.tabWidget.tabText(self.tabWidget.currentIndex())
        videosCount = len(self.TABS[tabName]['IDs'])
        msg = f'{videosCount:>4} videos  |  {self.API_state}'
        self.statusbar.showMessage(msg)
    
    def fetch_2(self, tabName=''):
        if not tabName:
            try:
                tabName = self.sender().text().split()[1]
            except AttributeError:
                tmp = self.tabWidget
                i = tmp.currentIndex()
                tabName = tmp.tabText(i)
        
        _old_IDs = self.TABS[tabName]['IDs']
        if tabName == 'New':
            tmpIDs = list(set(self.LikesIDs) - set(self.MusicIDs) - set(self.IgnoredIDs))
        elif self.update and tabName in ('Music', 'Likes'):
            self.statusbar.showMessage(f'Fetching {tabName} Playlist...')
            QtWidgets.QApplication.processEvents()
            
            tmpContents = self.youtube.playlistContents(tabName)
            if tabName == 'Music':
                self.MusicContents = tmpContents
                self.action_Delete_From_Music.setEnabled(True)
            
            tmpIDs = list(tmpContents)         
            with open(f'_{tabName}.txt', 'w') as f:
                f.write('\n'.join(tmpIDs))   
        else:
            with open(f'_{tabName}.txt', 'r') as f:
                tmpIDs = f.read().splitlines()
        if tmpIDs == _old_IDs:
            return
        if tabName in ('Music', 'Likes'):
            diffirence = set(_old_IDs) - set(tmpIDs)
            if diffirence:
                with open(f'_{tabName}_Deleted.txt', 'a+') as f:
                    f.write('\n'.join(diffirence))
                    f.write('\n')
        self.TABS[tabName]['IDs'] = tmpIDs
        self.add_Tab(tabName)
        self.tabChanged()
        if tabName != 'New' and self.LikesIDs and self.MusicIDs:
            self.fetch_playlist('New')
        
    def menuChange(self):
        for actionName in self.menuChangeDict['actionNames']:
            if actionName == 'Fetch Music' and not self.TABS['Music']['PLS']:
                continue
            enabled = self.menuChangeDict['enable']
            actionName = actionName.replace(" ","_")
            actionName = f'action_{actionName}'
            getattr(self, actionName).setEnabled(enabled)
        
    def get_chkbox_state(self, tabName):
        self.checkedBoxes.clear()
        self.uncheckedBoxes.clear()
        Q = (self.uncheckedBoxes, self.checkedBoxes)
        T = self.TABS[tabName]
        for CB, vidID in zip(T['CBs'], T['IDs']):
            Q[CB.isChecked()].append(vidID)

    def MusicApiCooldown(self):
        self.tabWidget.setCurrentIndex(1)
        QtWidgets.QApplication.processEvents()
        with open('_Music.txt', 'w') as f:
            self.TABS['New']['IDs']
            f.write('\n'.join(self.TABS['Music']['IDs']))
        self.update = 0
        self.fetch_playlist('Music')
        self.update = 1
        
        self.menuChangeDict['actionNames'] = (
            'Fetch Music',
            'Sort New',
        )
        self.menuChangeDict['enable'] = 0
        self.menuChange()
        self.menuChangeDict['enable'] = 1
        QtCore.QTimer.singleShot(30000, self.menuChange)
        
    def Sort_New(self):
        if not self.TABS['New']['IDs']:
            return
        
        self.get_chkbox_state('New')
        if not self.checkedBoxes:
            self.TABS['Ignored']['IDs'] = self.uncheckedBoxes + self.TABS['Ignored']['IDs']
            self.fetch_playlist('Ignored')
            return
        
        global current_insert
        insert_titles = [(THUMBNAILS[ID][0], ID) for ID in self.checkedBoxes]
        current_insert = {title:'Pending' for title, _ in insert_titles}
        self.gen_titles = iter(insert_titles)

        self.Sort_New_MessageBox = QtWidgets.QMessageBox(
            windowTitle='Sort New',
            detailedText=make_details(),
            font=self.fontMsgBox,
        )
        self.Sort_New_MessageBox.setStyleSheet("QLabel {min-width: 400px;}")
        start_button = self.Sort_New_MessageBox.addButton('Start', QtWidgets.QMessageBox.ActionRole)
        start_button.clicked.disconnect()
        start_button.clicked.connect(self.start_insert)
        self.Sort_New_MessageBox.addButton(QtWidgets.QMessageBox.Cancel)

        self.Sort_New_MessageBox.exec_()
        
    def start_insert(self):
        self.sender().setEnabled(False)
        self.on_finished()
        
    def on_finished(self):
        try:
            self.next_insert(next(self.gen_titles))
        except StopIteration:
            self.update_details(f'{make_details()}\nFinished!')
            self.TABS['Music']['IDs'] = self.checkedBoxes + self.TABS['Music']['IDs']
            with open(f'_Music.txt', 'w') as f:
                f.write('\n'.join(self.TABS['Music']['IDs']))
            self.add_Tab('Music')
            self.TABS['Ignored']['IDs'] = self.uncheckedBoxes + self.TABS['Ignored']['IDs']
            self.fetch_playlist('Ignored')
            self.checkedBoxes.clear()
            self.uncheckedBoxes.clear()
        
    def next_insert(self, vid):
        self.thread = UpdateStatus(vid)
        self.thread.finished.connect(self.on_finished)
        self.thread.updated.connect(self.update_details)
        self.thread.start()
        
    def update_details(self, text):
        self.Sort_New_MessageBox.setDetailedText(text)
        
    def Delete_From_Music(self):
        self.get_chkbox_state('Music')
        if self.uncheckedBoxes:
            ids = self.TABS['Music']['IDs']
            mus_pls = self.TABS['Music']['PLS']
            for vidID in self.uncheckedBoxes:
                ids.remove(vidID)
                vid = mus_pls[vidID]
                vidTitle = vid['vidTitle']
                #rewrite
                self.statusbar.showMessage(f'Deleting from Music: {vidTitle}')
                QtWidgets.QApplication.processEvents()
                vidIDPls = vid['vidIDPls'][0]
                self.youtube.del_video(vidIDPls)
            with open('_Music.txt', 'w') as f:
                f.write('\n'.join(ids))
            self.add_Tab('Music')
            self.fetch_playlist('New')
        
    def Delete_From_Ignored(self):
        self.get_chkbox_state('Ignored')
        if self.uncheckedBoxes:
            ids = self.TABS['Ignored']['IDs']
            for vidID in self.uncheckedBoxes:
                ids.remove(vidID)
            self.fetch_playlist('Ignored')
        
    def Exit_App(self):
        sys.exit()


class CombineDicts(threading.Thread):
    lst = []
        
    def __init__(self):
        super().__init__()
        self.lock = threading.RLock()
        self.daemon = True
        
    def update_d_q(self, another_dict):
        with self.lock:
            self.lst.append(another_dict)
        
    def run(self):
        while 1:
            if self.lst:
                lst_old = list(self.lst)
                with self.lock:
                    master_dict = {}
                    for D in self.lst:
                        for vidID, linked_objects in D.items():
                            master_dict.setdefault(vidID, set()).add(linked_objects)
                    t = DL_Q(master_dict)
                    t.start()
                    master_dict = {}
                    t.join()
                if self.lst == lst_old:
                    self.lst.clear()
            time.sleep(1)

    
class DL_Q(threading.Thread):
    def __init__(self, D):
        super().__init__()
        self.D = D
        
    def fetch_thumbnail(self, vidID, linked_objects):
        def get_thumbnail():
            if vidID in THUMBNAILS:
                return THUMBNAILS[vidID]
            try:
                with open(f'cached/{vidID}', 'rb') as f:
                    f = f.read()
                return f[:NAMELEN].decode(), f[NAMELEN:]
            except FileNotFoundError:
                self.c += 1
                _thumbnail = main_window.youtube.get_thumbnail(vidID)
                _title = main_window.youtube.save_thumbnail_w_name(_thumbnail, vidID)
                return _title, _thumbnail
        
        vidTitle, vidThumbnail = get_thumbnail()
        
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(vidThumbnail)
        THUMBNAILS[vidID] = (vidTitle, vidThumbnail)
            
        for thumbnail, title in linked_objects:
            try:
                title.setText(vidTitle)
                thumbnail.setPixmap(pixmap)
            except RuntimeError:
                pass
                #print(title, 'HAVE BEEN DELETED')
        
    def run(self):
        self.c = 0
        self.threads_ = []
        for vidID, linked_objects in self.D.items():
            t = threading.Thread(target=self.fetch_thumbnail, args=(vidID, linked_objects, ))
            self.threads_.append(t)
            t.start()
            if self.c > 100:
                self.c = 0
                for t in self.threads_:
                    t.join()
                time.sleep(1)
                self.threads_ = []
                print('Done')


#rewrite this
current_insert = {}

def make_details():
    return '\n'.join(f'{status:<10}| {title[:40]}' for title, status in current_insert.items())

class UpdateStatus(QtCore.QThread):
    updated = QtCore.pyqtSignal(str)
        
    def __init__(self, vid):
        super().__init__()
        self.vidTitle, self.vidID = vid
        
    def setStatus(self, status):
        current_insert[self.vidTitle] = status
        self.updated.emit(make_details())
        
    def run(self):
        self.setStatus('Inserting')
        main_window.youtube.pls_insert(self.vidID, MUSIC_PLS)
        self.setStatus('Done')

try:
    with open('thumbnails_cache.pickle', 'rb') as fl:
        THUMBNAILS = pickle.load(fl)
except FileNotFoundError:
    THUMBNAILS = {}

THUMBNAILS_OLD = dict(THUMBNAILS)
app = QtWidgets.QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
app.exec_()

if THUMBNAILS_OLD != THUMBNAILS:
    with open('thumbnails_cache.pickle', 'wb') as fl:
        pickle.dump(THUMBNAILS, fl)
