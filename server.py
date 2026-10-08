#!/usr/bin/env python3
"""
server.py — the web UI for Arthabodh (Sarathi Labs).

Pure Python standard library: no Flask, no FastAPI, no npm, no build step.
That is deliberate: anyone can clone this repo and run it in 5 seconds
on any machine with Python 3.10+, with zero installs and zero cost.

    python server.py            # http://localhost:8000
    PORT=9000 python server.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from idea_oracle import IdeaOracle, describe_providers, get_brain  # noqa: E402

ORACLE = IdeaOracle(brain=get_brain())  # IdeaOracle == Arthabodh (see docs/BRAND.md)

PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Arthabodh — test any business idea · Sarathi Labs</title>
<style>
  :root{
    --bg:#0d1117; --panel:#161b22; --panel2:#1c2430; --line:#2b3544;
    --ink:#e6edf3; --muted:#8b98a5; --accent:#f0a500; --accent2:#3fb950;
    --red:#f85149; --amber:#d29922; --blue:#58a6ff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
  .wrap{max-width:980px;margin:0 auto;padding:28px 20px 80px}
  header{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:6px}
  .logo{width:42px;height:42px;border-radius:11px;flex:0 0 auto;
        background:linear-gradient(135deg,var(--accent),#e0523c);
        display:grid;place-items:center;font-size:22px}
  h1{font-size:26px;margin:0;letter-spacing:-.3px}
  .sub{color:var(--muted);font-size:13.5px;margin:2px 0 22px}
  .lab{color:var(--muted);font-size:12.5px;margin-top:1px;letter-spacing:.2px}
  .lab strong{color:var(--accent);font-weight:600}
  .dev{color:var(--muted);font-size:19px;font-weight:400;margin-left:6px}
  .tag{display:inline-block;margin-left:8px;font-size:11px;font-weight:700;letter-spacing:.7px;
       text-transform:uppercase;color:var(--accent);border:1px solid var(--accent);
       border-radius:5px;padding:1px 6px;vertical-align:middle}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin-bottom:18px}
  label{display:block;font-size:13px;color:var(--muted);margin:0 0 6px;font-weight:600;
        text-transform:uppercase;letter-spacing:.6px}
  textarea,input,select{width:100%;background:var(--panel2);border:1px solid var(--line);border-radius:9px;
        color:var(--ink);padding:11px 12px;font-size:15px;font-family:inherit;resize:vertical}
  textarea:focus,input:focus,select:focus{outline:none;border-color:var(--accent)}
  .row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin-top:12px}
  @media(max-width:640px){.row{grid-template-columns:1fr}}
  button{width:100%;margin-top:16px;padding:13px;border:0;border-radius:9px;cursor:pointer;
         background:var(--accent);color:#1a1200;font-weight:700;font-size:15.5px}
  button:hover{filter:brightness(1.08)}
  button:disabled{opacity:.55;cursor:wait}
  .chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}
  .chip{background:var(--panel2);border:1px solid var(--line);color:var(--muted);
        border-radius:999px;padding:5px 11px;font-size:12.5px;cursor:pointer}
  .chip:hover{color:var(--ink);border-color:var(--accent)}
  .meta{display:flex;gap:10px;align-items:center;font-size:12.5px;color:var(--muted);margin-bottom:14px;flex-wrap:wrap}
  .badge{background:var(--panel2);border:1px solid var(--line);border-radius:999px;padding:3px 10px}
  .badge.on{border-color:var(--accent2);color:var(--accent2)}
  pre{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:22px;
      overflow:auto;white-space:pre-wrap;word-wrap:break-word;font-size:14px;line-height:1.65;
      font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .err{background:#3d1418;border:1px solid var(--red);color:#ffd7d5;border-radius:10px;padding:14px;font-size:14px}
  .foot{color:var(--muted);font-size:12.5px;margin-top:18px;line-height:1.7}
  a{color:var(--blue)}
  .spin{display:none;color:var(--accent);font-size:14px;margin-top:12px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo">☸</div>
    <div>
      <h1>Arthabodh <span class="dev">अर्थबोध</span></h1>
      <div class="lab">by <strong>Sarathi Labs</strong> · engine: <strong>Shodh</strong> शोध</div>
    </div>
  </header>
  <p class="sub">Shodh your idea. Get your Arthabodh — a culture-aware reality check built from real case files of what worked and what killed the lookalikes.</p>

  <div class="card">
    <label for="idea">Your idea</label>
    <textarea id="idea" rows="5" placeholder="e.g. Existing family bakery in Naples, Italy. We want to export packaged biscuits to supermarkets in Germany. Small budget, no marketing team."></textarea>
    <div class="row">
      <div>
        <label for="country">Target market</label>
        <select id="country"></select>
      </div>
      <div>
        <label for="budget">Budget</label>
        <select id="budget">
          <option value="">auto-detect</option>
          <option value="none">none ($0)</option>
          <option value="small">small</option>
          <option value="medium">medium</option>
          <option value="large">large</option>
        </select>
      </div>
      <div>
        <label for="mode">Mode</label>
        <select id="mode">
          <option value="">auto (use best free brain)</option>
          <option value="offline">offline (no LLM, $0)</option>
        </select>
      </div>
    </div>
    <div class="chips" id="examples"></div>
    <button id="go">Shodh my idea → Arthabodh</button>
    <div class="spin" id="spin">Running shodh — searching case files, culture profiles and model patterns…</div>
  </div>

  <div class="meta" id="meta"></div>
  <div id="err"></div>
  <pre id="out" style="display:none"></pre>

  <p class="foot">
    <strong style="color:var(--ink)">Arthabodh</strong> — a product of <strong style="color:var(--ink)">Sarathi Labs</strong>.
    Research by the <strong style="color:var(--ink)">Shodh</strong> engine, in the <strong style="color:var(--ink)">Arthashastra</strong> tradition of Kautilya.<br>
    Runs 100% locally. Add a free API key (Groq / Gemini / OpenRouter) to enable the LLM brain, or leave it offline —
    the evidence is identical either way. Cultural scores are country-level averages, not individuals; case files carry
    survivorship bias. Verify before you spend money.
  </p>
</div>

<script>
const IDEAS = [
  ["☕ Melbourne coffee subscription", "I want to open a specialty coffee subscription in Melbourne, Australia. Customers pay monthly and I deliver beans to offices. I have no money, just a bike."],
  ["🥐 Naples bakery → Germany export", "Existing family bakery in Naples, Italy. We want to export packaged biscuits to supermarkets in Germany and the UK. Small budget, no marketing team."],
  ["📱 Mobile money for farmers", "A mobile money and savings app for smallholder farmers in Kenya who have no bank accounts. I can build the app myself, no budget for marketing."],
  ["🧺 Laundry pickup India", "A laundry pickup and delivery service in Mumbai, India aimed at working professionals in apartment buildings. I have a small budget and a scooter."],
  ["🎮 VR arcade Saudi Arabia", "I want to open a VR gaming arcade in Riyadh, Saudi Arabia for teenagers and families. Medium budget from family savings."],
  ["🍜 Home-cooking marketplace", "A marketplace where home cooks sell meals to neighbours in Jakarta, Indonesia. Cash on delivery. No budget, will start with 10 cooks."]
];

const $ = (id) => document.getElementById(id);

async function init(){
  const sel = $("country");
  try{
    const r = await fetch("api/health");
    const d = await r.json();
    (d.countries||[]).forEach(c=>{
      const o=document.createElement("option"); o.value=c; o.textContent=c; sel.appendChild(o);
    });
    $("meta").innerHTML = `<span class="badge ${d.brain_offline?'':'on'}">brain: ${d.brain}</span>
       <span class="badge">${d.cases} case files</span>
       <span class="badge">${d.patterns} model patterns</span>
       <span class="badge">${d.cultures} cultures</span>`;
  }catch(e){ $("meta").innerHTML = "could not reach API"; }
}

function renderExamples(){
  const box = $("examples");
  IDEAS.forEach(([label, text])=>{
    const c = document.createElement("div");
    c.className="chip"; c.textContent=label;
    c.onclick=()=>{ $("idea").value = text; };
    box.appendChild(c);
  });
}

async function analyse(){
  const idea = $("idea").value.trim();
  if(!idea){ $("err").innerHTML = '<div class="err">Write an idea first — or click an example chip.</div>'; return; }
  $("go").disabled = true; $("spin").style.display="block";
  $("err").innerHTML=""; $("out").style.display="none";
  try{
    const r = await fetch("api/analyze", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({idea, country:$("country").value, budget:$("budget").value, mode:$("mode").value})
    });
    const d = await r.json();
    if(d.error){ throw new Error(d.error); }
    $("out").textContent = d.markdown;
    $("out").style.display="block";
    $("out").scrollIntoView({behavior:"smooth", block:"start"});
  }catch(e){
    $("err").innerHTML = '<div class="err">'+e.message+'</div>';
  }finally{
    $("go").disabled=false; $("spin").style.display="none";
  }
}

$("go").onclick = analyse;
renderExamples(); init();
</script>
</body>
</html>
"""


def _json_default(o):
    return str(o)


class Handler(BaseHTTPRequestHandler):
    server_version = "Arthabodh/0.2 (Sarathi Labs)"

    def log_message(self, fmt, *args):  # quieter logs
        if os.environ.get("IDEA_ORACLE_VERBOSE"):
            super().log_message(fmt, *args)

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, default=_json_default).encode("utf-8"), "application/json; charset=utf-8")

    def do_OPTIONS(self):  # noqa: N802
        self._send(204, b"", "text/plain")

    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/health":
            self._json({
                "ok": True,
                "product": "Arthabodh",
                "lab": "Sarathi Labs",
                "engine": "Shodh",
                "version": "0.2.0",
                "brain": ORACLE.brain.label,
                "brain_offline": type(ORACLE.brain).__name__ == "OfflineBrain",
                "brain_provider": getattr(ORACLE.brain, "provider_name", "offline"),
                "cases": len(ORACLE.kb.cases),
                "patterns": len(ORACLE.kb.patterns),
                "cultures": len(ORACLE.kb.cultures),
                "countries": ORACLE.kb.all_countries(),
            })
        elif path == "/api/providers":
            self._send(200, describe_providers().encode("utf-8"), "text/plain; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802
        if self.path.split("?")[0] != "/api/analyze":
            self._send(404, b"not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length) or b"{}")
            idea = (payload.get("idea") or "").strip()
            if not idea:
                self._json({"error": "No idea provided."}, 400)
                return
            mode = payload.get("mode") or ""
            oracle = ORACLE
            if mode == "offline" and type(ORACLE.brain).__name__ != "OfflineBrain":
                from idea_oracle import OfflineBrain  # local import keeps startup fast
                oracle = IdeaOracle(data_dir=None, brain=OfflineBrain())
            report = oracle.analyze(idea,
                                    country=payload.get("country", ""),
                                    budget=payload.get("budget", ""))
            self._json(report.to_dict())
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"Arthabodh (Sarathi Labs) running on http://{host}:{port}")
    print(f"brain : {ORACLE.brain.label}")
    print("engine: Shodh (retrieval + reasoning)")
    print(f"corpus: {len(ORACLE.kb.cases)} case files · {len(ORACLE.kb.patterns)} model patterns · {len(ORACLE.kb.cultures)} markets")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
