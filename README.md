# Edge-Driven Hybrid Forecasting: A Minimalist IoT Framework for Proactive Climate Control

## 📌 Project Overview
This project proposes a **Hybrid Predictive Framework** for indoor climate management using minimal IoT infrastructure. While traditional smart home systems rely on expensive sensor grids, this study investigates the "Predictive Ceiling" of a **single DHT22 sensor** node.

Our research identifies the transition point where simple **Persistence Logic** (Reactive) hands over control to **SARIMA-based Modeling** (Proactive). This framework is designed for "Cold-Start" scenarios, requiring only 7 days of historical data to begin optimizing energy consumption.

---

## 🏗️ System Architecture & Logic

The system utilizes a **Hybrid Control Loop** that combines statistical forecasting (SARIMA) with immediate sensor-triggered overrides for real-time responsiveness.



### 🚥 LED Signaling Framework
To provide transparency into the AI's decision-making, the hardware utilizes a three-tier signaling system:

* 🔴 **Red LED (Steady) | IDLE STATE:** The environment is stable. The appliance (Aircon/Fan) is **OFF** to maximize energy conservation.
* 🟡 **Yellow LED (Blinking) | PREDICTIVE AWARENESS:** The SARIMA model has detected a rising thermal trend within the 30-60 minute horizon. The system is preparing to engage.
* 🟢 **Green LED (Steady) | ACTIVE COOLING:** The appliance is **ON**. This is triggered either **Proactively** (to mitigate heat before it peaks) or **Reactively** (if a sudden heat spike/heater is detected).

---

## 🧪 Research Methodology
We utilize an **Ablation Study** to compare three logic layers across 10, 30, and 60-minute horizons:

1.  **Persistence (Naive):** The baseline "yesterday = today" reactive logic.
2.  **SARIMA (Univariate):** Captures thermal inertia and periodic room cycles.
3.  **SARIMAX (Multivariate):** Evaluating Humidity as a lead indicator vs. stochastic noise.

### Technical Constraints:
* **Hardware:** Single DHT22 (Temp/Humidity) via ESP32.
* **Sampling:** 5-minute intervals (300s).
* **Dataset:** 2,017 observations (Jan 23–30, 2026).
* **Validation:** Performance is benchmarked against the sensor’s physical resolution (0.1°C) and accuracy (±0.5°C).

---

## 📊 Key Research Findings
* **Persistence Supremacy:** In stable indoor micro-climates, the current state is an elite 10-minute predictor ($MAE \approx 0.02°C$).
* **The Proactive Edge:** While SARIMA has a higher MAE than Persistence, it provides **Lead Time**. It identifies a "Heat Slope" up to 60 minutes before it happens, allowing for low-intensity pre-cooling.
* **Humidity Paradox:** In residential settings, adding humidity data (ARIMAX) introduced noise rather than precision, suggesting univariate models are more efficient for edge deployment.



---

## 🌍 Global Sustainability Impact (SDGs)

### 🌱 SDG 7: Affordable and Clean Energy
By shifting from reactive "Full-Power" cooling to proactive "Low-Intensity" pre-cooling, this framework reduces peak load demand on local grids using sub-$10 hardware.

### 🏙️ SDG 11: Sustainable Cities and Communities
Enables smart-home retrofitting for older residential structures without requiring invasive multi-sensor installations or months of data collection.

---

## 🛠️ Repository Structure
```text
├── app/
│   └── test_load.py           # Python Inference Engine (tests)
├── data/
│   ├── processed/             # Cleaned 5-min interval data
│   └── raw/                   # Original telemetry logs
├── firmware/
│   └── proactive_node.ino      # ESP32 C++ source code
├── models/
│   └── sarima_thermal_model.pkl # Exported SARIMA weights
├── notebooks/
│   ├── 01_eda_stationarity.ipynb
│   └── 02_modeling_evaluation.ipynb
└── requirements.txt           # Python dependency manifest