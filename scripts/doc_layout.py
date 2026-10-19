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
    title_height=txt(c,title,42,72,876,34,WHITE if dark else INK,True,39) if title else 0
    if sub: txt(c,sub,44,max(126,80+title_height),865,14,'B9D2CE' if dark else MUTED)
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


"""Current presentation layout draft; model context is supplied after artifact freeze."""
import json
from pathlib import Path
from reportlab.pdfgen import canvas


def table(c, headings, rows, widths, x=42, y=186, row_height=42):
    total=sum(widths)
    rr(c,x,y,total,row_height,INK,9)
    for j,heading in enumerate(headings): txt(c,str(heading),x+sum(widths[:j])+13,y+11,widths[j]-24,12,WHITE,True)
    for i,row in enumerate(rows):
        yy=y+(i+1)*row_height
        rr(c,x,yy,total,row_height-2,WHITE if i%2==0 else '#E8F3EF',3)
        for j,value in enumerate(row): txt(c,str(value),x+sum(widths[:j])+13,yy+11,widths[j]-24,13,INK,j==0)

def three(c,items,y=188,h=246):
    for i,(title,body,number) in enumerate(items): card(c,42+i*302,y,272,h,title,body,number,MINT if i==2 else WHITE)

def draw_slide(c,slide,ctx):
    n=slide['slide']; kind=slide['kind']; title=slide['title']
    if kind in ('cover','closing'):
        base(c,n,'Current decision-policy edition',None,dark=True)
        txt(c,'AURA Twin' if kind=='cover' else 'A forecast you can inspect.',44,103,850,48,WHITE,True,55)
        txt(c,'History + wearable state.<br/>Fresh-patient evidence.<br/>A challengeable prediction.' if kind=='cover' else 'A working fusion pipeline.<br/>A measured synthetic comparison.<br/>A reproducible challenge.',47,191,815,31,'B9D2CE',False,43)
        pill(c,ctx['model_version'].upper(),47,372,230)
        txt(c,'Black Squad · Amrita Vishwa Vidyapeetham, Chennai',47,427,850,17,WHITE,True)
        txt(c,'Banu Sreya V. · Duvvuru Deepak Reddy',47,458,850,14,MINT)
        txt(c,'Generated data only · No clinical validation or treatment recommendation',47,487,850,11,MINT)
        return
    subtitle=slide.get('subtitle','Current model '+ctx['model_version']+' · synthetic benchmark evidence')
    base(c,n,slide.get('kicker','Model, product and evidence'),title,subtitle)
    if kind=='target':
        rr(c,42,187,524,247,INK)
        txt(c,'EXACT-HORIZON EVENT',65,213,460,12,MINT,True)
        txt(c,'Glucose ≥180 mg/dL<br/>at t + 120 minutes',65,252,465,31,WHITE,True,40)
        txt(c,'Not any excursion during the next two hours.',65,370,465,14,'B9D2CE')
        bullets(c,[('Four forecasts','+30 / +60 / +90 / +120 minutes'),('One event probability','Calibrated estimate for the exact two-hour reading'),('Explicit convention','70–180 is common CGM context; inclusive 180 is our label.')],604,190,314,16,17)
        txt(c,'Context: NIDDK, Clinical Targets for Continuous Glucose Monitoring Data. Individual targets can differ.',44,474,874,10,MUTED)
    elif kind=='architecture':
        card(c,42,187,214,104,'Historical EHR','Age · BMI · HbA1c · LDL<br/>Diabetes duration',fill=MINT)
        card(c,42,325,214,113,'Wearable history','CGM · HR · HRV<br/>Steps · sleep; cutoff-bounded',fill=MINT)
        card(c,309,240,277,163,'Past-only feature fusion',str(ctx['feature_count'])+' clock-free features<br/>'+ctx['algorithm_short']+'<br/>Calibration + residual bands')
        card(c,641,187,277,104,'Local + hosted inference','Exported JSON model<br/>Shared JavaScript evaluator')
        card(c,641,325,277,113,'Clinician review','Replay · uncertainty · records<br/>Challenge Lab · receipt export')
        arrow(c,256,239,309,277); arrow(c,256,380,309,350); arrow(c,586,294,641,239); arrow(c,780,291,780,325)
        txt(c,'No future meals, future readings or hidden simulator state enter inference.',44,470,868,14,TEAL,True)
    elif kind=='split':
        parts=[('768','Fit','Training identities<br/>Candidate fitting only'),('80','Select','Separate identities<br/>Choose candidate + policy shape'),('96','Calibrate','Separate identities<br/>Probability, bands, threshold'),('120','Final test','New indices 2000–2119<br/>Generate after model freeze')]
        for i,(num,title,body) in enumerate(parts): card(c,42+i*224,187,203,242,title,body,num,MINT if i==3 else WHITE)
        txt(c,'Every routine variant and window for an identity stays in one partition.',44,454,866,15,TEAL,True)
        txt(c,'Six familiar families + one withheld factor combination; the same 120 final identities.',44,483,870,11,MUTED)
    elif kind=='decisions':
        table(c,['Frozen policy','Threshold','Recall','Precision','Missed +','False +'],ctx['decision_table'],[255,105,123,123,135,135],y=188,row_height=54)
        txt(c,ctx['decision_change'],44,384,868,21,TEAL,True)
        txt(c,ctx['error_summary'],44,427,868,15,INK,True)
        txt(c,'Primary familiar-family test · overlapping windows, not unique clinical episodes.',44,476,870,12,MUTED)
    elif kind=='results':
        table(c,['Model','+120 MAE ↓','AUROC ↑','Brier ↓'],ctx['model_table'],[345,177,177,177],row_height=40)
        txt(c,ctx['policy_summary'],44,443,868,15,TEAL,True)
        txt(c,'Units: mg/dL. Repeated windows are correlated. Scores do not establish clinical validity.',44,481,870,11,MUTED)
    elif kind=='routines':
        table(c,['Routine','FN: v2 → v3','FP: v2 → v3','V3 recall','V3 precision'],ctx['routine_table'],[280,149,149,149,149],y=174,row_height=39)
        txt(c,ctx['unseen_caption'],44,467,870,13,TEAL,True)
        txt(c,'Withheld combination is separate from this six-family primary table.',44,491,870,10,MUTED)
    elif kind=='uncertainty':
        three(c,[('Observed coverage','Nominal 90% descriptive residual bands.<br/>Measured on the fresh final cohort.',ctx['coverage_display']),('Mean band width','At the two-hour horizon.<br/>Broader uncertainty can accompany irregular behavior.',ctx['width_display']),('Review policy','Threshold fixed on calibration patients.<br/>Not a validated clinical trigger.',ctx['threshold_display'])],h=241)
        txt(c,'Coverage is marginal. No guarantee per patient, subgroup or shifted population.',44,462,870,16,TEAL,True)
    elif kind in ('dashboard','replay','record'):
        filename={'dashboard':'dashboard-current.png','replay':'dashboard-current.png','record':'record-current.png'}[kind]
        crop={'dashboard':None,'replay':(.234,.312,.916,.73),'record':(.234,.312,.916,.67)}[kind]
        if not screenshot(c,filename,42,174,876,290,crop=crop):
            three(c,slide['cards'],h=241)
        txt(c,slide.get('caption','Actual local interface · all observations are generated for this demonstration'),44,480,870,12,TEAL,True)
    elif kind=='scenario':
        card(c,42,189,418,248,'Baseline forecast','The fitted model provides the numerical trajectory and event probability.<br/><br/>Reset restores this baseline.','01')
        card(c,500,189,418,248,'Illustrative sensitivity','Meal/activity sliders apply hand-authored arithmetic assumptions.<br/><br/>Trained risk remains unchanged.','02',MINT)
        txt(c,'No future meal knowledge. No causal benefit estimate. No treatment or dosing recommendation.',44,470,870,14,TEAL,True)
    elif kind=='challenge':
        parts=[('01','Choose','Patient, cutoff, sensor case.<br/>Copy and truncate history.'),('02','Freeze','Predict before seeing outcomes.<br/>Preserve output + hashes.'),('03','Reveal','Original recorded future.<br/>No recomputation.'),('04','Compare','Model vs persistence.<br/>Interval hits + receipt.')]
        for i,(num,title,body) in enumerate(parts):
            card(c,42+i*224,188,202,245,title,body,num,MINT if i==1 else WHITE)
            if i<3: arrow(c,247+i*224,308,263+i*224,308)
        txt(c,'Public data: this enforces a computation boundary, not secure study blinding.',44,465,870,14,TEAL,True)
    elif kind=='faults':
        items=[('Clean replay','An honest baseline; a local window may lose to persistence.'),('10-minute CGM gap','Forward fill permitted; show degraded quality.'),('30-minute dropout','Stale signal; withhold forecast and probability.'),('Undetected sensor bias','Plausible +30 mg/dL input shift may pass freshness checks.')]
        for i,(title,body) in enumerate(items): card(c,42+(i%2)*457,183+(i//2)*145,419,124,title,body,fill=MINT if i==3 else WHITE)
        txt(c,'The reference future stays unchanged. Persistence sees the same perturbed current value.',44,478,870,12,TEAL,True)
    elif kind=='receipt':
        card(c,42,188,418,230,'What can be checked','Raw model bytes → SHA-256<br/>Canonical input prefix → SHA-256<br/>Recomputed forecast and revealed score<br/>Mismatch detection for altered artifacts','01')
        card(c,500,188,418,230,'What is not established','No digital signature<br/>No independent timestamp<br/>No trusted authorship guarantee<br/>No clinical audit certification','02',MINT)
        rr(c,42,443,876,47,INK)
        txt(c,'node scripts/verify_receipt.mjs path/to/receipt.json',59,456,844,17,WHITE,True)
    else:
        three(c,slide['cards'],h=245)
        if slide.get('caption'): txt(c,slide['caption'],44,465,870,14,TEAL,True)

def build(slides,ctx,out):
    deck=canvas.Canvas(str(out/'AURA_Twin_Presentation.pdf'),pagesize=(W,H))
    deck.setTitle('AURA Twin — Current decision-policy edition'); deck.setAuthor('Black Squad')
    for slide in slides: draw_slide(deck,slide,ctx); deck.showPage()
    deck.save()
    arch=canvas.Canvas(str(out/'AURA_Twin_Architecture.pdf'),pagesize=(W,H)); arch.setTitle('AURA Twin — Current architecture'); arch.setAuthor('Black Squad')
    for index in [5,6,15]:
        draw_slide(arch,slides[index],ctx); arch.showPage()
    arch.save()
