import pyspark
from pyspark.sql import SparkSession
import pprint
import json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, ArrayType, FloatType, MapType
from pyspark.sql import Window
from math import radians, cos, sin, asin, sqrt
from pyspark.sql.functions import lead, udf, struct, col, from_json, explode, split

def To_numb(x):
  x['is_open'] = int(x['is_open'])
  x['review_count'] = int(x['review_count'])
  x['latitude'] = float(x['latitude'])
  x['longitude'] = float(x['longitude'])
  x['stars'] = float(x['stars'])
  return x

sc = pyspark.SparkContext()

#PACKAGE_EXTENSIONS= ('gs://hadoop-lib/bigquery/bigquery-connector-hadoop2-latest.jar')

bucket = sc._jsc.hadoopConfiguration().get('fs.gs.system.bucket')
project = sc._jsc.hadoopConfiguration().get('fs.gs.project.id')
input_directory = 'gs://{}/hadoop/tmp/bigquerry/pyspark_input'.format(bucket)
output_directory = 'gs://{}/pyspark_demo_output'.format(bucket)

spark = SparkSession \
  .builder \
  .master('yarn') \
  .appName('Yelp_Businesses') \
  .getOrCreate()

conf={
      'mapred.bq.project.id':project,
      'mapred.bq.gcs.bucket':bucket,
      'mapred.bq.temp.gcs.path':input_directory,
      'mapred.bq.input.project.id': "final-project-cs512-381002",
      'mapred.bq.input.dataset.id': 'Final_project_dataset',
      'mapred.bq.input.table.id': 'yelp_academic_dataset_business',
  }

## pull table from big query
table_data = sc.newAPIHadoopRDD(
    'com.google.cloud.hadoop.io.bigquery.JsonTextBigQueryInputFormat',
    'org.apache.hadoop.io.LongWritable',
    'com.google.gson.JsonObject',
    conf = conf)

## convert table to a json like object, turn PosTime and Fseen back into numbers... not sure why they changed
vals = table_data.values()
vals = vals.map(lambda line: json.loads(line))
vals = vals.map(To_numb)

#schema
schema = StructType([
    StructField("business_id", StringType(), True),
    StructField("city", StringType(), True),
    StructField("hours", StringType(), True),
    StructField("is_open", IntegerType(), True),
    StructField("latitude", FloatType(), True),
    StructField("longitude", FloatType(), True),
    StructField("name", StringType(), True),
    StructField("review_count", IntegerType(), True),
    StructField("stars", FloatType(), True),
    StructField("categories", StringType(), True),
    StructField("state", StringType(), True)
])

## create a dataframe object
df1 = spark.createDataFrame(vals, schema=schema)

df_high_rated = df1.filter(df1.stars >= 4)

df_categories = df_high_rated.select(explode(split(df_high_rated.categories, ",\s*")).alias("category"))

df_category_counts = df_categories.groupBy("category").count()
df_category_counts = df_category_counts.sort("count", ascending=False)
df_category_counts.show(10, truncate=False)


## deletes the temporary files
input_path = sc._jvm.org.apache.hadoop.fs.Path(input_directory)
input_path.getFileSystem(sc._jsc.hadoopConfiguration()).delete(input_path, True)
