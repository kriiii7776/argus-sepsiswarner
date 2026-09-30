import pandas as pd
import numpy as np
import logging
import yaml
import os

# Set up logging strategy
logging.basicConfig(
    filename='pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SepsisGuardPipeline")

class MIMICPipeline:
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        logger.info(f"Pipeline initialized with config version: {self.config['pipeline']['version']}")
        
    def execute_sql_extraction(self):
        """Step 1: Extract and join tables, filtering to ICU stays only."""
        logger.info("Starting SQL extraction...")
        # Placeholder for actual database connection
        # e.g., pd.read_sql(sql_query, con=engine)
        
        # Simulated raw dataframe
        df = pd.DataFrame({
            'stay_id': [1, 1],
            'charttime': ['2100-01-01 10:00:00', '2100-01-01 10:30:00'],
            'itemid': [223762, 220045], # Temp F, HR
            'valuenum': [101.5, 315.0]
        })
        logger.info(f"Extracted {len(df)} rows.")
        return df

    def normalize_units(self, df):
        """Step 2: Convert divergent units (e.g., Fahrenheit to Celsius)."""
        logger.info("Normalizing units...")
        
        temp_f_ids = self.config['item_mappings']['temp_f']
        
        # Temp Conversion
        mask = df['itemid'].isin(temp_f_ids)
        df.loc[mask, 'valuenum'] = (df.loc[mask, 'valuenum'] - 32) * 5/9
        # Assuming we then map all temp_f items to the temp_c item ID for consistency
        df.loc[mask, 'itemid'] = self.config['item_mappings']['temp_c'][0]
        
        logger.info(f"Converted {mask.sum()} Temperature (F) rows to Celsius.")
        return df

    def handle_implausible_values(self, df):
        """Step 3: Remove known sensor artifacts based on config thresholds."""
        logger.info("Cleaning physiologically implausible values...")
        initial_len = len(df)
        
        # Heart Rate Thresholds
        hr_ids = self.config['item_mappings']['heart_rate']
        hr_mask = df['itemid'].isin(hr_ids)
        hr_invalid = hr_mask & ((df['valuenum'] < self.config['normalization']['hr_min']) | 
                                (df['valuenum'] > self.config['normalization']['hr_max']))
        
        df.loc[hr_invalid, 'valuenum'] = np.nan
        dropped_hr = hr_invalid.sum()
        
        if dropped_hr > 0:
            logger.warning(f"Set {dropped_hr} implausible Heart Rate values to NaN.")
            
        # Add checks for MAP, Temp, etc.
        
        return df

    def data_quality_checks(self, df):
        """Validation step to ensure data integrity before saving."""
        logger.info("Running Data Quality Checks...")
        
        # Check 1: No remaining Fahrenheits
        temp_f_ids = self.config['item_mappings']['temp_f']
        if df['itemid'].isin(temp_f_ids).any():
            logger.error("Data Quality Failure: Fahrenheit itemids remain after normalization.")
            raise ValueError("Fahrenheit values detected.")
            
        # Check 2: Check null percentage
        null_pct = df['valuenum'].isna().mean() * 100
        logger.info(f"Overall valuenum missingness: {null_pct:.2f}%")
        if null_pct > 20.0:
            logger.warning("High missingness detected across value column.")
            
        logger.info("Data Quality Checks passed.")

    def run(self):
        """Orchestrates the pipeline."""
        logger.info("--- Pipeline Run Started ---")
        try:
            df = self.execute_sql_extraction()
            df = self.normalize_units(df)
            df = self.handle_implausible_values(df)
            self.data_quality_checks(df)
            
            # Save intermediate
            # df.to_parquet('data/interim/icu_events.parquet')
            logger.info("--- Pipeline Run Completed Successfully ---")
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    # Create dummy config for test execution
    dummy_config = {
        'pipeline': {'version': '1.0.0'},
        'item_mappings': {'temp_f': [223762], 'temp_c': [223761], 'heart_rate': [220045]},
        'normalization': {'hr_min': 0, 'hr_max': 300}
    }
    with open("config.yaml", "w") as f:
        yaml.dump(dummy_config, f)
        
    pipeline = MIMICPipeline("config.yaml")
    pipeline.run()
