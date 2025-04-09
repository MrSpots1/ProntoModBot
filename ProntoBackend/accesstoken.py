import os

def getAccesstoken():
    accesstoken = os.getenv("accesstoken")
    print(accesstoken)
    return accesstoken
