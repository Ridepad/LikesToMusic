# -*- coding: utf-8 -*-

TODO = '''
multiprocessing

dublicates in music

reuse likes

check if removed in music

checkbox -> icons
(likes = likesicons
other trashcan)
'''

from PyQt5 import QtCore, QtGui, QtWidgets
import os
import sys
import time
import yt_api
import pickle
import threading
import webbrowser

if not os.path.exists('cached'):
    os.makedirs('cached')

for file_name in ('Errors', 'Ignored', 'Likes', 'Music', 'Likes_Deleted'):
    file_name = f'_{file_name}.txt'
    try:
        open(file_name, 'r').close()
    except:
        open(file_name, 'w').close()

current_insert = dict()

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
        st = main_window.youtube.pls_insert(self.vidID)
        self.setStatus('Done')


class FetchThumbnail(QtCore.QThread):
    #thumbnail_loaded = QtCore.pyqtSignal(list)
    NameLen = 150
    def __init__(self, vid):
        super().__init__()
        self.vidID, self.THUMBNAIL, self.TITLE = vid
        
    def run(self):
        vidTitle, vidThumbnail = self.get_thumbnail()
        if not vidTitle:
            vidTitle, vidThumbnail = self.vidID, False
        self.TITLE.setText(vidTitle)
        if vidThumbnail:
            pixmap = QtGui.QPixmap()
            pixmap.loadFromData(vidThumbnail)
            self.THUMBNAIL.setPixmap(pixmap)
            THUMBNAILS[self.vidID] = (vidTitle, vidThumbnail)
        else:
            self.THUMBNAIL.setPixmap(main_window.defaultPixmap)
        #self._emit.append(vidTitle)
        #self._emit.append(vidThumbnail)
        #self.thumbnail_loaded.emit(self._emit)
    
    def get_thumbnail(self):
        cached_thumbnail = THUMBNAILS.get(self.vidID)
        if cached_thumbnail:
            return cached_thumbnail
        try:
            with open(f'cached/{self.vidID}', 'rb') as f:
                f = f.read()
            return f[:self.NameLen].decode(), f[self.NameLen:]
        except FileNotFoundError:
            #if no cache, wait for yt api and download thumbnail
            while 1:
                try:
                    return main_window.youtube.get_thumbnail(self.vidID, save=1)
                except AttributeError:
                    pass


class MainWindow(QtWidgets.QMainWindow):
    if 1:   #convenience to hide all class variables
        THUMBNAIL_W = 320
        THUMBNAIL_H = 180
        TITLE_H = 23
        sizeDel = QtCore.QSize(40, TITLE_H)
        sizeChkBx = QtCore.QSize(16, TITLE_H)
        sizeTitle = QtCore.QSize(300, TITLE_H)
        sizeThumbnail = QtCore.QSize(THUMBNAIL_W, THUMBNAIL_H)
        fontMsgBox = QtGui.QFont("Lucida Console")
        fontTitle = QtGui.QFont("Calibri", 15)
        #fontDel = QtGui.QFont("Segoe UI Black", 14, QtGui.QFont.Bold)

        update = 0
        NewIDs = []
        LikesIDs = []
        MusicIDs = []
        ErrorsIDs = set()
        IgnoredIDs = []
        
        actionsList = [
            'Reconnect API',
            '',
            'Fetch Music',
            'Fetch Likes',
            '',
            'Add New to Music',
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
        thumbnails_list = []
        TABS = dict()
    
    def setupUi(self):
        self.setWindowTitle("Likes to Music")
        self.setWindowIcon(QtGui.QIcon('logo.ico'))
        
        display = QtWidgets.QApplication.desktop().screenGeometry()
        
        self.MAX_COLLUMNS = (display.width()-self.scrollbarW-4) // (self.THUMBNAIL_W + self.SPACING)
        self.width = self.MAX_COLLUMNS * (self.THUMBNAIL_W + self.SPACING) - self.SPACING
        
        usable_height = display.height() - self.menubarH - self.tabbarH - self.statusbarH - 30
        vid_height = self.THUMBNAIL_H + self.TITLE_H + self.SPACING*2
        max_rows = usable_height // vid_height
        self.height = max_rows * (self.THUMBNAIL_H + self.TITLE_H + self.SPACING*2)
        
        self.setFixedSize(
            6 + self.scrollbarW + self.width, 
            6 + self.statusbarH + self.height + self.tabbarH + self.menubarH)
        
        self.defaultPixmap = QtGui.QPixmap("default.png")
        
        self.MainwWindow_CentralWidget = QtWidgets.QWidget(self)
        
        self.menubar = QtWidgets.QMenuBar(self)
        self.menuStart = QtWidgets.QMenu(self.menubar, title="Menu")
        self.setMenuBar(self.menubar)
        for actionName in self.actionsList:
            if not actionName:
                self.menuStart.addSeparator()
                continue
            action = QtWidgets.QAction(text=actionName)
            actionName = actionName.replace(" ","_")
            actionFunc = getattr(self, actionName, self.fetch_playlist)
            actionName = f'action_{actionName}'
            setattr(self, actionName,  action)
            if actionName == 'action_Delete_From_Music':
                action.setEnabled(False)
            action.triggered.connect(actionFunc)
            self.menuStart.addAction(action)
        self.menubar.addAction(self.menuStart.menuAction())
        
        self.statusbar = QtWidgets.QStatusBar(
            font=self.fontTitle,
            sizeGripEnabled=False,
        )
        self.setStatusBar(self.statusbar)

        self.tabWidget = QtWidgets.QTabWidget(self.MainwWindow_CentralWidget)
        self.tabWidget.setGeometry(QtCore.QRect(0, 0, self.width+self.scrollbarW+8, self.height+self.tabbarH+7))
        self.tabWidget.currentChanged.connect(self.tabChanged)
        self.setCentralWidget(self.MainwWindow_CentralWidget)
        
        for tabName in ('Likes', 'Music', 'New', 'Ignored'):
            _Tab = QtWidgets.QWidget()
            self.tabWidget.addTab(_Tab, tabName)
            _Tab_scrollArea = QtWidgets.QScrollArea(_Tab)
            _Tab_scrollArea.setGeometry(QtCore.QRect(0, 0, self.width+self.scrollbarW+2, self.height+2))
            
            tab_dict = {
                'tab' : _Tab,
                'tab_scrollArea' : _Tab_scrollArea,
                'IDs' : []
            }
            self.TABS[tabName] = tab_dict
        
    def add_Tab(self, tabName):
        def add_Vid(row, col, vidID):
            def add_del_button(): #not used
                _ButtonName = f'{tabName}_Button_{row}_{col}'
                _Button = QtWidgets.QPushButton(
                    objectName=_ButtonName,
                    minimumSize=self.sizeDel,
                    maximumSize=self.sizeDel,
                    font=self.fontDel,
                    text="X"
                )
                setattr(self, _ButtonName, _Button)
                _Button.clicked.connect(self.butPress)
                _scrollAreaContents_Grid.addWidget(_Button, row*2+1, col*2+1, 1, 1)
            
            _ThumbnailName = f'{tabName}_Thumbnail_{row}_{col}'
            self._Thumbnail = QtWidgets.QLabel(
                objectName=vidID,
                minimumSize=self.sizeThumbnail,
                maximumSize=self.sizeThumbnail)
            self._Thumbnail.installEventFilter(self)
            setattr(self, _ThumbnailName, self._Thumbnail)
            _scrollAreaContents_Grid.addWidget(self._Thumbnail, row*2, col*2, 1, 2)
            
            _TitleName = f'{tabName}_Label_{row}_{col}'
            self._Title = QtWidgets.QLabel(
                minimumSize=self.sizeTitle,
                maximumSize=self.sizeTitle,
                font=self.fontTitle)
            setattr(self, _TitleName, self._Title)
            _scrollAreaContents_Grid.addWidget(self._Title, row*2+1, col*2, 1, 1)
            
            _checkBoxName = f'{tabName}_checkBox_{row}_{col}'
            _checkBox = QtWidgets.QCheckBox(
                objectName=_checkBoxName,
                toolTip="Uncheck to remove",
                toolTipDuration=2000,
                checked=True)
            setattr(self, _checkBoxName, _checkBox)
            _scrollAreaContents_Grid.addWidget(_checkBox, row*2+1, col*2+1, 1, 1)
        
        _Tab = self.TABS[tabName]['tab']
        _Tab_scrollArea = self.TABS[tabName]['tab_scrollArea']
        
        tmpIDs = getattr(self, f'{tabName}IDs')
        _scrollAreaContents = QtWidgets.QWidget()
        _scrollAreaContents_Grid = QtWidgets.QGridLayout(_scrollAreaContents)
        _scrollAreaContents_Grid.setSpacing(self.SPACING)
        _scrollAreaContents_Grid.setContentsMargins(0, 0, 0, 0)
        for x in range(4):
            _scrollAreaContents_Grid.setColumnStretch(x*2, 1)
        
        def add_row(cols):
            for col in range(cols):
                vidID = tmpIDs[row * self.MAX_COLLUMNS + col]
                add_Vid(row, col, vidID)
                _Thread = FetchThumbnail([vidID, self._Thumbnail, self._Title])
                setattr(self, f'{tabName}_{vidID}_Thread', _Thread)
                _Thread.start()
        
        rows, col_last_row = divmod(len(tmpIDs), self.MAX_COLLUMNS)
        row = -1
        for row in range(rows):
            add_row(self.MAX_COLLUMNS)
        row += 1
        add_row(col_last_row)
        
        _Tab_scrollArea.setWidget(_scrollAreaContents)
    
    def connect_yt_api(self):
        self.youtube = yt_api.YT()
        #auth = bool(self.youtube.youtube)
        auth = self.youtube.auth_valid()
        self.API_state = ('YouTube API IS UNAVAILABLE!', 'YouTube API Connected!')[auth]
        if not self.youtube.youtube:
            self.menuChangeDict['enable'] = 0
            self.menuChangeDict['actionNames'] = (
                'Fetch Music',
                'Fetch Likes',
                'Add New to Music',
            )
            self.menuChange()
        self.tabChanged()

    def Reconnect_API(self):
        self.youtube.youtube = self.youtube.main_auth_full()
        auth = self.youtube.auth_valid()
        self.API_state = ('YouTube API IS UNAVAILABLE!', 'YouTube API Connected!')[auth]
        self.menuChangeDict['enable'] = auth
        self.menuChangeDict['actionNames'] = (
            'Fetch Music',
            'Fetch Likes',
        )
        self.menuChange()
        self.tabChanged()

    def on_load(self):
        threading.Thread(target=self.connect_yt_api).start()
        self.fetch_playlist('Ignored')
        self.fetch_playlist('Likes')
        self.fetch_playlist('Music')
        self.update = 1

    def menuChange(self):
        for actionName in self.menuChangeDict['actionNames']:
            if actionName == 'Fetch Music' and not self.MusicContents:
                continue
            enabled = self.menuChangeDict['enable']
            actionName = actionName.replace(" ","_")
            _action = getattr(self, f'action_{actionName}')
            _action.setEnabled(enabled)

    def tabChanged(self):
        tmp = self.tabWidget
        i = tmp.currentIndex()
        _tabName = self.tabName = tmp.tabText(i)
        videosCount = len(getattr(self, f'{_tabName}IDs'))
        self.statusbar.showMessage(f'{videosCount:>4} videos  |  {self.API_state}')
    
    def eventFilter(self, object, event):
        if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == 1:
            webbrowser.open(f'https://youtu.be/{object.objectName()}')
        return False
    
    def fetch_playlist(self, tabName=''):
        if not tabName:
            try:
                tabName = self.sender().text().split()[1]
            except AttributeError:
                tmp = self.tabWidget
                i = tmp.currentIndex()
                tabName = tmp.tabText(i)
            
        if tabName == 'New':
            tmpIDs = list(set(self.LikesIDs) - set(set(self.MusicIDs) | set(self.IgnoredIDs)))
        #elif self.update and not tabName == 'Ignored':
        elif self.update and tabName in ('Music', 'Likes'):
            self.statusbar.showMessage(f'Fetching {tabName} Playlist...')
            QtWidgets.QApplication.processEvents()
            tmpContents = self.youtube.playlistContents(tabName)
            tmpIDs = list(tmpContents.keys())
            _IDs = getattr(self, f'{tabName}IDs')
            if tmpIDs == _IDs:
                return self.tabChanged()
            if tabName == 'Music':
                self.MusicContents = tmpContents
                _action = getattr(self, 'action_Delete_From_Music')
                _action.setEnabled(True)
            if tabName == 'Likes':
                with open('_Likes.txt', 'r') as f:
                    Likes_old = f.read().splitlines()
                with open('_Likes_Deleted.txt', 'a+') as f:
                    t = set(Likes_old) - set(tmpIDs)
                    f.write('\n'.join(t))
                    f.write('\n')
            with open(f'_{tabName}.txt', 'w') as f:
                f.write('\n'.join(tmpIDs))
        else:
            try:
                with open(f'_{tabName}.txt', 'r') as f:
                    tmpIDs = f.read().splitlines()
            except FileNotFoundError:
                if tabName != 'Ignored':
                    return
                if 0:
                    if tabName == 'Ignored':
                        with open(f'_{tabName}.txt', 'w'):
                            pass
                    else:
                        return
        setattr(self, f'{tabName}IDs', tmpIDs)
        self.add_Tab(tabName)
    
        if tabName != 'New':
            if self.LikesIDs and self.MusicIDs:
                self.fetch_playlist('New')
        self.tabChanged()

    def get_chkbox_state(self, tabName):
        _checkedBoxes = []
        _uncheckedBoxes = []
        vidIDs = getattr(self, f'{tabName}IDs')
        for n, vidID in enumerate(vidIDs):
            row, col = divmod(n, self.MAX_COLLUMNS)
            checkBoxName = f'{tabName}_checkBox_{row}_{col}'
            _checkBox = getattr(self, checkBoxName)
            if _checkBox.isChecked():
                _checkedBoxes.append(vidID)
            else:
                _uncheckedBoxes.append(vidID)
        self.checkedBoxes = _checkedBoxes
        self.uncheckedBoxes = _uncheckedBoxes

    def MusicApiCooldown(self):
        self.tabWidget.setCurrentIndex(1)
        QtWidgets.QApplication.processEvents()
        with open('_Music.txt', 'w') as f:
            f.write('\n'.join(self.MusicIDs) + '\n')
        self.update=0
        self.fetch_playlist('Music')
        self.update=1
        
        self.menuChangeDict['actionNames'] = (
            'Fetch Music',
            'Add New to Music',
        )
        self.menuChangeDict['enable'] = 0
        self.menuChange()
        self.menuChangeDict['enable'] = 1
        QtCore.QTimer.singleShot(30000, self.menuChange)

    def Add_New_to_Music(self):
        global current_insert
        
        if not getattr(self, 'NewIDs'):
            return
        
        self.get_chkbox_state('New')
        #new_checkedBoxes, new_uncheckedBoxes = self.get_chkbox_state('New')
        
        insert_titles = [(THUMBNAILS[ID][0], ID) for ID in self.checkedBoxes]
        current_insert = {title:'Pending' for title, _ in insert_titles}
        
        self.gen_titles = (vid for vid in insert_titles)
        
        msg = self.msg = QtWidgets.QMessageBox(
            windowTitle='Add New to Music',
            detailedText=make_details(),
            font=self.fontMsgBox,
        )
        msg.setStyleSheet("QLabel {min-width: 400px;}")
        
        start_button = msg.addButton('Start', QtWidgets.QMessageBox.ActionRole)
        start_button.clicked.disconnect()
        start_button.clicked.connect(self.start_insert)
            
        msg.addButton(QtWidgets.QMessageBox.Cancel)
            
        msg.exec_()
        
    def start_insert(self):
        self.sender().setEnabled(False)
        self.on_finished()
    
    def on_finished(self):
        try:
            self.next_insert(next(self.gen_titles))
        except StopIteration:
            #print('kekw')
            self.update_details(f'{make_details()}\nFinished!')
            self.MusicIDs = self.checkedBoxes + self.MusicIDs
            self.MusicApiCooldown()
            with open('_Ignored.txt', 'w') as f:
                f.write('\n'.join(self.uncheckedBoxes + self.IgnoredIDs))
            self.fetch_playlist('Ignored')

    def next_insert(self, vid):
        self.thread = UpdateStatus(vid)
        self.thread.finished.connect(self.on_finished)
        self.thread.updated.connect(self.update_details)
        self.thread.start()
    
    def update_details(self, text):
        self.msg.setDetailedText(text)

    def Delete_From_Music(self):
        self.get_chkbox_state('Music')
        for vidID in self.uncheckedBoxes:
            self.MusicIDs.remove(vidID)
            vid = self.MusicContents[vidID]
            vidTitle = vid['vidTitle']
            vidIDPls = vid['vidIDPls'][0]
            self.statusbar.showMessage(f'Deleting from Music: {vidTitle}')
            QtWidgets.QApplication.processEvents()
            self.youtube.del_video(vidIDPls)
        self.MusicApiCooldown()

    def Delete_From_Ignored(self):
        self.get_chkbox_state('Ignored')
        if self.uncheckedBoxes:
            for vidID in self.uncheckedBoxes:
                self.IgnoredIDs.remove(vidID)
            with open('_Ignored.txt', 'w') as f:
                f.write('\n'.join(self.IgnoredIDs))
            self.fetch_playlist('Ignored')

    def Exit_App(self):
        sys.exit()


try:
    with open('thumbnails.pickle', 'rb') as fl:
        THUMBNAILS = pickle.load(fl)
except FileNotFoundError:
    THUMBNAILS = dict()

THUMBNAILS_OLD = dict(THUMBNAILS)
app = QtWidgets.QApplication(sys.argv)
main_window = MainWindow()
main_window.setupUi()
main_window.show()
main_window.on_load()
app.exec_()

if THUMBNAILS_OLD != THUMBNAILS:
    with open('thumbnails.pickle', 'wb') as fl:
        pickle.dump(THUMBNAILS, fl)
