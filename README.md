Limits of Short-Term Indoor Temperature Forecasting with Minimal IoT Sensing

📌 Project Overview

This study investigates the practical boundaries of time-series forecasting in "data-starved" and constrained environments. Using only a single DHT22 sensor and a 7-day window, we evaluate at what point predictive modeling ceases to provide value over a simple persistence (naive) approach.

Most IoT projects focus on maximizing accuracy; this project focuses on identifying failure points. We benchmark forecasting performance across 10, 30, and 60-minute horizons to determine the "predictive ceiling" imposed by low-cost hardware and minimal features.

🧪 Research Methodology

- **Sensor:** Single DHT22 (Temp and Humidity)
- **Sampling Interval:** 5 Minutes
- **Data Volume:** ~2,016 observations (7 days)
- **Core Challenge:** Predicting temperature with no external data (weather APIs, occupancy, or HVAC state).

🛠️ Logic & Workflow

- **Stationarity Analysis:** Utilizing Augmented Dickey-Fuller (ADF) tests to determine the integration order (d) for ARIMA.

- **The Persistence Benchmark:** Establishing the MAEpersistence​ for every horizon.

- **Cross-Validation:** Implementing a Time-Series Rolling Window validation to ensure results aren't artifacts of a specific 48-hour period.

- **Error Calibration:** Benchmarking model error against the DHT22’s native 0.5∘C margin of error.

📊 Key Questions that we aim to address:

1. Does Humidity (Multivariate) actually reduce RMSE, or does it introduce collinearity noise?
2. At what horizon (t+n) does the model error exceed the sensor's physical accuracy?
3. Can a "dumb" persistence model outperform an optimized ARIMA in a stable indoor environment?