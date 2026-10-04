# Builds the 3D, Division-style "Company as a Human" page.
# Reuses the data model + db glue from app_build.py and motionFrom() from creature.html;
# replaces the 2D stick figure with a rigged, skinned soldier (three.js) in a night street scene.
import re, sys
mode = sys.argv[1] if len(sys.argv) > 1 else 'publish'   # 'local' serves three.js from node_modules for testing

ab = open('app_build.py', encoding='utf-8').read()
model_js = re.search(r"model_js = r'''(.*?)'''", ab, re.S).group(1)
glue_js = re.search(r"glue_js = r'''(.*?)'''", ab, re.S).group(1)
src = open('creature.html', encoding='utf-8').read()
motion_js = src[src.index('/* ---------- motion parameters'): src.index('/* ---------- the person (canvas)')]

# small patches to the glue: ring gauge, slider fill, no 2D resize
glue_js = glue_js.replace("$('health-score').textContent=Math.round(r.health);",
    "$('health-score').textContent=Math.round(r.health);setRing(r.health);")
glue_js = glue_js.replace("values[id]=val;const b=t.parentElement.querySelector('[data-v]');",
    "values[id]=val;fillRange(t,i,val);const b=t.parentElement.querySelector('[data-v]');")
glue_js = glue_js.replace("if(document.activeElement!==el)el.value=values[i.id];",
    "if(document.activeElement!==el)el.value=values[i.id];fillRange(el,i,values[i.id]);")
glue_js = glue_js.replace("recall();fitName();buildOrgans();buildQuick();syncQuick();resize();update();requestAnimationFrame(draw);",
    "recall();fitName();buildOrgans();buildQuick();syncQuick();update();startEngine();")
glue_js = glue_js.replace("(function(){\n'use strict';", "")  # model_js opens the IIFE; we close it ourselves
model_js = model_js.replace("(function(){\n'use strict';", "")
glue_js = glue_js.replace("})();\n", "")
assert 'setRing' in glue_js and 'fillRange' in glue_js and 'startEngine' in glue_js

if mode == 'local':
    importmap = '{"imports":{"three":"/node_modules/three/build/three.module.js","three/addons/":"/node_modules/three/examples/jsm/"}}'
else:
    importmap = '{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}'

css = r'''
:root{
  --bg:#0a0c10; --surface:rgba(17,20,26,.88); --surface-2:#161a21; --ink:#e9edf1; --ink-2:#a8b1bb; --ink-3:#6c7682; --line:rgba(255,255,255,.13); --line-2:rgba(255,255,255,.26);
  --accent:#ff7a1a; --accent-2:#ffb366; --accent-ink:#0a0c10; --accent-soft:rgba(255,122,26,.14); --cyan:#7fd0ff;
  --good:#5fd36f; --warn:#f2b233; --serious:#ff7a1a; --critical:#ff3b3b;
  --display:"Rajdhani","Barlow Condensed","Arial Narrow",sans-serif;
  --body:"Rajdhani","Segoe UI",Arial,sans-serif;
  --mono:"Share Tech Mono",ui-monospace,"SF Mono",Menlo,monospace;
  color-scheme:dark;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){ --bg:#0a0c10; color-scheme:dark } }
:root[data-theme="dark"]{ --bg:#0a0c10; color-scheme:dark }
*{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg) radial-gradient(1200px 500px at 50% -10%,rgba(255,122,26,.08),transparent 70%);color:var(--ink);font-family:var(--body);font-size:16px;line-height:1.4;font-weight:500}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.018) 0 1px,transparent 1px 3px)}
.wrap{position:relative;z-index:1;max-width:1240px;margin:0 auto;padding:14px 16px 56px}
h1,h2,h3{font-family:var(--display);margin:0;line-height:1.05;text-transform:uppercase;letter-spacing:.06em}
h2{font-size:18px;font-weight:700;color:var(--ink)}
h2::before{content:"// ";color:var(--accent)}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.eyebrow{font-family:var(--display);font-size:12px;text-transform:uppercase;letter-spacing:.22em;color:var(--accent);font-weight:700}
.muted{color:var(--ink-2)} .small{font-size:13px}
button{font:inherit;cursor:pointer}
:focus-visible{outline:1px solid var(--accent);outline-offset:2px}
/* panels with corner brackets */
.panel{position:relative;background:var(--surface);border:1px solid var(--line);backdrop-filter:blur(6px)}
.panel::before,.panel::after{content:"";position:absolute;width:12px;height:12px;border-color:var(--accent);border-style:solid;pointer-events:none}
.panel::before{left:-1px;top:-1px;border-width:2px 0 0 2px}
.panel::after{right:-1px;bottom:-1px;border-width:0 2px 2px 0}
.panel.alt::before{left:auto;right:-1px;border-width:2px 2px 0 0}
.panel.alt::after{right:auto;left:-1px;border-width:0 0 2px 2px}

header.top{display:flex;flex-wrap:wrap;gap:12px 24px;align-items:center;justify-content:space-between;margin-bottom:12px;padding:8px 0 10px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:14px;min-width:0}
.brand .mark{width:46px;height:46px;flex:none;border:2px solid var(--accent);border-radius:50%;display:grid;place-items:center;position:relative;box-shadow:0 0 18px rgba(255,122,26,.35),inset 0 0 10px rgba(255,122,26,.25)}
.brand .mark::before{content:"";width:22px;height:22px;border:2px solid var(--accent);border-radius:50%;border-left-color:transparent;border-right-color:transparent;transform:rotate(45deg)}
.brand .mark::after{content:"";position:absolute;width:6px;height:6px;background:var(--accent);border-radius:50%;box-shadow:0 0 10px var(--accent)}
.namebox{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;min-width:0}
.namebox input{font-family:var(--display);font-weight:700;text-transform:uppercase;letter-spacing:.05em;font-size:clamp(22px,3.4vw,34px);border:0;border-bottom:1px solid var(--line-2);background:transparent;color:var(--ink);padding:0 4px;min-width:10ch;max-width:100%}
.namebox input:focus{outline:none;border-bottom-color:var(--accent)}
.namebox .tag{font-family:var(--mono);font-size:12px;color:var(--ink-3);letter-spacing:.1em}
.healthbadge{display:flex;align-items:center;gap:12px;padding:6px 14px 6px 6px}
.gauge{position:relative;width:74px;height:74px;flex:none}
.gauge svg{position:absolute;inset:0;transform:rotate(-90deg)}
.gauge .score{position:absolute;inset:0;display:grid;place-items:center;font-family:var(--display);font-size:30px;font-weight:700;line-height:1}
.healthbadge .label{font-family:var(--display);font-weight:700;font-size:20px;text-transform:uppercase;letter-spacing:.08em}
.pill{display:inline-flex;align-items:center;gap:6px;padding:1px 8px;font-family:var(--mono);font-size:11.5px;letter-spacing:.06em;color:#0a0c10;white-space:nowrap;clip-path:polygon(6px 0,100% 0,calc(100% - 6px) 100%,0 100%)}
.pill.good{background:var(--good)} .pill.warn{background:var(--warn)} .pill.serious{background:var(--serious)} .pill.critical{background:var(--critical);color:#fff}

.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:8px 10px;margin-bottom:12px}
.toolbar .status{font-family:var(--mono);font-size:12px;color:var(--ink-3);margin-left:auto;letter-spacing:.04em}
.btn{font-family:var(--display);font-weight:700;text-transform:uppercase;letter-spacing:.1em;font-size:13px;border:1px solid var(--line-2);background:rgba(255,255,255,.03);color:var(--ink);padding:6px 14px;clip-path:polygon(8px 0,100% 0,calc(100% - 8px) 100%,0 100%);transition:background .15s,color .15s}
.btn:hover{background:rgba(255,122,26,.18);color:var(--accent-2)}
.btn.primary{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}
.btn.primary:hover{background:var(--accent-2);color:var(--accent-ink)}
.btn:disabled{opacity:.45;cursor:not-allowed}
select.btn{appearance:none;padding-right:26px;background-image:linear-gradient(45deg,transparent 50%,var(--accent) 50%),linear-gradient(135deg,var(--accent) 50%,transparent 50%);background-position:calc(100% - 16px) 50%,calc(100% - 11px) 50%;background-size:5px 5px;background-repeat:no-repeat}
select.btn option{background:#161a21;color:var(--ink)}

.field-stage{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:12px;align-items:start}
@media (max-width:900px){.field-stage{grid-template-columns:1fr;gap:10px}}
.stick{position:sticky;top:env(safe-area-inset-top,0px);z-index:2;display:grid;gap:8px}
@media (max-width:900px){.stick{background:var(--bg);padding-bottom:6px}}
.canvasbox{position:relative;border:1px solid var(--line-2);overflow:hidden;background:#0a0c10;min-height:240px}
canvas#field{display:block;width:100%;height:100%}
.hud{position:absolute;inset:0;pointer-events:none}
.hud .scan{position:absolute;inset:0;background:repeating-linear-gradient(0deg,rgba(0,0,0,.14) 0 1px,transparent 1px 3px);mix-blend-mode:multiply}
.hud .vig{position:absolute;inset:0;background:radial-gradient(ellipse at center,transparent 38%,hsla(var(--vh,120),80%,45%,var(--va,.3)) 100%)}
.hud .corner{position:absolute;width:22px;height:22px;border-color:var(--accent);border-style:solid}
.hud .c1{left:8px;top:8px;border-width:2px 0 0 2px}.hud .c2{right:8px;top:8px;border-width:2px 2px 0 0}.hud .c3{left:8px;bottom:8px;border-width:0 0 2px 2px}.hud .c4{right:8px;bottom:8px;border-width:0 2px 2px 0}
.hud .legend{position:absolute;left:22px;top:16px;font-family:var(--mono);font-size:12px;letter-spacing:.06em;color:var(--accent-2);text-shadow:0 0 8px rgba(255,122,26,.5);max-width:calc(100% - 44px);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hud .sys{position:absolute;right:22px;top:16px;font-family:var(--mono);font-size:11px;color:var(--ink-2);text-align:right;letter-spacing:.06em;line-height:1.5}
.hud .sys b{color:var(--accent-2);font-weight:400}
.hud .tick{position:absolute;left:22px;right:22px;bottom:14px;height:10px;background:repeating-linear-gradient(90deg,var(--line-2) 0 1px,transparent 1px 24px);opacity:.7}
.hud .tick::after{content:"";position:absolute;left:0;right:0;bottom:0;height:1px;background:var(--line-2)}
.agentbar{position:absolute;left:0;top:0;transform:translate(-50%,-100%);display:grid;gap:3px;justify-items:center;width:150px;transition:opacity .3s}
.agentbar .n{font-family:var(--display);font-weight:700;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#fff;text-shadow:0 0 6px rgba(0,0,0,.9);white-space:nowrap;max-width:150px;overflow:hidden;text-overflow:ellipsis}
.agentbar .hb{width:150px;height:7px;background:rgba(0,0,0,.6);border:1px solid rgba(255,255,255,.35);position:relative;overflow:hidden}
.agentbar .hb i{position:absolute;left:0;top:0;bottom:0;background:var(--accent);box-shadow:0 0 8px var(--accent);transition:width .4s}
.agentbar .hb::after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent 0 13px,rgba(0,0,0,.7) 13px 15px)}
.agentbar .st{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--accent-2)}
@media (max-width:900px){.agentbar{display:none}.hud .sys{display:none}}

.monitor{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:6px}
.monitor .trace{grid-column:span 3;padding:6px 10px 2px;min-width:0}
.trace .k,.ro .k{font-family:var(--display);font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.18em;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.trace .k span{color:var(--accent-2);margin-left:6px}
.trace canvas{display:block;width:100%;height:34px}
.monitor .ro{padding:6px 10px;min-width:0;display:block}
.monitor .ro.wide{grid-column:span 2}
.ro .v{font-family:var(--display);font-weight:700;font-size:19px;line-height:1.1;overflow-wrap:anywhere;text-transform:uppercase;letter-spacing:.03em}
.ro .v small{font-family:var(--mono);font-weight:400;font-size:10px;color:var(--ink-3);margin-left:4px;letter-spacing:.06em;text-transform:none}
@media (max-width:900px){.monitor{grid-template-columns:repeat(4,minmax(0,1fr))}.monitor .trace{grid-column:span 2}.monitor .ro.wide,.monitor .ro:nth-child(n+9){display:none}}

.controls{display:grid;gap:10px;min-width:0}
.quick{padding:10px 14px 14px;display:grid;gap:8px;max-height:calc(100vh - 40px);overflow:auto}
@media (max-width:900px){.quick{max-height:none}}
.quick .dept{font-family:var(--display);font-size:12px;text-transform:uppercase;letter-spacing:.2em;color:var(--accent);font-weight:700;margin-top:8px;padding-bottom:3px;border-bottom:1px solid var(--line)}
.quick .dept:first-child{margin-top:0}
.quick .q label{font-size:14px;display:flex;justify-content:space-between;gap:8px;color:var(--ink);line-height:1.25}
.quick .q label b{font-family:var(--mono);font-weight:400;white-space:nowrap;color:var(--accent-2)}
.quick .q .help{font-family:var(--mono);font-size:11px;color:var(--ink-3);margin-top:1px}
.quick .q input[type=number]{width:15ch;font-family:var(--mono);font-size:14px;padding:4px 8px;border:1px solid var(--line-2);background:rgba(0,0,0,.35);color:var(--accent-2);text-align:right;margin-top:3px}
.quick .q input[type=range]{-webkit-appearance:none;appearance:none;width:100%;height:18px;background:transparent;margin:0;display:block;--p:50%}
.quick .q input[type=range]::-webkit-slider-runnable-track{height:3px;background:linear-gradient(90deg,var(--accent) var(--p),rgba(255,255,255,.18) var(--p))}
.quick .q input[type=range]::-moz-range-track{height:3px;background:rgba(255,255,255,.18)}
.quick .q input[type=range]::-moz-range-progress{height:3px;background:var(--accent)}
.quick .q input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:10px;height:16px;margin-top:-6.5px;background:var(--ink);border:1px solid var(--accent);clip-path:polygon(50% 0,100% 25%,100% 100%,0 100%,0 25%);box-shadow:0 0 8px rgba(255,122,26,.6)}
.quick .q input[type=range]::-moz-range-thumb{width:10px;height:16px;border-radius:0;background:var(--ink);border:1px solid var(--accent)}

section.block{margin-top:26px}
section.block > .hd{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.howto{padding:14px 18px;font-size:15px;color:var(--ink-2)}
.howto ol{margin:6px 0 0;padding-left:20px} .howto b{color:var(--ink)}
.map{margin-top:14px;padding:10px 14px}
.map table{width:100%;border-collapse:collapse;font-size:14.5px}
.map th{font-family:var(--display);text-transform:uppercase;letter-spacing:.16em;font-size:11.5px;color:var(--accent);font-weight:700}
.map th,.map td{text-align:left;padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
.map td.num{text-align:right;white-space:nowrap}
.map tr:last-child td{border-bottom:0}
.map td .why{color:var(--ink-2);font-size:13.5px}
.tablewrap{overflow-x:auto}
.organs{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:10px}
.organ{padding:12px 14px;min-width:0;border-left:3px solid var(--line-2)}
.organ.good{border-left-color:var(--good)} .organ.warn{border-left-color:var(--warn)} .organ.serious{border-left-color:var(--serious)} .organ.critical{border-left-color:var(--critical)}
.organ .head{display:flex;gap:10px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}
.organ .name{font-family:var(--display);font-weight:700;font-size:19px;text-transform:uppercase;letter-spacing:.08em}
.organ .part{color:var(--ink-3);font-size:13px;margin-left:8px;font-family:var(--mono)}
.organ .score{font-family:var(--display);font-weight:700;font-size:26px;min-width:3ch;text-align:right}
.organ.good .score{color:var(--good)} .organ.warn .score{color:var(--warn)} .organ.serious .score{color:var(--serious)} .organ.critical .score{color:var(--critical)}
.bar{position:relative;height:8px;background:rgba(255,255,255,.08);margin:8px 0 7px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--ink-3);transition:width .5s ease}
.bar::after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(90deg,transparent 0 calc(10% - 2px),var(--bg) calc(10% - 2px) 10%)}
.organ.good .bar i{background:var(--good)} .organ.warn .bar i{background:var(--warn)} .organ.serious .bar i{background:var(--serious)} .organ.critical .bar i{background:var(--critical)}
.organ .why{font-size:14.5px;color:var(--ink-2)}
.organ .motion{font-family:var(--mono);font-size:12px;color:var(--cyan);margin-top:5px;letter-spacing:.03em}
.organ details{margin-top:6px}
.organ summary{cursor:pointer;font-family:var(--display);font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:700;list-style:none}
.organ summary::before{content:"▸ "} .organ details[open] summary::before{content:"▾ "}
.formula{font-family:var(--mono);font-size:12.5px;background:rgba(0,0,0,.35);border-left:2px solid var(--accent);padding:8px 10px;margin-top:6px;white-space:pre-wrap;word-break:break-word;color:var(--ink-2)}
.gallery{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px}
.gcard{padding:10px 12px;cursor:pointer;display:grid;gap:4px;min-width:0}
.gcard:hover{border-color:var(--accent)}
.gcard .n{font-family:var(--display);font-weight:700;font-size:17px;text-transform:uppercase;letter-spacing:.06em;overflow-wrap:anywhere}
.gcard .s{font-size:12.5px;color:var(--ink-2);font-family:var(--mono)}
.toast{position:fixed;left:50%;bottom:calc(18px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);background:var(--accent);color:var(--accent-ink);padding:8px 16px;font-family:var(--display);font-weight:700;letter-spacing:.08em;text-transform:uppercase;font-size:13px;opacity:0;transition:opacity .25s;pointer-events:none;z-index:9;clip-path:polygon(8px 0,100% 0,calc(100% - 8px) 100%,0 100%)}
.toast.show{opacity:1}
footer{margin-top:36px;font-size:13px;color:var(--ink-3);max-width:76ch;font-family:var(--mono);line-height:1.5}
'''

html = r'''<title>Company as a Human</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=Share+Tech+Mono&display=swap">
<style>''' + css + r'''</style>
<script type="importmap">''' + importmap + r'''</script>

<div class="wrap">
<header class="top">
  <div class="brand">
    <div class="mark" aria-hidden="true"></div>
    <div>
      <div class="eyebrow">Company as a Human · Agent status</div>
      <div class="namebox"><input id="cname" value="A typical company" aria-label="Company name" maxlength="60"><span class="tag">// WALKS LIKE THIS</span></div>
    </div>
  </div>
  <div class="healthbadge panel" aria-live="polite">
    <div class="gauge"><svg viewBox="0 0 74 74" aria-hidden="true"><circle cx="37" cy="37" r="32" fill="none" stroke="rgba(255,255,255,.12)" stroke-width="5"/><circle id="health-ring" cx="37" cy="37" r="32" fill="none" stroke="#ff7a1a" stroke-width="5" stroke-dasharray="201 201" stroke-dashoffset="201" stroke-linecap="butt"/></svg><div class="score num" id="health-score">—</div></div>
    <div><div class="eyebrow">Overall health</div><div class="label" id="health-label">—</div><div class="small muted" id="health-sub">weighted from 11 systems</div></div>
  </div>
</header>

<div class="toolbar panel alt" role="toolbar" aria-label="Company actions">
  <button class="btn" id="b-typical">Typical company</button>
  <button class="btn" id="b-demo">Demo: AHD Group</button>
  <button class="btn primary" id="b-save" title="Save this company to your account">Save</button>
  <select class="btn" id="s-mine" aria-label="My saved companies"><option value="">My companies…</option></select>
  <button class="btn" id="b-share">Share link</button>
  <button class="btn" id="b-gallery">Shared companies</button>
  <span class="status" id="status">NUMBERS STAY IN THIS BROWSER UNTIL YOU SAVE</span>
</div>

<div class="field-stage">
  <div class="stick">
    <div class="canvasbox">
      <canvas id="field" role="img" aria-label="A person walking down a night street. Their pace, stride, posture, breathing, stumbles and limp follow the company's numbers."></canvas>
      <div class="hud">
        <div class="vig" id="vig"></div><div class="scan"></div>
        <i class="corner c1"></i><i class="corner c2"></i><i class="corner c3"></i><i class="corner c4"></i>
        <div class="legend" id="legend">LOADING AGENT…</div>
        <div class="sys" id="sys"></div>
        <div class="tick"></div>
        <div class="agentbar" id="agentbar" style="opacity:0"><div class="n" id="ab-name">AGENT</div><div class="hb"><i id="ab-fill" style="width:50%"></i></div><div class="st" id="ab-st">—</div></div>
      </div>
    </div>
    <div class="monitor" id="monitor">
      <div class="trace panel"><div class="k">Heart <span class="num" id="tr-hr"></span></div><canvas id="ecg"></canvas></div>
      <div class="trace panel alt"><div class="k">Breath <span class="num" id="tr-br"></span></div><canvas id="resp"></canvas></div>
      <div class="ro panel"><div class="k">Gait</div><div class="v" id="ro-gait">—</div></div>
      <div class="ro panel"><div class="k">Speed</div><div class="v num" id="ro-speed">—<small>km/h</small></div></div>
      <div class="ro panel"><div class="k">Cadence</div><div class="v num" id="ro-cad">—<small>steps/min</small></div></div>
      <div class="ro panel"><div class="k">Stride</div><div class="v num" id="ro-stride">—<small>m</small></div></div>
      <div class="ro wide panel"><div class="k">Posture</div><div class="v" id="ro-posture">—</div></div>
      <div class="ro wide panel"><div class="k">Gaze</div><div class="v" id="ro-gaze">—</div></div>
      <div class="ro panel"><div class="k">Stumbles</div><div class="v num" id="ro-stumble">—</div></div>
      <div class="ro panel"><div class="k">Reaction</div><div class="v num" id="ro-react">—<small>s</small></div></div>
      <div class="ro wide panel"><div class="k">Limp</div><div class="v" id="ro-limp">—</div></div>
    </div>
  </div>
  <div class="controls">
    <div class="quick panel" id="quick"></div>
  </div>
</div>

<section class="block" id="gallery-block" hidden>
  <div class="hd"><h2>Shared companies</h2><span class="small muted">Tap one to watch it walk. Only what each person chose to share.</span></div>
  <div class="gallery" id="gallery"></div>
</section>

<section class="block">
  <div class="hd"><h2>How to read the agent</h2></div>
  <div class="howto panel">
    Each department is the body system that does the same job in a person. Its numbers set that system's score from 0 to 100, and the score is in the way the agent moves. A healthy company runs; a sick one shuffles.
    <ol>
      <li><b>Enter your numbers</b> on the right. Money fields are in any currency; only the ratios matter. Percentages are shares of your open orders, items or records.</li>
      <li><b>Watch the walk change</b> at the speed the brain allows: a company with many decisions waiting takes seconds to respond.</li>
      <li><b>Save</b> keeps the company in your account, <b>Share link</b> lets others watch it, and the gallery shows what people chose to share.</li>
    </ol>
  </div>
</section>

<div class="map panel alt">
  <div class="eyebrow" style="margin-bottom:6px">Departments and their body systems</div>
  <div class="tablewrap"><table><thead><tr><th>Department</th><th>Body system</th><th>Why this system</th><th>Score</th><th>Seen in the walk as</th></tr></thead><tbody id="map-body"></tbody></table></div>
</div>

<section class="block">
  <div class="hd"><h2>The systems</h2><span class="small muted">Each one scores a department's numbers and drives one part of the body.</span></div>
  <div class="organs" id="organs"></div>
</section>

<footer>
  <p>HOW IT WORKS // Numbers feed derived figures, rules turn them into eleven system scores, and the scores drive a rigged human model in real time: walk and run cycles blended by fitness, cadence from the heart, posture and gaze from margin and management, breathing from purchasing, tremor from data quality, stumbles from planning, a limp from delivery and invoicing, and the orange pulse on his wrist from the heartbeat. Thresholds and weights are first settings; nothing here is financial advice. Character model: three.js Soldier (Mixamo), CC-BY.</p>
</footer>
</div>
<div class="toast" id="toast" role="status"></div>
'''

engine_js = r'''
/* ---------- the agent (three.js) ---------- */
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const cv=$('field');
const ecg=$('ecg'),ecgCtx=ecg.getContext('2d'),resp=$('resp'),respCtx=resp.getContext('2d');
let W=0,H=0,DPR=1,motion=null,targetMotion=null;
let tSim=0,cycle=0,dist=0,lastT=performance.now(),lastCycleInt=0,stumble=0,stumbles=0;
const ecgBuf=new Float32Array(160).fill(0),respBuf=new Float32Array(160).fill(0);let bufT=0;
let renderer,scene,camera,mixer,actions={},bones={},bodyMat,visorMat,watchLight,watchGlow,ground,groundTex,buildings=[],lamps=[],snow,snowPos,hemi,keyLight,ready=false,failed=false;
const WALK_DUR=1.0333,RUN_DUR=0.7,WALK_SPM=116,RUN_SPM=171;

function setRing(h){const c=$('health-ring');const L=2*Math.PI*32;c.setAttribute('stroke-dasharray',L+' '+L);c.setAttribute('stroke-dashoffset',String(L*(1-h/100)));c.setAttribute('stroke',h>=75?'#5fd36f':h>=50?'#f2b233':h>=25?'#ff7a1a':'#ff3b3b')}
function fillRange(el,i,val){if(el.type==='range')el.style.setProperty('--p',((val-i.min)/(i.max-i.min)*100).toFixed(1)+'%')}

function makeCanvasTex(w,h,paint,repX=1,repY=1){const c=document.createElement('canvas');c.width=w;c.height=h;paint(c.getContext('2d'),w,h);const t=new THREE.CanvasTexture(c);t.wrapS=t.wrapT=THREE.RepeatWrapping;t.repeat.set(repX,repY);t.colorSpace=THREE.SRGBColorSpace;t.anisotropy=8;return t}
function rand(seed){let s=seed>>>0;return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296}}

function buildScene(){
  renderer=new THREE.WebGLRenderer({canvas:cv,antialias:true,powerPreference:'high-performance'});
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.outputColorSpace=THREE.SRGBColorSpace;
  scene=new THREE.Scene();scene.background=new THREE.Color(0x0a0c10);scene.fog=new THREE.FogExp2(0x0b0e13,0.075);
  camera=new THREE.PerspectiveCamera(27,1,0.1,120);camera.position.set(2.5,1.35,4.6);camera.lookAt(0.1,0.92,0);
  hemi=new THREE.HemisphereLight(0x6f86a8,0x15110d,0.55);scene.add(hemi);
  keyLight=new THREE.DirectionalLight(0xd6e4ff,1.7);keyLight.position.set(-3,6.5,4.5);keyLight.castShadow=true;keyLight.shadow.mapSize.set(2048,2048);
  const sc=keyLight.shadow.camera;sc.left=-5;sc.right=5;sc.top=5;sc.bottom=-5;sc.near=1;sc.far=20;keyLight.shadow.bias=-0.0008;keyLight.shadow.radius=3;scene.add(keyLight);
  const rim=new THREE.PointLight(0xff8a2a,14,14,2);rim.position.set(1.6,3.3,-2.6);scene.add(rim);
  const fill=new THREE.PointLight(0x7fb0ff,3,10,2);fill.position.set(3,2,3);scene.add(fill);
  // ground: slushy asphalt with sidewalk edge and lane paint
  const r=rand(7);
  groundTex=makeCanvasTex(1024,512,(g,w,h)=>{
    g.fillStyle='#262a30';g.fillRect(0,0,w,h);
    for(let i=0;i<9000;i++){const a=r();g.fillStyle=`rgba(${a>0.5?255:0},${a>0.5?255:0},${a>0.5?255:0},${0.03+0.05*r()})`;g.fillRect(r()*w,r()*h,1+r()*3,1+r()*2)}
    for(let i=0;i<70;i++){g.fillStyle=`rgba(210,220,232,${0.05+0.14*r()})`;const x=r()*w,y=r()*h;g.beginPath();g.ellipse(x,y,15+r()*50,4+r()*14,0,0,Math.PI*2);g.fill()}
    g.fillStyle='rgba(255,196,80,.35)';for(let x=0;x<w;x+=170)g.fillRect(x,h*0.5-3,90,6);
    g.fillStyle='#3a3d44';g.fillRect(0,0,w,h*0.14);g.fillStyle='rgba(255,255,255,.25)';g.fillRect(0,h*0.14-3,w,3);
    g.fillStyle='rgba(0,0,0,.35)';for(let x=0;x<w;x+=128)g.fillRect(x,0,2,h*0.14);
  },14,4);
  ground=new THREE.Mesh(new THREE.PlaneGeometry(70,20),new THREE.MeshStandardMaterial({map:groundTex,roughness:0.86,metalness:0.08,color:0xbfc4cc}));
  ground.rotation.x=-Math.PI/2;ground.position.set(0,0,-4);ground.receiveShadow=true;scene.add(ground);
  // buildings: two rows of dark blocks with lit windows
  const winTex=makeCanvasTex(256,256,(g,w,h)=>{g.fillStyle='#0b0d12';g.fillRect(0,0,w,h);for(let y=10;y<h;y+=32)for(let x=10;x<w;x+=32){const lit=r()<0.13;g.fillStyle=lit?(r()<0.7?'#ffb866':'#9fc3ff'):'#0f1218';g.fillRect(x,y,14,20)}},1,1);
  const bMat=new THREE.MeshStandardMaterial({color:0x1c2029,roughness:0.95,emissive:0xffffff,emissiveMap:winTex,emissiveIntensity:0.55});
  const rows=[{z:-10,n:14,hmin:6,hmax:15},{z:-17,n:12,hmin:12,hmax:30}];
  for(const row of rows){let x=-34;for(let i=0;i<row.n;i++){const w=3.5+r()*4,h=row.hmin+r()*(row.hmax-row.hmin),d=5+r()*3;
    const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),bMat.clone());m.material.emissiveMap=winTex.clone();m.material.emissiveMap.repeat.set(Math.max(1,Math.round(w/2.4)),Math.max(1,Math.round(h/2.6)));m.material.emissiveMap.needsUpdate=true;
    m.position.set(x+w/2,h/2,row.z-d/2);m.userData.w=w+0.6;scene.add(m);buildings.push(m);x+=w+0.6+r()*1.5}}
  // street lamps along the sidewalk edge
  const glowTex=makeCanvasTex(64,64,(g,w,h)=>{const gr=g.createRadialGradient(32,32,2,32,32,32);gr.addColorStop(0,'rgba(255,190,110,1)');gr.addColorStop(0.35,'rgba(255,140,50,.5)');gr.addColorStop(1,'rgba(255,120,30,0)');g.fillStyle=gr;g.fillRect(0,0,w,h)});
  for(let i=0;i<6;i++){const grp=new THREE.Group();const pole=new THREE.Mesh(new THREE.CylinderGeometry(0.04,0.06,4.2,8),new THREE.MeshStandardMaterial({color:0x1b1e24,roughness:.7,metalness:.6}));pole.position.y=2.1;pole.castShadow=true;grp.add(pole);
    const arm=new THREE.Mesh(new THREE.BoxGeometry(0.9,0.06,0.06),pole.material);arm.position.set(0.4,4.15,0);grp.add(arm);
    const sp=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,color:0xffffff,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true}));sp.scale.set(1.6,1.6,1);sp.position.set(0.85,4.1,0);grp.add(sp);
    const pl=new THREE.PointLight(0xffa040,5,7,2);pl.position.set(0.85,4.0,0);grp.add(pl);
    grp.position.set(-18+i*8,0,-2.9);scene.add(grp);lamps.push(grp)}
  // snow
  const N=1600;snowPos=new Float32Array(N*3);for(let i=0;i<N;i++){snowPos[i*3]=(Math.random()-0.5)*30;snowPos[i*3+1]=Math.random()*9;snowPos[i*3+2]=-12+Math.random()*18}
  const sg=new THREE.BufferGeometry();sg.setAttribute('position',new THREE.BufferAttribute(snowPos,3));
  const flake=makeCanvasTex(32,32,(g,w,h)=>{const gr=g.createRadialGradient(16,16,0,16,16,16);gr.addColorStop(0,'rgba(255,255,255,1)');gr.addColorStop(0.5,'rgba(255,255,255,.5)');gr.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=gr;g.fillRect(0,0,w,h)});
  snow=new THREE.Points(sg,new THREE.PointsMaterial({size:0.07,map:flake,transparent:true,opacity:0.75,depthWrite:false,sizeAttenuation:true}));scene.add(snow);
  // the agent
  const onErr=e=>{failed=true;$('legend').textContent='3D MODEL COULD NOT LOAD — readouts still live';console.warn(e)};
  // the model ships base64-encoded next to the page (binary .glb is not a served type)
  fetch('models/soldier.glb.txt').then(r=>{if(!r.ok)throw new Error('model '+r.status);return r.text()}).then(t=>{const bin=atob(t.trim());const u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);new GLTFLoader().parse(u.buffer,'',g=>{
    const model=g.scene;model.rotation.y=-Math.PI/2;scene.add(model);
    model.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(o.name==='vanguard_Mesh')bodyMat=o.material;if(o.name==='vanguard_visor')visorMat=o.material}if(o.isBone)bones[o.name.replace('mixamorig','')]=o});
    if(bodyMat){bodyMat.roughness=0.75;bodyMat.metalness=0.05}
    mixer=new THREE.AnimationMixer(model);
    for(const clip of g.animations){const a=mixer.clipAction(clip);a.play();a.setEffectiveTimeScale(0);a.setEffectiveWeight(clip.name==='Walk'?1:0);actions[clip.name]=a}
    // SHD watch: orange glow + light on the left wrist
    const hand=bones.LeftForeArm||bones.LeftHand;
    if(hand){watchGlow=new THREE.Mesh(new THREE.SphereGeometry(0.022,12,12),new THREE.MeshBasicMaterial({color:0xff8a2a}));watchGlow.position.set(0,0.26,0.035);hand.add(watchGlow);
      watchLight=new THREE.PointLight(0xff7a1a,2,1.6,2);watchLight.position.copy(watchGlow.position);hand.add(watchLight);
      const halo=new THREE.Sprite(new THREE.SpriteMaterial({map:glowTex,blending:THREE.AdditiveBlending,depthWrite:false,transparent:true,opacity:.9}));halo.scale.set(0.22,0.22,1);halo.position.copy(watchGlow.position);hand.add(halo);watchGlow.userData.halo=halo}
    for(const b of Object.values(bones)){b.userData.rot0=b.rotation.clone();}
    ready=true;$('legend').textContent='AGENT ONLINE';$('agentbar').style.opacity='1';
  },onErr)}).catch(onErr);
}
function resize(){
  const box=cv.parentElement.getBoundingClientRect();
  W=Math.max(300,box.width);H=W<700?Math.max(240,Math.min(W*0.78,window.innerHeight*0.46)):Math.max(320,Math.min(520,W*0.56));
  DPR=Math.min(2,window.devicePixelRatio||1);
  cv.parentElement.style.height=H+'px';
  if(renderer){renderer.setPixelRatio(DPR);renderer.setSize(W,H,false);camera.aspect=W/H;camera.updateProjectionMatrix()}
  for(const c of [ecg,resp]){const r=c.getBoundingClientRect();c.width=Math.max(60,r.width)*DPR;c.height=38*DPR}
}
function startEngine(){
  try{buildScene()}catch(e){failed=true;$('legend').textContent='WEBGL UNAVAILABLE — readouts still live';console.warn(e)}
  resize();addEventListener('resize',resize);requestAnimationFrame(draw);
}
function ecgSample(p){let v=0;
  v+=0.12*Math.exp(-Math.pow((p-0.12)/0.03,2));v-=0.15*Math.exp(-Math.pow((p-0.20)/0.008,2));v+=1.0*Math.exp(-Math.pow((p-0.22)/0.012,2));
  v-=0.25*Math.exp(-Math.pow((p-0.245)/0.01,2));v+=0.28*Math.exp(-Math.pow((p-0.40)/0.05,2));return v}
function drawTrace(c,el,buf,amp,color){
  const w=el.width/DPR,h=el.height/DPR;c.setTransform(DPR,0,0,DPR,0,0);c.clearRect(0,0,w,h);
  c.strokeStyle='rgba(255,255,255,.12)';c.lineWidth=1;c.beginPath();c.moveTo(0,h*0.65);c.lineTo(w,h*0.65);c.stroke();
  c.strokeStyle=color;c.lineWidth=1.6;c.lineJoin='round';c.shadowColor=color;c.shadowBlur=6;c.beginPath();
  for(let i=0;i<buf.length;i++){const x=i/(buf.length-1)*w,y=h*0.65-buf[i]*h*amp;if(i===0)c.moveTo(x,y);else c.lineTo(x,y)}
  c.stroke();c.shadowBlur=0;
}
const _v=new THREE.Vector3(),_v2=new THREE.Vector3();
function draw(now){
  requestAnimationFrame(draw);
  const dt=Math.min(0.05,(now-lastT)/1000);lastT=now;
  if(!motion)return;
  const k=1-Math.exp(-dt/Math.max(0.15,motion.reaction));
  for(const key of Object.keys(targetMotion)){const tv=targetMotion[key];
    if(typeof tv==='number')motion[key]=lerp(motion[key],tv,k);else if(key==='legs'){for(const l in tv)motion.legs[l]=lerp(motion.legs[l],tv[l],k)}else motion[key]=tv}
  const m=motion;tSim+=dt;
  let st=0;if(stumble>0){st=Math.sin(Math.PI*(1-stumble/0.6));stumble-=dt}
  const jitter=(1+m.rhythmJitter*Math.sin(tSim*7.3)*Math.sin(tSim*2.1))*(1-0.55*st);
  cycle+=dt*m.cadenceHz*jitter;dist+=dt*m.speed*(1-0.5*st);
  const ci=Math.floor(cycle*2);
  if(ci!==lastCycleInt){lastCycleInt=ci;if(stumble<=0&&Math.random()<m.stumbleChance/2){stumble=0.6;stumbles++}}
  const breath=Math.sin(2*Math.PI*m.breathHz*tSim)*m.breathDepth;
  const beatPhase=(tSim*m.heartBpm/60)%1;
  const pulse=Math.exp(-beatPhase*10)*0.7+Math.exp(-(((beatPhase-0.32)%1+1)%1)*16)*0.3;
  const mps=m.speed/100;

  if(renderer&&!failed){
    // world scrolls past the agent
    groundTex.offset.x=(dist/100)/5;
    for(const b of buildings){b.position.x-=mps*dt;if(b.position.x+b.userData.w/2<-36)b.position.x+=72}
    for(const l of lamps){l.position.x-=mps*dt;if(l.position.x<-26)l.position.x+=48}
    for(let i=0;i<snowPos.length;i+=3){snowPos[i+1]-=(0.55+0.3*Math.sin(i))*dt;snowPos[i]-=(0.25+mps*0.9)*dt+Math.sin(tSim*1.3+i)*0.002;if(snowPos[i+1]<0){snowPos[i+1]=9;snowPos[i]=(Math.random()-0.5)*30}if(snowPos[i]<-15)snowPos[i]+=30}
    snow.geometry.attributes.position.needsUpdate=true;
    if(ready){
      const phi=cycle%1;
      actions.Walk.time=phi*WALK_DUR;actions.Run.time=phi*RUN_DUR;
      actions.Walk.setEffectiveWeight(1-m.run);actions.Run.setEffectiveWeight(m.run);
      if(actions.Idle)actions.Idle.setEffectiveWeight(0);
      mixer.update(0);
      // layer the company's state on top of the clips
      const B=bones;const pitch=((m.lean-4-7*m.run)*1.1+22*st)*D2R;
      B.Spine.rotation.x+=pitch*0.4;B.Spine1.rotation.x+=pitch*0.35;B.Spine2.rotation.x+=pitch*0.25+0.35*m.slump;
      const headDown=((30*(1-m.gaze)+18*st)*D2R)-0.25*m.slump;B.Neck.rotation.x+=headDown*0.45;B.Head.rotation.x+=headDown*0.55;
      B.LeftShoulder.rotation.z-=0.28*m.slump;B.RightShoulder.rotation.z+=0.28*m.slump;
      if(st>0){B.LeftArm.rotation.z-=0.7*st;B.RightArm.rotation.z+=0.7*st;B.Hips.position.y-=0.07*st}
      if(m.tremor>0){const t=m.tremor*0.3;B.LeftHand.rotation.x+=(Math.random()-0.5)*t;B.RightHand.rotation.x+=(Math.random()-0.5)*t;B.LeftHand.rotation.z+=(Math.random()-0.5)*t;B.RightHand.rotation.z+=(Math.random()-0.5)*t;
        if(m.tremor>0.5){B.Head.rotation.z+=(Math.random()-0.5)*0.04*(m.tremor-0.5)}}
      const fat=1+0.24*m.fat,chest=1+0.03*breath;B.Spine1.scale.set(fat,1,fat*chest);B.Neck.scale.set(1/fat,1,1/(fat*chest));
      // limp: the hip drops over the weak stance leg
      B.LeftFoot.getWorldPosition(_v);B.RightFoot.getWorldPosition(_v2);const stance=_v.y<_v2.y?'L':'R';const lw=m.legs[stance];
      if(lw<0.5){const sev=1-2*lw;B.Hips.position.y-=0.07*sev;B.Spine.rotation.z+=0.14*sev*(stance==='L'?1:-1);B.Head.rotation.z-=0.1*sev*(stance==='L'?1:-1)}
      B.Hips.position.y-=0.02*m.slump;
      if(bodyMat)bodyMat.color.setRGB(1,1-0.22*m.flush,1-0.28*m.flush);
      if(visorMat)visorMat.opacity=1;
      if(watchLight){watchLight.intensity=0.8+5*pulse;watchGlow.material.color.setHSL(0.07,1,0.5+0.3*pulse);watchGlow.userData.halo.material.opacity=0.35+0.6*pulse}
      // HUD bar above the head
      B.Head.getWorldPosition(_v);_v.y+=0.33;_v.project(camera);
      const ab=$('agentbar');ab.style.transform=`translate(${((_v.x+1)/2*W).toFixed(1)}px,${((1-_v.y)/2*H).toFixed(1)}px) translate(-50%,-100%)`;
    }
    // camera breathes a little with the run
    camera.position.y=1.35+0.02*Math.sin(tSim*0.7);camera.lookAt(0.1,0.92+0.01*Math.sin(tSim*0.9),0);
    renderer.render(scene,camera);
  }
  // status vignette: hue from red (critical) through amber to green (thriving), pulsing with the heartbeat
  const hue=4+116*Math.pow(m.health,1.4);const a=(0.22+0.30*pulse)*(1.1-0.35*m.health);
  const vig=$('vig');vig.style.setProperty('--vh',hue.toFixed(0));vig.style.setProperty('--va',a.toFixed(3));
  bufT+=dt;if(bufT>0.03){bufT=0;ecgBuf.copyWithin(0,1);ecgBuf[ecgBuf.length-1]=ecgSample(beatPhase);respBuf.copyWithin(0,1);respBuf[respBuf.length-1]=breath/m.breathDepth}
  drawTrace(ecgCtx,ecg,ecgBuf,0.5,'#ff7a1a');drawTrace(respCtx,resp,respBuf,0.45,'#7fd0ff');
  updateReadouts(m);
}
/* ---------- readouts ---------- */
let roTick=0;
function updateReadouts(m){
  roTick++;if(roTick%6)return;
  $('ro-gait').textContent=m.gait;
  if(ready)$('legend').textContent=`${m.gait.toUpperCase()} · ${m.kmh.toFixed(1)} KM/H · ${Math.round(m.stepsPerMin)} SPM · HR ${Math.round(m.heartBpm)} · ${Math.round(dist/100).toLocaleString('en-US')} M`;
  $('sys').innerHTML=`POSTURE <b>${m.slump<0.25?'UPRIGHT':m.slump<0.5?'STOOPED':m.slump<0.75?'ROUNDED':'HUNCHED'}</b><br>BREATH <b>${Math.round(m.breathHz*60)}/MIN${m.panting?' PANTING':''}</b><br>REACT <b>${m.reaction.toFixed(1)}S</b>`;
  $('tr-hr').textContent=Math.round(m.heartBpm)+' bpm';$('tr-br').textContent=Math.round(m.breathHz*60)+'/min'+(m.panting?' · mouth open':'');
  $('ro-speed').innerHTML=m.kmh.toFixed(1)+'<small>km/h</small>';
  $('ro-cad').innerHTML=Math.round(m.stepsPerMin)+'<small>steps/min</small>';
  $('ro-stride').innerHTML=m.strideM.toFixed(2)+'<small>m</small>';
  const post=m.slump<0.25?'upright, shoulders back':m.slump<0.5?'slightly stooped':m.slump<0.75?'stooped, shoulders rounded':'hunched';
  $('ro-posture').textContent=(m.run>0.5?'running form, ':'')+post;
  $('ro-gaze').textContent=m.gaze>0.75?'on the horizon':m.gaze>0.5?'a few metres ahead':m.gaze>0.3?'at the path':'at their feet';
  $('ro-stumble').innerHTML=stumbles+'<small>so far, '+Math.round(m.stumbleChance*100)+'% per stride</small>';
  const limp=[];if(m.legs.L<0.5)limp.push(m.legs.L<0.25?'left drags (delivery)':'left (delivery)');if(m.legs.R<0.5)limp.push(m.legs.R<0.25?'right drags (invoicing)':'right (invoicing)');
  $('ro-limp').textContent=limp.length?limp.join(', '):'none';
  $('ro-react').innerHTML=m.reaction.toFixed(1)+'<small>s</small>';
  const h=Math.round(m.health*100);$('ab-fill').style.width=h+'%';$('ab-fill').style.background=h>=75?'#ff7a1a':h>=50?'#f2b233':h>=25?'#ff7a1a':'#ff3b3b';
  $('ab-name').textContent=$('cname').value||'AGENT';$('ab-st').textContent=(m.gait+' · '+(h>=75?'thriving':h>=50?'stable':h>=25?'sick':'critical')).toUpperCase();
}
'''

page = html + '\n<script type="module">\n' + model_js + '\n' + motion_js + '\n' + engine_js + '\n' + glue_js + '\n</script>\n'
open('company_human.html', 'w', encoding='utf-8').write(page)
doc = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>' + page + '</body></html>'
open('company_human_standalone.html', 'w', encoding='utf-8').write(doc)
print(mode, 'built', len(page))
