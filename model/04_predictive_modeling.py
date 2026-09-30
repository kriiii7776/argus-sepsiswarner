import pandas as pd
import numpy as np
import xgboost as xgb
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    roc_auc_score, average_precision_score, confusion_matrix,
    f1_score, brier_score_loss, classification_report
)
from sklearn.impute import SimpleImputer
import shap

def grouped_train_val_test_split(df, group_col, test_size=0.15, val_size=0.15, random_state=42):
    """
    Splits the data into train, val, and test sets ensuring no patient overlaps.
    70% Train, 15% Val, 15% Test.
    """
    print("Splitting data ensuring patient-level separation...")
    
    # First split: Train vs (Val + Test)
    # Val + Test combined size = 0.30
    gss1 = GroupShuffleSplit(n_splits=1, test_size=(test_size + val_size), random_state=random_state)
    train_idx, val_test_idx = next(gss1.split(df, groups=df[group_col]))
    
    train_df = df.iloc[train_idx]
    val_test_df = df.iloc[val_test_idx]
    
    # Second split: Val vs Test
    # Relative test size = 0.15 / 0.30 = 0.50
    gss2 = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=random_state)
    val_idx, test_idx = next(gss2.split(val_test_df, groups=val_test_df[group_col]))
    
    val_df = val_test_df.iloc[val_idx]
    test_df = val_test_df.iloc[test_idx]
    
    print(f"Train patients: {train_df[group_col].nunique()}")
    print(f"Val patients: {val_df[group_col].nunique()}")
    print(f"Test patients: {test_df[group_col].nunique()}")
    
    return train_df, val_df, test_df

def calculate_scale_pos_weight(y_train):
    """Calculates class weight strictly from the training set."""
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    # Avoid division by zero in demo edge cases
    return n_neg / n_pos if n_pos > 0 else 1.0

def evaluate_model(y_true, y_probs, threshold=0.5):
    """Calculates comprehensive clinical and statistical metrics."""
    y_pred = (y_probs >= threshold).astype(int)
    
    auroc = roc_auc_score(y_true, y_probs)
    auprc = average_precision_score(y_true, y_probs)
    brier = brier_score_loss(y_true, y_probs)
    f1 = f1_score(y_true, y_pred)
    
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    ppv = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    npv = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    
    return {
        "AUROC": auroc,
        "AUPRC": auprc,
        "Brier Score": brier,
        "F1 Score": f1,
        "Sensitivity (Recall)": sensitivity,
        "Specificity": specificity,
        "PPV (Precision)": ppv,
        "NPV": npv
    }

def train_and_evaluate_models(X_train, y_train, X_val, y_val, X_test, y_test):
    """
    Trains LR, XGBoost, and LightGBM models.
    """
    results = {}
    
    # 1. Logistic Regression (Baseline)
    print("\n--- Training Logistic Regression ---")
    # LR cannot handle NaNs, requires imputation. We fit imputer strictly on train.
    imputer = SimpleImputer(strategy='median')
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)
    
    lr = LogisticRegression(class_weight='balanced', max_iter=1000)
    lr.fit(X_train_imp, y_train)
    lr_probs = lr.predict_proba(X_test_imp)[:, 1]
    results['Logistic Regression'] = evaluate_model(y_test, lr_probs)
    
    # Calculate scale_pos_weight for trees
    spw = calculate_scale_pos_weight(y_train)
    print(f"\nCalculated scale_pos_weight from train data: {spw:.2f}")
    
    # 2. XGBoost (Primary)
    print("\n--- Training XGBoost ---")
    xgb_model = xgb.XGBClassifier(
        scale_pos_weight=spw,
        eval_metric='aucpr',
        early_stopping_rounds=10,
        random_state=42,
        # Let XGBoost handle NaNs natively
        missing=np.nan 
    )
    # Using validation set for early stopping
    xgb_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False
    )
    xgb_probs = xgb_model.predict_proba(X_test)[:, 1]
    results['XGBoost'] = evaluate_model(y_test, xgb_probs)
    
    # 3. LightGBM (Comparator)
    print("\n--- Training LightGBM ---")
    lgb_model = lgb.LGBMClassifier(
        class_weight='balanced',
        random_state=42
    )
    lgb_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        eval_metric='aucpr'
    )
    lgb_probs = lgb_model.predict_proba(X_test)[:, 1]
    results['LightGBM'] = evaluate_model(y_test, lgb_probs)
    
    # Print Results
    print("\n=== Model Comparison (Test Set) ===")
    for model_name, metrics in results.items():
        print(f"\n{model_name}:")
        for k, v in metrics.items():
            print(f"  {k}: {v:.4f}")
            
    return xgb_model, results

def generate_shap_explanations(model, X_test):
    """Generates global and local SHAP explanations using TreeExplainer."""
    print("\n--- Generating SHAP Explanations ---")
    # Using the XGBoost model
    explainer = shap.TreeExplainer(model)
    # Calculate SHAP values for a subset (or all) of the test set
    shap_values = explainer.shap_values(X_test)
    print("SHAP values calculated successfully. Ready for visualization.")
    return explainer, shap_values

if __name__ == "__main__":
    print("Predictive Modeling Pipeline Initialized.")
    # In a full run, we would load the engineered features and labels here.
