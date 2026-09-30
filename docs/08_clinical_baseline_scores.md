# SepsisGuard AI: Clinical Rule Baseline Engine

This engine calculates traditional heuristic early-warning scores. **Important Disclaimer:** These scores evaluate non-specific physiological deterioration. They do not diagnose sepsis. Sepsis requires clinical suspicion of infection. These scores are implemented strictly as statistical comparators to the SepsisGuard AI model.

---

## 1. SIRS (Systemic Inflammatory Response Syndrome)
**Version:** ACCP/SCCM Consensus Conference (1992)
**Required Variables:**
1.  Temperature (°C)
2.  Heart Rate (bpm)
3.  Respiratory Rate (insp/min)
4.  WBC Count ($10^9$/L)

**Limitations & Missing Data:**
*   *Limitation:* The original criteria allow for PaCO2 $< 32$ mmHg instead of RR $>20$, and $>10\%$ bands instead of WBC abnormalities. Due to the rarity of continuous ABGs and manual differentials in general ICU streaming, we strictly use RR and total WBC.
*   *Missing Data:* If a variable is missing, it contributes 0 points. If $\ge 2$ variables are missing, the score validity is downgraded to "PARTIAL".

---

## 2. MEWS (Modified Early Warning Score)
**Version:** Subbe et al. (2001)
**Required Variables:**
1.  Respiratory Rate
2.  Heart Rate
3.  Systolic Blood Pressure (SBP)
4.  Temperature (°C)
5.  AVPU (Alert, Voice, Pain, Unresponsive)

**Limitations & Missing Data:**
*   *Limitation:* MIMIC-IV generally records GCS (Glasgow Coma Scale) rather than AVPU. We map GCS as a proxy if required (e.g., GCS 15 = Alert).
*   *Missing Data:* If a variable is missing, it contributes 0 points. The validity flag tracks exactly which components were unavailable.

---

## 3. NEWS2 (National Early Warning Score 2)
**Version:** Royal College of Physicians (2017)
**Required Variables:**
1.  Respiratory Rate
2.  SpO2 Scale 1 or Scale 2
3.  Air or Oxygen usage
4.  Systolic Blood Pressure
5.  Heart Rate
6.  Level of Consciousness (ACVPU)
7.  Temperature

**Limitations & Missing Data:**
*   *Limitation:* NEWS2 has two SpO2 scales depending on whether the patient has hypercapnic respiratory failure (usually COPD). Without comprehensive diagnosis parsing to flag COPD, we assume Scale 1. Extracting continuous "Air vs. Oxygen" parameters from the `inputevents` table in MIMIC is notoriously unreliable; therefore, NEWS2 is often excluded or marked "PARTIAL" in historical retrospective streaming analyses.
*   *Missing Data:* Follows the same strict partial-validity logic as MEWS.

---

## Engine Architecture
The engine is completely decoupled from the SepsisGuard Machine Learning model. It takes a dictionary of raw (or binned) vital signs and outputs a standardized JSON payload detailing the score, the components used, what was missing, and a validity flag, ensuring a fair apples-to-apples performance comparison during Phase 4 validation.
