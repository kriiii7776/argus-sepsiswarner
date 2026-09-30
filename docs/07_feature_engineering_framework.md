# SepsisGuard AI: Comprehensive Feature Engineering Framework

This document outlines the complete mathematical and clinical feature space extracted during the Observation Window (e.g., $W=4\text{h}$) to capture the dynamic physiological decline characteristic of sepsis.

---

## 1. Feature Categories

### A. Current Physiological Values
*   **Definition:** The value recorded in the most recent 1-hour bin ($t_{current}$).
*   **Variables:** `HR_curr`, `MAP_curr`, `RR_curr`, `SpO2_curr`, `Temp_curr`.
*   **Rationale:** Baseline state of the patient at the moment of prediction.

### B. Rolling Statistics (4h Window)
*   **Mean/Median:** `HR_mean_4h`, `HR_median_4h`. Captures central tendency.
*   **Min/Max:** `MAP_min_4h`, `Temp_max_4h`. Captures the absolute physiological limits reached.

### C. Trend / Slope Features
*   **Delta:** $\Delta 1\text{h} = V_t - V_{t-1}$; $\Delta 4\text{h} = V_t - V_{t-4}$
*   **Slope:** $\frac{\Delta 4\text{h}}{4}$. Captures the linear trajectory.
*   **Percentage Change:** $\frac{V_t - V_{t-4}}{V_{t-4}} \times 100$

### D. Rate-of-Change & F. Acceleration Features
*   **Acceleration:** $\Delta 1\text{h}_t - \Delta 1\text{h}_{t-1}$. 
*   **Rationale:** Is the patient's heart rate merely high, or is it *accelerating* dangerously?

### E. Variability Features
*   **Standard Deviation:** `HR_std_4h`.
*   **Coefficient of Variation (CV):** $\frac{\sigma}{\mu} \times 100$.
*   **Rationale:** Loss of physiological variability (e.g., extremely rigid heart rate) is a hallmark of autonomic dysfunction in sepsis.

### G. Patient-Baseline Deviation
*   **Rolling Z-Score:** $\frac{V_t - \mu_{12\text{h}}}{\sigma_{12\text{h}}}$. 
*   **Rationale:** Measures how far the patient is deviating from *their own* historical normal, rather than a population normal.

### H. Cross-Parameter Interactions (Crucial)
*   **Shock Index (SI):** $\frac{HR}{SBP}$ (or $\frac{HR}{MAP}$). 
    *   *Rationale:* HR $\uparrow$ + MAP $\downarrow$. Normal is ~0.5-0.7. $>1.0$ strongly indicates impending cardiovascular collapse.
*   **Respiratory Distress Index:** $\frac{RR}{SpO_2}$. 
    *   *Rationale:* RR $\uparrow$ + SpO2 $\downarrow$. Identifies failing compensation.
*   **Fever Response Index:** $HR - (10 \times (Temp_C - 37))$.
    *   *Rationale:* HR $\uparrow$ + Temp $\uparrow$. Normal physiology adds ~10bpm per 1°C fever. Disproportionate tachycardia implies shock, not just fever.
*   **Hypoperfusion Index:** $\frac{Lactate}{MAP}$. 
    *   *Rationale:* High lactate with falling pressure indicates profound metabolic failure.

### I. Laboratory Trends & J. Clinical Context
*   **Time Above/Below Range:** Hours spent with MAP $< 65$ mmHg.
*   **Age/Gender:** Static clinical context.

### K. Missingness & L. Signal Quality Indicators
*   **Missing Masks:** `HR_missing`, `Lactate_missing`.
*   **Time Since Measurement:** `hours_since_last_Lactate`.
*   **Signal Quality:** Variance within a 1-hour bin (if raw frequency is 1-minute). High variance implies motion artifact.

### M. Clinical Score Features
*   **qSOFA Score:** (RR $\ge 22$) + (SBP $\le 100$) + (GCS $\le 14$). Ranging 0-3.

---

## 2. Complete Feature Dictionary (Example Extract)

| Feature Name | Formula / Calculation | Input Variables | Window | Units | Clinical Rationale | Leakage Risk | Missing Data Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `HR_slope_4h` | $(HR_t - HR_{t-4}) / 4$ | `heart_rate` | 4h | bpm/hr | Captures progressive tachycardia preceding shock. | None | Requires $\ge 2$ points; otherwise NaN. |
| `Shock_Index` | $HR_t / SBP_t$ | `heart_rate`, `sbp` | 1h | Ratio | Early indicator of left ventricular dysfunction and hypovolemia. | None | NaN if either HR or SBP is missing. |
| `Temp_Z_Score` | $(Temp_t - \mu_{12h}) / \sigma_{12h}$ | `temp_c` | 12h | SD | Individualized fever/hypothermia detection. | None | NaN if $<3$ measurements in 12h. |
| `MAP_time_low` | $\sum (MAP < 65)$ | `map` | 4h | hours | Cumulative hypoperfusion load damages organs. | None | Uses forward-filled MAP within limits. |
| `Lactate_missing`| $1$ if Lactate is NaN else $0$ | `lactate` | 1h | Binary | Identifies physician suspicion of sepsis. | **Low/Med** | N/A (this feature specifically captures missingness). |
| `HR_accel` | $(HR_t - HR_{t-1}) - (HR_{t-1} - HR_{t-2})$ | `heart_rate` | 3h | bpm/hr²| Identifies rapid decompensation vs. stable high HR. | None | Requires 3 consecutive 1h bins. |
| `qSOFA_curr` | $(RR\ge22) + (SBP\le100)$ | `resp_rate`, `sbp` | 1h | Points | Standard clinical heuristic for sepsis screening. | None | Defaults to 0 for missing components (clinical norm). |

*(Note: The full programmatic implementation of these features generates ~120 columns per patient time-step, which XGBoost will ingest and split based on feature importance).*
