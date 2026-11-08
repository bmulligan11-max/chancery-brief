"""Chancery Brief - daily build script (Claude, built for low cost).

  python build.py            build today's brief and publish it to docs/
                             (skips if today's page already exists, so re-runs cost nothing)
  python build.py --force    rebuild even if today's page exists
  python build.py --draft    write to draft/ only so you can review it first
  python build.py --publish  publish the saved draft (no API cost)
"""
import datetime
import html
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).parent
MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-5-5")
MAX_SEARCHES = int(os.environ.get("MAX_SEARCHES", "8"))   # each search costs $0.01
MAX_OUTPUT_TOKENS = 4000

# USD per million tokens (input, output). Haiku 5.5 rates apply to prompts up to 100K tokens;
# above that the whole request is billed at 5x, so keep MAX_SEARCHES modest.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.00, 10.00)}
SEARCH_FEE = 0.01

SOURCES = [
    "MFA", "PRC Embassy", "China Daily", "Xinhua", "Global Times", "People's Daily", "CGTN",
    "Qiushi", "NetEase", "TAO", "NPC", "12371", "CCDI", "PLA Daily", "MoD", "S&T Daily",
    "MOFCOM", "MOF", "MIIT", "CAC", "NBS", "BIS", "USTR", "Treasury", "DOJ", "State Dept",
    "White House", "DoD", "Taiwan MND", "Bloomberg", "NYT", "SCMP", "BBC", "Politico",
    "RealClearPolitics", "Sinocism", "Pekingnology", "China in Space", "TechNode", "Reuters",
]

SYSTEM = (
    "You are the analyst behind Chancery Brief, a daily political and economic brief on China for "
    "diplomats and policy readers. Accuracy matters more than volume. Use web search. Only report "
    "facts found in search results, and never invent a number, quote or URL. If you cannot verify "
    "something, leave it out. Paraphrase in your own words; do not copy article text."
)

PROMPT = """Today is TODAY. Build the Beijing brief for today.

Use at most MAXS web searches, chosen to cover: PRC leadership and MFA briefings; US-China trade,
export controls and sanctions (BIS, USTR, Treasury, MOFCOM); technology and AI policy; Chinese
commercial space; the economy; Taiwan and regional security; APEC and other diplomacy. Prefer
official sources and wire services, and items from the last 72 hours.
PREVIOUS
Reply with ONLY a JSON object, no markdown, in this shape:
{
 "flash": [ {"level": "high|moderate|routine", "title": "...", "body": "2-3 sentences",
             "tags": ["..."], "sources": [{"name": "Reuters", "url": "https://..."}]} ],
 "leadership": [ {"title": "...", "bullets": ["..."], "sources": [{"name": "...", "url": "..."}]} ],
 "state_media": {"bullets": ["..."], "temperature": "one sentence, labelled as your read"},
 "watchlist": [ {"date": "Nov 9", "event": "..."} ],
 "notes": "what you could not verify today"
}
Give 6 to 8 flash items, most important first. Every source url must be a page you actually found.
Where a source is on this list use its exact name: SOURCELIST. Plain text only."""


def previous_block():
    p = ROOT / "data" / "latest.json"
    if not p.exists():
        return "\n"
    try:
        old = json.loads(p.read_text(encoding="utf-8"))
        titles = "; ".join(i.get("title", "") for i in old.get("flash", []))[:900]
        return (f"\nYesterday's brief covered: {titles}\nRepeat a story only if there is a material "
                "update, and say what changed.\n")
    except Exception:
        return "\n"


def norm(u):
    return str(u).split("#")[0].rstrip("/").lower()


def fetch():
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
    today = datetime.date.today().strftime("%A %d %B %Y")
    prompt = (PROMPT.replace("TODAY", today).replace("MAXS", str(MAX_SEARCHES))
              .replace("PREVIOUS", previous_block()).replace("SOURCELIST", ", ".join(SOURCES)))
    messages = [{"role": "user", "content": prompt}]
    tools = [{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}]
    stats = {"in": 0, "out": 0, "searches": 0, "max_in": 0}
    urls = set()

    def call(use_tools=True):
        r = client.messages.create(model=MODEL, max_tokens=MAX_OUTPUT_TOKENS, system=SYSTEM,
                                   messages=messages, tools=tools if use_tools else [])
        u = r.usage
        stats["in"] += u.input_tokens
        stats["out"] += u.output_tokens
        stats["max_in"] = max(stats["max_in"], u.input_tokens)
        st = getattr(u, "server_tool_use", None)
        stats["searches"] += (getattr(st, "web_search_requests", 0) or 0) if st else 0
        for b in r.content:
            if getattr(b, "type", "") == "web_search_tool_result" and isinstance(b.content, list):
                urls.update(norm(x.url) for x in b.content if getattr(x, "url", None))
        return r

    r = call()
    for _ in range(4):  # long searches can pause; keep going
        if r.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": r.content})
        r = call()
    text = "".join(b.text for b in r.content if b.type == "text")
    try:
        data = parse(text)
    except ValueError:
        messages.append({"role": "assistant", "content": text or "(no text)"})
        messages.append({"role": "user", "content": "Reply with only the JSON object."})
        r = call(False)
        data = parse("".join(b.text for b in r.content if b.type == "text"))

    data = sanitize(data, urls)
    data["date"] = datetime.date.today().isoformat()
    data["generated"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    report_cost(stats)
    return data


def report_cost(s):
    pin, pout = PRICES.get(MODEL, (None, None))
    msg = f"Usage: {s['in']} in / {s['out']} out tokens, {s['searches']} searches."
    if pin is not None:
        cost = s["in"] / 1e6 * pin + s["out"] / 1e6 * pout + s["searches"] * SEARCH_FEE
        msg += f" Estimated cost ${cost:.3f}."
    if MODEL == "claude-haiku-5-5" and s["max_in"] > 90000:
        msg += " WARNING: a request neared 100K input tokens (5x price above that). Lower MAX_SEARCHES."
    print(msg)


def parse(text):
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError("no JSON found")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as e:
        raise ValueError(str(e))


def sanitize(data, urls):
    """Drop any link the model cites that it did not actually retrieve, and any item left unsourced."""
    removed = 0

    def clean(srcs):
        nonlocal removed
        out = []
        for s in srcs or []:
            if norm(s.get("url", "")) in urls:
                out.append(s)
            else:
                removed += 1
        return out

    for sec in ("flash", "leadership"):
        kept = []
        for it in data.get(sec, []):
            it["sources"] = clean(it.get("sources"))
            if it["sources"]:
                kept.append(it)
        data[sec] = kept
    if len(data.get("flash", [])) < 3:
        raise RuntimeError("Too few verified items; refusing to publish.")
    if removed:
        data["notes"] = (str(data.get("notes", "")) + f" {removed} cited link(s) were removed "
                         "because they did not match the pages retrieved today.").strip()
    return data


# ---------- rendering ----------
def e(s):
    return html.escape(str(s or ""))


def src_line(sources):
    out = []
    for s in sources or []:
        url = str(s.get("url", ""))
        name = e(s.get("name", "source"))
        out.append(f'<a href="{e(url)}" rel="noopener noreferrer" target="_blank">{name}</a>' if url.startswith("http") else name)
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
        out.append(f'<article class="{cls}"><div class="no">{i:02d}</div><div><p class="kicker">{kick}</p>'
                   f'<h3>{e(it.get("title"))}</h3><p>{e(it.get("body"))}</p>{src_line(it.get("sources"))}</div></article>')
    return "".join(out)


def render_leadership(items):
    boxes = []
    for it in items:
        bullets = "".join(f"<li>{e(b)}</li>" for b in it.get("bullets", []))
        boxes.append(f'<div><h3>{e(it.get("title"))}</h3><ul>{bullets}</ul>{src_line(it.get("sources"))}</div>')
    return '<div class="pair">' + "".join(boxes) + "</div>"


def render_sidebar(data):
    cited = " ".join(s.get("name", "") for sec in ("flash", "leadership") for it in data.get(sec, [])
                     for s in it.get("sources", [])).lower()
    rows, used = [], 0
    for name in SOURCES:
        pat = r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])"
        ok = bool(re.search(pat, cited))
        used += ok
        rows.append(f'<span class="chip{" g" if ok else ""}">{e(name)}</span>')
    return "".join(rows), used


def render(data):
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    sidebar, used = render_sidebar(data)
    sm = data.get("state_media", {})
    sm_html = "".join(f"<li>{e(b)}</li>" for b in sm.get("bullets", []))
    sm_temp = f'<div class="pull">{e(sm["temperature"])}</div>' if sm.get("temperature") else ""
    watch = "".join(f"<tr><td>{e(w.get('date'))}</td><td>{e(w.get('event'))}</td></tr>" for w in data.get("watchlist", []))
    date = datetime.date.fromisoformat(data["date"]).strftime("%A %d %B %Y")
    values = {"DATE": date, "FLASH": render_flash(data.get("flash", [])),
              "LEADERSHIP": render_leadership(data.get("leadership", [])),
              "STATE_BULLETS": sm_html, "STATE_TEMP": sm_temp, "WATCHLIST": watch,
              "NOTES": e(data.get("notes")), "SIDEBAR": sidebar, "USED": str(used),
              "TOTAL": str(len(SOURCES)), "ITEMS": str(len(data.get("flash", []))),
              "GENERATED": e(data.get("generated"))}
    for k, v in values.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    return tpl


def newsletter_md(data):
    """Plain markdown version, ready to paste into an email newsletter tool."""
    date = datetime.date.fromisoformat(data["date"]).strftime("%A %d %B %Y")
    lines = [f"# Chancery Brief — Beijing, {date}", ""]
    for i, it in enumerate(data.get("flash", []), 1):
        links = ", ".join(f"[{s.get('name', 'source')}]({s['url']})" for s in it.get("sources", []))
        lines += [f"**{i}. {it.get('title', '')}**", it.get("body", ""), f"Sources: {links}", ""]
    if data.get("watchlist"):
        lines += ["## Calendar ahead", ""] + [f"- **{w.get('date')}**: {w.get('event')}" for w in data["watchlist"]] + [""]
    lines.append("_AI-assisted brief; verify critical items at the source._")
    return "\n".join(lines)


def write_site(data, outdir, archive=False):
    outdir.mkdir(exist_ok=True)
    page = render(data)
    (outdir / "index.html").write_text(page, encoding="utf-8")
    (outdir / "newsletter.md").write_text(newsletter_md(data), encoding="utf-8")
    if archive:
        (outdir / "archive").mkdir(exist_ok=True)
        (outdir / "archive" / f"{data['date']}.html").write_text(page, encoding="utf-8")
    print("Wrote", outdir / "index.html")


def save(data):
    d = ROOT / "data"
    d.mkdir(exist_ok=True)
    txt = json.dumps(data, indent=2, ensure_ascii=False)
    (d / "latest.json").write_text(txt, encoding="utf-8")
    (d / f"{data['date']}.json").write_text(txt, encoding="utf-8")


def main():
    args = sys.argv[1:]
    if "--publish" in args:
        data = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))
        write_site(data, ROOT / "docs", archive=True)
        return
    today = datetime.date.today().isoformat()
    if "--force" not in args and "--draft" not in args and (ROOT / "docs" / "archive" / f"{today}.html").exists():
        print(f"Today's brief ({today}) already exists; nothing to do. Use --force to rebuild.")
        return
    data = fetch()
    save(data)
    if "--draft" in args:
        write_site(data, ROOT / "draft")
        print("Review draft/index.html, then run: python build.py --publish")
    else:
        write_site(data, ROOT / "docs", archive=True)


if __name__ == "__main__":
    main()
