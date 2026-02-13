# Edge-Driven Hybrid Forecasting: A Minimalist IoT Framework for Proactive Climate Control

## 📌 Project Overview
This project proposes a **Hybrid Predictive Framework** for indoor climate management using minimal IoT infrastructure. While traditional smart home systems rely on expensive sensor grids, this study investigates the "Predictive Ceiling" of a **single DHT22 sensor** node.

Our research identifies the transition point where simple **Persistence Logic** (reactive) should hand over control to **SARIMA-based Modeling** (proactive). This framework is designed for "Cold-Start" scenarios, requiring only 7 days of historical data to begin optimizing energy consumption.

---

## 🧪 Research Methodology
We utilize an **Ablation Study** to compare three logic layers across 10, 30, and 60-minute horizons:

1. **Persistence (Naive):** The baseline "reactive" logic.
2. **ARIMA (Univariate):** Capturing thermal inertia and trends.
3. **ARIMAX (Multivariate):** Evaluating Humidity as a stochastic noise factor vs. a lead indicator.

### Technical Constraints:
* **Hardware:** Single DHT22 (Temp/Humidity) via ESP32.
* **Sampling:** 5-minute intervals (300s).
* **Dataset:** 2,017 observations (Jan 23–30, 2026).
* **Validation:** Performance is benchmarked against the physical sensor resolution (0.1°C) and accuracy (±0.5°C).

---

## 🚀 The Hybrid Application Framework
The core innovation of this project is the **Dual-Mode Control Logic**, which translates "Low-Accuracy" forecasts into "High-Value" physical actions:

### 1. The Persistence-Inertia Mode (Short-Term: <15m)
For immediate stability, the system relies on Persistence logic. If the current temperature is within the "Comfort Zone," the hardware remains in a **Low-Power Deep Sleep state**, saving battery life (SDG 7).

### 2. The Proactive Trend Mode (Long-Term: 30-60m)
The SARIMA model is utilized to detect the **Slope of Change**. Even if the MAE is higher than the baseline, the model identifies *when* the temperature will likely breach a threshold.
* **Action:** The system triggers "Pre-Cooling" or "Pre-Heating" at low intensity (PWM control) before the threshold is reached, preventing high-energy spikes.



---

## 📊 Key Research Findings
* **Persistence Supremacy:** In stable indoor micro-climates, the current state is an elite 10-minute predictor ($MAE \approx 0.02°C$).
* **Quantization Limit:** Prediction errors remain below the sensor’s physical resolution, proving that "Minimal Sensing" is mathematically viable for control loops.
* **Humidity Paradox:** In residential settings, adding humidity data (ARIMAX) introduced noise rather than precision, suggesting that univariate models are more efficient for edge deployment.

---

## 🌍 Global Sustainability Impact (SDGs)

### 🌱 SDG 7: Affordable and Clean Energy
By shifting from reactive "Full-Power" cooling to proactive "Low-Intensity" pre-cooling, this framework reduces peak load demand on local grids using sub-$10 hardware.

### 🏙️ SDG 11: Sustainable Cities and Communities
Enables smart-home retrofitting for older residential structures without requiring invasive multi-sensor installations or months of data collection.

---

## 🛠️ Repository Structure
* `/notebooks`: Exploratory Data Analysis and Model Stress Testing.
* `/models`: Exported SARIMA weights (.pkl) for inference.
* `/firmware`: C++ logic for ESP32 implementing the "Hybrid Switch."
* `/app`: Python-based inference engine to bridge data and decisions.
