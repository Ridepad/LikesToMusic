import os
import re
import sys
import time
import json
import pickle
import requests
import traceback
import googleapiclient.errors

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
#os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
class YT:
    api_service_name = "youtube"
    api_version = "v3"
    
    def __init__(self, auth='full'):
        with open('credits','r') as f:
            c = json.loads(f.read())
        self.DEVELOPER_KEY = c['DEVELOPER_KEY']
        self.playlists = {'Music':c['MusicPlsID'], 'Likes':c['LikesPlsID']}
        if auth == 'full':
            self.youtube = self.main_auth_full()
        else:
            self.youtube = self.main_auth_readonly()

    def auth_valid(self):
        try:
            return self.creds.valid
        except NameError:
            return bool(self.youtube)
        return False

    def main_auth_full(self):
        # The file token.pickle stores the user's access and refresh tokens, and is created 
        # automatically when the authorization flow completes for the first time.
        creds = None
        if os.path.exists('yt_auth_full.pickle'):
            with open('yt_auth_full.pickle', 'rb') as fl:
                creds = pickle.load(fl)
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
        except googleapiclient.errors.UnknownApiNameOrVersion:
            print('ERROR! YOUTUBE API IS UNAVAILABLE!')
            self.save_log()
            return


    def main_auth_readonly(self):
        return build(self.api_service_name, self.api_version, developerKey=self.DEVELOPER_KEY)


    def save_log(self):
        #if error save to file
        t = time.strftime('%Y-%m-%d@%H-%M-%S', time.gmtime())
        pth = f'Logs/{t}.txt'
        print(f'Log saved as: {pth}')
        with open(pth, 'w') as f:
            f.write(traceback.format_exc() + '\nArguments:\n' + str(sys.argv))


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
            #with open('_Errors.txt', 'r') as f:
            #    errorIDs = f.read().splitlines()
            #if vidID not in errorIDs:
            #    errorIDs.append(vidID)
            print(f'{vidID} IS PRIVATE OR NO LONGER EXISTS!')
            with open('_Errors.txt', 'a+') as f:
                f.write(f'\n{vidID}')
            return 
        except:
            self.save_log()
    
    def get_title_requests(self, vidID):
        vid_raw = requests.get(f'https://www.youtube.com/watch?v={vidID}').text
        _search = re.search('alternate.*?title="(?P<title>.+?)"', vid_raw)
        try:
            return _search['title']
        except TypeError:
            return vidID
            #print(f'{vidID} IS PRIVATE OR NO LONGER EXISTS!')


    def get_thumbnail(self, vidID, save=1):
        while 1:
            try:
                img = requests.get(f'https://i.ytimg.com/vi/{vidID}/mqdefault.jpg', timeout=10).content
                break
            except requests.exceptions.Timeout:
                print(f'{vidID} thumbnail download timed out. Retry...')
            except requests.exceptions.ConnectionError:
                print(f'{vidID} thumbnail download timed out. Retry...')
        if save:
            return self.save_name_with_thumbnail(vidID, img)
        return '', img
    
    
    def save_name_with_thumbnail(self, vidID, img, maxNameLen=150):
        vidTitle = self.get_title_requests(vidID)
        vidTitle = vidTitle.encode()
        vidTitle = vidTitle[:maxNameLen]
        vidTitle = vidTitle.ljust(maxNameLen)
        with open(f'cached/{vidID}', 'wb') as f:
            f.write(vidTitle + img)
        return vidTitle, img
    
    
    def del_video(self, vidPlsID):
        self.youtube.playlistItems().delete(id=vidPlsID).execute()


    def _insert(self, vidID):
        playlistID = self.playlists['Music']
        if len(vidID) != 11:
            return f'Wrong vidID length: {vidID}'
        try:
            request = self.youtube.playlistItems().insert(
                part="snippet",
                fields="snippet/title",
                body={
                    "snippet": {
                        "position": 0,
                        "playlistId": playlistID,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": vidID
                        }
                    }
                }
            )
            vidTitle = request.execute()["snippet"]["title"]
            return f'Done with: {vidTitle}\n'
        except socket.timeout:
            print(f'{vidID} timeout, restarting...')
            return self._insert(vidID)
        except:
            self.save_log()
            return f'Error in:  {vidID}\n'


    def playlistContents(self, playlistName, getFull=1):
        '''
        tmpVideos = ID of video: {
            vidTitle: Title,
            vidIDPls: [IDs in playlist]
        }
        '''
        playlistID = self.playlists[playlistName]
        tmpVideos = dict()
        pT = ''
        while 1:
            request = self.youtube.playlistItems().list(
                part="snippet",
                maxResults=50,
                pageToken=pT,
                playlistId=playlistID,
                fields="pageInfo/totalResults, nextPageToken, items(id, snippet(title, resourceId/videoId))"
            )
            pls_videos = request.execute()
            pT = pls_videos.get('nextPageToken')
            for video in pls_videos['items']: 
                vidID = video['snippet']['resourceId']['videoId']
                vidTitle = video['snippet']['title']
                tmp = tmpVideos.get(vidID, {'vidTitle':vidTitle, 'vidIDPls':[]})['vidIDPls']
                #tmp = tmpVideos.get(vidID, {'vidIDPls':[]})['vidIDPls']
                tmp.append(video['id'])
                tmpVideos[vidID] = {'vidTitle':vidTitle, 'vidIDPls':tmp}
            
            if not pT or not getFull:
                break
        pls_len = pls_videos['pageInfo']['totalResults']
        #print('Done.')
        print(f'{playlistName} playlist reported length: {pls_len}')
        print(f'{playlistName} playlist  actual  length: {len(tmpVideos)}')
        return tmpVideos
