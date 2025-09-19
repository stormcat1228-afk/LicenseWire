import hashlib, json, os, pathlib, csv, io, requests, yaml
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "bots"
DATA = ROOT / "data"
BOTS = ROOT / "bots"
DOCS.mkdir(parents=True, exist_ok=True); DATA.mkdir(exist_ok=True)

def md5(s): return hashlib.md5(s.encode("utf-8")).hexdigest()

def load_yaml(p): return yaml.safe_load(pathlib.Path(p).read_text(encoding="utf-8"))
def load_seen(slug):
    f = DATA / f"{slug}_seen.json"
    return set(json.loads(f.read_text())) if f.exists() else set()
def save_seen(slug, s):
    (DATA / f"{slug}_seen.json").write_text(json.dumps(sorted(list(s)), indent=2, ensure_ascii=False))

def fetch_csv(url, mapping):
    r = requests.get(url, timeout=30); r.raise_for_status()
    content = r.content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    out = []
    for row in reader:
        rec = {k:(row.get(v,"") or "").strip() for k,v in mapping.items()}
        out.append(rec)
    return out

def fetch_html_table(url, row_sel, cols):
    html = requests.get(url, timeout=30).text
    soup = BeautifulSoup(html, "lxml")
    out=[]
    for tr in soup.select(row_sel):
        rec={}
        for k, sel in cols.items():
            el = tr.select_one(sel)
            rec[k] = (el.get_text(strip=True) if el else "")
        if any(rec.values()): out.append(rec)
    return out

def normalize(rec, cfg):
    key = "|".join([rec.get(k,"") for k in cfg["fields"]["id_key"]])
    rec["_id"] = md5(key)
    return rec

def run_one(bot_path):
    cfg = load_yaml(bot_path)
    slug = cfg["slug"]
    seen = load_seen(slug)
    fresh = []
    for src in cfg["sources"]:
        if src["type"] == "csv":
            rows = fetch_csv(src["url"], src["map"])
        elif src["type"] == "html_table":
            rows = fetch_html_table(src["url"], src["row"], src["cols"])
        else:
            continue
        for r in rows:
            n = normalize(r, cfg)
            if n["_id"] not in seen:
                fresh.append(n); seen.add(n["_id"])
    (DOCS / f"{slug}.json").write_text(json.dumps(fresh, indent=2, ensure_ascii=False))
    save_seen(slug, seen)

def main():
    for yml in sorted(BOTS.glob("*.yaml")):
        run_one(yml)

if __name__ == "__main__":
    main()
