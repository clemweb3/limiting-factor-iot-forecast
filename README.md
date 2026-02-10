# Limits of Short-Term Indoor Temperature Forecasting with Minimal IoT Sensing

##  Project Overview
This study investigates the practical boundaries of time-series forecasting in "data-starved" and constrained environments. Using a **single DHT22 sensor** and a limited **7-day observation window**, we evaluate the "Predictive Ceiling" where complex modeling ceases to provide value over a simple Persistence (Naive) approach.

While most IoT research focuses on maximizing accuracy through high-cost infrastructure, this project identifies **Failure Points** in minimalist setups. We benchmark performance across 10, 30, and 60-minute horizons to determine the limits of low-cost hardware in resource-constrained residential settings.

---

## 🧪 Research Methodology & Constraints

* **Sensor Node:** Single DHT22 (Temperature & Humidity).
* **Temporal Resolution:** 300-second (5-minute) sampling interval.
* **Data Volume:** ~2,017 observations (Jan 23–30, 2026).
* **Cold-Start Constraint:** No historical training beyond 7 days; no external exogenous data (Weather APIs, Occupancy, or HVAC state).
* **Hardware Baseline:** Performance is validated against the DHT22’s native **±0.5°C accuracy threshold**.

---

## 📊 Comparative Performance Analysis

Our research implemented an **Ablation Study** to compare predictive logic layers. The results demonstrate a "Persistence Supremacy" in stable indoor micro-climates.

| Model Logic | Complexity Level | 60-Min MAE | Performance vs. Baseline |
| :--- | :--- | :--- | :--- |
| **Persistence** | Naive Baseline | 0.0884°C | **Benchmark** |
| **ARIMA** | Univariate (Temp Only) | 0.0934°C | -5.66% Degradation |
| **ARIMAX** | Multivariate (Temp + Hum) | 0.2010°C | -127.38% Degradation |

### Key Findings:
1.  **The Persistence Paradox:** In high-inertia environments, the "Current State" is an elite predictor. Complex math (ARIMA) struggled to beat the naive baseline due to the room's thermal stability.
2.  **Multivariate Interference:** Adding Humidity (ARIMAX) acted as **stochastic noise** rather than a lead indicator, doubling the error rate compared to the univariate model.
3.  **Reliability Horizon:** All models—even the degraded ARIMAX—maintained an error rate **2.5x lower** than the sensor's physical tolerance (±0.5°C), proving the setup is physically valid for short-term control.

---

## 🛠️ Logic & Workflow

1.  **Stationarity Analysis:** Utilizing Augmented Dickey-Fuller (ADF) tests to determine the integration order ($d$).
2.  **Ablation Benchmarking:** Establishing MAE thresholds for Persistence, ARIMA, and ARIMAX.
3.  **Rolling Stress Test:** Implementing a Time-Series Rolling Window validation to ensure results are not artifacts of specific 48-hour climate anomalies.
4.  **Error Calibration:** Mapping model performance against the physical limitations of the hardware.

---

## 🌍 Global Sustainability Significance (SDGs)

This research translates theoretical predictive analytics into actionable strategies for global development:

### 🌱 Scaling Affordable Energy Efficiency (SDG 7)
High-end energy management often requires expensive, multi-sensor grids. This study validates a **"Minimal Sensing"** blueprint, proving that a single $5 sensor node can provide reliable 60-minute forecasts, making smart energy optimization accessible to resource-constrained households.

### 🏙️ Inclusive Smart City Development (SDG 11)
Sustainable cities must address older, non-digital residential structures. By proving the efficacy of **7-day "Cold-Start" datasets**, this research enables the rapid deployment of smart climate controls in older communities without requiring invasive renovations or long-term data collection.

---

## 📊 Research Objectives Addressed
* **Does Humidity reduce error?** No; it introduces collinearity noise in stable indoor environments.
* **Where is the "Breaking Point"?** Model error did not exceed sensor tolerance within the 60-minute horizon.
* **Can "Dumb" models win?** Yes; Persistence is the most efficient logic for high-inertia residential zones.