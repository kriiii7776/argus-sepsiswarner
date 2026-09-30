import time
import random
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

"""
WARNING: SYNTHETIC DATA GENERATOR
This simulator generates strictly synthetic patient data.
It is intended ONLY for software demonstration and system testing.
Under no circumstances should the simulated patients, their trajectories,
or any generated values be interpreted as representing real clinical outcomes
or real patient physiology.
"""

SCENARIOS = {
    1: "Stable patient",
    2: "Gradual deterioration",
    3: "Rapid deterioration",
    4: "Non-septic physiological abnormality",
    5: "Sensor artifact",
    6: "Missing-data scenario",
    7: "Recovery after deterioration",
    8: "High-risk patient with uncertain model prediction"
}

class PatientSimulator:
    def __init__(
        self,
        patient_id: str = None,
        scenario: int = 1,
        starting_vitals: Dict[str, float] = None,
        deterioration_rate: float = 1.0,
        sampling_frequency_sec: int = 1
    ):
        self.patient_id = patient_id or str(uuid.uuid4())
        self.scenario = scenario
        self.deterioration_rate = deterioration_rate
        self.sampling_frequency = sampling_frequency_sec
        self.step_count = 0
        self.start_time = datetime.utcnow()
        
        # Default healthy starting vitals
        self.current_vitals = starting_vitals or {
            "heart_rate": 75.0,
            "blood_pressure_sys": 120.0,
            "blood_pressure_dia": 80.0,
            "temperature": 37.0,
            "spo2": 98.0,
            "respiratory_rate": 16.0
        }

    def generate_step(self) -> Dict[str, Any]:
        """Generate the next data point in the synthetic time-series stream."""
        self.step_count += 1
        current_time = self.start_time + timedelta(seconds=self.step_count * self.sampling_frequency)
        
        # Base random noise for stable vitals
        noise = {
            "heart_rate": random.uniform(-1, 1),
            "blood_pressure_sys": random.uniform(-2, 2),
            "blood_pressure_dia": random.uniform(-1, 1),
            "temperature": random.uniform(-0.1, 0.1),
            "spo2": random.uniform(-0.5, 0.5),
            "respiratory_rate": random.uniform(-0.5, 0.5)
        }

        # Apply scenario logic
        if self.scenario == 1:
            # 1. Stable patient
            self._apply_noise(noise)
            
        elif self.scenario == 2:
            # 2. Gradual deterioration (Slowly increasing HR, Temp, decreasing BP)
            self._apply_noise(noise)
            self.current_vitals["heart_rate"] += (0.1 * self.deterioration_rate)
            self.current_vitals["blood_pressure_sys"] -= (0.1 * self.deterioration_rate)
            self.current_vitals["temperature"] += (0.01 * self.deterioration_rate)
            
        elif self.scenario == 3:
            # 3. Rapid deterioration
            self._apply_noise(noise)
            self.current_vitals["heart_rate"] += (0.5 * self.deterioration_rate)
            self.current_vitals["blood_pressure_sys"] -= (0.8 * self.deterioration_rate)
            self.current_vitals["spo2"] -= (0.2 * self.deterioration_rate)
            
        elif self.scenario == 4:
            # 4. Non-septic physiological abnormality (e.g., isolated tachycardia)
            self._apply_noise(noise)
            self.current_vitals["heart_rate"] += (0.2 * self.deterioration_rate)
            if self.current_vitals["heart_rate"] > 140:
                self.current_vitals["heart_rate"] = 140 + random.uniform(-2, 2)
                
        elif self.scenario == 5:
            # 5. Sensor artifact
            self._apply_noise(noise)
            # Randomly spike or drop a single vital sign abruptly
            if random.random() < 0.1:
                self.current_vitals["spo2"] = random.choice([50.0, 150.0]) # Impossible/artifact value
            else:
                self.current_vitals["spo2"] = 98.0 + random.uniform(-1, 1)
                
        elif self.scenario == 6:
            # 6. Missing-data scenario
            self._apply_noise(noise)
            # Randomly drop values completely (represented as None)
            vitals_output = self._get_current_vitals_dict(current_time)
            if random.random() < 0.2:
                vitals_output["heart_rate"] = None
            if random.random() < 0.2:
                vitals_output["blood_pressure_sys"] = None
            return vitals_output

        elif self.scenario == 7:
            # 7. Recovery after deterioration
            self._apply_noise(noise)
            if self.step_count < 50:
                self.current_vitals["heart_rate"] += 0.2
            else:
                self.current_vitals["heart_rate"] = max(75.0, self.current_vitals["heart_rate"] - 0.4)

        elif self.scenario == 8:
            # 8. High-risk patient with uncertain model prediction (Fluctuating wildly at threshold borders)
            self.current_vitals["heart_rate"] = 110 + random.uniform(-10, 10)
            self.current_vitals["blood_pressure_sys"] = 90 + random.uniform(-15, 15)

        # Cap bounds for realism (synthetic but within physiological possibility)
        self._cap_vitals()
        
        return self._get_current_vitals_dict(current_time)

    def _apply_noise(self, noise: Dict[str, float]):
        for k in self.current_vitals:
            self.current_vitals[k] += noise.get(k, 0)

    def _cap_vitals(self):
        self.current_vitals["heart_rate"] = max(0, min(self.current_vitals["heart_rate"], 300))
        self.current_vitals["spo2"] = max(0, min(self.current_vitals["spo2"], 100))

    def _get_current_vitals_dict(self, current_time: datetime) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "timestamp": current_time.isoformat(),
            "scenario": SCENARIOS.get(self.scenario),
            "is_synthetic": True,
            **self.current_vitals
        }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synthetic ICU Patient Simulator for System Testing")
    parser.add_argument("--patient-id", type=str, help="Configurable patient ID")
    parser.add_argument("--scenario", type=int, choices=SCENARIOS.keys(), default=1, help="Scenario selection (1-8)")
    parser.add_argument("--deterioration-rate", type=float, default=1.0, help="Multiplier for deterioration speed")
    parser.add_argument("--freq", type=int, default=1, help="Sampling frequency in seconds")
    parser.add_argument("--steps", type=int, default=10, help="Number of steps to simulate")
    
    args = parser.parse_args()
    
    print("="*60)
    print("WARNING: Generating SYNTHETIC time-series streams.")
    print("For demonstration and system testing only.")
    print(f"Scenario: {SCENARIOS[args.scenario]}")
    print("="*60)
    
    simulator = PatientSimulator(
        patient_id=args.patient_id,
        scenario=args.scenario,
        deterioration_rate=args.deterioration_rate,
        sampling_frequency_sec=args.freq
    )
    
    for _ in range(args.steps):
        data_point = simulator.generate_step()
        print(json.dumps(data_point))
        time.sleep(0.5) # Fake real-time delay
