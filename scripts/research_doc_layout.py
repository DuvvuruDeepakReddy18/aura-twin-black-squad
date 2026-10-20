"""Navy/cyan research-edition PDF layout; content is supplied by frozen artifacts."""
from pathlib import Path
import math
from html import escape
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
W, H = 960, 540
NAVY, CARD, BORDER = '#080F21', '#111C34', '#23334E'
WHITE, MUTED, CYAN, VIOLET, AMBER = '#F3F7FF', '#AFBCD2', '#5DE5EB', '#B5A0FF', '#F5C77B'
FONT, BOLD = 'Helvetica', 'Helvetica-Bold'
if Path('C:/Windows/Fonts/segoeui.ttf').exists():
    pdfmetrics.registerFont(TTFont('AuraRegular', 'C:/Windows/Fonts/segoeui.ttf'))
    pdfmetrics.registerFont(TTFont('AuraBold', 'C:/Windows/Fonts/segoeuib.ttf'))
    FONT, BOLD = 'AuraRegular', 'AuraBold'


def box(c, x, y, w, h, color=CARD, radius=12, stroke=None):
    c.setFillColor(HexColor(color))
    c.setStrokeColor(HexColor(stroke or color))
    c.roundRect(x, H-y-h, w, h, radius, fill=1, stroke=bool(stroke))


def text(c, value, x, y, w, size=16, color=WHITE, bold=False, max_height=None):
    # Content strings may intentionally contain only simple line-break markup.
    style = ParagraphStyle('aura', fontName=BOLD if bold else FONT,
                           fontSize=size, leading=size*1.3, textColor=HexColor(color))
    p = Paragraph(str(value), style)
    _, height = p.wrap(w, 1200)
    if max_height and height > max_height:
        raise ValueError(f'Text overflow: {str(value)[:80]!r}: {height:.1f} > {max_height}')
    p.drawOn(c, x, H-y-height)
    return height


def line(c, x1, y1, x2, y2, color=BORDER, width=1):
    c.setStrokeColor(HexColor(color)); c.setLineWidth(width)
    c.line(x1, H-y1, x2, H-y2)


def arrow(c, x1, y1, x2, y2):
    line(c, x1, y1, x2, y2, CYAN, 1.6)
    angle = math.atan2(y2-y1, x2-x1)
    for offset in [-.6, .6]:
        line(c, x2, y2, x2-7*math.cos(angle+offset), y2-7*math.sin(angle+offset), CYAN, 1.6)


def base(c, slide, title=None):
    c.setFillColor(HexColor(NAVY)); c.rect(0, 0, W, H, fill=1, stroke=0)
    box(c, 37, 28, 5, 19, CYAN, 2)
    text(c, 'AURA / TWIN', 52, 26, 240, 14, CYAN, True)
    text(c, 'RESEARCH EDITION  /  BLACK SQUAD', 620, 29, 300, 10, MUTED)
    line(c, 40, 62, 920, 62)
    title_height = text(c, title or slide['title'], 40, 85, 880, 32, WHITE, True, 88)
    text(c, slide.get('subtitle', ''), 42, 94+title_height, 876, 13, MUTED, max_height=52)
    line(c, 40, 497, 920, 497)
    text(c, 'Composite Research Twin  ·  Research prototype, not clinical validation', 42, 512, 800, 9, MUTED)
    text(c, f"{slide['slide']:02}", 883, 507, 36, 14, CYAN, True)


def card(c, x, y, w, h, title, body, index=None, accent=CYAN):
    box(c, x, y, w, h, stroke=BORDER)
    compact = h < 180
    if not compact:
        box(c, x+19, y+20, 24, 3, accent, 1)
    yy = y+(18 if compact else 38)
    if index:
        text(c, index, x+20, yy, w-40, 32, accent, True)
        yy += 49
    th = text(c, title, x+20, yy, w-40, 15 if compact else 17, WHITE, True, 70)
    gap = 8 if compact else 12
    text(c, body, x+20, yy+th+gap, w-40, 11.5 if compact else 12.5, MUTED,
         max_height=y+h-16-(yy+th+gap))


def three(c, cards, y=203, height=260):
    for i, (title, body) in enumerate(cards):
        card(c, 40+i*300, y, 280, height, title, body, f'0{i+1}', CYAN if i != 1 else VIOLET)


def table(c, headings, rows, widths, y=200, row_height=37, font_size=12):
    box(c, 40, y, 880, row_height, '#20324D', 7)
    for j, value in enumerate(headings):
        text(c, escape(str(value)), 51+sum(widths[:j]), y+10, widths[j]-20, 11, CYAN, True)
    for i, row in enumerate(rows):
        yy = y+(i+1)*row_height
        box(c, 40, yy+1, 880, row_height-2, CARD if i%2 == 0 else '#0E182D', 2)
        for j, value in enumerate(row):
            text(c, escape(str(value)), 51+sum(widths[:j]), yy+9, widths[j]-20, font_size, WHITE if j == 0 else MUTED,
                 j == 0, row_height-8)


def image(c, path, x=40, y=197, w=880, h=286, crop=None):
    if not path.exists():
        return False
    im = ImageReader(str(path)); iw, ih = im.getSize()
    left, top, right, bottom = crop or (0, 0, iw, ih)
    scale = min(w/(right-left), h/(bottom-top))
    dw, dh = (right-left)*scale, (bottom-top)*scale
    box(c, x, y, w, h, CARD, 10, BORDER)
    xx, yy = x+(w-dw)/2, H-y-h+(h-dh)/2
    c.saveState()
    region = c.beginPath(); region.rect(xx, yy, dw, dh); c.clipPath(region, stroke=0, fill=0)
    c.drawImage(im, xx-left*scale, yy+dh+top*scale-ih*scale, iw*scale, ih*scale, mask='auto')
    c.restoreState()
    return True


def architecture(c, slide, ctx):
    base(c, slide)
    card(c, 40, 203, 223, 111, 'Source acquisition', 'Pinned Synthea + PhysioNet<br/>Checksums, licenses, raw data')
    card(c, 40, 340, 223, 116, 'Past-only preprocessing', '6 h history · availability times<br/>No future fill · separate truth')
    card(c, 319, 246, 279, 168, 'Selected numerical model', f"{ctx['primary_family']}<br/>{ctx['feature_count']} selected features<br/>Calibration + residual bands")
    card(c, 655, 203, 265, 111, 'Review workspace', 'Replay · record · evidence<br/>3D/2D visual context')
    card(c, 655, 340, 265, 116, 'Challenge + receipt', 'Freeze → reveal original truth<br/>Model/input hashes + scores')
    arrow(c, 152, 314, 152, 340); arrow(c, 263, 398, 319, 354)
    arrow(c, 598, 291, 655, 260); arrow(c, 787, 314, 787, 340)


def draw(c, slide, ctx, assets):
    kind = slide['kind']
    if kind in ['cover', 'closing']:
        base(c, {**slide, 'title': '', 'subtitle': ''}, 'AURA Twin' if kind == 'cover' else 'A forecast you can question.')
        text(c, 'SEE THE PATIENT.<br/>UNDERSTAND WHAT<br/>COMES NEXT.' if kind == 'cover' else 'Actual sources.<br/>Inspectable predictions.<br/>Honest evidence.', 43, 179, 845, 35, WHITE, True, 155)
        box(c, 42, 350, 500, 35, CARD, 17, BORDER)
        text(c, 'COMPOSITE RESEARCH TWIN  /  '+ctx['model_version'], 58, 360, 470, 10, CYAN, True)
        text(c, 'Black Squad · Amrita Vishwa Vidyapeetham, Chennai', 42, 410, 870, 16, WHITE, True)
        text(c, 'Banu Sreya V.  ·  CH.EN.U4ECE23009     |     Duvvuru Deepak Reddy  ·  CH.EN.U4ECE23015', 42, 447, 870, 11, MUTED)
        return
    if kind == 'architecture':
        architecture(c, slide, ctx); return
    base(c, slide)
    if kind in ['cards', 'sources', 'legacy']:
        three(c, slide['cards'])
    elif kind == 'target':
        card(c, 40, 205, 515, 250, 'Current event contract', ctx['target_display'], '01')
        card(c, 580, 205, 340, 250, 'Observed ground truth', 'Nearest real CGM sample within ±150 seconds of the nominal horizon.<br/><br/>No interpolated outcomes. No future input.', '02', VIOLET)
    elif kind == 'split':
        for i, (number, title, detail) in enumerate([
            ('9', 'Train', 'Fit candidates<br/>IDs 001–009'),
            ('2', 'Select', 'Choose family/configuration<br/>IDs 010–011'),
            ('2', 'Calibrate', 'Probability, policy, bands<br/>IDs 012–013'),
            ('3', 'Final', 'Opened after freeze<br/>IDs 014–016'),
        ]):
            card(c, 40+i*224, 207, 208, 247, title, detail, number, CYAN if i<3 else VIOLET)
    elif kind == 'models':
        rows = [
            ['CGM history', 'Eligible', 'Recorded glucose history'],
            ['CGM + HR + RMSSD', 'Eligible', 'Adds actual wearable channels'],
            ['Matched research fusion', 'Eligible', 'Adds study HbA1c + sex'],
            ['Unmatched Synthea only', 'Negative control', 'Different synthetic person'],
            ['Unmatched composite fusion', 'Negative control', 'Cannot select primary family'],
            ['Persistence', 'Comparator', 'Latest glucose carried forward'],
        ]
        table(c, ['Family', 'Role', 'Interpretation'], rows, [330, 180, 370], y=200, row_height=38)
    elif kind == 'results':
        table(c, ['Model', '+120 MAE', 'Recall', 'Precision', 'FN / FP'], ctx['model_rows'],
              [320, 120, 120, 130, 190], y=194, row_height=38, font_size=11.3)
        text(c, 'Same eligible final windows · events are overlapping windows, not unique episodes', 43, 468, 870, 10.5, AMBER)
    elif kind == 'uncertainty':
        three(c, [
            ['Measured coverage', f"{ctx['coverage']}%<br/><br/>Nominal 90% empirical bands; only two calibration participants."],
            ['Mean interval width', f"{ctx['interval_width']} mg/dL<br/><br/>At approximately +120 minutes. No patient-level coverage guarantee."],
            ['Frozen review threshold', f"{ctx['threshold']}<br/><br/>Calibration maximum-F1 policy. Not a validated clinical trigger."],
        ])
    elif kind == 'screenshot':
        crop = (230, 310, 1190, 800) if slide['image'] == 'record-research.png' else None
        if not image(c, assets/slide['image'], crop=crop):
            three(c, slide['cards'])
    elif kind == 'challenge':
        for i, (title, detail) in enumerate([
            ('Choose', 'Participant, cutoff<br/>and input stress case'),
            ('Freeze', 'Restrict the prefix<br/>Preserve model output'),
            ('Reveal', 'Original recorded future<br/>No new prediction'),
            ('Compare', 'Error, persistence, bands<br/>Download receipt'),
        ]):
            card(c, 40+i*224, 207, 208, 247, title, detail, f'0{i+1}', CYAN if i != 1 else VIOLET)


def build(slides, ctx, out, assets):
    out.mkdir(parents=True, exist_ok=True)
    deck = canvas.Canvas(str(out/'AURA_Twin_Presentation.pdf'), pagesize=(W, H))
    deck.setTitle('AURA Twin — Composite Research Twin'); deck.setAuthor('Black Squad')
    deck.setSubject('Open research wearable data, Synthea context, prediction contract and measured evidence')
    for slide in slides:
        draw(deck, slide, ctx, assets); deck.showPage()
    deck.save()
    arch = canvas.Canvas(str(out/'AURA_Twin_Architecture.pdf'), pagesize=(W, H))
    arch.setTitle('AURA Twin — Research architecture and boundaries'); arch.setAuthor('Black Squad')
    for index in [4, 7, 14, 17]:
        draw(arch, slides[index], ctx, assets); arch.showPage()
    arch.save()
    challenge = canvas.Canvas(str(out/'AURA_Twin_Challenge_Lab.pdf'), pagesize=(W, H))
    challenge.setTitle('AURA Twin — Research challenge and evidence'); challenge.setAuthor('Black Squad')
    for index in [5, 9, 14, 15, 16, 18]:
        draw(challenge, slides[index], ctx, assets); challenge.showPage()
    challenge.save()
