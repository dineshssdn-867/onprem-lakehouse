import json
import os

import requests


def request_recommend(data: dict) -> dict:

    host = os.environ.get("MODEL_SERVER_HOST", "recommender_model")
    port = os.environ.get("MODEL_SERVER_PORT", "5001")
    url = f'http://{host}:{port}/api'

    j_data = json.dumps(data)

    headers = {
        'content-type': 'application/json',
        'Accept-Charset': 'UTF-8'
        }

    response = requests.post(url, data=j_data, headers=headers)
    if response.status_code != 200:
        return (f"Error: {response.status_code}")
    return response.json()
