import re
import time
import html
import json
import pickle
import requests
import traceback
import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

NAMELEN = 150

class YT:
    api_service_name = "youtube"
    api_version = "v3"
    
    def __init__(self):
        self.youtube = self.main_auth_full()

    def auth_valid(self):
        try:
            return self.creds.valid
        except NameError:
            return bool(self.youtube)
        return False

    def main_auth_full(self):
        # The pickle file stores the user's access and refresh tokens, and is created 
        # automatically when the authorization flow completes for the first time.
        creds = None
        try:
            with open('yt_auth_full.pickle', 'rb') as fl:
                creds = pickle.load(fl)
        except:
            pass
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                client_secret = 'client_secret.json'
                SCOPES = ['https://www.googleapis.com/auth/youtube', ]
                flow = InstalledAppFlow.from_client_secrets_file(client_secret, SCOPES)
                creds = flow.run_local_server()
            # Save the credentials for the next run
            with open('yt_auth_full.pickle', 'wb') as fl:
                pickle.dump(creds, fl)
        try:
            b = build(self.api_service_name, self.api_version, credentials=creds)
            self.creds = creds
            return b
        except:
            self.save_log()
            return

    def save_log(self):
        #if error save to file
        t = time.strftime('%Y-%m-%d@%H-%M-%S', time.gmtime())
        pth = f'Logs/{t}.txt'
        with open(pth, 'w') as f:
            f.write(traceback.format_exc())# + '\nArguments:\n' + str(sys.argv))

    def get_thumbnail(self, vidID):
        url = f'https://i.ytimg.com/vi/{vidID}/mqdefault.jpg'
        return requests.get(url).content
    
    def del_video(self, vidPlsID):
        self.youtube.playlistItems().delete(id=vidPlsID).execute()

    def pls_insert(self, vidID, playlistID, pos=0):
        if len(vidID) != 11:
            return f'Wrong vidID length: {vidID}'
        b = {
            "snippet": {
                "position": pos,
                "playlistId": playlistID,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": vidID
                }
            }
        }
        request = self.youtube.playlistItems().insert(
            part="snippet",
            fields="snippet/title",
            body=b
        )
        return request.execute()["snippet"]["title"]

    def playlist_generator(self, playlistID):
        pT = ''
        while 1:
            request = self.youtube.playlistItems().list(
                part="snippet",
                maxResults=50,
                pageToken=pT,
                playlistId=playlistID,
                fields="nextPageToken, items(id, snippet(title, resourceId/videoId))"
            )
            pls_videos = request.execute()
            yield pls_videos['items']
            pT = pls_videos.get('nextPageToken')
            if not pT:
                break

    def playlistContents(self, playlistID):
        '''
        tmpVideos = ...
            ID of video: {
                vidTitle: Title,
                vidIDPls: [IDs in playlist]
            }...
        '''
        tmpVideos = {}
        for page in self.playlist_generator(playlistID):
            for video in page:
                vidID = video['snippet']['resourceId']['videoId']
                vidIDPls = video['id']
                vidTitle = video['snippet']['title']
                tmpVideos.setdefault(vidID, {'vidTitle': vidTitle}) \
                    .setdefault('vidIDPls', []).append(vidIDPls)
        return tmpVideos
    
    def get_title_api(self, vidID):
        #get video title, if error = removed
        request = self.youtube.videos().list(
            part="snippet",
            id=vidID,
            fields="items/snippet/title"
        )
        try:
            title = request.execute()
            return title["items"][0]["snippet"]["title"]
        except IndexError:
            print(f'{vidID} IS PRIVATE OR NO LONGER EXISTS!')
            return vidID
    
    def get_title_requests(self, vidID):
        vid_raw = requests.get(f'https://www.youtube.com/watch?v={vidID}').text
        _search = re.search('alternate.*?title="(?P<title>.+?)"', vid_raw)
        try:
            t = _search['title']
            return html.unescape(t)
        except TypeError:
            return vidID
    
    def encode_title(self, vidTitle):
        vidTitle = vidTitle.encode()
        vidTitle = vidTitle[:NAMELEN]
        return vidTitle.ljust(NAMELEN)
    
    def save_thumbnail_w_name(self, img, vidID, vidTitle=''):
        if not vidTitle:
            vidTitle = self.get_title_requests(vidID)
        with open(f'cached/{vidID}', 'wb') as f:
            f.write(self.encode_title(vidTitle) + img)
        return vidTitle
