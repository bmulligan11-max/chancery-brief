"""Chancery Brief - daily build script for DeepSeek."""
import datetime
import html
import json
import os
import pathlib
import re
import sys
import requests

ROOT = pathlib.Path(__file__).parent
DEEPSEEK_BASE = "https://api.deepseek.com"
POST = "Beijing"

SOURCES = [
    "MFA", "PRC Embassy", "China Daily", "Xinhua", "Global Times", "People's Daily", "CGTN",
    "Qiushi", "NetEase", "TAO", "NPC", "12371", "CCDI", "PLA Daily", "MoD", "S&T Daily",
    "MOFCOM", "MOF", "MIIT", "CAC", "NBS", "BIS", "USTR", "Treasury", "DOJ", "State Dept",
    "White House", "DoD", "Taiwan MND", "Bloomberg", "NYT", "SCMP", "BBC", "Politico",
    "RealClearPolitics", "Sinocism", "Pekingnology", "China in Space", "TechNode", "Reuters",
]

SYSTEM = (
    "You are the analyst behind Chancery Brief, a daily political and economic intelligence "
    "brief on China for policy readers. Accuracy matters more than volume. "
    "Only report facts you found in the search results provided. Never invent a number, quote or URL. "
    "If you cannot verify something, leave it out."
)

PROMPT = """Today is TODAY. Build the Beijing brief for today.

Cover: PRC leadership and MFA activity; US-China trade, export controls and sanctions; technology and AI policy; Chinese commercial space and launches; the economy; Taiwan and regional security; APEC and other diplomacy. Prefer items from the last 72 hours.

Reply with ONLY a JSON object in this shape:
{
 "flash": [ {"level": "high|moderate|routine", "title": "...", "body": "2-3 sentences",
             "tags": ["..."], "sources": [{"name": "Reuters", "url": "https://..."}]} ],
 "leadership": [ {"title": "...", "bullets": ["..."], "sources": [{"name": "...", "url": "..."}]} ],
 "state_media": {"bullets": ["..."], "temperature": "one sentence, labelled as your read"},
 "watchlist": [ {"date": "Nov 9", "event": "..."} ],
 "notes": "what you could not verify today"
}
Give 6 to 9 flash items, most important first, each with at least one real source URL.
Write plain text only."""


def deepseek_search(query, count=5):
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY not set")
    r = requests.post(
        f"{DEEPSEEK_BASE}/v1/tools/search",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"query": query, "count": count},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def fetch():
    today = datetime.date.today().strftime("%A %d %B %Y")
    after = (datetime.date.today() - datetime.timedelta(days=3)).isoformat()

    queries = [
        f"China MFA spokesperson statement after:{after}",
        f"US China trade export controls BIS USTR after:{after}",
        f"China economy NBS data market after:{after}",
        f"China Taiwan regional security after:{after}",
        f"China technology AI policy CAC MIIT after:{after}",
    ]

    all_results = []
    for q in queries:
        try:
            all_results.extend(deepseek_search(q, count=6))
        except Exception as e:
            print(f"Search failed for {q}: {e}")

    context_parts = []
    for r in all_results[:24]:
        context_parts.append(
            f"Title: {r.get('title','')}\n"
            f"URL: {r.get('url','')}\n"
            f"Date: {r.get('date','')}\n"
            f"Summary: {r.get('summary','')}\n"
            f"Content: {str(r.get('content',''))[:800]}"
        )
    context = "\n\n---\n\n".join(context_parts)

    prompt = PROMPT.replace("TODAY", today)
    prompt += f"\n\nHere are the search results you must use:\n\n{context}"

    key = os.environ.get("DEEPSEEK_API_KEY")
    r = requests.post(
        f"{DEEPSEEK_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": 8000,
        },
        timeout=120,
    )
    r.raise_for_status()
    raw = r.json()["choices"][0]["message"]["content"]

    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("No JSON found in response")
    data = json.loads(m.group(0))
    data["date"] = datetime.date.today().isoformat()
    data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return data


def e(s):
    return html.escape(str(s or ""))


def src_line(sources):
    out = []
    for s in sources or []:
        url = str(s.get("url", ""))
        name = e(s.get("name", "source"))
        out.append(f'<a href="{e(url)}" rel="noopener" target="_blank">{name}</a>' if url.startswith("http") else name)
    return '<div class="via">' + " · ".join(out) + "</div>" if out else ""


def render_flash(items):
    pri = {"high": "Priority", "moderate": "Notable"}
    out = []
    for i, it in enumerate(items, 1):
        lvl = str(it.get("level", "")).lower()
        label = pri.get(lvl, "Background")
        tags = " · ".join(e(t) for t in it.get("tags", []))
        cls = ("item lead " if i == 1 else "item ") + (lvl if lvl in pri else "bg")
        kick = label + (" · " + tags if tags else "")
        out.append(
            f'<article class="{cls}"><div class="no">{i:02d}</div><div><p class="kicker">{kick}</p>'
            f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("body"))}</p>{src_line(it.get("sources"))}</div></article>'
        )
    return "".join(out)


def render_leadership(items):
    boxes = []
    for it in items:
        bullets = "".join(f"<li>{e(b)}</li>" for b in it.get("bullets", []))
        boxes.append(f'<div><h3>{e(it.get("title"))}</h3><ul>{bullets}</ul>{src_line(it.get("sources"))}</div>')
    return '<div class="pair">' + "".join(boxes) + "</div>"


def render_sidebar(data):
    cited = " ".join(
        s.get("name", "") for sec in ("flash", "leadership") for it in data.get(sec, [])
        for s in it.get("sources", [])
    ).lower()
    checked = [c.lower() for c in data.get("checked", [])]
    rows, used, searched = [], 0, 0
    for name in SOURCES:
        pat = r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])"
        ok = bool(re.search(pat, cited))
        chk = (not ok) and name.lower() in checked
        used += ok
        searched += chk
        rows.append(f'<span class="chip{" g" if ok else (" s" if chk else "")}">{e(name)}</span>')
    return "".join(rows), used, searched, len(SOURCES) - used - searched


def render(data):
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    sidebar, used, searched, missed = render_sidebar(data)
    sm = data.get("state_media", {})
    sm_html = "".join(f"<li>{e(b)}</li>" for b in sm.get("bullets", []))
    sm_temp = f'<div class="pull">{e(sm["temperature"])}</div>' if sm.get("temperature") else ""
    watch = "".join(f"<tr><td>{e(w.get('date'))}</td><td>{e(w.get('event'))}</td></tr>" for w in data.get("watchlist", []))
    date = datetime.date.fromisoformat(data["date"]).strftime("%A %d %B %Y")
    values = {
        "DATE": date,
        "FLASH": render_flash(data.get("flash", [])),
        "LEADERSHIP": render_leadership(data.get("leadership", [])),
        "STATE_BULLETS": sm_html,
        "STATE_TEMP": sm_temp,
        "WATCHLIST": watch,
        "NOTES": e(data.get("notes")),
        "SIDEBAR": sidebar,
        "USED": str(used),
        "SEARCHED": str(searched),
        "MISSED": str(missed),
        "ITEMS": str(len(data.get("flash", []))),
        "GENERATED": e(data.get("generated")),
    }
    for k, v in values.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def write_site(data, outdir):
    outdir.mkdir(exist_ok=True)
    page = render(data)
    (outdir / "index.html").write_text(page, encoding="utf-8")
    (outdir / "archive").mkdir(exist_ok=True)
    (outdir / "archive" / f"{data['date']}.html").write_text(page, encoding="utf-8")
    print("Wrote", outdir / "index.html")


def main():
    data = fetch()
    (ROOT / "docs").mkdir(exist_ok=True)
    write_site(data, ROOT / "docs")
    print("Done. Site ready in docs/")


if __name__ == "__main__":
    main()