import os
from pyspark.sql import SparkSession
from datetime import date

from sparksession import spark_session


spark = spark_session(SparkSession)

df = spark.read.json("s3a://raw-data/yelp/json/yelp_academic_dataset_review.json")
df.writeTo("bronze.review").using("iceberg").createOrReplace()
spark.sql("SHOW TABLES IN bronze").show()
