import os
from pyspark.sql import SparkSession
from datetime import date

from sparksession import spark_session


spark = spark_session(SparkSession)

spark.sql("CREATE NAMESPACE IF NOT EXISTS feature_store")
df = spark.read.table("bronze.review")
df = df.select("business_id", "user_id", "stars", "date")
df.writeTo("feature_store.review").using("iceberg").createOrReplace()
spark.sql("SHOW TABLES IN feature_store").show()
