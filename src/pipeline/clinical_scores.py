import pandas as pd
import numpy as np

class ClinicalBaselineEngine:
    """
    Independent engine for calculating traditional clinical early-warning scores.
    These scores are used strictly as a baseline comparator to SepsisGuard AI.
    NOTE: These scores do not diagnose sepsis. They evaluate non-specific physiological deterioration.
    """
    
    def __init__(self):
        # Explicit definitions of required variables for each score
        self.sirs_req = ['temp_c', 'heart_rate', 'resp_rate', 'wbc']
        self.mews_req = ['resp_rate', 'heart_rate', 'sbp', 'temp_c', 'gcs'] # GCS proxies AVPU
        self.news2_req = ['resp_rate', 'spo2', 'sbp', 'heart_rate', 'temp_c', 'gcs'] # Excluding 'on_oxygen' for simplicity in missingness
        
    def calculate_sirs(self, row):
        """
        SIRS Criteria (ACCP/SCCM Consensus 1992)
        Max points: 4
        """
        score = 0
        components = {}
        missing = []
        
        # Temp < 36 or > 38
        if pd.isna(row.get('temp_c')): missing.append('temp_c')
        else:
            v = row['temp_c']
            components['temp_c'] = v
            if v < 36.0 or v > 38.0: score += 1
                
        # HR > 90
        if pd.isna(row.get('heart_rate')): missing.append('heart_rate')
        else:
            v = row['heart_rate']
            components['heart_rate'] = v
            if v > 90: score += 1
                
        # RR > 20 (PaCO2 excluded due to rarity in continuous streams)
        if pd.isna(row.get('resp_rate')): missing.append('resp_rate')
        else:
            v = row['resp_rate']
            components['resp_rate'] = v
            if v > 20: score += 1
                
        # WBC < 4 or > 12 (bands excluded due to MIMIC extraction complexity)
        if pd.isna(row.get('wbc')): missing.append('wbc')
        else:
            v = row['wbc']
            components['wbc'] = v
            if v < 4.0 or v > 12.0: score += 1
                
        validity = "VALID" if len(missing) == 0 else "PARTIAL" if len(missing) < 4 else "INVALID"
        
        return {
            'score_type': 'SIRS_1992',
            'score': score if validity != "INVALID" else np.nan,
            'components': components,
            'missing': missing,
            'validity': validity
        }

    def calculate_mews(self, row):
        """
        Modified Early Warning Score (Subbe et al., 2001)
        """
        score = 0
        components = {}
        missing = []
        
        # RR
        if pd.isna(row.get('resp_rate')): missing.append('resp_rate')
        else:
            v = row['resp_rate']
            components['resp_rate'] = v
            if v < 9: score += 2
            elif 15 <= v <= 20: score += 1
            elif 21 <= v <= 29: score += 2
            elif v >= 30: score += 3
                
        # HR
        if pd.isna(row.get('heart_rate')): missing.append('heart_rate')
        else:
            v = row['heart_rate']
            components['heart_rate'] = v
            if v <= 40: score += 2
            elif 41 <= v <= 50: score += 1
            elif 101 <= v <= 110: score += 1
            elif 111 <= v <= 129: score += 2
            elif v >= 130: score += 3
                
        # SBP
        if pd.isna(row.get('sbp')): missing.append('sbp')
        else:
            v = row['sbp']
            components['sbp'] = v
            if v <= 70: score += 3
            elif 71 <= v <= 80: score += 2
            elif 81 <= v <= 100: score += 1
            elif v >= 200: score += 2
                
        # Temp
        if pd.isna(row.get('temp_c')): missing.append('temp_c')
        else:
            v = row['temp_c']
            components['temp_c'] = v
            if v < 35.0 or v >= 38.5: score += 2

        validity = "VALID" if len(missing) == 0 else "PARTIAL" if len(missing) < len(self.mews_req) else "INVALID"
        
        return {
            'score_type': 'MEWS_2001',
            'score': score if validity != "INVALID" else np.nan,
            'components': components,
            'missing': missing,
            'validity': validity
        }

    def calculate_news2(self, row):
        """NEWS2 Scale 1; oxygen and consciousness are explicit requirements.

        A partial score is returned for bedside transparency, but downstream
        model comparison must exclude PARTIAL rows or report their coverage.
        """
        score, components, missing = 0, {}, []
        def get(name):
            if pd.isna(row.get(name)):
                missing.append(name); return None
            components[name] = row[name]; return row[name]
        rr = get('resp_rate')
        if rr is not None: score += 3 if rr <= 8 or rr >= 25 else 2 if rr <= 11 else 1 if rr <= 20 else 0
        spo2 = get('spo2')
        if spo2 is not None: score += 3 if spo2 <= 91 else 2 if spo2 <= 93 else 1 if spo2 <= 95 else 0
        oxygen = get('on_oxygen')
        if oxygen is not None and bool(oxygen): score += 2
        sbp = get('sbp')
        if sbp is not None: score += 3 if sbp <= 90 or sbp >= 220 else 2 if sbp <= 100 else 1 if sbp <= 110 else 0
        hr = get('heart_rate')
        if hr is not None: score += 3 if hr <= 40 or hr >= 131 else 2 if hr <= 50 or hr >= 111 else 1 if 91 <= hr <= 110 else 0
        temp = get('temp_c')
        if temp is not None: score += 3 if temp <= 35.0 else 2 if temp >= 39.1 else 1 if temp <= 36.0 or temp >= 38.1 else 0
        gcs = get('gcs')
        if gcs is not None and gcs < 15: score += 3
        validity = 'VALID' if not missing else 'PARTIAL' if len(missing) < len(self.news2_req) else 'INVALID'
        return {'score_type': 'NEWS2_Scale1_2017', 'score': score if validity != 'INVALID' else np.nan,
                'components': components, 'missing': missing, 'validity': validity}
        
    def evaluate_patient_state(self, stay_id, timestamp, vitals_dict):
        """
        Evaluates a single patient at a specific timestamp across all available baseline rules.
        """
        row_series = pd.Series(vitals_dict)
        
        sirs_result = self.calculate_sirs(row_series)
        mews_result = self.calculate_mews(row_series)
        news2_result = self.calculate_news2(row_series)
        
        return {
            'stay_id': stay_id,
            'timestamp': timestamp,
            'baselines': [sirs_result, mews_result, news2_result]
        }

if __name__ == "__main__":
    engine = ClinicalBaselineEngine()
    
    # Example evaluation
    mock_patient = {
        'heart_rate': 115,
        'resp_rate': 24,
        'temp_c': 38.6,
        'sbp': 85,
        'wbc': 15.2,
        'gcs': 15
    }
    
    result = engine.evaluate_patient_state(stay_id=9999, timestamp="2100-01-01 12:00", vitals_dict=mock_patient)
    import json
    print(json.dumps(result, indent=2))
