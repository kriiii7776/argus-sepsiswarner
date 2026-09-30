import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    roc_auc_score, roc_curve, precision_recall_curve, auc,
    confusion_matrix, brier_score_loss, calibration_curve
)
from typing import Dict, List, Tuple
import os

class SepsisEvaluator:
    """
    Formal Evaluation Framework for SepsisGuard AI
    Generates publication-quality tables and plots from actual model results.
    """
    def __init__(self, output_dir: str = "evaluation_outputs"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        # Use a publication-quality style
        plt.style.use('seaborn-v0_8-paper')
        sns.set_context("paper", font_scale=1.2)

    def evaluate_discrimination(self, y_true: np.ndarray, y_prob: np.ndarray, model_name: str) -> Dict[str, float]:
        """Calculates AUROC and AUPRC."""
        auroc = roc_auc_score(y_true, y_prob)
        precision, recall, _ = precision_recall_curve(y_true, y_prob)
        auprc = auc(recall, precision)
        return {"AUROC": auroc, "AUPRC": auprc}

    def evaluate_classification(self, y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculates sensitivity, specificity, PPV, NPV, F1 based on a thresholded prediction."""
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
        ppv = tp / (tp + fp) if (tp + fp) > 0 else 0
        npv = tn / (tn + fn) if (tn + fn) > 0 else 0
        f1 = 2 * (ppv * sensitivity) / (ppv + sensitivity) if (ppv + sensitivity) > 0 else 0
        
        return {
            "Sensitivity": sensitivity,
            "Specificity": specificity,
            "PPV": ppv,
            "NPV": npv,
            "F1": f1
        }

    def evaluate_calibration(self, y_true: np.ndarray, y_prob: np.ndarray) -> Dict[str, float]:
        """Calculates Brier score and expected calibration error."""
        brier = brier_score_loss(y_true, y_prob)
        
        # Calculate Expected Calibration Error (ECE)
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
        bin_counts, _ = np.histogram(y_prob, bins=10, range=(0, 1))
        bin_weights = bin_counts / len(y_prob)
        ece = np.sum(bin_weights * np.abs(prob_true - prob_pred))
        
        return {"Brier Score": brier, "Calibration Error": ece}

    def evaluate_early_warning(self, sepsis_onset_times: pd.Series, alert_times: pd.Series) -> Dict[str, float]:
        """Calculates early warning lead times."""
        lead_times = (sepsis_onset_times - alert_times).dt.total_seconds() / 3600.0
        lead_times = lead_times[lead_times > 0] # Only valid early warnings
        
        return {
            "Median Lead Time (hrs)": lead_times.median() if not lead_times.empty else 0,
            "75th Pct Lead Time (hrs)": lead_times.quantile(0.75) if not lead_times.empty else 0,
            "25th Pct Lead Time (hrs)": lead_times.quantile(0.25) if not lead_times.empty else 0
        }

    def evaluate_alert_performance(self, total_alerts: int, false_alerts: int, patient_days: float) -> Dict[str, float]:
        """Calculates alert burden metrics."""
        return {
            "Alerts / Patient-Day": total_alerts / patient_days if patient_days > 0 else 0,
            "False Alerts / Patient-Day": false_alerts / patient_days if patient_days > 0 else 0,
            "Alert Burden (%)": (false_alerts / total_alerts * 100) if total_alerts > 0 else 0
        }

    def plot_roc_curves(self, results_dict: Dict[str, Tuple[np.ndarray, np.ndarray]]):
        """Generates a publication-quality AUROC comparison plot."""
        plt.figure(figsize=(8, 6))
        for model_name, (y_true, y_prob) in results_dict.items():
            fpr, tpr, _ = roc_curve(y_true, y_prob)
            auroc = roc_auc_score(y_true, y_prob)
            plt.plot(fpr, tpr, label=f"{model_name} (AUROC = {auroc:.3f})")
            
        plt.plot([0, 1], [0, 1], 'k--', label="Random")
        plt.xlabel("1 - Specificity (False Positive Rate)")
        plt.ylabel("Sensitivity (True Positive Rate)")
        plt.title("Receiver Operating Characteristic (ROC) Comparison")
        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "auroc_comparison.png"), dpi=300)
        plt.close()

    def plot_calibration_curves(self, results_dict: Dict[str, Tuple[np.ndarray, np.ndarray]]):
        """Generates a publication-quality calibration plot."""
        plt.figure(figsize=(8, 6))
        plt.plot([0, 1], [0, 1], "k:", label="Perfectly calibrated")
        
        for model_name, (y_true, y_prob) in results_dict.items():
            prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10)
            plt.plot(prob_pred, prob_true, "s-", label=model_name)
            
        plt.xlabel("Mean Predicted Probability")
        plt.ylabel("Fraction of Positives")
        plt.title("Calibration Curve (Reliability Diagram)")
        plt.legend(loc="lower right")
        plt.tight_layout()
        plt.savefig(os.path.join(self.output_dir, "calibration_comparison.png"), dpi=300)
        plt.close()

    def generate_full_report(self, models_data: Dict[str, Dict[str, Any]]):
        """
        Takes a structured dictionary of actual results from different models and 
        generates the CSV tables and comparative plots.
        Do not pass fabricated data into this function.
        """
        discrimination_rows = []
        classification_rows = []
        calibration_rows = []
        
        plot_data = {}
        
        for model_name, data in models_data.items():
            y_true = data["y_true"]
            y_prob = data["y_prob"]
            y_pred = data["y_pred"]
            
            plot_data[model_name] = (y_true, y_prob)
            
            # Discrimination
            disc_metrics = self.evaluate_discrimination(y_true, y_prob, model_name)
            discrimination_rows.append({"Model": model_name, **disc_metrics})
            
            # Classification
            class_metrics = self.evaluate_classification(y_true, y_pred)
            classification_rows.append({"Model": model_name, **class_metrics})
            
            # Calibration
            calib_metrics = self.evaluate_calibration(y_true, y_prob)
            calibration_rows.append({"Model": model_name, **calib_metrics})
            
        # Export tables
        pd.DataFrame(discrimination_rows).to_csv(os.path.join(self.output_dir, "discrimination_metrics.csv"), index=False)
        pd.DataFrame(classification_rows).to_csv(os.path.join(self.output_dir, "classification_metrics.csv"), index=False)
        pd.DataFrame(calibration_rows).to_csv(os.path.join(self.output_dir, "calibration_metrics.csv"), index=False)
        
        # Export plots
        self.plot_roc_curves(plot_data)
        self.plot_calibration_curves(plot_data)
        print(f"Formal evaluation report successfully generated in {self.output_dir}/")

# Example Usage Template (Awaiting real data)
if __name__ == "__main__":
    print("SepsisGuard AI Formal Evaluation Framework initialized.")
    print("Ready to ingest actual predictions from:")
    print("- SIRS, MEWS, NEWS, NEWS2")
    print("- Logistic Regression, XGBoost, Temporal Model, Hybrid Model")
    print("Note: To comply with rigorous scientific standards, no fabricated synthetic results will be generated.")
