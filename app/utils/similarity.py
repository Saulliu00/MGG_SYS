"""
PT-curve similarity scoring — modular and easy to swap.

Architecture
------------
* `compute_features(time, pressure)` — extract a feature dict from one curve.
* `score_pair(query, candidate)` — scalar similarity ∈ [0, 1] from two
  feature dicts (higher = more similar).
* `rank_candidates(...)` — convenience wrapper: score a list of candidates
  and return them sorted best-first.

To change the scoring logic: edit only the two "Configuration" blocks
below and/or the bodies of `compute_features` / `score_pair`.
Nothing else in the application needs to change.
"""

import math
import numpy as np
from typing import Dict, List, Tuple

# ── Configuration: weights ─────────────────────────────────────────────────────
# Must sum to 1.0
WEIGHTS = {
    'high': 0.75,   # peak pressure magnitude + peak timing
    'low':  0.25,   # rising-slope + falling-slope linear models
}

# ── Configuration: feature extraction ─────────────────────────────────────────
# End-time (ms) used for the falling-slope linear model
FALLING_SLOPE_END_TIME = 35.0

# How to locate the "ignition point" (where pressure leaves 0):
#   'threshold' — first sample where pressure ≥ IGNITION_THRESHOLD × peak
#   'first_point' — always use times[0]
IGNITION_METHOD = 'threshold'
IGNITION_THRESHOLD = 0.02      # 2 % of peak pressure


# ── Feature extraction ────────────────────────────────────────────────────────

def compute_features(time: List[float], pressure: List[float]) -> Dict:
    """
    Extract the feature vector used for comparison from one PT curve.

    Features
    --------
    max_pressure      : peak pressure (MPa)            — HIGH priority
    max_pressure_time : time of peak (ms)              — HIGH priority
    rising_slope      : slope of line (t_ignition, 0)
                        → (t_peak, P_peak)             — LOW priority
    falling_slope     : slope of line (t_peak, P_peak)
                        → (FALLING_SLOPE_END_TIME, P_end)  — LOW priority
    ignition_time     : detected ignition timing (ms)  — derived
    pressure_at_end   : interpolated P at end-time     — derived
    """
    t = np.asarray(time, dtype=float)
    p = np.asarray(pressure, dtype=float)

    # Peak
    peak_idx = int(np.argmax(p))
    max_pressure = float(p[peak_idx])
    max_pressure_time = float(t[peak_idx])

    # Ignition timing
    if IGNITION_METHOD == 'threshold' and max_pressure > 0:
        thresh = max_pressure * IGNITION_THRESHOLD
        ignition_idx = next((i for i, v in enumerate(p) if v >= thresh), 0)
        ignition_time = float(t[ignition_idx])
    else:
        ignition_time = float(t[0])

    # Linear model 1 — rising: (t_ignition, 0) → (t_peak, P_peak)
    dt_rise = max_pressure_time - ignition_time
    rising_slope = max_pressure / dt_rise if dt_rise > 1e-9 else 0.0

    # Linear model 2 — falling: (t_peak, P_peak) → (end_time, P_end)
    pressure_at_end = float(np.interp(FALLING_SLOPE_END_TIME, t, p))
    dt_fall = FALLING_SLOPE_END_TIME - max_pressure_time
    falling_slope = (pressure_at_end - max_pressure) / dt_fall if dt_fall > 1e-9 else 0.0

    return {
        'max_pressure':      max_pressure,
        'max_pressure_time': max_pressure_time,
        'ignition_time':     ignition_time,
        'rising_slope':      rising_slope,
        'falling_slope':     falling_slope,
        'pressure_at_end':   pressure_at_end,
    }


# ── Similarity scoring ────────────────────────────────────────────────────────

def score_pair(query: Dict, candidate: Dict) -> float:
    """
    Compute a similarity score ∈ [0, 1] between two feature dicts.
    Higher means more similar.

    To tune: adjust WEIGHTS above, or change the error formula below.
    """
    def _rel_err(a: float, b: float) -> float:
        denom = max(abs(a), 1e-6)
        return abs(a - b) / denom

    # HIGH priority
    hp_pressure = _rel_err(query['max_pressure'],      candidate['max_pressure'])
    hp_timing   = _rel_err(query['max_pressure_time'], candidate['max_pressure_time'])
    high_err = (hp_pressure + hp_timing) / 2.0

    # LOW priority (slope comparison = shape of the two linear models)
    lp_rise = _rel_err(query['rising_slope'],  candidate['rising_slope'])
    lp_fall = _rel_err(query['falling_slope'], candidate['falling_slope'])
    low_err = (lp_rise + lp_fall) / 2.0

    # Weighted combined error, clamped
    total_err = WEIGHTS['high'] * high_err + WEIGHTS['low'] * low_err
    total_err = min(total_err, 10.0)   # prevent exp underflow

    # Exponential decay: score = 1 when error = 0, approaches 0 for large errors
    return float(math.exp(-3.0 * total_err))


# ── Convenience ranking ───────────────────────────────────────────────────────

def rank_candidates(
    query_time: List[float],
    query_pressure: List[float],
    candidates: List[Tuple[str, List[float], List[float]]],
) -> List[Dict]:
    """
    Score every candidate against the query curve and return them sorted
    by score descending.

    Parameters
    ----------
    query_time, query_pressure : the uploaded user curve
    candidates : list of (label, time_list, pressure_list)

    Returns
    -------
    List of dicts: {label, score, features}  — best match first.
    """
    query_features = compute_features(query_time, query_pressure)
    ranked = []
    for label, ct, cp in candidates:
        if not ct or not cp:
            continue
        try:
            feat = compute_features(ct, cp)
            s = score_pair(query_features, feat)
            ranked.append({'label': label, 'score': s, 'features': feat})
        except Exception:
            pass
    ranked.sort(key=lambda x: x['score'], reverse=True)
    return ranked
