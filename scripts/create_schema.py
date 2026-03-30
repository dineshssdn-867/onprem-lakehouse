import os
from pyspark.sql import SparkSession
from datetime import date

from sparksession import spark_session


spark = spark_session(SparkSession)

spark.sql("CREATE NAMESPACE IF NOT EXISTS bronze")
spark.sql("CREATE NAMESPACE IF NOT EXISTS feature_store")
spark.sql("SHOW NAMESPACES").show()
