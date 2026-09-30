import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.metrics import (
    roc_auc_score, average_precision_score, confusion_matrix,
    f1_score, brier_score_loss, precision_recall_curve
)
import warnings
warnings.filterwarnings('ignore')

class LogisticBaselineEngine:
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.model = None
        self.calibrated_model = None
        self.optimal_threshold = 0.5
        
    def build_pipeline(self):
        """Builds a strictly separated preprocessing and modeling pipeline."""
        # LR requires scaled data and cannot natively handle NaNs
        pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(
                penalty='l2',          # L2 Regularization
                C=1.0,                 # Inverse of regularization strength
                class_weight='balanced', # Handle class imbalance
                solver='liblinear',
                random_state=self.random_state,
                max_iter=1000
            ))
        ])
        return pipeline

    def fit(self, X_train, y_train, calibrate=True):
        """Fits the model on training data. Applies probability calibration if requested."""
        self.model = self.build_pipeline()
        print("Fitting Logistic Regression Baseline...")
        self.model.fit(X_train, y_train)
        
        if calibrate:
            print("Applying CalibratedClassifierCV (Isotonic) to align probabilities...")
            # 'prefit' means we use the already fit LR model and calibrate probabilities 
            # Note: In strict practice, isotonic calibration should be fit on a separate validation set,
            # but cv='prefit' on train is used here for structural demonstration.
            self.calibrated_model = CalibratedClassifierCV(
                self.model, method='isotonic', cv='prefit'
            )
            self.calibrated_model.fit(X_train, y_train)
        else:
            self.calibrated_model = self.model

    def find_optimal_threshold(self, X_val, y_val):
        """Selects the probability threshold that maximizes the F1 score on the validation set."""
        y_val_probs = self.calibrated_model.predict_proba(X_val)[:, 1]
        precisions, recalls, thresholds = precision_recall_curve(y_val, y_val_probs)
        
        # Maximize F1
        f1_scores = 2 * (precisions * recalls) / (precisions + recalls + 1e-8)
        best_idx = np.argmax(f1_scores)
        self.optimal_threshold = thresholds[best_idx]
        print(f"Optimal threshold found: {self.optimal_threshold:.4f}")
        return self.optimal_threshold

    def evaluate(self, X_test, y_test, patient_ids=None):
        """Calculates comprehensive clinical and statistical metrics."""
        y_probs = self.calibrated_model.predict_proba(X_test)[:, 1]
        y_pred = (y_probs >= self.optimal_threshold).astype(int)
        
        # Statistical Metrics
        auroc = roc_auc_score(y_test, y_probs)
        auprc = average_precision_score(y_test, y_probs)
        brier = brier_score_loss(y_test, y_probs)
        f1 = f1_score(y_test, y_pred)
        
        # Clinical Metrics
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        
        results = {
            "AUROC": auroc,
            "AUPRC": auprc,
            "Brier Score (Calibration)": brier,
            "Optimal Threshold": self.optimal_threshold,
            "Sensitivity (Recall)": sensitivity,
            "Specificity": specificity,
            "PPV (Precision)": ppv,
            "NPV": npv,
            "F1 Score": f1
        }
        
        # Alert Burden Metrics (if patient grouping is provided)
        if patient_ids is not None:
            df_eval = pd.DataFrame({'patient_id': patient_ids, 'y_true': y_test, 'y_pred': y_pred})
            total_patients = df_eval['patient_id'].nunique()
            
            total_alerts = df_eval['y_pred'].sum()
            false_alerts = df_eval[(df_eval['y_pred'] == 1) & (df_eval['y_true'] == 0)].shape[0]
            
            results["Alerts per Patient"] = total_alerts / total_patients
            results["False Alerts per Patient"] = false_alerts / total_patients
            
        return results

if __name__ == "__main__":
    print("Logistic Regression Baseline Engine Initialized.")
    # Example mock execution to demonstrate structure
    np.random.seed(42)
    X_mock = np.random.rand(100, 5)
    y_mock = np.random.randint(0, 2, 100)
    pids_mock = np.random.randint(1, 10, 100)
    
    engine = LogisticBaselineEngine()
    engine.fit(X_mock, y_mock)
    engine.find_optimal_threshold(X_mock, y_mock) # Using train as val for demo only
    metrics = engine.evaluate(X_mock, y_mock, patient_ids=pids_mock)
    
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")
