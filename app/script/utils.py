import os

import pandas as pd

from script.s3_file import download, connect

pwd_dir = os.getcwd()

s3_connection = connect()

if not os.path.exists(pwd_dir + "/tmp/photos.json"):
    try:
        download(s3_connection, "raw-data", "yelp/images/photos.json")
    except Exception:
        pass

if os.path.exists(pwd_dir + "/tmp/photos.json"):
    imageJson = pd.read_json(pwd_dir + "/tmp/photos.json", lines=True)
else:
    imageJson = pd.DataFrame(columns=["business_id", "photo_id", "caption", "label"])


FALLBACK_IMAGE = "https://toohotel.com/wp-content/uploads/2022/09/TOO_restaurant_Panoramique_vue_Paris_nuit_v2-scaled.jpg"


def fetch_poster(res_id):
    try:
        row = imageJson[imageJson['business_id'] == res_id].iloc[0]
        photo = row['photo_id'] if 'photo_id' in imageJson.columns else row.iloc[3]
        local_path = pwd_dir + "/tmp/" + str(photo) + ".jpg"
        if not os.path.exists(local_path):
            download(s3_connection, "raw-data", "yelp/images/photos/" + str(photo) + ".jpg")
        return local_path
    except Exception:
        return FALLBACK_IMAGE
