# LikesToMusic
- You can separate music from Likes playlist into different one.
- You can delete videos from Music playlist.
- Open video by left clicking on thumbnail. 
- Caches already dowloaded titles and thumbnails of videos.
- Caches both Music and Likes playlist for faster opening at program start.

# How to use
- create new project https://console.cloud.google.com/cloud-resource-manager
- go to project
- APIs & Services -> Add youtube data
- APIs & Services -> Credentails, Add oauth and api key
- Dowload secret file, rename it to client_secret.json
- Create new playlist to store all music

## Credits file:
### "MusicPlsID": ""
- Create new playlist on youtube. Copy this playlist ID and put inbetween ""
### "LikesPlsID": "",
- Copy Likes playlist ID and put inbetween ""
### optional: "DEVELOPER_KEY": ""
- Copy API_KEY you created above and put inbetween ""

# Bugs
- Crashes on 1st use when Likes playlist have more than 500 videos
