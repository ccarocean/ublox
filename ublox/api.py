import requests
import jwt
import datetime as dt


def send(url, key, data):
    headers = {"Content-Type": "application/octet-stream",
               "Bearer": sign(key)} #decode to unicode?
    upload = requests.post(url, data=data, headers=headers)
    if upload.status_code != 201:
        return False
    return True


def sign(key):
    return jwt.encode({'t': str((dt.datetime.utcnow()-dt.datetime(1970, 1, 1)).total_seconds())}, key, algorithm='RS256')
