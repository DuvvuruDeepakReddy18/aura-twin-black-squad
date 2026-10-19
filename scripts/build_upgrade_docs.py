"""Generate the v2 Challenge Lab mini-deck and narration; leaves v1 artifacts unchanged."""
from pathlib import Path
import json, re
from reportlab.pdfgen import canvas
from pypdf import PdfReader
from build_docs import base, txt, rr, card, arrow, bullets, screenshot, W, H, INK, TEAL, MINT, MUTED, WHITE

PROJECT=Path(__file__).resolve().parents[1]
OUT=PROJECT/'docs'
STRESS=json.loads((PROJECT/'data/stress.json').read_text())

NARRATION=[
('A digital twin the jury can challenge.', '''AURA Twin version two turns model evidence into an interactive experiment. The original prototype combines synthetic historical health context and wearable signals to forecast glucose. The upgrade lets a reviewer choose a patient, a cutoff and a signal condition, freeze a prediction, then reveal the recorded future.

Our distinction is the complete inspection loop. We do not claim to have invented glucose digital twins or counterfactual interfaces. We make a prediction, its baseline comparison, its failure behavior and its artifact fingerprints reviewable together. This supplement covers the upgrade; the original walkthrough remains available. All data remain generated, the trained model is unchanged, and clinical validity is not established.'''),
('Freeze the available past. Reveal the recorded future.', '''The experiment begins with a patient, timestamp and sensor case. The server makes a copy of the history and physically truncates it at the prediction cutoff before inference. The freeze response contains the prediction and quality information but no future values. After inference, the server stores the original synthetic future for later comparison.

Reveal evaluates the frozen result without recomputing it. The reviewer sees each available forecast horizon, its recorded value, its error, the interval hit, and a persistence comparison using the same available input. One selected window is an example, not a cohort metric. The dataset is public, so this separation is a reproducible demonstration protocol, not a secure blinded clinical trial.'''),
('Four cases. Four different lessons.', '''Clean replay establishes the selected window's baseline. The ten-minute glucose gap removes the final two glucose readings and demonstrates degraded data and forward filling. The thirty-minute dropout removes six readings and crosses the stale-glucose boundary, so prediction is withheld.

The fourth case adds thirty milligrams per deciliter to the recent observed glucose window, with the documented upper bound. These values can remain plausible, complete and fresh. The quality gate can pass even though the input is biased. This is an intentionally exposed blind spot, not a bias detector. Each perturbation affects a copy of the input history; the reference future remains unchanged. The jury can inspect the actual selected-window result, including cases where persistence performs better.'''),
('Changed routines expose clock dependence.', '''The separate stress audit holds the model, scaling, calibration, intervals and twenty-percent alert threshold fixed. It changes main-meal timing for the same forty-eight held-out synthetic patients and evaluates six thousand seven hundred and twenty windows per case.

On the original schedule, two-hour mean absolute error is ten point nine five. With meals delayed two hours, it rises to twenty-one point six two. With a four-hour delay, it is twenty-two point seven eight, worse than persistence at nineteen point nine nine. Interval coverage falls from ninety percent to about sixty-one percent, and event recall falls sharply. Irregular timing also degrades performance. These post-hoc synthetic tests expose clock dependence; they are not evidence that robustness has been solved.'''),
('A receipt for the experiment, not a trust certificate.', '''A downloaded receipt records the frozen experiment and its revealed result. It includes SHA-two-fifty-six fingerprints of the exact model file and the canonical perturbed input prefix. An offline command verifies these fingerprints and recomputes the prediction and outcome from the packaged artifacts.

A hash is not a digital signature or independent timestamp. The verifier checks consistency with local artifacts; it does not establish trusted authorship. Server sessions are temporary and memory-only, so download the receipt while it is available. The receipt is a portable demonstration artifact, not a governed clinical audit record. These limits are part of the design explanation.'''),
('Let the jury inspect both the result and the limits.', '''The live challenge takes three minutes. Select a patient and a cutoff. Freeze the clean prediction and reveal the future. Compare the model with persistence. Try the short gap, the longer dropout, and the plausible bias. Export the receipt and point to the separate routine-shift results.

If the model misses, explain the failure before changing the patient. A summary score can hide local errors; this workflow makes them visible. AURA's contribution is a working combination of data fusion, explicit predictions, observable failure handling and traceable experiments. The next steps are broader testing and independent validation, guided by the limitations this challenge has exposed.''')
]

def draw():
    c=canvas.Canvas(str(OUT/'AURA_Twin_Challenge_Lab.pdf'),pagesize=(W,H))
    c.setTitle('AURA Twin — v2 Challenge Lab supplement'); c.setAuthor('Black Squad')
    base(c,1,'Version 2 / Evidence you can inspect',None,dark=True)
    txt(c,'A digital twin<br/>the jury can challenge.',44,113,850,47,WHITE,True,53)
    txt(c,'Choose. Freeze. Reveal. Compare.',47,263,820,27,MINT,True)
    txt(c,'An interactive test of the forecast, its failure boundaries<br/>and the artifacts behind the result.',47,315,820,21,'B9D2CE')
    txt(c,'Black Squad · Amrita Vishwa Vidyapeetham, Chennai',47,427,850,16,WHITE,True)
    txt(c,'v2 supplement · unchanged model · generated data only · not clinical validation',47,468,850,12,MINT)
    c.showPage()
    base(c,2,'Challenge architecture','Freeze the available past. Reveal the recorded future.','The freeze response omits future values; the public dataset makes this a demonstration protocol.')
    card(c,42,191,202,196,'Choose','Patient, cutoff and sensor condition. Copy and truncate history.','01')
    card(c,279,191,202,196,'Freeze','Infer on the prefix. Preserve output, quality and fingerprints.','02',MINT)
    card(c,516,191,202,196,'Reveal','Compare the frozen result with original recorded future.','03')
    card(c,753,191,165,196,'Export','Download the experiment receipt.','04')
    for x in [246,483,720]: arrow(c,x,288,x+29,288)
    rr(c,42,420,876,65,WHITE)
    txt(c,'Outcome table',62,438,175,15,TEAL,True)
    txt(c,'Forecast error · persistence error · interval hit · exact +120-minute label<br/>No recalculation on reveal. A selected window is not a cohort metric.',244,433,650,13,INK)
    c.showPage()
    base(c,3,'Failure behavior','Four cases. Four different lessons.','The reference future is unchanged; each challenge modifies only its input copy.')
    items=[('Clean replay','Original available history.<br/>Inspect an honest baseline.'),('10-minute CGM gap','Last two glucose samples removed.<br/>Degraded data; forward filling.'),('30-minute dropout','Last six glucose samples removed.<br/>Stale input; prediction withheld.'),('Undetected sensor bias','+30 mg/dL over the recent CGM window.<br/>Can pass freshness checks while wrong.')]
    for i,(title,body) in enumerate(items): card(c,42+(i%2)*457,183+(i//2)*144,419,122,title,body,fill=MINT if i==3 else WHITE)
    txt(c,'Quality checks are not a certificate of sensor correctness.',44,476,870,15,TEAL,True)
    c.showPage()
    base(c,4,'Post-hoc synthetic stress audit','Changed routines expose clock dependence.','Frozen model · fixed 0.20 alert threshold · 48 held-out patients / 6,720 windows per case')
    headers=[('Meal timing',58,260),('MAE',355,100),('Persistence',470,120),('Coverage',622,120),('Recall',780,100)]
    rr(c,42,183,876,41,MINT)
    for t,x,w in headers: txt(c,t,x,196,w,13,TEAL,True)
    labels=['Original schedule','Delayed +2 hours','Delayed +4 hours','Irregular (1.5h SD)']
    for i,case in enumerate(STRESS['cases']):
        yy=234+i*47
        rr(c,42,yy,876,40,WHITE)
        vals=[labels[i],f"{case['mae']:.2f}",f"{case['persistenceMae']:.2f}",f"{case['intervalCoverage']*100:.1f}%",f"{case['recall']*100:.1f}%"]
        for (unused,x,w),val in zip(headers,vals): txt(c,val,x,yy+11,w,14,INK,i==2)
    txt(c,'MAE in mg/dL at +120 min; interval coverage is for nominal 90% bands.',44,434,870,12,MUTED)
    txt(c,'The +4h case loses to persistence. This audit exposes a limitation; it does not fix it.',44,463,870,16,TEAL,True)
    c.showPage()
    base(c,5,'Provenance & boundaries','A receipt for the experiment, not a trust certificate.','SHA-256 fingerprints identify content. They do not establish clinical validity or trusted authorship.')
    card(c,42,185,419,230,'Inside the receipt','Patient + cutoff + case<br/>Frozen prediction and quality<br/>Model version and content fingerprint<br/>Perturbed input-prefix fingerprint<br/>Revealed outcome, when available','01')
    card(c,499,185,419,230,'Explicit boundaries','Unsigned; no independent timestamp<br/>Memory-only experiment sessions<br/>One-hour expiry; 128-session cap<br/>No clinical identity or audit governance<br/>No claim of tamper-proof evidence','02',MINT)
    txt(c,'Offline check: node scripts/verify_receipt.mjs receipt.json',44,443,870,16,TEAL,True)
    txt(c,'Recomputes hashes, prediction and reveal. Consistency does not authenticate the author or timestamp.',44,475,870,12,MUTED)
    c.showPage()
    base(c,6,'The live jury challenge','A three-minute challenge. A reviewable result.','Let the jury choose a supported patient and cutoff, then inspect the result together.')
    if not screenshot(c,'challenge.jpg',42,182,546,274,crop=(.179,.345,.703,.96)):
        bullets(c,[('Freeze and reveal','Compare four horizons with the same recorded future and persistence.'),('Challenge the input','Short gap, dropout and plausible bias expose different limits.'),('Preserve the evidence','Export the receipt; keep the post-hoc stress results separate.')],42,184,515,17,18)
    rr(c,608,184,310,258,MINT)
    txt(c,'Our defensible distinction',628,208,270,20,TEAL,True)
    txt(c,'A working, inspectable product-and-evidence loop.<br/><br/>No “first glucose twin” claim.<br/>No clinical efficacy claim.<br/>No causal treatment claim.',628,269,270,16,INK)
    txt(c,'Related work: GlyTwin (arXiv:2504.09846) · VVUQ perspective (npj Digital Medicine, 2025)',44,473,870,11,MUTED)
    c.linkURL('https://arxiv.org/abs/2504.09846',(44,48,430,69),relative=0,thickness=0)
    c.linkURL('https://www.nature.com/articles/s41746-025-01447-y',(432,48,918,69),relative=0,thickness=0)
    c.showPage(); c.save()
    records=[{'slide':i+1,'title':title,'text':text.strip()} for i,(title,text) in enumerate(NARRATION)]
    (OUT/'narration-upgrade.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
    count=sum(len(re.findall(r'\b[\w’.-]+\b',r['text'])) for r in records)
    print('Pages:',len(PdfReader(OUT/'AURA_Twin_Challenge_Lab.pdf').pages),'Narration words:',count)

if __name__=='__main__': draw()
