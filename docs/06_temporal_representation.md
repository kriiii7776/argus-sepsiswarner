# SepsisGuard AI: Temporal Representation Strategy

Irregular, high-frequency ICU data must be discretized into a mathematical representation before being fed into a machine learning model. This document defines the exact temporal translation mechanics for SepsisGuard.

## 1. Evaluation of Window Configurations

### 1.1 Time Resolution (Bin Size)
*   **5-Minute:** Captures micro-crises (e.g., transient desaturation) but results in >90% sparsity. Computationally heavy and prone to overfitting on noise.
*   **15-Minute:** Excellent balance for Deep Learning (GRU/TCN). Captures rapid onset dynamics while maintaining manageable sequence lengths.
*   **30-Minute:** Standard for many ICU models.
*   **1-Hour:** The standard for tabular models (XGBoost). Vitals are typically recorded hourly by nurses. Limits sparsity to ~10-20% for core vitals.

### 1.2 Observation Window (Sequence Length)
*   **2 Hours:** Too short to establish a reliable baseline. Cannot calculate a meaningful 4-hour slope.
*   **4 Hours:** Align closely with nursing observation cycles. Excellent for capturing acute deterioration slopes.
*   **6 Hours:** Captures longer trends, but restricts the available training cohort (requires patients to be in the ICU for $6 + Horizon$ hours before prediction).
*   **12 Hours:** Excellent context, but risks "washing out" acute signals in average statistics, and severely limits the early-onset patient cohort.

### 1.3 Primary Recommendation
For our **Phase 4 XGBoost Baseline**, the optimal configuration is:
*   **Bin Size:** 1 Hour
*   **Observation Window:** 4 Hours
*   *Rationale:* XGBoost treats time-series cross-sectionally (creating features like `HR_1h_ago`, `HR_slope_4h`). 1-hour bins over 4 hours yield 4 discrete time steps per variable, resulting in a dense, highly informative feature vector without exploding dimensionality.

*Note: If we upgrade to a Temporal Neural Network (GRU/TCN) later, we will shift to 15-minute bins over a 6-hour window (24 timesteps) to leverage sequence modeling.*

---

## 2. Temporal Definitions

1.  **Window Size (Bin):** $\Delta t = 1$ hour.
2.  **Prediction Horizon:** $H = 6$ hours.
3.  **Step Size:** $S = 1$ hour. For inference, the window slides forward 1 hour at a time.
4.  **Resampling Strategy:** Hourly mean for high-frequency vitals. Last recorded value for labs (with strictly enforced no-forward-fill rules).
5.  **Aggregation:** Data points falling within $[t, t+1)$ are averaged to represent the bin at $t$.
6.  **Missingness Representation:** A binary mask tensor $M$ where $1 = \text{missing}$, $0 = \text{present}$.
7.  **Time-Since-Last-Measurement:** A decay tensor $D$ tracking hours since $M=0$.
8.  **Patient Admission Alignment:** Bins are anchored to `intime` (e.g., bin 0 is `[intime, intime + 1h)`).
9.  **Event Alignment:** For positive training labels, the observation window strictly ends exactly at $t_{sepsis} - H$. The sequence is extracted backwards from this right-aligned anchor.
10. **Padding Strategy:** Pre-padding with `NaN` (and $M=1$). If a prediction must be made at hour 3 (where only 3 hours of the 4-hour window exist), the $t-4$ slot is padded.

---

## 3. Transformation Example: Raw $\rightarrow$ Tensor

### Step 1: Raw Measurements (Irregular)
*Patient ID: 1001, ICU Admit: 08:00*
| Timestamp | Variable | Value |
| :--- | :--- | :--- |
| 08:12 | HR | 82 |
| 08:45 | HR | 85 |
| 09:30 | HR | 88 |
| 11:15 | HR | 105 |
| 11:20 | Lactate | 2.1 |

### Step 2: Temporal Window Alignment (1-Hour Bins)
*Assuming current time $t = 12:00$. Observation window is $[08:00 - 12:00)$.*

| Bin | Time Interval | HR (Mean) | HR Missing | Time Since HR | Lactate | Lactate Missing | Time Since Lac |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| $t-4$ | [08:00, 09:00) | 83.5 | 0 | 0 | NaN | 1 | 0 |
| $t-3$ | [09:00, 10:00) | 88.0 | 0 | 0 | NaN | 1 | 1 |
| $t-2$ | [10:00, 11:00) | 88.0*| 1 | 1 | NaN | 1 | 2 |
| $t-1$ | [11:00, 12:00) | 105.0| 0 | 0 | 2.1 | 0 | 0 |

*(Note: HR at $t-2$ is forward-filled from $t-3$, but its missingness mask = 1 and time_since = 1)*

### Step 3: Model Input Representation

**For XGBoost (Tabular Vector $X_t$):**
Flattened features capturing the current state and physiological trends.
```python
X_t = [
    105.0,  # HR_current
    0,      # HR_current_missing
    0,      # time_since_HR
    +17.0,  # HR_delta_1h (105 - 88)
    +21.5,  # HR_delta_4h (105 - 83.5)
    91.1,   # HR_mean_4h
    2.1,    # Lactate_current
    0,      # Lactate_current_missing
    0       # time_since_Lactate
]
```

**For Deep Learning (Sequence Tensor $X$):**
Shape: `(Batch, Sequence_Length, Features)` $\rightarrow$ `(1, 4, 6)`
```python
# Tensor shape: (1 patient, 4 timesteps, 6 features [HR, HR_M, HR_T, Lac, Lac_M, Lac_T])
X_tensor = [
    [ [83.5, 0, 0, NaN, 1, 0],   # t-4
      [88.0, 0, 0, NaN, 1, 1],   # t-3
      [88.0, 1, 1, NaN, 1, 2],   # t-2
      [105.0,0, 0, 2.1, 0, 0] ]  # t-1
]
```

## 4. Leakage Prevention Guarantee
By mapping the raw data into strictly defined bins bounded by $[t_{start}, t_{end})$, and querying the database such that no `charttime` $\ge t_{end}$ is included in the aggregation, it is mathematically impossible for future data to leak into the observation window. Furthermore, forward-filling is applied sequentially (time $t$ only looks at $t-1$), inherently preserving the arrow of time.
