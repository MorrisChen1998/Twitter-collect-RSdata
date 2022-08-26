# coding:utf-8
import os
import re
import json
from tqdm import tqdm
from collections import Counter 

import tweepy
AUTHENTICATE_KEY = open('AUTHENTICATE_KEY2', 'r').read()
# client = tweepy.Client(AUTHENTICATE_KEY, wait_on_rate_limit=False)
client = tweepy.Client(AUTHENTICATE_KEY, wait_on_rate_limit=True)

# self made package
import dlmedia

#%%
def getURL(text):
    urls = re.findall(r'(https?://\S+)', text)
    return urls

#%% get users by ids and usernames, max to 100 users
def getUsers(uids = None, usernames = None):
    if(uids is not None):
        response = client.get_users(ids = uids, \
                                    user_fields=["profile_image_url",\
                                                 "description"])
    elif(usernames is not None):
        response = client.get_users(usernames = usernames, \
                                    user_fields=["profile_image_url",\
                                                 "description"])
            
    return extractUserInfo(response)

#%% tree node strategy for user collect
def TreeNodeStrategy(ancestor_uid):
    filePath = f'user_list/{ancestor_uid}_follower_list.json'
    second_layer_users = [u['id'] for u in readJson(filePath)]
    filePath = f'user_list/{ancestor_uid}/'
    if not os.path.exists(filePath):
        os.makedirs(filePath)

    third_layer_list = []
    total_collected_user_count = 0
    for uid in tqdm(second_layer_users):
        filePath = f'user_list/{ancestor_uid}/{uid}_follower_list.json'
        user_list = getUsersFollower(uid)
        outputJson(filePath, user_list)
        third_layer_list.append({
            'parent_user_id': uid, # second layer user
            'child_users': user_list # third layer user
        })
        total_collected_user_count += len(user_list)
        
    return third_layer_list, total_collected_user_count
    
#%% read out tree node users
def getTree(ancestor_uid):
    filePath = f'user_list/{ancestor_uid}_follower_list.json'
    second_layer_users = [u['id'] for u in readJson(filePath)]
    
    third_layer_list = []
    total_collected_user_count = 0
    for uid in tqdm(second_layer_users):
        filePath = f'user_list/{ancestor_uid}/{uid}_follower_list.json'
        user_list = readJson(filePath)
        third_layer_list.append({
            'parent_user_id': uid, # second layer user
            'child_users': user_list # third layer user
        })
        total_collected_user_count += len(user_list)
        
    total_user_list = readJson(f'user_list/{ancestor_uid}_total_user_list.json')
    return third_layer_list, total_user_list, total_collected_user_count

#%% get users following list
def getUsersFollowing(uid):
    response = client.get_users_following(id = uid, max_results=1000,\
                        user_fields=["profile_image_url","description"])

    return extractUserInfo(response) if response.data else []

#%% get user's followers
def getUsersFollower(uid):
    response = client.get_users_followers(id = uid, max_results=1000,\
                        user_fields=["profile_image_url","description"])

    return extractUserInfo(response) if response.data else []
    
#%% tree node strategy for liked history
def TreeLikedHistory(ancestor_uid):
    filePath = f'user_list/{ancestor_uid}_follower_list.json'
    second_layer_users = [u['id'] for u in readJson(filePath)]
    
    filePath = f'liked_history_list/{ancestor_uid}/'
    if not os.path.exists(filePath):
        os.makedirs(filePath)
    filePath = f'tweet_list/{ancestor_uid}/'
    if not os.path.exists(filePath):
        os.makedirs(filePath)
    
    third_layer_list = []
    total_tweet_list = []
    total_interactions = []
    for i, uid_2nd in enumerate(second_layer_users[:3]):
        filePath = f'user_list/{ancestor}/{uid_2nd}_follower_list.json'
        third_layer_users = [uid_2nd] + [u['id'] for u in readJson(filePath)]

        filePath_liked = f'liked_history_list/{ancestor}/{uid_2nd}_follower_liked_history_list.json'
        filePath_tweet = f'tweet_list/{ancestor}/{uid_2nd}_follower_liked_tweet_list.json'
        if os.path.exists(filePath_liked) and \
            os.path.exists(filePath_tweet):
            print(f'donwload {i+1}/1000...already existed!')
            continue
        else:
            print(f'donwload {i+1}/1000...')

        users_sequence_list = []
        tweet_list = []
        for uid_3rd in tqdm(third_layer_users):
            liked_list = getUserLiked(uid_3rd, max_liked = 200)
            if(len(liked_list) < 5):
                continue
            user_sequence = dict()
            user_sequence['id'] = uid_3rd
            user_sequence['liked_history'] = [t['id'] for t in liked_list]
            users_sequence_list.append(user_sequence)

            total_interactions += user_sequence['liked_history']
            for t in liked_list:
                if t['id'] not in tweet_list:
                    tweet_list.append(t)

        outputJson(filePath_liked, users_sequence_list)
        outputJson(filePath_tweet, tweet_list)

        total_tweet_list += tweet_list
        third_layer_list.append({
            'parent_user_id': uid_2nd, # second layer user
            'child_users': users_sequence_list # third layer user
        })
            
    return third_layer_list, total_tweet_list, Counter(total_interactions)

#%% read out all the users' liked history in tree 
def getTreeLiked(ancestor_uid):
    filePath = f'user_list/{ancestor_uid}_follower_list.json'
    second_layer_users = [u['id'] for u in readJson(filePath)]
    
    third_layer_list = []
    total_interactions = []
    for uid_2nd in tqdm(second_layer_users):
        filePath_liked = f'liked_history_list/{ancestor}/{uid_2nd}_follower_liked_history_list.json'
        users_sequence_list = readJson(filePath_liked)

        for u in users_sequence_list:
            total_interactions += u['liked_history']
            
        third_layer_list.append({
            'parent_user_id': uid_2nd, # second layer user
            'child_users': users_sequence_list # third layer user
        })

    total_tweet_list = readJson(f'tweet_list/{ancestor}_total_tweet_list.json')
    return third_layer_list, total_tweet_list, Counter(total_interactions)

#%% get user liked list
def getUserLiked(uid, max_liked = 500): 
    response = client.get_liked_tweets(id = uid, \
                                 expansions = ["attachments.media_keys"],\
                                 media_fields=["type","preview_image_url"])
    if not(response.data):
        return []

    liked_list = extractTweetInfo(response)
    
    count_liked = 100
    while('next_token' in response.meta and \
          response.meta['next_token'] and \
          count_liked < max_liked):
        
        response = client.get_liked_tweets(id = uid, \
                            expansions = ["attachments.media_keys"], \
                            media_fields=["type","preview_image_url"],\
                            pagination_token = response.meta['next_token'])
        
        if not(response.meta['result_count'] > 0):
            break
        count_liked += 100
        liked_list = liked_list + extractTweetInfo(response)
    
    return liked_list

#%% get tweets by ids, max to 100 tweets
def getTweets(tweet_ids):
    response = client.get_tweets(tweet_ids,\
                                 expansions= ["attachments.media_keys"],\
                                 media_fields=["type","preview_image_url"])
    
    return extractTweetInfo(response)
    
#%% extract user information from response object
def extractUserInfo(response):
    user_list = []
    for u in response.data:
        user = dict()
        user['id'] = u.id
        user['username'] = u.username
        user['name'] = u.name
        user['description'] = u.description
        user['profile_image_url'] = u.profile_image_url
        user['media_download_status'] = -1

        user_list.append(user)
    return user_list

#%% extract tweet information from response object
def extractTweetInfo(response):
    if not(response.includes):
        return []
    
    media_type = dict()
    media_url = dict()
    for media in response.includes['media']:
        mkey = media.media_key
        media_type[mkey] = media.type
        media_url[mkey] = media.preview_image_url
        
    tweets = list()
    for t in response.data:
        tweet = dict()
        tweet['id'] = t.id
        tweet['type'] = ''
        tweet['text'] = t.text
        tweet['media_download_status'] = -1
        tweet['preview_image_url'] = ''
        
        try:
            for key in t.data['attachments']['media_keys']:
                tweet['type'] = media_type[key]
                tweet['preview_image_url'] = media_url[key]
        except:
            tweet['type'] = 'text'
        
        if(tweet['type']=='video'):
            tweets.append(tweet)
            
    return tweets

#%% download media
def downloadVideoProcessing(video_list):
    print('download micro-video...')
    checklist = dict()
    for t in tqdm(video_list):
        tid = t['id']
        return_code = dlmedia.downloadVideo(tid = tid)
        checklist[tid] = return_code
    return checklist

def downloadPhotoProcessing(user_list):
    print('download user profile photo...')
    checklist = dict()
    for u in tqdm(user_list):
        uid = u['id']
        return_code = dlmedia.downloadPhoto(uid, u['profile_image_url'])
        checklist[uid] = return_code
    return checklist

#%% print out json file
def outputJson(filePath, userList):
    with open(filePath, 'w', encoding='utf-8') as f:
        json.dump(userList, f, indent=2)

def readJson(filePath):
    with open(filePath, encoding='utf-8') as f:
        user_list = json.load(f)
    return user_list

#%%
if __name__ == '__main__':
    '''
    Get ancestor user list
    '''
    myuid = getUsers(usernames=['AncestorMorris'])[0]['id']
    # ancestor_user_list = getUsersFollowing(myuid)
    # outputJson('ANCESTOR_USERS.json', ancestor_user_list)

    # ancestor_user_list = readJson('ANCESTOR_USERS.json')
    # ancestor_user_ids = [u['id'] for u in ancestor_user_list]

    '''
    Collect ancestor's followers(second layer user)
    Amount: ancestor x 1000(1 request)
    Rate limit: 15 requests per 15-minute
    '''
    # for u in tqdm(ancestor_user_list):
    #     uid = u['id']
    #     follower_list = getUsersFollower(uid)
    #     filePath = f'user_list/{uid}_follower_list.json'
    #     outputJson(filePath, follower_list)

    ancestor = 110365072
    '''
    Collet third layer user(second layer users' followers)
    Amount: ancestor x 1000(1 request)
    Rate limit: 15 requests per 15-minute
    '''
    # third_layer_user_list, total_collected_user_count = TreeNodeStrategy(ancestor)
    third_layer_user_list, total_user_list, total_collected_user_count = getTree(ancestor)
    print(f'\ntotal colleted user from {ancestor}: {total_collected_user_count}')
    
    '''
    Collect users' liked history
    Amount: 
    Rate limit: 75 requests per 15-minute
    For each user give at most 5 requests
        (500 tweets to find video tweet),
        so 15 users per 15-minute in worst case
    '''
    # third_layer_liked_history_list, total_tweet_list, interaction_count = TreeLikedHistory(ancestor)
    third_layer_liked_history_list, total_tweet_list, interaction_count = getTreeLiked(ancestor)
    print(f'\ninteraction count: {sum(interaction_count.values())}')
    print(f'tweet count: {len(interaction_count)}')
    
    '''
    '''
    
    
#%%


