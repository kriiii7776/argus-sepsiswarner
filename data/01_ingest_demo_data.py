import os
import urllib.request
import zipfile
from pyspark.sql import SparkSession

def download_mimic_demo(download_dir="data/raw"):
    # Using the publicly available MIMIC-IV Clinical Database Demo (v2.2)
    # This dataset contains ~100 patients and does not require credentialing.
    url = "https://physionet.org/static/published-projects/mimic-iv-demo/mimic-iv-clinical-database-demo-2.2.zip"
    os.makedirs(download_dir, exist_ok=True)
    zip_path = os.path.join(download_dir, "mimic_demo.zip")
    
    if not os.path.exists(zip_path):
        print(f"Downloading MIMIC-IV Demo dataset from {url}...")
        urllib.request.urlretrieve(url, zip_path)
        print("Download complete.")
        
        print("Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(download_dir)
        print("Extraction complete.")
    else:
        print("Dataset already downloaded.")
        
    return os.path.join(download_dir, "mimic-iv-clinical-database-demo-2.2")

def init_spark():
    return SparkSession.builder \
        .appName("SepsisGuard-DataPrep") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()

def load_tables_to_spark(spark, data_dir):
    """
    Loads core MIMIC-IV tables into Spark Temp Views so we can 
    use the MIT-LCP SQL scripts natively.
    """
    modules = ['core', 'hosp', 'icu']
    tables_registered = []
    
    for module in modules:
        module_path = os.path.join(data_dir, module)
        if not os.path.exists(module_path):
            continue
            
        for file in os.listdir(module_path):
            if file.endswith(".csv.gz"):
                table_name = file.replace(".csv.gz", "")
                file_path = os.path.join(module_path, file)
                
                # Load CSV into Spark DataFrame
                df = spark.read.csv(file_path, header=True, inferSchema=True)
                
                # Register as a temporary SQL view
                df.createOrReplaceTempView(table_name)
                tables_registered.append(table_name)
                
    print(f"Registered {len(tables_registered)} tables in Spark SQL.")
    return tables_registered

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    raw_data_dir = os.path.join(base_dir, "raw")
    
    extracted_dir = download_mimic_demo(raw_data_dir)
    
    spark = init_spark()
    print(f"Spark initialized: {spark.version}")
    
    tables = load_tables_to_spark(spark, extracted_dir)
    print("Available tables:", tables)
