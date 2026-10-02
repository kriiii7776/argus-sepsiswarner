# ARGUS Simulation Scenarios & State Machine Specification

**Status:** Specification  
**Scope:** ARGUS Part 1 Simulator State Machine  

---

## 1. Overview

The ARGUS simulation engine models synthetic ICU patient physiology using continuous state-machine trajectories, controlled physiological variation, noise injection, and sensor fault simulation.

*Important:* All scenario states describe **simulator state transitions** and mathematical trajectories. They DO NOT compute clinical diagnosis or sepsis prediction.

---

## 2. Scenario Catalog

### 2.1 `stable`
- **Description:** Baseline physiological equilibrium with normal sinus rhythm and respiratory dynamics.
- **Vitals Trajectory:** Oscillates smoothly around individual patient baseline values with natural respiratory sinus arrhythmia (RSA) and micro-variability.

### 2.2 `gradual_deterioration`
- **Description:** Progressive linear/sigmoid drift in baseline vital parameters over a configurable time horizon (e.g. 30–60 minutes simulated time).
- **Vitals Trajectory:** Heart rate increases gradually; blood pressure trends downward; SpO2 exhibits slight desaturation.

### 2.3 `rapid_deterioration`
- **Description:** Acute physiological baseline shift simulating decompensation over a short horizon (e.g. 5–15 minutes simulated time).
- **Vitals Trajectory:** Steep increase in heart rate and respiratory rate; sharp decrease in mean arterial pressure (MAP).

### 2.4 `recovery`
- **Description:** Physiological parameters returning towards initial baseline equilibrium following therapeutic or scenario reset triggers.
- **Vitals Trajectory:** Smooth exponential decay back to baseline equilibrium.

### 2.5 `noisy`
- **Description:** Superimposition of high-amplitude Gaussian and pink noise, motion artifacts, or transient spikes on top of current physiological vitals.

### 2.6 `sensor_failure` & `data_quality_problem`
- **Description:** Fault injection modes generating lead disconnections, missing frames (`null` vitals), delayed packets, or out-of-bounds artifact values with explicit `quality_status` metadata flags.
