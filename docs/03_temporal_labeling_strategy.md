# SepsisGuard AI: Temporal Sepsis-Label Construction Strategy

A rigorous temporal strategy is the most critical component of an early-warning AI model. Poor temporal design inevitably leads to label leakage and immortal time bias.

## 1. Core Temporal Definitions

### 1.1 Sepsis-3 Labeling Definitions
1.  **Exact Positive-Event Definition:** An ICU stay where the patient develops Sepsis-3, defined as suspected infection (antibiotics + blood culture) accompanied by an acute increase in SOFA score $\ge$ 2 within the infection assessment window (-48h to +24h around the suspected infection).
2.  **Exact Negative-Event Definition:** An ICU stay where the patient *never* meets the Sepsis-3 criteria at any point during their admission.
3.  **Event Timestamp ($t_{sepsis}$):** The clinically defined onset of sepsis. Operationally, this is the *earlier* of the culture timestamp or the antibiotic administration timestamp, provided the SOFA increase condition is met.

### 1.2 Window Parameters
4.  **Prediction Horizon:** $H$ = 6 hours. The gap between the end of our data observation and the onset of sepsis. 
5.  **Observation Window:** $W$ = 4 hours. The period from which physiological features (mean, slopes, deltas) are aggregated to make a single prediction.
6.  **Exclusion Period:** The time equal to the Prediction Horizon ($H$). Data within this period is excluded from training because clinical interventions (fluids, oxygen) often begin here, leading to label leakage.
7.  **Pre-event Window:** The time from ICU admission to the start of the observation window.

## 2. Cohort Cohort Inclusion/Exclusion Logic

### 2.1 Post-Event and Multiple Events
8.  **Post-Event Handling:** **Strictly discard all data after $t_{sepsis}$ for positive patients.** Physiology after sepsis onset reflects treatment (e.g., vasopressors artificially raising BP), not the predictive physiological decline.
9.  **Multiple-Event Handling:** Only the **first** Sepsis-3 occurrence per ICU stay is used. Subsequent events are ignored to maintain independent and identically distributed (I.I.D.) assumptions and prevent data leakage.

### 2.2 Patient Sub-cohorts
10. **Already Septic at Admission:** **Excluded.** If $t_{sepsis} \le t_{ICU\_admit} + W + H$, the patient is excluded. We cannot provide a 6-hour "early warning" if they arrive septic.
11. **Develop Sepsis Later:** **Included as Positive.** We extract their observation window exactly at $[t_{sepsis} - H - W, t_{sepsis} - H]$.
12. **Never Develop Sepsis:** **Included as Negative.** We extract random or matched observation windows during their stay, provided the window ends at least $H$ hours before their discharge.
13. **Discharged Early:** **Excluded.** If the total ICU stay $< W + H$ (e.g., stay $< 10$ hours), they are excluded as there is insufficient data to observe.
14. **Missing Data Cases:** Retained (per our Phase 3 missingness strategy) unless 100% of vital signs are completely absent during the observation window.

---

## 3. Temporal Timeline Diagram

```text
Time --->

[Positive Patient Timeline]
ICU Admit                                                     Sepsis Onset (t_sepsis)
    |------------------|======================|-----------------------|xxxxxxxxxxxxxxxxxxxxx| Disch.
         Pre-Event       Observation Window     Prediction Horizon        Post-Event
         (Ignored)           (W = 4h)               (H = 6h)             (DISCARDED)
                       <--- Features Here ---> <--- Exclusion --->
                                              ^
                                      Prediction Time (t_pred)

[Negative Patient Timeline]
ICU Admit                                                                                   Disch.
    |------------------|======================|---------------------------------------------|
                         Observation Window     Control Horizon (Patient stays healthy)
                              (W = 4h)               (H = 6h)
                                              ^
                                      Prediction Time (t_pred)
```

---

## 4. Bias and Leakage Prevention

*   **Label Leakage:** Prevented by enforcing the Exclusion Period. We do not use features extracted right up to $t_{sepsis}$, as clinicians often order labs (lactate) or start undocumented fluids hours before the formal Sepsis-3 timestamp.
*   **Immortal Time Bias:** Prevented by ensuring control (negative) observation windows are sampled *strictly during* the patient's actual ICU stay. A control window must be valid; we cannot assign a prediction time if the patient was already dead or discharged.
*   **Temporal Leakage:** Prevented by strict chronological sorting and using only `ffill` (forward fill). `bfill` (backward fill) or linear interpolation are strictly prohibited as they pull future values into past predictions.
*   **Duplicated Patient Windows:** Positive patients contribute exactly ONE row to the training set (the window aligned with their first sepsis event). Negative patients contribute a matched number of windows, ensuring the model does not overfit to the baseline physiology of patients with long ICU stays.

---

## 5. Alternative Strategies & Recommendation

**Strategy A: Fixed-Window Alignment (Recommended)**
*   *Method:* Extract exactly one positive window per septic patient at $t_{sepsis} - 6h$, and randomly sample 1-3 valid windows per negative patient.
*   *Pros:* Computationally light; avoids over-representing long-stay patients; clean I.I.D. setup for training.
*   *Limitations:* Does not teach the model how a single patient transitions from healthy to septic over time (within-patient temporal variance is lost).

**Strategy B: Continuous Sliding Window**
*   *Method:* Generate a prediction every hour for every patient. Label all windows $\le 6h$ from onset as Positive, all others Negative.
*   *Pros:* Mimics real-world deployment perfectly; trains the model on the full trajectory.
*   *Limitations:* Massive class imbalance; requires complex grouped train/test splits; highly correlated sequential samples violate standard ML assumptions without temporal architectures (like RNNs).

**Recommendation:** For the initial XGBoost model, we will use **Strategy A (Fixed-Window)** to establish a clean, unbiased baseline. When moving to the Temporal Model (GRU/TCN) in later phases, we will shift to Strategy B.

---

## 6. Pseudocode / Algorithm

```python
def generate_labels(df_stays, df_sepsis_events, obs_win_hrs=4, pred_horizon_hrs=6):
    """
    Constructs the temporal labels based on Strategy A.
    """
    cohort = []
    
    # Merge stays with events (left join)
    patients = merge(df_stays, df_sepsis_events, on='stay_id', how='left')
    
    for patient in patients:
        stay_duration = patient.outtime - patient.intime
        min_required_time = obs_win_hrs + pred_horizon_hrs
        
        # Rule 13: Exclude short stays
        if stay_duration < min_required_time:
            continue
            
        if patient.is_septic:
            t_sepsis = patient.t_sepsis
            
            # Rule 10: Exclude already septic at admission
            if t_sepsis <= (patient.intime + min_required_time):
                continue
                
            # Define exact observation window for positive case
            obs_start = t_sepsis - pred_horizon_hrs - obs_win_hrs
            obs_end = t_sepsis - pred_horizon_hrs
            
            cohort.append({
                'stay_id': patient.stay_id,
                'label': 1,
                'obs_start': obs_start,
                'obs_end': obs_end
            })
            
        else:
            # Negative Patient (Rule 12)
            # Randomly select a valid observation end time during their stay
            # Must leave room for the prediction horizon before discharge
            valid_start_bound = patient.intime + obs_win_hrs
            valid_end_bound = patient.outtime - pred_horizon_hrs
            
            if valid_start_bound < valid_end_bound:
                # Randomly sample an end time
                obs_end = random_time_between(valid_start_bound, valid_end_bound)
                obs_start = obs_end - obs_win_hrs
                
                cohort.append({
                    'stay_id': patient.stay_id,
                    'label': 0,
                    'obs_start': obs_start,
                    'obs_end': obs_end
                })
                
    return cohort
```
