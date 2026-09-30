"""Patient-level ablation: engineered features with vs without personal baselines.

The same GroupShuffleSplit partitions, XGBoost tuning protocol, class weighting,
early stopping, validation calibration, and alert threshold are used in both
arms. The validation table is the selection evidence; test metrics are emitted
only after the comparison definition is frozen.
"""
import importlib.util
import json
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

tab = load(os.path.join(os.path.dirname(__file__), '05_train_models.py'), 'tabular')
feat = load(os.path.join(ROOT, 'data', '03_feature_engineering.py'), 'features')

BASELINE_VALUES = ('hr_curr', 'map_curr', 'rr_curr', 'spo2_curr', 'temp_curr',
                   'lactate', 'creatinine', 'wbc', 'platelet')

def evaluate_arm(train, val, test, features, arm_name):
    """Train a fully independent XGBoost arm; no features are learned on test."""
    Xt, Xv, Xte = train[features].values, val[features].values, test[features].values
    yt, yv, yte = train.label, val.label, test.label.values
    spw = (yt == 0).sum() / max((yt == 1).sum(), 1)
    model, calibrator, seconds, cv_auc = tab.train_xgboost(Xt, yt, Xv, yv, train.subject_id.values, spw)
    val_p = calibrator.predict_proba(model.predict_proba(Xv)[:, 1])
    val_metrics = tab.compute_metrics(yv.values, val_p, f'{arm_name} validation')
    # This is the only test prediction pass for this arm.
    test_p = calibrator.predict_proba(model.predict_proba(Xte)[:, 1])
    test_metrics = tab.compute_metrics(yte, test_p, arm_name)
    return {'validation': val_metrics, 'test': test_metrics, 'train_seconds': seconds, 'cv_auroc': cv_auc,
            'n_features': len(features)}

def main():
    source = 'data/processed/aligned_cohort.parquet'
    frame = pd.read_parquet(source) if os.path.exists(source) else tab.generate_demo_dataset()
    # This transform is causal within a stay, so it can run before splitting;
    # it never pools patients or reads a later timestamp.
    enhanced = feat.add_personalized_baseline_features(frame, BASELINE_VALUES)
    train, val, test = tab.patient_split(enhanced)
    excluded = {'subject_id', 'stay_id', 'hour', 'label', 'charttime', 'intime', 'outtime'}
    raw_features = [c for c in frame if c not in excluded]
    personal = [c for c in enhanced if ('_baseline' in c or '_deviation_from_baseline' in c)]
    with_personal = raw_features + [c for c in personal if c not in raw_features]
    no_personal = evaluate_arm(train, val, test, raw_features, 'XGBoost without personalized features')
    with_personal_result = evaluate_arm(train, val, test, with_personal, 'XGBoost with personalized features')
    rows = []
    for label, result in (('Without personalized features', no_personal), ('With personalized features', with_personal_result)):
        rows.append({'Arm': label, **{f'Validation {k}': v for k, v in result['validation'].items() if k != 'model'},
                     **{f'Test {k}': v for k, v in result['test'].items() if k != 'model'},
                     'Features': result['n_features'], 'Train seconds': result['train_seconds'], 'CV AUROC': result['cv_auroc']})
    comparison = pd.DataFrame(rows).set_index('Arm')
    os.makedirs('model', exist_ok=True)
    comparison.to_csv('model/personalized_baseline_ablation.csv')
    selected = comparison['Validation AUPRC'].idxmax()
    with open('model/personalized_baseline_ablation_decision.json', 'w') as f:
        json.dump({'selected_arm': selected, 'selection_split': 'validation only',
                   'test_use': 'final reporting only after arm selection',
                   'baseline_method': 'causal robust median/MAD reference interval'}, f, indent=2)
    print(comparison.round(4).to_string())

if __name__ == '__main__':
    main()
