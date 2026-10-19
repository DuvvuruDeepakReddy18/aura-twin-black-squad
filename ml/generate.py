"""Seeded synthetic EHR + wearable simulator. No patient or source dataset is used."""
from datetime import datetime, timedelta, timezone
import numpy as np

SEED = 20261019
START = datetime(2026, 10, 12, tzinfo=timezone.utc)
NAMES = ["Maya Rao", "Arjun Mehta", "Leela Shah", "Kabir Nair", "Anika Sen", "Rohan Iyer", "Diya Kapoor", "Neel Joshi"]
COLORS = ["#6366f1", "#14b8a6", "#f59e0b", "#ec4899", "#3b82f6", "#8b5cf6", "#10b981", "#f97316"]


def generate_patient(index, days=4, *, meal_shift_hours=0.0, meal_jitter_hours=.38,
                     day_shift_hours_sd=0.0, meal_skip_probability=.06, variable_routine=False):
    """Generate a patient for paired routine audits and augmented training.

    Defaults preserve the original training generator exactly. Timing controls change
    only the timing expression and consume the same original random draws. Daily
    timing and sleep/activity variations use separate random streams. These controls
    support paired synthetic comparisons; a routine used in training is not unseen.
    """
    if not np.isfinite(meal_shift_hours) or not -6 <= meal_shift_hours <= 6:
        raise ValueError("meal_shift_hours must be finite and between -6 and 6")
    if not np.isfinite(meal_jitter_hours) or not 0 <= meal_jitter_hours <= 3:
        raise ValueError("meal_jitter_hours must be finite and between 0 and 3")
    if not np.isfinite(day_shift_hours_sd) or not 0 <= day_shift_hours_sd <= 4:
        raise ValueError("day_shift_hours_sd must be finite and between 0 and 4")
    if not np.isfinite(meal_skip_probability) or not .06 <= meal_skip_probability <= .5:
        raise ValueError("meal_skip_probability must be between .06 and .5")
    rng = np.random.default_rng(SEED + index * 104729)
    timing_rng = np.random.default_rng(SEED + index * 104729 + 700000003)
    routine_rng = np.random.default_rng(SEED + index * 104729 + 900000011)
    age = int(rng.integers(28, 75))
    bmi = round(float(rng.uniform(21, 36)), 1)
    hba1c = round(float(rng.uniform(5.5, 9.1)), 1)
    years = round(float(max(0, rng.normal((hba1c - 5.5) * 3, 2))), 1)
    ehr = {"age": age, "bmi": bmi, "hba1c": hba1c,
           "ldl": int(rng.integers(75, 175)), "diabetesYears": years,
           "diagnoses": ["Type 2 diabetes (simulated)"] if hba1c >= 6.5 else ["Elevated glucose history (simulated)"],
           "medications": ["Fictional medication history; no dose or treatment model"],
           "geneticMarker": "Fictional marker GT-SIM-" + str(index % 3 + 1) + "; descriptive only"}
    count = days * 288
    minute = np.arange(count) * 5.
    hour = minute / 60 % 24
    sleep_start = float(rng.uniform(22, 23.5))
    wake = float(rng.uniform(5.7, 7.6))
    sleep = ((hour >= sleep_start) | (hour < wake)).astype(float)
    steps = np.where(sleep > 0, rng.poisson(.3, count), rng.poisson(8, count)).astype(float)
    activity = np.zeros(count)
    meal = np.zeros(count)
    resistance = .52 + .21 * (hba1c - 5.5) + .006 * (bmi - 25)
    tau = 48 + 11 * (hba1c - 5.5)
    # Prior-day pulses initialize the first day without a cold-start meal artifact.
    for day in range(-1, days):
        day_shift = timing_rng.normal(0, day_shift_hours_sd)
        for meal_hour, carbs in [(7.7, 48), (12.7, 68), (19.0, 62)]:
            skip_draw = rng.random()
            if skip_draw < .06:
                continue
            meal_minute = (day * 24 + meal_hour + meal_shift_hours + day_shift + rng.normal(0, meal_jitter_hours)) * 60
            amount = max(15, rng.normal(carbs, 12))
            # Extra skips consume the original jitter/amount draws, preserving other streams.
            if skip_draw < meal_skip_probability:
                continue
            elapsed = np.maximum(0, minute - meal_minute)
            pulse = (elapsed / tau) * np.exp(1 - elapsed / tau)
            pulse[minute < meal_minute] = 0
            meal += amount * resistance * pulse
        if rng.random() < .35:
            snack = (day * 24 + rng.uniform(14, 17)) * 60
            elapsed = np.maximum(0, minute - snack)
            pulse = elapsed / tau * np.exp(1 - elapsed / tau)
            pulse[minute < snack] = 0
            meal += rng.uniform(12, 32) * resistance * pulse
        walk_start = (day * 24 + rng.uniform(16, 18)) * 60
        walk_mask = (minute >= walk_start) & (minute < walk_start + rng.uniform(20, 50))
        steps[walk_mask] += rng.integers(180, 410, int(walk_mask.sum()))
        elapsed = np.maximum(0, minute - walk_start)
        effect = 12 * elapsed / 45 * np.exp(1 - elapsed / 45)
        effect[minute < walk_start] = 0
        activity += effect
    if variable_routine:
        # Separate RNG changes daily sleep/activity without perturbing the original noise draws.
        for day in range(days):
            block = slice(day*288, (day+1)*288)
            sleep_shift = routine_rng.normal(0, 1.25)
            wake_shift = sleep_shift + routine_rng.normal(0, .6)
            local_hour = hour[block]
            bedtime, waketime = (sleep_start+sleep_shift)%24, (wake+wake_shift)%24
            asleep = ((local_hour >= bedtime) & (local_hour < waketime)) if bedtime < waketime else ((local_hour >= bedtime) | (local_hour < waketime))
            sleep[block] = asleep.astype(float)
            activity_shift = int(round(routine_rng.uniform(-3, 3)*12))
            activity[block] = np.roll(activity[block], activity_shift)
            steps[block] = np.roll(steps[block], activity_shift)
        sleeping = sleep > 0
        steps[sleeping] = routine_rng.poisson(.3, int(sleeping.sum()))
    noise = np.zeros(count)
    for i in range(1, count):
        noise[i] = .93 * noise[i-1] + rng.normal(0, 1.5)
    baseline = 99 + 6.5 * (hba1c - 5.5) + .25 * (bmi - 25) + rng.normal(0, 6)
    glucose = np.clip(baseline + meal - activity + 5 * np.sin(2 * np.pi * (hour - 4) / 24) + noise, 65, 310)
    hr = np.clip(69 + .2 * (age-45) - 9 * sleep + .045 * steps + .06 * meal + rng.normal(0, 2.8, count), 44, 145)
    hrv = np.clip(49 - .25 * (age-45) - 2 * (hba1c-6) + 13 * sleep - .018 * steps + rng.normal(0, 4, count), 12, 95)
    series = [{"timestamp": (START + timedelta(minutes=i*5)).isoformat().replace("+00:00", "Z"),
               "glucose": round(float(glucose[i]), 1), "hr": round(float(hr[i]), 1),
               "hrv": round(float(hrv[i]), 1), "steps": int(steps[i]), "sleep": int(sleep[i])}
              for i in range(count)]
    return {"id": f"SYN-{index+1:03d}", "name": f"Synthetic patient {index+1}", "initials": "SP",
            "sex": "Female" if index % 2 == 0 else "Male", "age": age, "color": COLORS[index % 8],
            "ehr": ehr, "series": series, "defaultCursor": count-25, "synthetic": True}


def display_patient(patient, display_index):
    patient["name"] = NAMES[display_index]
    patient["initials"] = "".join(n[0] for n in NAMES[display_index].split())
    patient["color"] = COLORS[display_index]
    return patient
