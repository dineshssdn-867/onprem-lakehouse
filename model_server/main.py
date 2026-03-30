import json
from flask import Flask, request
from pyspark.sql import SparkSession
from pyspark.ml.recommendation import ALSModel
from pyspark.sql.functions import explode, col


app = Flask(__name__)

MODEL_S3_PATH = "s3a://mlflow/models/restaurant_recommender"

spark = (SparkSession.builder
    .appName('Recommendation system')
    .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000")
    .config("spark.hadoop.fs.s3a.access.key", "minio")
    .config("spark.hadoop.fs.s3a.secret.key", "minio123")
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .getOrCreate()
)

_cached_model = None

@app.route('/api/', methods=['POST'])
def makecalc():
    data = request.get_json()
    user_id = data["userid"]
    res_num = data["res_num"]
    token = data["token"]
    if data["token"] != "systemapi":
        return f"Token not validate !"
        
    print(user_id, res_num) 
    json_path = write_file(data)
    user_data = prepare_data(json_path) 
    model = load_model() 
    prediction = predict(model, user_data, res_num)
    prediction.show() 
    return df_to_json(prediction) 

def write_file(data):
    with open("/opt/mlflow/data.json", "w") as f:
        json.dump(data, f)
    return "/opt/mlflow/data.json"

def load_model():
    global _cached_model
    if _cached_model is not None:
        return _cached_model
    print(f"Loading model from {MODEL_S3_PATH}...")
    _cached_model = ALSModel.load(MODEL_S3_PATH)
    return _cached_model

def prepare_data(data):
    print("Create dataframe...")
    df = spark.read.json(data).select("userid")
    df.show() 
    return df

def df_to_json(data):
    recommend_df = (data
        .withColumn("rec_exp", explode("recommendations"))\
        .select('userid', col("rec_exp.businessid"), col("rec_exp.rating"))
    )
    list_of_recommend = recommend_df.collect()

    alls = {
        "userid": "",
        "results": [],
        "businessid": [],
        "rating": []
    }
    for row in list_of_recommend:
        alls["userid"] = row[0]
        alls["businessid"].append(row[1])
        alls["rating"].append(row[2])
        alls["results"].append(
            {
                "businessid": row[1],
                "rating": row[2]
            }
        )

    return json.dumps(alls)
 
def predict(model, data, num):
    print("Predicting...")
    return model.recommendForUserSubset(data, num)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5001')