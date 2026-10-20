"""Causal preprocessing and feature extraction for public BIG IDEAs v1.1.3.

Dates in the source are shifted, timezone unspecified. Z is a sortable neutral
encoding here, not a claim that source collection occurred in UTC.
"""
from pathlib import Path
import json
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "work" / "big-ideas-1.1.3"
PROTOCOL = json.loads((ROOT / "data" / "research-protocol.json").read_text())
HORIZONS = [30, 60, 90, 120]
CGM_FEATURES = ["glucose", "glucoseAgeMinutes"] + [f"lag{n}" for n in [15,30,60,90,120,180,360]]
for duration in [30,60,120,360]:
    CGM_FEATURES += [f"gMean{duration}",f"gStd{duration}",f"gMin{duration}",f"gMax{duration}",
                     f"gSlope{duration}",f"gCoverage{duration}"]
CGM_FEATURES += ["gRiseFraction60","gMeanAbsChange60","gAboveMean360"]
WEARABLE_FEATURES = []
for signal in ["hr", "hrv"]:
    for duration in [30,120,360]:
        WEARABLE_FEATURES += [f"{signal}Mean{duration}",f"{signal}Std{duration}",f"{signal}Coverage{duration}"]
MATCHED_FEATURES = ["researchHba1c", "researchSexMale"]
SYNTHETIC_FEATURES = ["syntheticAge", "syntheticBmi", "syntheticHba1c", "syntheticLdl"]
FEATURES = CGM_FEATURES + WEARABLE_FEATURES + MATCHED_FEATURES + SYNTHETIC_FEATURES


def iso(timestamp):
    return pd.Timestamp(timestamp).isoformat(timespec="seconds") + "Z"


def finite(value):
    return value is not None and isinstance(value, (int,float,np.number)) and math.isfinite(value)


def parse(path, kind):
    frame = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
    frame.columns = frame.columns.str.strip()
    original = len(frame)
    if kind == "glucose":
        frame = frame.loc[frame["Event Type"] == "EGV",
                          ["Timestamp (YYYY-MM-DDThh:mm:ss)", "Glucose Value (mg/dL)"]].copy()
    else:
        frame = frame.iloc[:, :2].copy()
    frame.columns = ["time", "value"]
    frame["time"] = pd.to_datetime(frame["time"], format="mixed", errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    invalid = int(frame.isna().any(axis=1).sum())
    frame = frame.dropna().sort_values("time", kind="stable")
    lo, hi = {"glucose": (40,400), "hr": (30,220), "ibi": (.3,2.)}[kind]
    outlier = ~frame["value"].between(lo,hi)
    outliers = int(outlier.sum())
    frame = frame.loc[~outlier].copy()
    duplicates = int(frame["time"].duplicated().sum())
    # Repeated rounded HR minutes are real samples, not duplicate sensor records.
    if kind != "hr":
        frame = frame.drop_duplicates("time", keep="last")
    return frame, {"rawRows": original, "signalRows": len(frame), "invalidRows": invalid,
                   "outliersRemoved": outliers, "repeatedTimestamps": duplicates,
                   "repeatedTimestampPolicy": "Retain minute-rounded HR samples" if kind == "hr" else "Keep last record"}


def load_participant(identifier, raw=RAW):
    folder = raw / identifier
    glucose, ga = parse(folder / f"Dexcom_{identifier}.csv", "glucose")
    hr, ha = parse(folder / f"HR_{identifier}.csv", "hr")
    ibi, ia = parse(folder / f"IBI_{identifier}.csv", "ibi")
    # Minute-truncated HR timestamps cannot prove within-minute order. Do not use
    # the samples until the minute has fully elapsed; exact timestamps add no delay.
    original_hr = pd.read_csv(folder / f"HR_{identifier}.csv", encoding="utf-8-sig", usecols=[0]).iloc[:,0].astype(str)
    rounded = not bool(original_hr.str.contains(r":\d\d:\d\d").any())
    if rounded:
        hr["time"] += pd.Timedelta(seconds=60)
    ha["availabilityDelaySeconds"] = 60 if rounded else 0
    hr["bin"] = hr["time"].dt.ceil("5min")
    hrag = hr.groupby("bin")["value"].agg(["mean","count"])
    ibi["bin"] = ibi["time"].dt.ceil("5min")
    dt = ibi["time"].diff().dt.total_seconds()
    previous_valid = ibi["bin"].eq(ibi["bin"].shift()) & dt.between(.3,10)
    ibi["diffSquared"] = (ibi["value"].diff()*1000)**2
    ibi.loc[~previous_valid,"diffSquared"] = np.nan
    ibiag = ibi.groupby("bin")["diffSquared"].agg(["mean","count"])
    ibiag["rmssd"] = np.sqrt(ibiag["mean"])
    ibiag.loc[ibiag["count"] < 20,"rmssd"] = np.nan
    ia["rmssdBinsOver500msRemoved"] = int((ibiag["rmssd"]>500).sum())
    ibiag.loc[ibiag["rmssd"]>500,"rmssd"] = np.nan
    ia["rmssdDefinition"] = "sqrt(mean(successive accepted IBI differences squared)), ms; same completed 5min bin, adjacent gap<=10s, >=20 pairs"
    grid = pd.DataFrame({"time": pd.date_range(glucose["time"].iloc[0].ceil("5min"),
                                              glucose["time"].iloc[-1].floor("5min"), freq="5min")})
    aligned = pd.merge_asof(grid, glucose.rename(columns={"time":"sourceTime","value":"glucose"}),
                            left_on="time",right_on="sourceTime",direction="backward",
                            tolerance=pd.Timedelta(minutes=15))
    aligned["hr"] = aligned["time"].map(hrag["mean"])
    aligned["hrSamples"] = aligned["time"].map(hrag["count"]).fillna(0).astype(int)
    aligned.loc[aligned["hrSamples"] < 60, "hr"] = np.nan
    aligned["hrv"] = aligned["time"].map(ibiag["rmssd"])
    aligned["ibiPairs"] = aligned["time"].map(ibiag["count"]).fillna(0).astype(int)
    demo = pd.read_csv(raw/"Demographics.csv")
    match = demo.loc[demo.ID == int(identifier)].iloc[0]
    series = []
    for row in aligned.itertuples():
        series.append({"timestamp":iso(row.time),
                       "glucose":float(row.glucose) if pd.notna(row.glucose) else None,
                       "hr":float(row.hr) if pd.notna(row.hr) else None,
                       "hrv":float(row.hrv) if pd.notna(row.hrv) else None,
                       "activity":None,"sleep":None,"steps":None,
                       "sourceTimestamp":iso(row.sourceTime) if pd.notna(row.sourceTime) else None,
                       "quality":{"hrSamples":int(row.hrSamples),"ibiPairs":int(row.ibiPairs),
                                  "glucoseAgeMinutes":(row.time-row.sourceTime).total_seconds()/60 if pd.notna(row.sourceTime) else None}})
    patient = {"id":f"research-{identifier}","name":f"Research participant {identifier}",
               "sourceParticipantId":identifier,"type":"Composite Research Twin",
               "partition":next(key for key,ids in PROTOCOL["splits"].items() if identifier in ids),
               "researchContext":{"sex":str(match.Gender).lower(),"hba1c":float(match.HbA1c),
                                  "source":"PhysioNet Demographics.csv",
                                  "timingAssumption":"Source has no lab timestamp; HbA1c is treated as available baseline research context, not proven pre-replay EHR."},
               "ehr":{},"series":series,
               "availableSignals":["glucose","hr","hrv"],"unavailableSignals":["activity","steps","sleepStages","genetics"],
               "timeBasis":"Date-shifted source local times, timezone unspecified; Z used only as neutral timestamp encoding.",
               "provenance":{"wearable":"PhysioNet BIG IDEAs v1.1.3, de-identified open research data",
                             "hr":"Completed past5min HR mean, minute-rounded source delayed60sec",
                             "hrv":"Derived RMSSD from accepted source IBI differences; not clinical ECG HRV",
                             "syntheticEhr":"Synthea context is a different simulated person; arbitrary composite assignment"}}
    audit = {"participant":identifier,"glucose":ga,"hr":ha,"ibi":ia,"gridRows":len(series),
             "missing":{name:int(aligned[name].isna().sum()) for name in ["glucose","hr","hrv"]},
             "firstTimestamp":series[0]["timestamp"],"lastTimestamp":series[-1]["timestamp"]}
    # Pandas3 may infer microsecond resolution. Make the integer unit explicit.
    targets = (glucose["time"].astype("datetime64[ns]").astype("int64").to_numpy()/1e9,glucose["value"].to_numpy())
    return patient, audit, targets


def features(patient, cursor):
    """Every lookup is confined to the selected prefix. No centered smoothing."""
    if cursor < 72 or cursor >= len(patient["series"]):
        raise ValueError("At least six hours of recorded history are required")
    history = causal_history(patient, cursor)
    f = {"glucose":history[-1]["glucose"],"glucoseAgeMinutes":history[-1].get("quality",{}).get("glucoseAgeMinutes")}
    for lag in [15,30,60,90,120,180,360]:
        f[f"lag{lag}"] = history[-1-lag//5]["glucose"]
    for duration in [30,60,120,360]:
        values = np.array([r["glucose"] if finite(r["glucose"]) else np.nan for r in history[-(duration//5+1):]])
        valid = np.isfinite(values)
        clean = values[valid]
        x = np.arange(len(values))[valid]*5.
        f.update({f"gMean{duration}":float(clean.mean()) if len(clean) else None,
                  f"gStd{duration}":float(clean.std()) if len(clean) else None,
                  f"gMin{duration}":float(clean.min()) if len(clean) else None,
                  f"gMax{duration}":float(clean.max()) if len(clean) else None,
                  f"gCoverage{duration}":float(valid.mean()),
                  f"gSlope{duration}":float(np.sum((x-x.mean())*(clean-clean.mean()))/np.sum((x-x.mean())**2)) if len(clean)>1 else None})
    differences = np.diff(np.array([r["glucose"] if finite(r["glucose"]) else np.nan for r in history[-13:]]))
    differences = differences[np.isfinite(differences)]
    f["gRiseFraction60"] = float(np.mean(differences>0)) if len(differences) else None
    f["gMeanAbsChange60"] = float(np.mean(np.abs(differences))) if len(differences) else None
    f["gAboveMean360"] = f["glucose"]-f["gMean360"] if finite(f["glucose"]) and finite(f["gMean360"]) else None
    for signal in ["hr","hrv"]:
        for duration in [30,120,360]:
            values = [row[signal] for row in history[-duration//5:] if finite(row[signal])]
            f[f"{signal}Mean{duration}"] = float(np.mean(values)) if values else None
            f[f"{signal}Std{duration}"] = float(np.std(values)) if values else None
            f[f"{signal}Coverage{duration}"] = len(values)/(duration//5)
    f["researchHba1c"] = patient["researchContext"].get("hba1c")
    f["researchSexMale"] = {"male":1.,"female":0.}.get(patient["researchContext"].get("sex"))
    for name in ["age","bmi","hba1c","ldl"]:
        value = patient.get("ehr",{}).get(name)
        # Synthea adapter may expose provenance-rich values.
        if isinstance(value,dict):
            value = value.get("value")
        f[f"synthetic{name[0].upper()+name[1:]}"] = value if finite(value) else None
    return f


def causal_history(patient,cursor):
    history=[]
    previous=None
    for row in patient["series"][max(0,cursor-75):cursor+1]:
        item={**row,"quality":dict(row.get("quality",{}))}
        if finite(row["glucose"]):
            previous=row
        elif previous is not None:
            source=previous.get("sourceTimestamp") or previous["timestamp"]
            age=(pd.Timestamp(row["timestamp"])-pd.Timestamp(source)).total_seconds()/60
            if age<=15:
                item["glucose"]=previous["glucose"]
                item["sourceTimestamp"]=source
                item["quality"]["glucoseAgeMinutes"]=age
                item["carriedForward"]=True
        history.append(item)
    return history[-73:]


def valid_window(patient,cursor):
    if cursor<72:
        return False
    h=causal_history(patient,cursor)
    return (finite(h[-1]["glucose"]) and
            h[-1].get("quality",{}).get("glucoseAgeMinutes",100)<=15 and
            sum(finite(row["glucose"]) for row in h[-13:])>=10 and
            sum(finite(row["glucose"]) for row in h)>=58)


def window_dataset(patients, targets):
    rows, ys, groups, cursors, target_times = [],[],[],[],[]
    for patient in patients:
        times, glucose = targets[patient["sourceParticipantId"]]
        for cursor in range(72,len(patient["series"]),3):
            if not valid_window(patient,cursor):
                continue
            now=pd.Timestamp(patient["series"][cursor]["timestamp"]).timestamp()
            future=[]
            stamps=[]
            for horizon in HORIZONS:
                desired=now+horizon*60
                i=np.searchsorted(times,desired)
                choices=[j for j in [i-1,i] if 0<=j<len(times)]
                best=min(choices,key=lambda j:abs(times[j]-desired)) if choices else None
                if best is None or abs(times[best]-desired)>150 or times[best]<=now:
                    break
                future.append(float(glucose[best]));stamps.append(float(times[best]))
            if len(future)!=4:
                continue
            f=features(patient,cursor)
            rows.append([f[name] if finite(f[name]) else np.nan for name in FEATURES])
            ys.append(future);groups.append(patient["sourceParticipantId"]);cursors.append(cursor);target_times.append(stamps)
    return {"x":np.asarray(rows),"y":np.asarray(ys),"groups":np.asarray(groups),
            "cursors":np.asarray(cursors),"targetTimes":np.asarray(target_times)}
