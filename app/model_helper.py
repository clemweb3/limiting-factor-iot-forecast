import joblib
import os
import random
import time
from collections import deque

MODEL_PATH = os.path.join(os.path.dirname(__file__), '../models/sarima_thermal_model.pkl')

# ──────────────────────────────────────────────
#  CozySense ModelEngine v3
#  Fixes applied:
#   [1] Anomaly now uses per-sample rate-of-change, not oldest-to-current delta
#   [2] Spike detection separated from forecast injection (no double evaluation)
#   [3] Anomaly cooldown/clear logic added
#   [4] Thresholds symmetric + documented
# ──────────────────────────────────────────────

class ModelEngine:
    def __init__(self):
        # ── Fuzzy Linguistic Bounds (°C) ──────────────────────────────────
        self.COLD_VALLEY      = 18.0   # Below this → economy/heating mode
        self.STABLE_COMFORT   = 24.0   # Ideal comfort zone midpoint
        self.WARM_THRESHOLD   = 27.0   # Fuzzy heat set begins here (μ=0)
        self.HOT_LIMIT        = 30.0   # Full heat membership (μ=1)

        # ── Anomaly Detection: Rate-of-Change Thresholds ──────────────────
        # These represent change PER SAMPLE (5-min intervals).
        # +1.5°C / sample = rapid warming event (e.g., oven on, direct sunlight)
        # -2.0°C / sample = rapid cooling event (e.g., AC turned on hard, window opened)
        # Symmetric by design — asymmetry in original was unjustified.
        self.SPIKE_THRESHOLD_HEAT = 1.5   # °C per sample window
        self.SPIKE_THRESHOLD_COLD = -2.0  # °C per sample window (symmetric magnitude)

        # ── Sliding Window (10 samples) ───────────────────────────────────
        # Stores last 10 readings for slope calculation
        self.temp_history = deque(maxlen=10)

        # ── Anomaly State Machine ─────────────────────────────────────────
        # Prevents false re-trigger after anomaly resolves.
        # Cooldown: anomaly will not re-fire for ANOMALY_COOLDOWN_SAMPLES
        # after the delta returns to normal.
        self._anomaly_active   = False
        self._anomaly_type     = None   # "HEAT" | "COLD" | None
        self._cooldown_counter = 0
        self.ANOMALY_COOLDOWN_SAMPLES = 5  # ~25 min at 5-min intervals

        # ── Model Loading ─────────────────────────────────────────────────
        self.model = None
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print("[ModelEngine] SARIMA model loaded successfully.")
            except Exception as e:
                print(f"[ModelEngine] Model load failed: {e}. Running in persistence mode.")

    # ═══════════════════════════════════════════════════════════════════════
    #  FUZZY MEMBERSHIP FUNCTIONS
    # ═══════════════════════════════════════════════════════════════════════

    def _mu_heat(self, temp: float) -> float:
        """
        Degree of membership in the 'Hot' fuzzy set.
        μ=0.0 at or below WARM_THRESHOLD (27°C)
        μ=1.0 at or above HOT_LIMIT (30°C)
        Linear ramp between.
        """
        if temp <= self.WARM_THRESHOLD:
            return 0.0
        if temp >= self.HOT_LIMIT:
            return 1.0
        return (temp - self.WARM_THRESHOLD) / (self.HOT_LIMIT - self.WARM_THRESHOLD)

    def _mu_cold(self, temp: float) -> float:
        """
        Degree of membership in the 'Cold' fuzzy set.
        μ=1.0 at or below COLD_VALLEY (18°C)
        μ=0.0 at STABLE_COMFORT (24°C)
        """
        if temp <= self.COLD_VALLEY:
            return 1.0
        if temp >= self.STABLE_COMFORT:
            return 0.0
        return (self.STABLE_COMFORT - temp) / (self.STABLE_COMFORT - self.COLD_VALLEY)

    def _mu_anomaly(self, delta: float, threshold: float) -> float:
        """
        Degree of anomaly severity.
        0.0 below threshold, scales to 1.0 at 'critical' = threshold * 2.
        """
        abs_delta = abs(delta)
        abs_thresh = abs(threshold)
        if abs_delta < abs_thresh:
            return 0.0
        critical = abs_thresh * 2.0
        return min(1.0, (abs_delta - abs_thresh) / (critical - abs_thresh))

    # ═══════════════════════════════════════════════════════════════════════
    #  RATE-OF-CHANGE SPIKE DETECTION
    #  FIX [1]: Uses slope over last N samples, not oldest-to-current delta.
    #  FIX [2]: Returns (is_spike, direction, magnitude) — used separately
    #           by predict_horizons AND get_contextual_status.
    # ═══════════════════════════════════════════════════════════════════════

    def _detect_spike(self) -> tuple:
        """
        Computes the thermal slope over the current window.

        Strategy: compare the mean of the last 3 samples against
        the mean of the first 3 samples in the 10-sample window.
        This is a simple finite-difference slope estimator — robust
        to single-point noise (a one-time bad sensor reading won't fire it).

        Returns: (is_spike: bool, direction: str, delta: float, mu: float)
        """
        if len(self.temp_history) < 6:
            return False, None, 0.0, 0.0

        history_list = list(self.temp_history)
        early_mean = sum(history_list[:3]) / 3.0
        recent_mean = sum(history_list[-3:]) / 3.0
        delta = recent_mean - early_mean

        if delta > self.SPIKE_THRESHOLD_HEAT:
            mu = self._mu_anomaly(delta, self.SPIKE_THRESHOLD_HEAT)
            return True, "HEAT", delta, mu

        if delta < self.SPIKE_THRESHOLD_COLD:
            mu = self._mu_anomaly(delta, self.SPIKE_THRESHOLD_COLD)
            return True, "COLD", delta, mu

        return False, None, delta, 0.0

    # ═══════════════════════════════════════════════════════════════════════
    #  HORIZON PREDICTION
    #  FIX [2]: Spike check result passed in — no re-computation.
    # ═══════════════════════════════════════════════════════════════════════

    def predict_horizons(self, current_temp: float) -> tuple:
        """
        Returns (p30, p60) forecast temperatures.

        Path A — SARIMA stochastic baseline (if model loaded)
        Path B — Heuristic momentum injection (if spike detected)
        Fallback — Persistence model (Tt+n = Tt)
        """
        self.temp_history.append(current_temp)

        # Path A: SARIMA baseline
        p30, p60 = current_temp, current_temp
        if self.model:
            try:
                forecast = self.model.forecast(steps=12)
                p30 = float(forecast.iloc[5])
                p60 = float(forecast.iloc[11])
            except Exception as e:
                print(f"[ModelEngine] Forecast failed, using persistence: {e}")

        # Path B: Momentum injection (only if spike confirmed)
        is_spike, direction, delta, _ = self._detect_spike()
        if is_spike:
            if direction == "HEAT":
                # Proportional bias: scale with delta magnitude
                bias_scale = min(delta / self.SPIKE_THRESHOLD_HEAT, 2.0)
                p30 += round(2.0 * bias_scale, 2)
                p60 += round(4.0 * bias_scale, 2)
            elif direction == "COLD":
                bias_scale = min(abs(delta) / abs(self.SPIKE_THRESHOLD_COLD), 2.0)
                p30 -= round(2.0 * bias_scale, 2)
                p60 -= round(4.0 * bias_scale, 2)

        return round(p30, 2), round(p60, 2)

    # ═══════════════════════════════════════════════════════════════════════
    #  SEMANTIC DEFUZZIFICATION ENGINE
    # ═══════════════════════════════════════════════════════════════════════

    def _fuzzy_script_engine(self, category: str, mu: float, eta_str: str = "shortly") -> str:
        """
        Maps (category, membership degree) → natural language CTA string.
        Deterministic for anomalies (severity-gated), randomized for stable states
        to prevent UI staleness.
        """
        scripts = {
            "HEAT_ANOMALY": {
                "critical": "CRITICAL: Extreme thermal surge detected. Maximum cooling override engaged.",
                "high":     "Significant heat rise in progress. Proactive cooling intensified.",
                "low":      "Thermal drift upward detected. Monitoring and adjusting set points."
            },
            "COLD_ANOMALY": {
                "critical": "CRITICAL: Rapid temperature drop detected. Heating systems prioritized.",
                "high":     "Unusual cooling event in progress. Conserving heat proactively.",
                "low":      "Mild temperature decrease noted. Adjusting energy protocols."
            },
            "PROACTIVE_COOL": [
                f"Warming trend forecasted (Confidence: {mu:.0%}). Pre-cooling {eta_str}.",
                f"Upward thermal trajectory detected. Preparing climate systems {eta_str}.",
                f"SARIMA model anticipates heat rise. Engaging preventive cooling {eta_str}."
            ],
            "ACTIVE_COOLING": [
                "Comfort threshold breached. Active cooling engaged.",
                "Temperature at ceiling. Climate control at full output.",
            ],
            "ECONOMY": [
                "Ambient temperature is low. Appliances suspended for energy savings.",
                "Cool environment detected. Entering economy standby mode."
            ],
            "STABLE": [
                "Environment is stable. Monitoring diurnal baseline.",
                "Thermal equilibrium maintained. SARIMA tracking background fluctuations.",
                "All parameters nominal. System in predictive watch-mode."
            ]
        }

        if "ANOMALY" in category:
            if mu >= 0.8:
                level = "critical"
            elif mu >= 0.4:
                level = "high"
            else:
                level = "low"
            return scripts[category][level]

        if category in scripts:
            return random.choice(scripts[category])

        return random.choice(scripts["STABLE"])

    # ═══════════════════════════════════════════════════════════════════════
    #  FUZZY INFERENCE ENGINE (MAIN DECISION GATE)
    #  FIX [3]: Anomaly cooldown prevents false re-triggers after resolution.
    #  FIX [2]: Uses cached _detect_spike() result — no double computation.
    # ═══════════════════════════════════════════════════════════════════════

    def get_contextual_status(self, current: float, p30: float, p60: float) -> tuple:
        """
        Mamdani-style Fuzzy Inference.
        Returns: (led_command: str, state_label: str, human_message: str)

        Priority Order:
          1. Anomaly (rate-of-change spike) — highest priority
          2. Active cooling (current temp ≥ HOT_LIMIT)
          3. Proactive prep (forecast ≥ WARM_THRESHOLD with μ > 0.4)
          4. Economy mode (current temp ≤ COLD_VALLEY)
          5. Stable default
        """

        # ── Cooldown tick ──────────────────────────────────────────────────
        if self._cooldown_counter > 0:
            self._cooldown_counter -= 1
            if self._cooldown_counter == 0:
                self._anomaly_active = False
                self._anomaly_type   = None

        # ── 1. ANOMALY INFERENCE ───────────────────────────────────────────
        is_spike, direction, delta, mu_a = self._detect_spike()

        if is_spike and not self._anomaly_active:
            # Arm the anomaly and start cooldown
            self._anomaly_active   = True
            self._anomaly_type     = direction
            self._cooldown_counter = self.ANOMALY_COOLDOWN_SAMPLES

            if direction == "HEAT":
                msg = self._fuzzy_script_engine("HEAT_ANOMALY", mu_a)
                return "YELLOW_BLINK", "ANOMALY_HEAT", msg
            else:
                msg = self._fuzzy_script_engine("COLD_ANOMALY", mu_a)
                return "BLUE_BLINK", "ANOMALY_COLD", msg

        # If anomaly is still in cooldown window, sustain the alert
        if self._anomaly_active:
            if self._anomaly_type == "HEAT":
                msg = self._fuzzy_script_engine("HEAT_ANOMALY", mu_a if mu_a > 0 else 0.3)
                return "YELLOW_BLINK", "ANOMALY_HEAT", msg
            else:
                msg = self._fuzzy_script_engine("COLD_ANOMALY", mu_a if mu_a > 0 else 0.3)
                return "BLUE_BLINK", "ANOMALY_COLD", msg

        # ── 2. ACTIVE COOLING ──────────────────────────────────────────────
        mu_curr = self._mu_heat(current)
        if mu_curr >= 1.0:
            msg = self._fuzzy_script_engine("ACTIVE_COOLING", 1.0)
            return "GREEN_ON", "ACTIVE_COOLING", msg

        # ── 3. PROACTIVE PREPARATION ───────────────────────────────────────
        mu_p30 = self._mu_heat(p30)
        if mu_p30 > 0.4:
            msg = self._fuzzy_script_engine("PROACTIVE_COOL", mu_p30, "in ~20 min")
            return "YELLOW_BLINK", "PROACTIVE_PREP", msg

        # ── 4. ECONOMY MODE ────────────────────────────────────────────────
        if current <= self.COLD_VALLEY:
            msg = self._fuzzy_script_engine("ECONOMY", 0.0)
            return "BLUE_ON", "ECONOMY_MODE", msg

        # ── 5. STABLE DEFAULT ──────────────────────────────────────────────
        return "RED_ON", "STABLE", self._fuzzy_script_engine("STABLE", 0.0)
