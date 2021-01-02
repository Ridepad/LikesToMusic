# LikesToMusic
- You can separate music from Likes playlist into different one.
- You can delete videos from Music playlist.
- Open video by left clicking on thumbnail. 
- Caches already dowloaded titles and thumbnails of videos.
- Caches both Music and Likes playlist for faster program launch.

# How to use
- create new project https://console.cloud.google.com/cloud-resource-manager
- go to project
- APIs & Services -> Add youtube data
- APIs & Services -> Credentails, Add oauth and api key
- Download secret file, rename it to client_secret.json
- Create new YpuTube playlist to store all music and put its ID into PUT_PLAYLIST_ID_INSIDE.txt

# Bugs
- memory spike after playlist update
