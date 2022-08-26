# coding:utf-8
import os
import requests

VIDEO_DOWNLOAD_STATUS = {
    -1:"UNDONE",
    0:"SUCCESS",
    1:"DOWNLOAD FAILED",
    2:"NO INPUT"
}
PHOTO_DOWNLOAD_STATUS = {
    -1:"UNDONE",
    0:"SUCCESS",
    1:"NOT PHOTO URL",
    2:"URL ERROR"
}

#%%
def downloadVideo(tid = None, url = None):
    cmd = "youtube-dl -f worst --no-warnings -o /tweet_video/%(id)s.%(ext)s "
    if(url is not None):
        cmd += url
    elif(tid is not None):
        cmd += "https://twitter.com/i/status/" + str(tid)
    else:
        return 2 # "INPUT ERROR"
    
    try:
        if os.system(cmd) != 0:
            return 1 # "DOWNLOAD FAILED"
        else:
            return 0 # "SUCCESS"
    except:
        if(url is not None or tid is not None):
            return 1 # "DOWNLOAD FAILED"
        else:
            return 2 # "INPUT ERROR"

#%%
def downloadPhoto(uid, url):
    try:
        rq = requests.get(url)
        img_type = ("image/png", "image/jpeg", "image/jpg")
        if rq.headers["content-type"] in img_type:
            with open('user_profile_photo/%s.jpg'%str(uid), 'wb') as f:
                f.write(rq.content)
            return 0 # "SUCCESS"
        else:
            return 1 # "NOT PHOTO URL"
    except:
        return 2 # "URL ERROR"
    
#%%
if __name__ == '__main__':
    print(downloadVideo(tid='1556486427176828928')) # tweet with video
    # print(downloadVideo(tid='124124'))# inexist tweet id
    print(downloadVideo(url='https://t.co/dcDUy4y3Nb')) # url tweet with video
    