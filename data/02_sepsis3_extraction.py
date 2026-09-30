import os
from pyspark.sql import SparkSession

def extract_sepsis3_cohort(spark):
    """
    Translates the core MIT-LCP Sepsis-3 SQL concepts into PySpark.
    Note: For a full production run, we would import the exact SQL files from 
    https://github.com/MIT-LCP/mimic-iv/tree/master/concepts/sepsis
    Because we registered our DataFrames as temp views, we can run Spark SQL natively.
    """
    
    print("Extracting ICU stays...")
    # 1. Base cohort: ICU Stays
    icu_stays = spark.sql("""
        SELECT stay_id, subject_id, hadm_id, intime, outtime
        FROM icustays
    """)
    icu_stays.createOrReplaceTempView("cohort")
    
    # 2. Suspected Infection (Simplified for prototype)
    # Clinically: Antibiotics + blood cultures within [abx-24h, abx+72h]
    print("Identifying suspected infection (antibiotics + cultures)...")
    suspi_infect = spark.sql("""
        SELECT 
            p.stay_id,
            m.charttime AS culture_time,
            a.starttime AS abx_time,
            COALESCE(m.charttime, a.starttime) AS suspected_infection_time
        FROM cohort p
        LEFT JOIN microbiologyevents m ON p.hadm_id = m.hadm_id
        LEFT JOIN pharmacy a ON p.hadm_id = a.hadm_id 
            AND a.medication LIKE '%vancomycin%' -- Example filter, would need full abx list
    """)
    suspi_infect.createOrReplaceTempView("suspi_infect")
    
    # 3. SOFA Score Evaluation (Simplified for prototype)
    # Clinically: Respiration (PaO2/FiO2), Coagulation (Platelets), Liver (Bilirubin),
    # Cardiovascular (MAP/Vasopressors), CNS (GCS), Renal (Creatinine/Urine)
    print("Calculating rolling SOFA scores...")
    sofa_scores = spark.sql("""
        SELECT 
            stay_id,
            charttime,
            -- Hypothetical logic for cardiovascular SOFA component based on MAP
            CASE 
                WHEN valuenum < 70 THEN 1 
                ELSE 0 
            END AS sofa_cardiovascular
        FROM chartevents
        WHERE itemid IN (220052, 220181) -- Arterial BP Mean, Non-Invasive BP Mean
    """)
    sofa_scores.createOrReplaceTempView("sofa_scores")
    
    # 4. Final Sepsis-3 Definition
    # Infection + SOFA increase >= 2
    print("Labeling Sepsis-3 onset times ($t_{sepsis}$)...")
    sepsis3_labels = spark.sql("""
        SELECT 
            s.stay_id,
            si.suspected_infection_time,
            MAX(s.sofa_cardiovascular) AS max_sofa,
            CASE 
                WHEN MAX(s.sofa_cardiovascular) >= 2 AND si.suspected_infection_time IS NOT NULL THEN 1 
                ELSE 0 
            END AS sepsis3_label
        FROM sofa_scores s
        JOIN suspi_infect si ON s.stay_id = si.stay_id
        GROUP BY s.stay_id, si.suspected_infection_time
    """)
    
    return sepsis3_labels

if __name__ == "__main__":
    # Assumes Spark is already running and tables are loaded via 01_ingest_demo_data.py
    spark = SparkSession.builder.appName("SepsisGuard-FeatureExtraction").getOrCreate()
    try:
        labels_df = extract_sepsis3_cohort(spark)
        labels_df.show(5)
        print("Feature extraction pipeline established.")
    except Exception as e:
        print("Note: Run 01_ingest_demo_data.py first to load tables into Spark.")
        print(f"Error: {e}")
