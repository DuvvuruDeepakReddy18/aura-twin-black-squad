"""Real research-data experiment. Develop freezes before evaluate opens final data.

Synthetic EHR is an unmatched negative control, not physiological ground truth.
The prior synthetic v3 experiment is preserved and never scored on these data.
"""
from pathlib import Path
import os
os.environ.setdefault("OMP_NUM_THREADS","4")
import argparse
import hashlib
import json
import pickle
from datetime import datetime,timezone
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor,HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (roc_auc_score,average_precision_score,brier_score_loss,
                            confusion_matrix,precision_recall_curve,roc_curve)
from research_data import (ROOT, RAW, PROTOCOL, HORIZONS, FEATURES, CGM_FEATURES,
                          WEARABLE_FEATURES,MATCHED_FEATURES,SYNTHETIC_FEATURES,
                          load_participant,features,window_dataset,finite)
from train_robust import export_tree as original_export_tree,bins

OUT=ROOT/"data"
WORK=ROOT/"work"/"research"
SEED=PROTOCOL["seed"]
TRUTH={}
FAMILIES={
 "cgmOnly":{"label":"CGM history only","features":CGM_FEATURES},
 "wearableOnly":{"label":"CGM + HR + IBI-derived RMSSD","features":CGM_FEATURES+WEARABLE_FEATURES},
 "matchedFusion":{"label":"Matched research HbA1c/sex + wearables","features":CGM_FEATURES+WEARABLE_FEATURES+MATCHED_FEATURES},
 "ehrOnly":{"label":"Unmatched Synthea EHR only (negative control)","features":SYNTHETIC_FEATURES},
 "compositeFusion":{"label":"Unmatched Synthea EHR + wearables (negative control)","features":CGM_FEATURES+WEARABLE_FEATURES+SYNTHETIC_FEATURES},
}
def now(): return datetime.now(timezone.utc).isoformat()
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,allow_nan=False),encoding="utf-8")
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def sigmoid(x):return 1/(1+np.exp(-np.clip(x,-700,700)))
def export_tree(estimator):
    result=original_export_tree(estimator)
    for tree in result["trees"]:
        for node in tree["nodes"]:
            # HistGradientBoosting uses +inf to split missing versus all finite
            # values. MAX_FLOAT preserves every finite comparison in JSON.
            if np.isposinf(node[1]):node[1]=float(np.finfo(np.float64).max)
            if not np.isfinite(node[1]):raise ValueError("Unexpected non-finite tree threshold")
    return result
def load_split(name):
    patients=[];audits=[];targets={}
    synthea=json.loads((ROOT/"data"/"research"/"synthea.json").read_text(encoding="utf-8"))["profiles"]
    publisher_hashes={}
    for line in (RAW/"SHA256SUMS.txt").read_text().splitlines():
        value,path=line.split(maxsplit=1);publisher_hashes[path.lstrip("*./")]=value
    for identifier in PROTOCOL["splits"][name]:
        print(f"Preprocessing {name} participant {identifier}",flush=True)
        verified={}
        for signal in ["Dexcom","HR","IBI"]:
            relative=f"{identifier}/{signal}_{identifier}.csv"
            actual=digest(RAW/relative)
            assert actual==publisher_hashes[relative],f"Raw source checksum mismatch: {relative}"
            verified[relative]=actual
        patient,audit,target=load_participant(identifier)
        audit["sourceSHA256"]=verified
        TRUTH[identifier]=[{"timestamp":datetime.fromtimestamp(float(t),timezone.utc).isoformat().replace("+00:00","Z"),
                            "glucose":float(v)} for t,v in zip(*target)]
        patient["ehr"]=synthea[int(identifier)-1]
        patient["provenance"]["assignment"]="Source ID rank maps to UUID-sorted Synthea profile; arbitrary, not a matched person."
        patients.append(patient);audits.append(audit);targets[identifier]=target
    data=window_dataset(patients,targets)
    if not len(data["x"]):raise ValueError(f"No eligible windows: {name}")
    audit_result=audit_dataset(data,patients)
    for patient in patients:
        eligible=data["cursors"][data["groups"]==patient["sourceParticipantId"]]
        patient["defaultCursor"]=int(eligible[0]) if len(eligible) else None
    for audit in audits:audit["leakageAudit"]=audit_result
    return data,patients,audits

def audit_dataset(data,patients):
    all_ids=sum(PROTOCOL["splits"].values(),[])
    assert len(all_ids)==len(set(all_ids)), "Participant split overlap"
    by_id={p["sourceParticipantId"]:p for p in patients}
    cutoffs=np.array([datetime.fromisoformat(by_id[g]["series"][int(c)]["timestamp"].replace("Z","+00:00")).timestamp()
                       for g,c in zip(data["groups"],data["cursors"])])
    assert np.all(data["targetTimes"]>cutoffs[:,None]), "Target is not strictly future"
    assert np.all(np.abs(data["targetTimes"]-cutoffs[:,None]-np.array(HORIZONS)[None,:]*60)<=150), "Target outside tolerance"
    checked=0
    for patient in patients:
        times=[datetime.fromisoformat(r["timestamp"].replace("Z","+00:00")) for r in patient["series"]]
        assert all((b-a).total_seconds()==300 for a,b in zip(times,times[1:])), "Grid is not regular"
        for row,stamp in zip(patient["series"],times):
            source=row.get("sourceTimestamp")
            assert source is None or datetime.fromisoformat(source.replace("Z","+00:00"))<=stamp, "Future CGM in input"
        eligible=data["cursors"][data["groups"]==patient["sourceParticipantId"]]
        for cursor in eligible[::max(1,len(eligible)//4)][:4]:
            full=features(patient,int(cursor))
            truncated=features({**patient,"series":patient["series"][:int(cursor)+1]},int(cursor))
            np.testing.assert_allclose([full[n] if finite(full[n]) else np.nan for n in FEATURES],
                                       [truncated[n] if finite(truncated[n]) else np.nan for n in FEATURES],
                                       rtol=0,atol=0,equal_nan=True)
            checked+=1
    return {"passed":True,"checkedWindows":len(data["x"]),"prefixTruncationCases":checked,
            "splitDisjointness":True,"inputSourceTimesNotFuture":True,"targetsStrictlyFutureWithinTolerance":True}
def labels(data,target):
    if target["kind"]=="absolute":return data["y"][:,-1]>=target["threshold"]
    return data["y"][:,-1]-data["x"][:,FEATURES.index("glucose")]>=target["threshold"]
def macro(values,groups):return float(np.mean([np.mean(values[groups==g]) for g in np.unique(groups)]))
def fit(data,names,config):
    indices=[FEATURES.index(n) for n in names]
    x=data["x"][:,indices]
    options=dict(max_iter=config["maxIter"],max_leaf_nodes=config["maxLeafNodes"],
                 min_samples_leaf=config["minSamplesLeaf"],learning_rate=config["learningRate"],
                 l2_regularization=config["l2Regularization"],max_bins=63,
                 early_stopping=False,random_state=SEED)
    groups=data["groups"]
    weights=np.array([len(groups)/len(np.unique(groups))/np.sum(groups==g) for g in groups])
    regressors=[HistGradientBoostingRegressor(loss="absolute_error",**options).fit(x,data["y"][:,i],sample_weight=weights) for i in range(4)]
    classifier=HistGradientBoostingClassifier(**options).fit(x,data["labels"],sample_weight=weights)
    return {"names":names,"indices":indices,"regressors":regressors,"classifier":classifier,"config":config}
def predict(family,data):
    x=data["x"][:,family["indices"]]
    return np.column_stack([m.predict(x) for m in family["regressors"]]),family["classifier"].decision_function(x)
def calibrate(family,data):
    pred,raw=predict(family,data)
    mapping=LogisticRegression(C=10,max_iter=1000,random_state=SEED).fit(raw.reshape(-1,1),data["labels"])
    probability=mapping.predict_proba(raw.reshape(-1,1))[:,1]
    widths=np.quantile(np.abs(data["y"]-pred),.9,axis=0,method="higher")
    scored=[]
    for threshold in np.arange(.025,.976,.005):
        tn,fp,fn,tp=confusion_matrix(data["labels"],probability>=threshold,labels=[False,True]).ravel()
        f1=2*tp/max(1,2*tp+fp+fn)
        scored.append((f1,float(threshold)))
    threshold=max(scored)[1]
    return {"slope":float(mapping.coef_[0,0]),"intercept":float(mapping.intercept_[0]),
            "widths":widths.tolist(),"threshold":threshold,
            "calibrationF1":max(scored)[0],"calibrationWindows":len(probability)}
def export(family,calibration,target,selected_key):
    names=family["names"]
    training=family["trainingX"]
    refs=[];ranges=[]
    for col in training.T:
        values=col[np.isfinite(col)]
        refs.append(float(np.median(values)) if len(values) else None)
        ranges.append({"low":float(np.quantile(values,.01)),"high":float(np.quantile(values,.99))} if len(values) else None)
    classifier=export_tree(family["classifier"])
    classifier.update(calibrationSlope=calibration["slope"],calibrationIntercept=calibration["intercept"])
    groups=[]
    for title,source,groupnames in [
        ("Recent glucose trajectory","Open research CGM",CGM_FEATURES),
        ("Heart rate and IBI-derived variability","Open research HR + derived RMSSD",WEARABLE_FEATURES),
        ("Matched research baseline","Matched source HbA1c/sex; timing assumption disclosed",MATCHED_FEATURES),
        ("Unmatched synthetic EHR","Different Synthea person; negative control",SYNTHETIC_FEATURES)]:
        indices=[i for i,n in enumerate(names) if n in groupnames]
        if indices:groups.append({"name":title,"source":source,"indices":indices})
    return {"schemaVersion":1,"modelVersion":"aura-research-1.0.0","modelKind":"hist_gradient_boosting",
        "featureSet":"big_ideas_history_v1","featureNames":names,"referenceValues":refs,"trainingRanges":ranges,
        "primaryFamily":selected_key,"familyLabel":FAMILIES[selected_key]["label"],"driverGroups":groups,
        "regression":{"models":[export_tree(m) for m in family["regressors"]],"residualQuantiles":calibration["widths"]},
        "classification":classifier,"target":target,
        "targetDefinition":target["definition"],"inputHistoryMinutes":360,"targetTimestampToleranceSeconds":150,
        "alertPolicy":{"threshold":calibration["threshold"],"method":"Maximum F1 on separate calibration participants; threshold grid .025..975 step .005; ties choose higher threshold.",
                       "calibrationF1":calibration["calibrationF1"]},
        "split":PROTOCOL["splits"],"inputSources":[g["source"] for g in groups],
        "datasetVersion":"1.1.3","seed":SEED,"frozenAt":now(),
        "syntheticEhrUsed":selected_key in ["ehrOnly","compositeFusion"],
        "limitations":["Only16 research participants; final evaluation has3 and calibration2.",
                       "Unmatched Synthea EHR belongs to a different simulated person and cannot establish clinical fusion.",
                       "Matched HbA1c measurement time is unspecified; treating it as baseline is an assumption.",
                       "Source HR timestamps may be minute-rounded; conservatively delayed to completed minute.",
                       "No sleep stages, step counts or activity were imported; missing channels remain unavailable.",
                       "Targets use nearest actual CGM observation within150seconds of nominal horizon; no target interpolation.",
                       "Empirical residual intervals and Platt calibration are limited by the small calibration cohort."]}
def metric(data,pred,prob,widths,threshold):
    y=data["y"];lab=data["labels"];decision=prob>=threshold
    tn,fp,fn,tp=confusion_matrix(lab,decision,labels=[False,True]).ravel()
    result={"windows":len(y),"participants":len(np.unique(data["groups"])),
        "positiveWindows":int(lab.sum()),"positiveRate":float(lab.mean()),
        "mae":float(np.mean(np.abs(y[:,-1]-pred[:,-1]))),
        "participantMacroMae":macro(np.abs(y[:,-1]-pred[:,-1]),data["groups"]),
        "rmse":float(np.sqrt(np.mean((y[:,-1]-pred[:,-1])**2))),
        "auroc":float(roc_auc_score(lab,prob)) if len(np.unique(lab))==2 else None,
        "auprc":float(average_precision_score(lab,prob)) if lab.any() else None,
        "brier":float(brier_score_loss(lab,prob)),"threshold":float(threshold),
        "recall":float(tp/max(1,tp+fn)),"precision":float(tp/max(1,tp+fp)),
        "f1":float(2*tp/max(1,2*tp+fp+fn)),
        "confusionMatrix":[[int(tn),int(fp)],[int(fn),int(tp)]],
        "intervalCoverage":float(np.mean(np.abs(y[:,-1]-pred[:,-1])<=widths[-1])),
        "intervalMeanWidth":float(2*widths[-1]),"calibration":bins(lab,prob)}
    result["ece"]=float(sum(b["count"]/len(lab)*abs(b["observed"]-b["predicted"]) for b in result["calibration"] if b["count"]))
    result["byHorizon"]=[{"minutes":h,"mae":float(np.mean(np.abs(y[:,i]-pred[:,i]))),
        "rmse":float(np.sqrt(np.mean((y[:,i]-pred[:,i])**2))),
        "intervalCoverage":float(np.mean(np.abs(y[:,i]-pred[:,i])<=widths[i])),
        "intervalMeanWidth":float(2*widths[i])} for i,h in enumerate(HORIZONS)]
    return result
def subset(data,mask):return {k:v[mask] for k,v in data.items() if isinstance(v,np.ndarray) and len(v)==len(mask)}
def develop():
    if (OUT/"research-model.json").exists():raise RuntimeError("Frozen research artifact exists; refuse overwrite.")
    WORK.mkdir(parents=True,exist_ok=True)
    train,trainpatients,trainaudit=load_split("train")
    audit=[]
    for kind,threshold in [("absolute",180),("rise",20)]:
        lab=(train["y"][:,-1]>=threshold) if kind=="absolute" else (train["y"][:,-1]-train["x"][:,0]>=threshold)
        audit.append({"kind":kind,"threshold":threshold,"windows":len(lab),"positiveWindows":int(lab.sum()),
                      "positiveRate":float(lab.mean()),
                      "positiveParticipants":len(np.unique(train["groups"][lab])),
                      "byParticipant":[{"id":g,"windows":int(np.sum(train["groups"]==g)),
                                         "positives":int(np.sum(lab[train["groups"]==g]))} for g in np.unique(train["groups"])]})
    a=audit[0];r=audit[1]
    target={"kind":"absolute","threshold":180,"horizonMinutes":120,"toleranceSeconds":150,
            "definition":"Observed CGM glucose >=180 mg/dL at approximately +120 minutes (nearest measurement within ±150 seconds).","unit":"mg/dL"}
    if not (a["positiveWindows"]>=200 and a["positiveRate"]>=.05 and a["positiveParticipants"]>=5):
        if not (r["positiveWindows"]>=100 and r["positiveParticipants"]>=5):
            write(OUT/"research-label-audit.json",{"audit":audit,"decision":"Classification unsupported"})
            raise RuntimeError("Insufficient positive support for predeclared research targets; no fabricated classifier.")
        target.update(kind="rise",threshold=20,
                      definition="Observed CGM glucose rise >=20 mg/dL from the latest available current value by approximately +120 minutes (nearest measurement within ±150 seconds).")
    write(OUT/"research-label-audit.json",{"createdAt":now(),"scope":"Train participants only","audit":audit,"selectedTarget":target,
                                          "rule":PROTOCOL["targetAuditRule"]})
    print("Train-only target audit:",target,flush=True)
    selection,selectionpatients,selectionaudit=load_split("selection")
    train["labels"]=labels(train,target);selection["labels"]=labels(selection,target)
    chosen={};ranking={}
    for key,info in FAMILIES.items():
        results=[]
        for config in PROTOCOL["modelCandidates"]:
            print(f"Fitting {key}/{config['id']}",flush=True)
            family=fit(train,info["features"],config)
            pred,raw=predict(family,selection);p=sigmoid(raw)
            results.append({"family":family,"config":config,
                "selectionMae":macro(np.abs(selection["y"][:,-1]-pred[:,-1]),selection["groups"]),
                "selectionBrier":macro((selection["labels"]-p)**2,selection["groups"])})
        reg=min(results,key=lambda x:x["selectionMae"]);clf=min(results,key=lambda x:x["selectionBrier"])
        selected=reg["family"]
        selected["classifier"]=clf["family"]["classifier"]
        selected["regressionConfig"]=reg["config"];selected["classificationConfig"]=clf["config"]
        selected["trainingX"]=train["x"][:,selected["indices"]]
        chosen[key]=selected
        ranking[key]={"label":info["label"],"candidates":[{k:v for k,v in r.items() if k!="family"} for r in results],
                      "selectedRegression":reg["config"]["id"],"selectedClassification":clf["config"]["id"],
                      "selectionMae":reg["selectionMae"],"selectionBrier":clf["selectionBrier"]}
    primary=min(["cgmOnly","wearableOnly","matchedFusion"],key=lambda k:ranking[k]["selectionMae"])
    calibration,calpatients,calaudit=load_split("calibration");calibration["labels"]=labels(calibration,target)
    persistence_calibration=np.repeat(calibration["x"][:,0,None],4,axis=1)
    persistence_widths=np.quantile(np.abs(calibration["y"]-persistence_calibration),.9,axis=0,method="higher").tolist()
    fitted={}
    for key,family in chosen.items():
        cal=calibrate(family,calibration);artifact=export(family,cal,target,key)
        pred,raw=predict(family,calibration)
        fitted[key]={"family":family,"calibration":cal,"artifact":artifact,
                     "calibrationMetrics":metric(calibration,pred,sigmoid(raw*cal["slope"]+cal["intercept"]),cal["widths"],cal["threshold"])}
    selected=fitted[primary]
    write(OUT/"research-model.json",selected["artifact"])
    write(OUT/"research-ablations.json",{key:item["artifact"] for key,item in fitted.items()})
    write(OUT/"research-selection.json",{"createdAt":now(),"primaryFamily":primary,"families":ranking})
    frozen={"modelVersion":"aura-research-1.0.0","modelSHA256":digest(OUT/"research-model.json"),"frozenAt":now(),
            "protocolSHA256":digest(OUT/"research-protocol.json"),"testOpened":False,"primaryFamily":primary,
            "target":target,"threshold":selected["calibration"]["threshold"],
            "ablationsSHA256":digest(OUT/"research-ablations.json"),
            "persistenceResidualQuantiles":persistence_widths}
    write(OUT/"research-freeze.json",frozen)
    with (WORK/"frozen-models.pkl").open("wb") as f:
        pickle.dump({"fitted":fitted,"target":target,"primary":primary,"audit":trainaudit+selectionaudit+calaudit,
                     "developmentPatients":trainpatients+selectionpatients+calpatients,"truth":TRUTH,
                     "persistenceWidths":persistence_widths},f)
    # Independent JS parity uses development participants only before final opens.
    parity=[]
    for patient in trainpatients[:4]:
        for cursor in [100,150,200,300]:
            f=features(patient,cursor)
            x=np.array([[f[name] if finite(f[name]) else np.nan for name in FEATURES]])
            pred,raw=predict(selected["family"],{"x":x});cal=selected["calibration"]
            parity.append({"patientId":patient["id"],"cursor":cursor,"features":f,
                           "forecast":pred[0].tolist(),"risk":float(sigmoid(raw*cal["slope"]+cal["intercept"])[0])})
    write(OUT/"research-parity.json",{"modelSHA256":frozen["modelSHA256"],"cases":parity})
    write(OUT/"research-patients.json",trainpatients[:4])
    seal()
    print("Frozen research artifact",frozen,flush=True)

def seal():
    """Bind reproducibility inputs after fitting and before opening final data."""
    if (OUT/"research-final-started.json").exists():raise RuntimeError("Cannot reseal after final opened")
    frozen=json.loads((OUT/"research-freeze.json").read_text())
    assert digest(OUT/"research-model.json")==frozen["modelSHA256"]
    assert digest(OUT/"research-ablations.json")==frozen["ablationsSHA256"]
    assert digest(OUT/"research-protocol.json")==frozen["protocolSHA256"]
    frozen["sealedAt"]=now()
    frozen["cacheSHA256"]=digest(WORK/"frozen-models.pkl")
    paths=["ml/research_data.py","ml/train_research.py","lib/research-model.mjs",
           "scripts/ingest_wearable.py","scripts/ingest_synthea.py",
           "data/research/synthea.json","data/research/PHYSIONET_SHA256SUMS.txt"]
    frozen["sourceSHA256"]={name:digest(ROOT/name) for name in paths}
    frozen["sealNote"]="Cache and source fingerprints recorded before final evaluation; local audit trail, not external preregistration."
    write(OUT/"research-freeze.json",frozen)

def evaluate():
    frozen=json.loads((OUT/"research-freeze.json").read_text())
    if digest(OUT/"research-model.json")!=frozen["modelSHA256"]:raise RuntimeError("Model changed after freeze")
    if digest(OUT/"research-ablations.json")!=frozen["ablationsSHA256"]:raise RuntimeError("Ablations changed after freeze")
    if digest(OUT/"research-protocol.json")!=frozen["protocolSHA256"]:raise RuntimeError("Protocol changed after freeze")
    if digest(WORK/"frozen-models.pkl")!=frozen.get("cacheSHA256"):raise RuntimeError("Fitted cache changed or not sealed")
    for name,expected in frozen.get("sourceSHA256",{}).items():
        if digest(ROOT/name)!=expected:raise RuntimeError(f"Source changed after seal: {name}")
    if (OUT/"research-final-started.json").exists():raise RuntimeError("Final already started; no retuning/repeated selection.")
    write(OUT/"research-final-started.json",{"at":now(),"modelSHA256":frozen["modelSHA256"]})
    with (WORK/"frozen-models.pkl").open("rb") as f:state=pickle.load(f)
    test,patients,audit=load_split("test");test["labels"]=labels(test,state["target"])
    models={};predictions={}
    for key,item in state["fitted"].items():
        pred,raw=predict(item["family"],test);cal=item["calibration"];prob=sigmoid(raw*cal["slope"]+cal["intercept"])
        models[key]={"label":FAMILIES[key]["label"],**metric(test,pred,prob,cal["widths"],cal["threshold"])}
        predictions[key]=(pred,prob,cal)
    persistence=np.repeat(test["x"][:,0,None],4,axis=1)
    # A deterministic persistence classifier is never called calibrated probability.
    p=(persistence[:,-1]>=180).astype(float) if state["target"]["kind"]=="absolute" else np.zeros(len(test["y"]))
    # Comparator bands were fit on calibration and frozen before any final data.
    pw=state["persistenceWidths"]
    models["persistence"]={"label":"Latest glucose persistence (deterministic event baseline)",
                           **metric(test,persistence,p,pw,.5)}
    primary=state["primary"];models["primary"]={**models[primary],"aliasOf":primary}
    pred,prob,cal=predictions[primary]
    error_by_patient=[]
    for group in np.unique(test["groups"]):
        mask=test["groups"]==group
        error_by_patient.append({"participant":group,**metric(subset(test,mask),pred[mask],prob[mask],cal["widths"],cal["threshold"])})
    quality_slices=[]
    for label,mask in [
        ("High CGM coverage",test["x"][:,FEATURES.index("gCoverage120")]>=.96),
        ("Reduced CGM coverage",test["x"][:,FEATURES.index("gCoverage120")]<.96),
        ("HRV coverage <50%",test["x"][:,FEATURES.index("hrvCoverage120")]<.5),
        ("HRV coverage >=50%",test["x"][:,FEATURES.index("hrvCoverage120")]>=.5),
        ("Current glucose <140",test["x"][:,0]<140),
        ("Current glucose >=140",test["x"][:,0]>=140),
        ("Rising prior-hour glucose",test["x"][:,FEATURES.index("gSlope60")]>0),
        ("Flat/falling prior-hour glucose",test["x"][:,FEATURES.index("gSlope60")]<=0)]:
        if mask.any():quality_slices.append({"label":label,**metric(subset(test,mask),pred[mask],prob[mask],cal["widths"],cal["threshold"])})
    fpr,tpr,_=roc_curve(test["labels"],prob)
    precision,recall,_=precision_recall_curve(test["labels"],prob)
    def thin(a,b,n=101):
        ids=np.unique(np.linspace(0,len(a)-1,min(n,len(a))).astype(int))
        return [{"x":float(a[i]),"y":float(b[i])} for i in ids]
    snapshots=[]
    for i in np.linspace(0,len(test["y"])-1,min(120,len(test["y"]))).astype(int):
        snapshots.append({"participant":str(test["groups"][i]),"cursor":int(test["cursors"][i]),
            "actual":float(test["y"][i,-1]),"prediction":float(pred[i,-1]),"risk":float(prob[i]),
            "absoluteError":float(abs(test["y"][i,-1]-pred[i,-1]))})
    patient_map={p["sourceParticipantId"]:p for p in patients}
    hours=np.array([int(patient_map[g]["series"][int(c)]["timestamp"][11:13]) for g,c in zip(test["groups"],test["cursors"])])
    by_time=[]
    for start in [0,6,12,18]:
        mask=(hours>=start)&(hours<start+6)
        if mask.any():by_time.append({"label":f"{start:02d}:00–{start+6:02d}:00 source clock",
            **metric(subset(test,mask),pred[mask],prob[mask],cal["widths"],cal["threshold"])})
    residuals=pred[:,-1]-test["y"][:,-1]
    hist,edges=np.histogram(residuals,bins=20)
    residual_hist=[{"lower":float(edges[i]),"upper":float(edges[i+1]),"count":int(hist[i])} for i in range(len(hist))]
    limits=state["fitted"][primary]["artifact"]["limitations"]+[
        "The primary eligible model was selected on two participants; model ranking may be unstable.",
        "Three held-out participants do not support reliable population confidence intervals or clinical claims.",
        "Window counts overlap in time and are not independent adverse episodes.",
        "No genuine clinical history is linked to the wearable participants beyond supplied research metadata.",
        "Unmatched EHR ablations test arbitrary composite assignment, not physiological fusion.",
        "The primary event is a predeclared research label chosen from train-only prevalence, not a medical diagnosis.",
        "Performance cannot be compared numerically with legacy synthetic v3 because cohort and possibly target differ."]
    metrics={"schemaVersion":1,"modelVersion":"aura-research-1.0.0","modelSHA256":frozen["modelSHA256"],
        "evaluatedAt":now(),"dataType":"open_research","syntheticOnly":False,"target":state["target"],
        "datasetVersion":"1.1.3","primaryFamily":primary,"models":models,"splits":PROTOCOL["splits"],
        "testParticipants":len(patients),"testWindows":len(test["y"]),"byParticipant":error_by_patient,
        "errorAnalysis":quality_slices,"errorByTime":by_time,"residualDistribution":residual_hist,
        "curves":{"roc":thin(fpr,tpr),"precisionRecall":thin(recall,precision)},
        "predictionExamples":snapshots,"calibrationStatus":"Platt calibrated on2 separate participants; small-sample calibration is limited.",
        "calibrationMetrics":state["fitted"][primary]["calibrationMetrics"],
        "limitations":limits,"legacyComparison":"Not comparable: v3 used synthetic streams and a different population/target.",
        "environment":{"numpy":np.__version__,"scikitLearn":sklearn.__version__},
        "leakageAudit":{"passed":all(a["leakageAudit"]["passed"] for a in state["audit"]+audit),
                        "executedChecks":audit[0]["leakageAudit"],"featureHistory":"Only prefix observations, maximum6h",
                        "target":"Actual observation strictly aftercutoff and within150s of each nominalhorizon",
                        "participantPartitionsDisjoint":True,"testOpenedAfterModelFreeze":True}}
    write(OUT/"research-metrics.json",metrics)
    allpatients=state["developmentPatients"]+patients
    write(OUT/"research-patients.json",allpatients)
    write(OUT/"research-truth.json",{**state["truth"],**TRUTH})
    write(OUT/"research-validation.json",{"datasetVersion":"1.1.3","processingVersion":"research-causal-1.0.0",
        "participants":state["audit"]+audit,
        "rules":{"glucose":"OnlyEGV rows;40..400mg/dL; lastobservation <=cutoff within15min, never backwardfill",
                 "hr":"30..220bpm; completed5minmean with>=60samples; roundedminute timestamps delayed60sec",
                 "hrv":"IBI0.3..2sec; successiveacceptedpairs within10sec/samebin;>=20pairs; RMSSDmilliseconds",
                 "unavailable":"No steps, activity or sleep stages fabricated"}})
    download=json.loads((RAW/"download-manifest.json").read_text())
    synthea=json.loads((ROOT/"data"/"research"/"synthea-provenance.json").read_text())
    provenance={"schemaVersion":1,"sources":[
        {"id":"big_ideas","name":"BIG IDEAs Lab Glycemic Variability and Wearable Device Data","version":"1.1.3",
         "url":"https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/",
         "doi":"https://doi.org/10.13026/aw6y-fc44","type":"open_deidentified_research",
         "license":"Open Data Commons Attribution License1.0",
         "licenseUrl":"https://physionet.org/content/big-ideas-glycemic-wearable/view-license/1.1.3/",
         "citation":"Cho,P.,Kim,J.,Bent,B.,&Dunn,J.(2026). BIG IDEAs Lab Glycemic Variability and Wearable Device Data(v1.1.3). PhysioNet.",
         "signals":["CGMmg/dL","HRbpm","IBIseconds"],"derived":["past5minHRmean","IBI-derivedRMSSDmilliseconds"],
         "notImported":["accelerometry","BVP","EDA","temperature","foodlogs"],
         "unavailable":["sleepstages","stepcounts"],"files":download["files"]},
        {"id":"synthea","type":"synthetic_ehr","details":synthea}],
        "compositeWarning":"Synthea profiles and open wearable participants are different people; arbitrary pairing does not validate physiological fusion.",
        "matchedContextWarning":"PhysioNet HbA1c and sex are linked to wearable IDs, but lab availability timing is unspecified.",
        "noIdentifiableRealPatientData":True}
    write(OUT/"research-provenance.json",provenance)
    manifest={"schemaVersion":1,"modelVersion":metrics["modelVersion"],"modelSHA256":frozen["modelSHA256"],
        "datasetVersion":"1.1.3","preprocessingVersion":"research-causal-1.0.0","featureVersion":"big_ideas_history_v1",
        "seed":SEED,"target":state["target"],"split":PROTOCOL["splits"],"evaluationAt":metrics["evaluatedAt"],
        "freeze":frozen,"sourceFiles":download["files"],"leakageAudit":metrics["leakageAudit"],
        "artifacts":{name:{"sha256":digest(OUT/name)} for name in ["research-model.json","research-metrics.json","research-patients.json","research-truth.json","research-protocol.json"]}}
    write(OUT/"research-manifest.json",manifest)
    print(json.dumps({"primaryFamily":primary,"primary":models["primary"],"byParticipant":[
        {k:r[k] for k in ["participant","windows","mae","recall","precision"]} for r in error_by_patient]},indent=2),flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--phase",choices=["develop","seal","evaluate"],required=True)
    parser.add_argument("--output-dir",default=str(OUT))
    parser.add_argument("--work-dir",default=str(WORK))
    args=parser.parse_args()
    OUT=Path(args.output_dir).resolve()
    WORK=Path(args.work_dir).resolve()
    OUT.mkdir(parents=True,exist_ok=True)
    if not (OUT/"research-protocol.json").exists():
        (OUT/"research-protocol.json").write_bytes((ROOT/"data"/"research-protocol.json").read_bytes())
    {"develop":develop,"seal":seal,"evaluate":evaluate}[args.phase]()
