# -*- coding: utf-8 -*-
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

TODO = '''
checkbox -> icons
(likes = likesicons
other trashcan)
'''

st = time.time()

current_insert = dict()

def getTime(txt):
    t = time.time() - st
    t = round(t, 2)
    print(t, txt)

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
        global main_window
        self.setStatus('Inserting')
        st = main_window.youtube.pls_insert(self.vidID)
        self.setStatus('Done')


class FetchThumbnail(QtCore.QThread):
    thumbnail_loaded = QtCore.pyqtSignal(list)
    NameLen = 150
    def __init__(self, vidID, row, col, tabName):
        QtWidgets.QMainWindow.__init__(self)
        self.vidID = vidID
        self._emit = [vidID, row, col, tabName]
    
    def run(self):
        vidTitle, vidThumbnail = self.get_thumbnail()
        if vidTitle:
            vidTitle = vidTitle.decode()
        else:
            vidTitle, vidThumbnail = self.vidID, False
        self._emit.append(vidTitle)
        self._emit.append(vidThumbnail)
        self.thumbnail_loaded.emit(self._emit)
        
    def get_thumbnail(self):
        try:
            with open(f'cached/{self.vidID}', 'rb') as f:
                f = f.read()
            return f[:self.NameLen], f[self.NameLen:]
        except FileNotFoundError:
            return main_window.youtube.get_thumbnail(self.vidID, save=1)


class MainWindow(QtWidgets.QMainWindow):
    if 1:   #convenience to hide all class variables
        thumbnail_W = 320
        thumbnail_H = 180
        title_H = 23
        sizeDel = QtCore.QSize(40, title_H)
        sizeChkBx = QtCore.QSize(16, title_H)
        sizeTitle = QtCore.QSize(300, title_H)
        sizeThumbnail = QtCore.QSize(thumbnail_W, thumbnail_H)
        bold = QtGui.QFont.Bold
        famAnonymous = "Anonymous Pro"
        famSitka = "Sitka"
        famTahoma = "Tahoma"
        famUbuntu = "Ubuntu"
        famSegoe = "Segoe UI Black"
        famCalibri = "Calibri"
        famLucida = "Lucida Console"
        fontMsgBox = QtGui.QFont(famLucida)
        fontTitle = QtGui.QFont(famCalibri, 15)
        fontDel = QtGui.QFont(famSegoe, 14, bold)

        update = 0
        NewIDs = []
        LikesIDs = []
        MusicIDs = []
        ErrorsIDs = set()
        IgnoredIDs = []
        
        LastModified = {
            'Music' : 0,
            'Likes' : 0,
            'Errors' : 0,
            'Ignored' : 0
        }
        
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
    
    def __init__(self):
        #Depending on user's monitor resolution adjusts W, H and grid of app
        super().__init__()
        display = QtWidgets.QApplication.desktop().screenGeometry()
        self.MAX_COLLUMNS = (display.width()-self.scrollbarW-4) // (self.thumbnail_W + self.SPACING)
        usable_height = display.height() - self.menubarH - self.tabbarH - self.statusbarH - 30
        vid_height = self.thumbnail_H + self.title_H + self.SPACING*2
        self.MAX_ROWS = usable_height // vid_height
        self.width = self.MAX_COLLUMNS * (self.thumbnail_W + self.SPACING) - self.SPACING
        self.height = self.MAX_ROWS * (self.thumbnail_H + self.title_H + self.SPACING*2)
        self.defaultPixmap = QtGui.QPixmap("default.png")

    def add_Tab(self, tabName):
        def add_Vid(row, col, vidID):
            def add_thumbnail():
                _ThumbnailName = f'{tabName}Thumbnail{row}_{col}'
                _Thumbnail = QtWidgets.QLabel(
                    objectName=vidID,
                    minimumSize=self.sizeThumbnail,
                    maximumSize=self.sizeThumbnail,
                    pixmap=qpxmp
                )
                _Thumbnail.installEventFilter(self)
                setattr(self, _ThumbnailName, _Thumbnail)
                _scrollAreaContents_Grid.addWidget(_Thumbnail, row*2, col*2, 1, 2)

            def add_title():
                _TitleName = f'{tabName}Label{row}_{col}'
                _Title = QtWidgets.QLabel(
                    minimumSize=self.sizeTitle,
                    maximumSize=self.sizeTitle,
                    font=self.fontTitle,
                    text=vidTitle
                )
                setattr(self, _TitleName, _Title)
                _scrollAreaContents_Grid.addWidget(_Title, row*2+1, col*2, 1, 1)
                
            def add_checkBox():
                _checkBoxName = f'{tabName}_checkBox_{row}_{col}'
                _checkBox = QtWidgets.QCheckBox(
                    objectName=_checkBoxName,
                    minimumSize=self.sizeChkBx,
                    maximumSize=self.sizeChkBx,
                    toolTip="Uncheck to remove",
                    toolTipDuration=2000,
                    checked=True,
                )
                #_checkBox.setStyleSheet("QCheckBox.indicator {width:16px;height: 16px;}");
                setattr(self, _checkBoxName, _checkBox)
                _scrollAreaContents_Grid.addWidget(_checkBox, row*2+1, col*2+1, 1, 1)
            
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
            
            thumbnail = THUMBNAILS.get(vidID)
            if thumbnail and thumbnail[1]:
                vidTitle, vidThumbnail = THUMBNAILS[vidID]
                qpxmp = QtGui.QPixmap()
                qpxmp.loadFromData(vidThumbnail)
            else:
                vidTitle = vidID
                qpxmp = self.defaultPixmap
            
            add_thumbnail()
            add_title()
            add_checkBox()
            
            return thumbnail
        
        _Tab_Name = f'{tabName}_Tab'
        _Tab_scrollArea_Name = f'{tabName}_Tab_scrollArea'
        
        tmpIDs = getattr(self, f'{tabName}IDs')
        
        tabExists = _Tab_Name in self.__dict__
        if tabExists:
            _Tab = getattr(self, _Tab_Name)
            _Tab_scrollArea = getattr(self, _Tab_scrollArea_Name)
        else:
            _Tab = QtWidgets.QWidget()
            setattr(self, _Tab_Name, _Tab)
            _Tab_scrollArea = QtWidgets.QScrollArea(_Tab)
            _Tab_scrollArea.setGeometry(QtCore.QRect(0, 0, self.width+self.scrollbarW+2, self.height+2))
            setattr(self, _Tab_scrollArea_Name, _Tab_scrollArea)
        
        
        rows, col_last_row = divmod(len(tmpIDs), self.MAX_COLLUMNS)
        __H = (self.thumbnail_H + self.title_H + self.SPACING*2)*(rows+bool(col_last_row))
        _scrollAreaContents = QtWidgets.QWidget()
        _scrollAreaContents.setGeometry(QtCore.QRect(0, 0, self.width, __H))
        _scrollAreaContents.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        _scrollAreaContents_Grid = QtWidgets.QGridLayout(_scrollAreaContents)
        for x in range(5):
            _scrollAreaContents_Grid.setColumnStretch(x*2, 1)
        _scrollAreaContents_Grid.setSpacing(self.SPACING)
        _scrollAreaContents_Grid.setContentsMargins(0, 0, 0, 0)


        #setattr(self, _scrollAreaContents_Name, _scrollAreaContents)
        #setattr(self, _scrollAreaContents_Grid_Name, _scrollAreaContents_Grid)
        
        def add_row(cols):
            for col in range(cols):
                vidID = tmpIDs[row * self.MAX_COLLUMNS + col]
                thumbnail = add_Vid(row, col, vidID)
                if not thumbnail:
                    _Thread = FetchThumbnail(vidID, row, col, tabName)
                    _Thread.thumbnail_loaded.connect(self.got_thumb)
                    setattr(self, f'{tabName}_{vidID}_Thread', _Thread)
                    _Thread.start()
        
        row = -1
        for row in range(rows):
            add_row(self.MAX_COLLUMNS)
        row += 1
        add_row(col_last_row)
        
        _Tab_scrollArea.setWidget(_scrollAreaContents)
        
        if not tabExists:
            self.tabWidget.addTab(_Tab, tabName)
    
        QtWidgets.QApplication.processEvents()
    
    def got_thumb(self, raw_thumb):
        vidID, row, col, tabName, vidTitle, vidThumbnail = raw_thumb
        #while 1:
        try:
            _Title = getattr(self, f'{tabName}Label{row}_{col}')
            _Title.setText(vidTitle)
            if vidThumbnail:
                pixmap = QtGui.QPixmap()
                pixmap.loadFromData(vidThumbnail)
                _Thumbnail = getattr(self, f'{tabName}Thumbnail{row}_{col}')
                _Thumbnail.setPixmap(pixmap)
            
                THUMBNAILS[vidID] = (vidTitle, vidThumbnail)
            #break
        except RuntimeError:
            pass
    
    def setupUi(self):
        self.setWindowTitle("From likes to music playlist")
        self.setFixedSize(
            self.width + self.scrollbarW + 6, 
            self.height + self.statusbarH + self.tabbarH + self.menubarH + 6)
        
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
        QtWidgets.QApplication.processEvents()
        QtCore.QMetaObject.connectSlotsByName(self)

    #def check_API_state(self):
    #    return ('YouTube API IS UNAVAILABLE!', 'YouTube API Connected!')[bool(self.youtube.youtube)]
    
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
        getTime('connect_yt_api:')

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
        def len_likes():
            with open('_Likes.txt', 'r') as f:
                return len(f.readlines()) 
        if all(os.path.exists(f'_{name}.txt') for name in ('Likes', 'Music', 'Ignored')) and \
            len(os.listdir('cached')) >= len_likes():
            threading.Thread(target=self.connect_yt_api).start()
        else:
            self.connect_yt_api()
        self.fetch_playlist('Likes')
        self.fetch_playlist('Music')
        self.fetch_playlist('Ignored')
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

    #not used
    def butPress(self):
        tmpButton = self.sender()
        self.statusbar.showMessage(f'{tmpButton} clicked')
        t = tmpButton.objectName().split('_')
        tmpIndex = int(t[-1]) + (5 * int(t[-2]))

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
        getTime(f'Done with {tabName}:')
    
        if tabName != 'New':
            if self.LikesIDs and self.MusicIDs:
                self.fetch_playlist('New')
        self.tabChanged()

    def get_chkbox_state(self, tabName):
        _checkedBoxes = []
        _uncheckedBoxes = []
        #vidIDs = self.__dict__[f'{tabName}IDs']
        vidIDs = getattr(self, f'{tabName}IDs')
        for n, vidID in enumerate(vidIDs):
            row, col = divmod(n, self.MAX_COLLUMNS)
            checkBoxName = f'{tabName}_checkBox_{row}_{col}'
            #_checkBox = self.__dict__[checkBoxName]
            _checkBox = getattr(self, checkBoxName)
            if _checkBox.isChecked():
                _checkedBoxes.append(vidID)
            else:
                _uncheckedBoxes.append(vidID)
        return _checkedBoxes, _uncheckedBoxes

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
        new_checkedBoxes, new_uncheckedBoxes = self.get_chkbox_state('New')
        
        insert_titles = [(THUMBNAILS[ID][0], ID) for ID in new_checkedBoxes]
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
        
        self.MusicIDs = new_checkedBoxes + self.MusicIDs
        self.MusicApiCooldown()
        with open('_Ignored.txt', 'w') as f:
            f.write('\n'.join(new_uncheckedBoxes + self.IgnoredIDs))
        self.fetch_playlist('Ignored')
        
    def start_insert(self):
        self.sender().setEnabled(False)
        self.on_finished()
    
    def on_finished(self):
        try:
            self.next_insert(next(self.gen_titles))
        except StopIteration:
            self.update_details(f'{make_details()}\nFinished!')

    def next_insert(self, vid):
        self.thread = UpdateStatus(vid)
        self.thread.finished.connect(self.on_finished)
        self.thread.updated.connect(self.update_details)
        self.thread.start()
    
    def update_details(self, text):
        self.msg.setDetailedText(text)

    def Delete_From_Music(self):
        music_uncheckedBoxes = self.get_chkbox_state('Music')[1]
        for vidID in music_uncheckedBoxes:
            self.MusicIDs.remove(vidID)
            vid = self.MusicContents[vidID]
            vidTitle = vid['vidTitle']
            vidIDPls = vid['vidIDPls'][0]
            self.statusbar.showMessage(f'Deleting from Music: {vidTitle}')
            QtWidgets.QApplication.processEvents()
            self.youtube.del_video(vidIDPls)
        self.MusicApiCooldown()

    def Delete_From_Ignored(self):
        ignored_uncheckedBoxes = self.get_chkbox_state('Ignored')[1]
        if ignored_uncheckedBoxes:
            for rem in ignored_uncheckedBoxes:
                self.IgnoredIDs.remove(rem)
            with open('_Ignored.txt', 'w') as f:
                f.write('\n'.join(self.IgnoredIDs))
            self.fetch_playlist('Ignored')

    def Exit_App(self):
        sys.exit(0)


if __name__ == "__main__":
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
    getTime('MainWindow.show()')
    main_window.on_load()
    app.exec_()
    if THUMBNAILS_OLD != THUMBNAILS:
        with open('thumbnails.pickle', 'wb') as fl:
            pickle.dump(THUMBNAILS, fl)
