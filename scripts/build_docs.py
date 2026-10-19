from pathlib import Path
import json, math, textwrap
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor as _HexColor, Color, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT/'docs'
OUT.mkdir(parents=True, exist_ok=True)
M = json.loads((PROJECT/'data/metrics.json').read_text())
MODEL = json.loads((PROJECT/'data/model.json').read_text())
F = M['models']['fused']
P = MODEL.get('alertPolicy', {})
W,H=960,540
INK='#102D32'; TEAL='#087F78'; MINT='#C8F1E5'; BG='#F4F8F7'; MUTED='#567078'; CORAL='#CD694F'; LIGHT='#E3ECE9'; WHITE='#FFFFFF'
def HexColor(value): return _HexColor(value if value.startswith('#') else '#'+value)

def rr(c,x,y,w,h,fill=WHITE,r=15,stroke=None):
    c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke or fill)); c.roundRect(x,H-y-h,w,h,r,fill=1,stroke=bool(stroke))

def txt(c,text,x,y,w=850,size=16,color=INK,bold=False,leading=None):
    style=ParagraphStyle('a',fontName='Helvetica-Bold' if bold else 'Helvetica',fontSize=size,leading=leading or size*1.32,textColor=HexColor(color),spaceAfter=0)
    p=Paragraph(text,style); ww,hh=p.wrap(w,1000); p.drawOn(c,x,H-y-hh); return hh

def line(c,x1,y1,x2,y2,color=TEAL,width=2,dash=None):
    c.setStrokeColor(HexColor(color)); c.setLineWidth(width); c.setDash(dash or []); c.line(x1,H-y1,x2,H-y2); c.setDash([])

def arrow(c,x1,y1,x2,y2,color=TEAL):
    line(c,x1,y1,x2,y2,color,2)
    a=math.atan2(y2-y1,x2-x1)
    for d in [-.55,.55]: line(c,x2,y2,x2-8*math.cos(a+d),y2-8*math.sin(a+d),color,2)

def base(c,n,kicker,title,sub=None,dark=False):
    c.setFillColor(HexColor(INK if dark else BG)); c.rect(0,0,W,H,fill=1,stroke=0)
    txt(c,'AURA / TWIN',42,22,180,12,MINT if dark else TEAL,True)
    txt(c,kicker.upper(),650,23,268,10,MINT if dark else MUTED)
    if title: txt(c,title,42,72,876,34,WHITE if dark else INK,True,39)
    if sub: txt(c,sub,44,126,865,14,'B9D2CE' if dark else MUTED)
    txt(c,'BLACK SQUAD   /   SYNTHETIC PROOF OF CONCEPT',42,511,740,9,'B9D2CE' if dark else MUTED)
    txt(c,f'{n:02}',884,508,35,12,MINT if dark else TEAL,True)

def pill(c,label,x,y,w=135,fill=MINT,color=TEAL):
    rr(c,x,y,w,26,fill,13); txt(c,label,x+13,y+6,w-20,10,color,True)

def card(c,x,y,w,h,title,body=None,number=None,fill=WHITE):
    rr(c,x,y,w,h,fill)
    yy=y+21
    if number: txt(c,number,x+20,yy,w-40,33,TEAL,True); yy+=48
    th=txt(c,title,x+20,yy,w-40,18,INK,True)
    if body: txt(c,body,x+20,yy+th+9,w-40,13,MUTED)

def bullets(c,items,x,y,w=420,size=16,gap=18):
    for i,(title,body) in enumerate(items):
        rr(c,x,y+3,25,25,MINT,12)
        txt(c,str(i+1),x+8,y+7,16,10,TEAL,True)
        hh=txt(c,title,x+40,y,w-40,size,INK,True)
        bh=txt(c,body,x+40,y+hh+6,w-40,size-3,MUTED)
        y+=hh+bh+gap+8

def mini_chart(c,x=570,y=230,w=300,h=170):
    rr(c,x-20,y-30,w+40,h+66,WHITE)
    for g in range(4): line(c,x,y+g*h/3,x+w,y+g*h/3,LIGHT,1)
    vals=[.73,.69,.72,.61,.60,.51,.50,.39,.45,.36,.31,.25,.18,.21]
    for i in range(len(vals)-1): line(c,x+i*w/(len(vals)-1),y+vals[i]*h,x+(i+1)*w/(len(vals)-1),y+vals[i+1]*h,TEAL,3)
    txt(c,'history',x,y+h+12,100,11,MUTED)
    txt(c,'future state',x+w-85,y+h+12,100,11,TEAL)

def screenshot(c,name,x=42,y=170,w=876,h=300,crop=None):
    p=OUT/'assets'/name
    if not p.exists(): p=p.with_suffix('.jpg')
    if p.exists():
        from PIL import Image
        im=Image.open(p); iw,ih=im.size
        left,top,right,bottom=(0,0,iw,ih) if crop is None else (crop[0]*iw,crop[1]*ih,crop[2]*iw,crop[3]*ih)
        cw,ch=right-left,bottom-top
        scale=min(w/cw,h/ch); dw,dh=cw*scale,ch*scale
        rr(c,x-2,y-2,w+4,h+4,WHITE,13)
        xx=x+(w-dw)/2; yy=H-y-dh
        c.saveState(); clip=c.beginPath(); clip.rect(xx,yy,dw,dh); c.clipPath(clip,stroke=0,fill=0)
        c.drawImage(ImageReader(str(p)),xx-left*scale,H-y+top*scale-ih*scale,iw*scale,ih*scale,mask='auto'); c.restoreState()
        return True
    return False

def flow(c,y=220):
    nodes=[('01','Select','Search the synthetic\npatient cohort'),('02','Inspect','Context, trends,\nand signal quality'),('03','Review','Forecast, probability\nand model drivers'),('04','Document','Acknowledge alert\nand save a local note'),('05','Export','Carry the demo review\ninto a readable file')]
    for i,(num,title,body) in enumerate(nodes):
        xx=42+i*181
        card(c,xx,y,157,178,title,body.replace('\n','<br/>'),num)
        if i<4: arrow(c,xx+160,y+86,xx+178,y+86)

def diagram(c,n=1):
    base(c,n,'System architecture','Two streams. One inspectable patient state.','Implemented local prototype: synthetic data generation, trained models and clinician review.')
    card(c,42,179,220,104,'Historical profile','Age · BMI · HbA1c · LDL<br/>Diabetes duration',fill=MINT)
    card(c,42,310,220,116,'Wearable replay','Five-minute CGM, HR, HRV<br/>Steps and sleep; trailing windows',fill=MINT)
    card(c,320,231,260,156,'Feature fusion','36 features; current + past only<br/>Train-only standardization<br/>Ridge forecasts + calibrated logistic risk')
    card(c,640,179,278,104,'Local inference','JSON model artifacts<br/>Node.js service + browser client')
    card(c,640,310,278,116,'Clinician dashboard','Forecasts · evidence · replay<br/>Sensitivity sandbox · local review')
    arrow(c,262,232,320,269); arrow(c,262,367,320,339); arrow(c,580,283,640,232); arrow(c,780,283,780,310)
    txt(c,'Future observations are training labels only. They never enter the inference feature window.',43,461,860,13,TEAL,True)

def architecture():
    c=canvas.Canvas(str(OUT/'AURA_Twin_Architecture.pdf'),pagesize=(W,H)); c.setTitle('AURA Twin — Architecture'); c.setAuthor('Black Squad')
    diagram(c); c.showPage()
    base(c,2,'Evidence & boundaries','A separate training path protects the test cohort.','Patient-level partitions keep one person’s repeated windows together.')
    for x,n,t,b in [(42,'144','Training patients','Fit scaling, Ridge and logistic models.<br/>20,160 windows.'),(345,'48','Validation patients','Fit probability calibration and residual intervals.<br/>6,720 windows.'),(648,'48','Test patients','Report final metrics and ablations.<br/>6,720 windows.')]: card(c,x,183,270,191,t,b,n)
    rr(c,42,405,876,71,MINT)
    txt(c,'BOUNDARY',61,423,120,12,TEAL,True)
    txt(c,'Generated data only · no real device or EHR connection · no treatment recommendation<br/>Local demo state is not a clinical record. Clinical validation and governed deployment are future work.',190,418,700,13,INK)
    c.showPage(); c.save()

def presentation():
    c=canvas.Canvas(str(OUT/'AURA_Twin_Presentation.pdf'),pagesize=(W,H)); c.setTitle('AURA Twin — Phase 1 Prototype'); c.setAuthor('Black Squad')
    base(c,1,'Phase 1 / Prototype & Code Submission',None,dark=True)
    txt(c,'A patient’s history.<br/>A signal’s next chapter.',43,110,600,48,WHITE,True,54)
    txt(c,'AURA Twin',45,249,500,24,MINT,True)
    txt(c,'A synthetic digital twin for glucose forecasting<br/>and clinician-led review.',45,293,540,20,'B9D2CE')
    pill(c,'+120 MINUTE HORIZON',45,377,182)
    txt(c,'Black Squad',45,434,500,16,WHITE,True)
    txt(c,'Amrita Vishwa Vidyapeetham, Chennai<br/>Banu Sreya V. · Duvvuru Deepak Reddy',45,461,750,12,'B9D2CE')
    for r,col in [(125,'1B4649'),(96,'215B59'),(64,'2A7C72')]:
        c.setFillColor(HexColor(col)); c.circle(775,H-265,r,fill=1,stroke=0)
    c.setFillColor(HexColor(MINT)); c.circle(775,H-265,18,fill=1,stroke=0)
    c.showPage()
    base(c,2,'The healthcare use case','Give changing signals their historical context.','A focused proof of concept for reviewing possible future high glucose.')
    card(c,42,189,273,231,'The history','Static records explain baseline context, but cannot show what changed in the last hour.','01')
    card(c,344,189,273,231,'The stream','Wearable trends show recent change, but do not carry the whole historical profile.','02')
    card(c,646,189,272,231,'The twin','A fused patient state updates a forecast and makes its inputs available for review.','03',MINT)
    txt(c,'Intended interaction: select a patient → inspect context → review forecast and evidence → document a demo review.',44,449,860,14,TEAL,True)
    c.showPage()
    base(c,3,'A measurable target','Predict a defined event, at a defined time.','A precise outcome prevents a convincing demo from becoming an ambiguous claim.')
    rr(c,42,190,520,245,INK)
    txt(c,'EVENT LABEL',65,215,450,12,MINT,True)
    txt(c,'Glucose ≥180 mg/dL<br/>at exactly t + 120 min',65,253,465,31,WHITE,True,39)
    txt(c,'Not “any excursion within the next two hours.”',65,366,450,14,'B9D2CE')
    bullets(c,[('Numerical trajectory','Forecasts at +30, +60, +90 and +120 minutes.'),('Binary probability','Risk of the exact +120-minute reading meeting the threshold.'),('Range context','70–180 mg/dL is a common CGM context; the ≥180 boundary is our explicit convention.')],603,189,315,16,14)
    txt(c,'Source: NIDDK, Clinical Targets for Continuous Glucose Monitoring Data. Individual clinical targets can differ.',44,468,870,10,MUTED)
    c.linkURL('https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data',(44,H-483,916,H-465),relative=0,thickness=0)
    c.showPage()
    base(c,4,'Data provenance','Wholly synthetic. Fully inspectable.','No real patient records, device accounts or clinical trial data are used.')
    card(c,42,184,418,229,'Static / historical EHR','Age, BMI, HbA1c, LDL and diabetes duration.<br/><br/>Generated demographic and clinical context. Arbitrary genotype markers are excluded from prediction.','A')
    card(c,499,184,419,229,'Dynamic / wearable stream','CGM glucose, heart rate, HRV, step count and sleep.<br/><br/>Five-minute readings with synthetic routines, noise and person-level variation.','B',MINT)
    txt(c,'240 generated patients · 4 simulated days each · fixed seed 20261019',44,438,870,19,TEAL,True)
    txt(c,'Synthea is a future integration option, not the source of these results. The simulator’s design limits generalization.',44,472,870,11,MUTED)
    c.showPage()
    base(c,5,'Digital twin definition','The patient state evolves with the stream.','A narrow data-driven twin, not a whole-body physiological simulator.')
    bullets(c,[('Stable context','Historical features remain attached to the selected synthetic patient.'),('Time-local state','Causal features summarize only observations available at the replay timestamp.'),('Updated outlook','A new prediction follows each replay step; forecast, risk and drivers are inspectable.')],42,190,480,17,22)
    mini_chart(c,592,229,280,175)
    txt(c,'Illustrative state trajectory',585,435,300,12,MUTED)
    c.showPage()
    diagram(c,6); c.showPage()
    base(c,7,'Model design','Small enough to inspect. Real enough to test.','An exported model powers inference; dashboard values are not fixed mockup numbers.')
    card(c,42,183,273,239,'Feature fusion','36 standardized features: EHR context, CGM lags/trends, HR/HRV, activity, sleep, clock harmonics and explicit interactions.','01')
    card(c,344,183,273,239,'Two outputs','Ridge regression forecasts four horizons. Logistic regression estimates the +120-minute event probability.','02')
    card(c,646,183,272,239,'Validation layer','Platt probability calibration and descriptive residual intervals fitted on validation patients.','03',MINT)
    txt(c,'Coefficient contributions describe model behavior. They do not establish causality.',44,451,870,17,TEAL,True)
    c.showPage()
    base(c,8,'Evaluation protocol','Split people before fitting models.','Repeated windows from the same synthetic patient never cross train / validation / test partitions.')
    for x,n,t,b in [(42,'144','Train','20,160 windows<br/>Fit scaler + model'),(345,'48','Validation','6,720 windows<br/>Calibration + intervals'),(648,'48','Test','6,720 windows<br/>Final evidence only')]: card(c,x,186,270,215,t,b,n,MINT if x==648 else WHITE)
    rr(c,42,429,876,54,WHITE)
    txt(c,'30-minute window stride · 24-hour history · exact future labels · 8.04% test event prevalence',62,446,835,14,TEAL,True)
    c.showPage()
    base(c,9,'Measured results / synthetic test patients','Quantify the prediction and its tradeoffs.','48 held-out synthetic patients, 6,720 correlated windows; alert threshold = 0.20.')
    vals=[(f"{F['mae']:.2f}",'MAE / mg/dL','+120-minute forecast'),(f"{F['auroc']:.3f}",'AUROC','Event discrimination'),(f"{F['averagePrecision']:.3f}",'Average precision','8.04% event prevalence'),(f"{P['testRecall']*100:.1f}%",'Recall at 0.20','87 / 540 positive windows missed')]
    for i,(num,t,b) in enumerate(vals): card(c,42+i*225,183,201,185,t,b,num,MINT if i==3 else WHITE)
    txt(c,f"Brier {F['brier']:.4f}  ·  Alert precision {P['testPrecision']*100:.1f}%  ·  MAE patient-bootstrap 95% CI {F['maePatientBootstrap95CI'][0]:.2f}–{F['maePatientBootstrap95CI'][1]:.2f} mg/dL",44,396,870,14,TEAL,True)
    rr(c,42,434,876,49,'F9E9E2')
    txt(c,'These results test a designed simulator. They do not establish clinical safety, effectiveness or real-world accuracy.',60,450,842,13,INK)
    c.showPage()
    base(c,10,'Ablation / same held-out cohort','Both streams improve this synthetic forecast.','+120-minute mean absolute error; lower is better. No clinical generalization claim.')
    rows=[('Fused',M['models']['fused']['mae'],TEAL),('Wearables only',M['models']['sensorOnly']['mae'],'58A39A'),('Historical EHR only',M['models']['staticOnly']['mae'],'9FB9B3'),('Persistence',M['models']['persistence']['mae'],'BDCEC9')]
    for i,(label,v,col) in enumerate(rows):
        yy=194+i*62; txt(c,label,44,yy+9,210,16,INK,True); rr(c,253,yy, v/25*548,38,col,9); txt(c,f'{v:.2f}',267+v/25*548,yy+9,90,16,TEAL,True)
    txt(c,f"Fusion reduces MAE by {(1-F['mae']/M['models']['sensorOnly']['mae'])*100:.1f}% versus wearables only in this experiment.",44,457,870,16,TEAL,True)
    txt(c,'Regular routines and HbA1c-linked simulator kinetics can advantage fusion. Persistence copies the current reading.',44,484,870,10,MUTED)
    c.showPage()
    base(c,11,'Clinician experience','An overview designed for a clinical review.','Patient context, a temporal forecast and supporting evidence share one workspace.')
    if not screenshot(c,'dashboard.png',42,168,876,310,crop=(.179,.345,.703,.844)):
        card(c,42,184,208,286,'Patient panel','Search and choose a generated patient.<br/><br/>Replay status and identity remain visible.','01')
        card(c,273,184,414,286,'Forecast workspace','Historical glucose joins four future horizons.<br/><br/>Visible units, time labels and a descriptive interval help readers interpret the signal.','02',MINT)
        card(c,710,184,208,286,'Evidence','Risk, model drivers and both data streams support inspection.','03')
    c.showPage()
    base(c,12,'Replay & uncertainty','Watch the forecast change as time advances.','Pause, inspect a time point and advance the synthetic stream.')
    if not screenshot(c,'replay.png',42,171,576,302,crop=(.179,.345,.583,.846)): mini_chart(c,68,230,510,185)
    bullets(c,[('Historical versus projected','The future curve is a forecast, not a sensor measurement.'),('Descriptive interval','Validation residuals give a marginal error band.'),('Know the limitation',f"Test coverage: {F['intervalCoverage']*100:.1f}%; mean width: {F['intervalMeanWidth']:.1f} mg/dL. No per-patient guarantee.")],650,179,268,15,18)
    c.showPage()
    base(c,13,'Context & explanations','Make the model’s inputs visible.','A useful interface lets a reviewer inspect the basis of an estimate.')
    if not screenshot(c,'record.png',42,175,565,297,crop=(.19,.39,.98,.98)):
        card(c,42,181,565,274,'Patient record + signal context','Historical EHR: age, BMI, HbA1c, LDL, diabetes duration.<br/><br/>Wearable state: CGM trajectory, recent variability, HR/HRV, steps and sleep.<br/><br/>All observations are generated for this demonstration.',fill=MINT)
    bullets(c,[('Explanations are mathematical','Feature contributions describe fitted log-odds behavior.'),('They are not causal','Correlated inputs and interactions can complicate interpretation.'),('Keep units explicit','Probability, glucose and log-odds contributions are different quantities.')],645,181,273,16,15)
    c.showPage()
    base(c,14,'Hypothetical sensitivity','Explore an assumption. Do not infer a treatment.','Scenario controls are an illustrative arithmetic sandbox, separate from validated causal inference.')
    card(c,42,183,418,233,'Baseline prediction','The trained probability remains the baseline model output.<br/><br/>Reset restores the original forecast.','01')
    card(c,499,183,419,233,'Hypothetical scenario','Meal carbohydrate and activity controls modify a displayed forecast through simplified assumptions.<br/><br/>No claim of intervention efficacy.','02',MINT)
    rr(c,42,449,876,42,'F9E9E2'); txt(c,'No medication guidance, dosing, treatment recommendation or causal benefit estimate is produced.',61,462,839,13,INK,True)
    c.showPage()
    base(c,15,'Review workflow','Close the loop with an inspectable demo record.','Local actions demonstrate an interaction pattern; they are not a production clinical record.')
    flow(c,199)
    txt(c,'Acknowledge a demo alert · save local notes · download a clinician summary',43,418,870,20,TEAL,True)
    txt(c,'Acknowledgement records review, not safety. Authentication, governed audit logs and shared clinical records are future work.',43,463,870,12,MUTED)
    c.showPage()
    base(c,16,'Reproducibility','The evidence travels with the code.','The repository contains the generator, training pipeline and exported artifacts.')
    if screenshot(c,'evidence.png',42,179,576,252,crop=(.19,.40,.98,1.0)):
        bullets(c,[('Generate & train','Fixed seed and train-only preprocessing.'),('Inspect & verify','Readable model, metrics and ablations.'),('Run & review','Local Node.js and JavaScript application.')],650,182,268,15,15)
    else:
        for x,t,b,n in [(42,'Generate & train','Fixed seed; documented Python environment; train-only preprocessing.','01'),(345,'Inspect & verify','Readable model JSON, metrics JSON, ablations and validation checks.','02'),(648,'Run & review','Local Node.js application; no dashboard framework or remote model account required.','03')]: card(c,x,182,270,238,t,b,n)
    txt(c,'Model version: '+MODEL['modelVersion'],44,445,870,18,TEAL,True)
    txt(c,'Numerical results are bound to the submitted code, seed and dependencies. Use the root README for exact commands.',44,477,870,11,MUTED)
    c.showPage()
    base(c,17,'Limitations','The strongest claim is an inspectable prototype.','Clinical benefit, generalization and compliance have not been demonstrated.')
    for x,y,t,b in [(42,183,'Simulator bias','Designed routines and HbA1c-linked kinetics may make prediction easier.'),(499,183,'Alert tradeoff','At threshold 0.20: 87 false-negative and 398 false-positive test windows.'),(42,327,'Distribution shift','New populations, devices, medications and unusual routines are untested.'),(499,327,'Governance gap','No clinical authentication, consent workflow, regulated validation or production audit trail.')]: card(c,x,y,419,123,t,b)
    txt(c,'Synthetic development is not proof of DPDP / HIPAA compliance or medical-device readiness.',44,475,870,12,TEAL,True)
    c.showPage()
    base(c,18,'Future work / explicitly unbuilt','Validate in stages before pursuing deployment.','Progress should be gated by evidence, not the sophistication of the interface.')
    stages=[('01','Stress tests','Missingness, clock shifts, routine changes, subgroup checks.'),('02','Independent data','Appropriate permissions; external validation and recalibration.'),('03','Silent study','Prospective performance, alert burden and missed-event analysis.'),('04','Clinical workflow','Usability, escalation ownership, security and governance.')]
    for i,(n,t,b) in enumerate(stages): card(c,42+i*225,188,201,239,t,b,n,MINT if i==3 else WHITE)
    txt(c,'Real device / EHR connections and any clinical deployment remain future work.',44,459,870,17,TEAL,True)
    c.showPage()
    base(c,19,'Submission artifacts','A complete local package. Clear publishing steps.','Black Squad · Amrita Vishwa Vidyapeetham, Chennai')
    card(c,42,183,418,255,'Included locally','Working application and source<br/>Synthetic data and model artifacts<br/>Training and evaluation code<br/>Architecture + presentation PDFs<br/>MIT license and technical documentation','01')
    card(c,499,183,419,255,'Final team handoff','Verify the real demonstration video<br/>Publish a public GitHub repository<br/>Insert accessible links into README<br/>Test every link while signed out<br/>Enter leader details in the portal','02',MINT)
    txt(c,'Leader: Banu Sreya V. · Member: Duvvuru Deepak Reddy · Public contact details intentionally omitted.',44,469,870,11,MUTED)
    c.showPage()
    base(c,20,'Black Squad / Phase 1',None,dark=True)
    txt(c,'From two streams<br/>to one reviewable outlook.',44,117,840,43,WHITE,True,51)
    txt(c,'A working fusion pipeline.<br/>A measurable two-hour target.<br/>A clinician-oriented interface.<br/>Evidence with explicit boundaries.',47,262,805,24,'B9D2CE',False,35)
    pill(c,'AURA TWIN',47,433,132)
    txt(c,'Synthetic prototype · no clinical validation or treatment recommendation',47,477,850,13,MINT)
    c.showPage(); c.save()

def cards():
    features='\n'.join('- `'+x+'`' for x in MODEL['featureNames'])
    rows='\n'.join('| '+name+' | '+f"{M['models'][k]['mae']:.4f} | {M['models'][k]['auroc']:.4f} | {M['models'][k]['averagePrecision']:.4f} | {M['models'][k]['brier']:.4f} |" for name,k in [('Fused','fused'),('Sensor only','sensorOnly'),('Static only','staticOnly'),('Persistence','persistence')])
    body=f'''# AURA Twin — model and data card

## Identity and intended use

- **Model:** `{MODEL['modelVersion']}`.
- **Team:** Black Squad, Amrita Vishwa Vidyapeetham, Chennai.
- **Purpose:** a synthetic proof of concept of historical/wearable fusion, glucose prediction and clinician-oriented review.
- **Not intended for:** diagnosis, treatment decisions, dosing, emergency triage, autonomous alerts in clinical care, or any claim of clinical validation.
- **Target:** glucose **≥180 mg/dL at exactly +120 minutes**. This is not an any-excursion-within-two-hours label. Regressions also predict +30, +60 and +90 minute glucose.
- **Boundary:** the common CGM range context is 70–180 mg/dL; inclusive 180 is this prototype's explicit event convention, not an individualized clinical target.

## Data provenance

All records and wearable traces are generated by the repository's own seeded simulator. No real patient data, PHI, hospital data, device accounts, MIMIC-IV data or Synthea-generated records were used for these results. Synthetic records are generated, not anonymized records from people.

The cohort contains **240 generated patients**, **4 days each**, at **5-minute cadence**. Windows have 24 hours of available history and a 30-minute stride. The fixed seed is `{M['seed']}`. The generator includes simplified routines, variation, noise, and relationships between historical profile and glucose kinetics. Those design choices can favor the fusion model and limit transfer to other generators or real populations.

Historical features: age, BMI, HbA1c, LDL and diabetes duration. Dynamic inputs: CGM glucose, heart rate, heart rate variability, step count and sleep. Clock harmonics and explicit HbA1c interactions support the generated routines. Arbitrary genetic markers are excluded from prediction rather than assigned unsupported biological meaning.

## Model and feature construction

The pipeline uses train-only StandardScaler preprocessing, multi-output Ridge regression (alpha 30), logistic classification (C 0.3), and validation-set Platt calibration (logistic C 100). See `data/model.json` for exported coefficients and preprocessing parameters. The model uses {len(MODEL['featureNames'])} inputs:

{features}

Features use only observations at or before the prediction timestamp. Future readings are labels only. Time windows from one person remain in the same partition. Missing or stale signals are checked by the application quality gate; severe quality problems trigger abstention. This behavior is a prototype guardrail, not evidence of real device robustness. Consult the shipped inference code for exact thresholds.

## Evaluation protocol

| Partition | Patients | Windows | Role |
|---|---:|---:|---|
| Training | 144 | 20,160 | Fit scaler and predictive models |
| Validation | 48 | 6,720 | Calibration and residual interval estimation |
| Test | 48 | 6,720 | Held-out reporting |

Test event prevalence is **{M['cohort']['positiveRate']['test']*100:.2f}%** (540 positive windows). Repeated windows are correlated; 6,720 windows do not represent 6,720 independent people. The reported MAE uncertainty resamples at the patient level. Other reported metrics have no interval estimate in this release.

## Measured results

All results below refer to **held-out synthetic patients**. MAE is in mg/dL at +120 minutes; lower is better. Higher AUROC and average precision are better; lower Brier is better for comparable probabilistic models.

| Model | +120 min MAE | AUROC | Average precision | Brier |
|---|---:|---:|---:|---:|
{rows}

Persistence copies the current glucose and uses a hard 0/1 event estimate. Its Brier/AUROC are not a calibration-equivalent probability comparison. The fusion MAE reduction versus sensor only is **{(1-F['mae']/M['models']['sensorOnly']['mae'])*100:.1f}%** under this simulator.

The **dashboard alert threshold is 0.20**, chosen as the highest threshold on a 0.01 grid attaining at least 80% recall on validation patients. Validation recall is **{P['validationRecall']*100:.2f}%**. Held-out test recall is **{P['testRecall']*100:.2f}%** and precision is **{P['testPrecision']*100:.2f}%**. Test counts at this threshold: TN 5,782; FP 398; FN 87; TP 453. This is a synthetic development policy, not a validated clinical threshold. Adjacent windows may describe the same episode, so these counts are not independent clinical alert episodes.

For a fixed-threshold comparison, `metrics.json` reports the **0.50 probability threshold**: fused precision **{F['precision']*100:.2f}%**, recall **{F['recall']*100:.2f}%**, and F1 **{F['f1']:.4f}**. The 0.50 confusion matrix is:

| Actual / prediction | Negative | Positive |
|---|---:|---:|
| Actual negative | 6,066 | 114 |
| Actual positive | 244 | 296 |

**244 of 540 positive windows are missed at this threshold.** A high AUROC does not remove this limitation. Do not describe this operating point as clinically safe.

Fused +120 minute MAE patient-bootstrap 95% interval: **{F['maePatientBootstrap95CI'][0]:.2f}–{F['maePatientBootstrap95CI'][1]:.2f} mg/dL**. This reflects uncertainty within the simulated population, not external validity.

## Forecast intervals and explanations

For each horizon, the 90th percentile of validation absolute residuals defines a symmetric descriptive error band. At +120 minutes, held-out marginal coverage is **{F['intervalCoverage']*100:.2f}%** and mean width **{F['intervalMeanWidth']:.2f} mg/dL**. Coverage is not guaranteed per patient, for subgroups, or under distribution shift.

Risk drivers are coefficient-based contributions to model log-odds, not SHAP values or causal effects. Explicit interactions and correlated variables limit naive feature interpretation. The scenario sandbox applies illustrative arithmetic changes to the forecast; the trained probability stays at baseline. It does not estimate the causal effect of activity, meals, or treatment.

## Limits and failure modes

1. Designed synthetic relationships may inflate performance and favor fusion.
2. Four days per patient and relatively regular routines do not represent clinical diversity.
3. Medication effects, complicated comorbidity, device drift and unusual behaviors are not validated.
4. Sensor problems can make forecasts unavailable; the quality gate is not a complete safety system.
5. No independent clinical validation, prospective study, subgroup efficacy study or measured workflow benefit exists.
6. Local review notes and acknowledgements are demonstration state, not a governed clinical record.
7. No HIPAA, DPDP, regulatory or medical-device compliance claim is made.

## Reproducibility and environment

Use the root README for setup and commands. The measured artifact environment records Python **{M['environment']['python']}**, NumPy **{M['environment']['numpy']}**, scikit-learn **{M['environment']['scikitLearn']}**. Review pinned requirements and numerical tolerances before comparing environments. The repository includes generated artifacts so the dashboard can be reviewed without retraining.

## Future validation

Stress-test alternative simulators, missingness and routine shifts; evaluate on appropriately permitted independent data; assess calibration and subgroups; measure alert burden and missed events in prospective silent mode; involve clinicians in usability and escalation design; implement security and governance before any real use. These are future tasks, not completed features.

## References

- [NIDDK: Clinical Targets for Continuous Glucose Monitoring Data](https://www.niddk.nih.gov/health-information/professionals/diabetes-discoveries-practice/clinical-targets-for-continuous-glucose-monitoring-data), accessed 19 October 2026. Supports the common 70–180 mg/dL context, not this model's validity.
- [Synthea: Synthetic Patient Generation](https://synthetichealth.github.io/synthea/), accessed 19 October 2026. Optional future source/integration; not used in this experiment.
'''
    (OUT/'MODEL_DATA_CARD.md').write_text(body,encoding='utf-8')

if __name__=='__main__':
    architecture(); presentation(); cards()
    for name in ['AURA_Twin_Architecture.pdf','AURA_Twin_Presentation.pdf']:
        r=PdfReader(OUT/name)
        print(name,len(r.pages),'pages',sum(len(p.extract_text()) for p in r.pages),'text characters')
