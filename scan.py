#!/usr/bin/env python3
"""Radar Futsal — motor CLOUD (corre no GitHub Actions, sem Mac).
Lê feeds RSS/Atom datados, filtra 48h, deduplica, escreve index.html autónomo.
Sem dependências externas (só stdlib). Estado de dedup persiste em seen.json (commitado)."""
import email.utils, html as html_mod, json, os, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
JANELA_H = 48
MAX_ITENS = 40

FUTSAL_RE = re.compile(r"futsal|f[úu]tbol sala|calcio a 5|liga placard|futsalista", re.I)
TEMA_RE = re.compile(
    r"futsal|f[úu]tbol sala|calcio a 5|liga placard|benfica|sporting|braga|bar[çc]a|barcelona|"
    r"elpozo|palma|jimbee|movistar|cartagena|valdepe|pe[ñn][íi]scola|santa coloma|xota|osasuna magna|"
    r"magnus|pato futsal|corinthians|joinville|cascavel|carlos barbosa|kairat|lnfs?\b|uefa|champions|"
    r"sele[çc][ãa]o|fifa|fund[ãa]o|el[ée]ctrico|famalic[ãa]o|z[êe]zere|porto salvo|portimonense|"
    r"rio ave|torreense|upvn|nun.?[áa]lvares|liga feminina", re.I)

FEEDS = [
    ("Palma Futsal", "https://www.palmafutsal.com/feed/", None),
    ("ElPozo Murcia", "https://www.elpozomurcia.com/feed/", None),
    ("Movistar Inter", "https://www.interfutbolsala.com/feed/", None),
    ("Jimbee Cartagena", "https://jimbeecartagena.es/feed/", None),
    ("Valdepeñas", "https://www.fsvaldepenas.com/feed/", None),
    ("Osasuna Magna", "https://xota.es/feed/", None),
    ("Peñíscola", "https://peniscolafs.com/feed/", None),
    ("Santa Coloma", "https://fsgarcia.cat/feed/", None),
    ("CROfutsal", "https://www.crofutsal.com/feed/", None),
    ("Futsal Dinamo", "https://futsal-dinamo.hr/feed/", None),
    ("Magnus", "https://magnusfutsal.com.br/feed/", None),
    ("Pato Futsal", "https://patofutsal.com.br/feed/", None),
    ("LNF Brasil", "https://lnfoficial.com.br/noticias/feed/", None),
    ("Itália C5", "https://www.divisionecalcioa5.it/feed/", None),
    ("Meta Catania", "https://metacatania.it/feed/", None),
    ("Famalicão", "https://www.fcfamalicao.pt/feed/", "FUTSAL"),
    ("zerozero", "https://www.zerozero.pt/rss/noticias.php", "FUTSAL"),
    ("Record", "https://www.record.pt/rss", "FUTSAL"),
    ("CONMEBOL", "https://www.conmebol.com/feed/", "FUTSAL"),
    ("Google Alerts", "https://www.google.com/alerts/feeds/07340303412689524551/4521077332057732674", "TEMA"),
    ("Alerts Futsal", "https://www.google.com/alerts/feeds/07340303412689524551/6715931025412471738", "TEMA"),
    ("X · Palma", "https://nitter.net/PalmaFutsal/rss", None),
    ("X · Magnus", "https://nitter.net/MagnusFutsal/rss", None),
    ("X · Jimbee", "https://nitter.net/JimbeeCartagena/rss", None),
    ("X · Barça FS", "https://nitter.net/FCBfutbolsala/rss", None),
    ("X · LNFS", "https://nitter.net/LNFS/rss", None),
    ("X · UEFA Futsal", "https://nitter.net/UEFAFutsal/rss", None),
    ("X · RFEF", "https://nitter.net/RFEF/rss", "FUTSAL"),
]

RUIDO = re.compile(
    r"zapatill|sapatilh|decathlon|\bnike\b|\bjoma\b|ripley|balon\b|bolas?\b|tienda|loja|"
    r"sala de espera|sala de consumo|sala de imprensa|sala de aula|"
    # futsal amador/municipal/base (BR/US) — o Carlos não publica isto:
    r"campeonato municipal|municipal de futsal|interinstitucional|copa .{0,18} de futsal|"
    r"de base\b|futsal de base|categorias de base|entrada gratuita|rel[âa]mpago|"
    r"unitedfutsal|united futsal|world futsal champ|liga usuluteca|santafesina|"
    r"bauru cup|araucária|arapiraca|traipu|citadino|distrital amador|"
    r"ver[ãa]o|f[ée]rias|escolar\b|amistoso beneficente|torneio solid[áa]rio",
    re.I)

# prioridade editorial do Carlos (PT + PT no estrangeiro + Placard + relevante)
PRIO_PT = re.compile(
    r"benfica|sporting|braga|porto|fc porto|leões porto salvo|el[ée]ctrico|torreense|fund[ãa]o|"
    r"famalic[ãa]o|z[êe]zere|portimonense|rio ave|upvn|nun.?[áa]lvares|liga placard|liga feminina|"
    r"sele[çc][ãa]o portuguesa|portugu[êe]s|portuguesa|treinador portugu|fpf|"
    r"barcelona|bar[çc]a|palma|elpozo|movistar|jimbee|rfef|lnfs|uefa futsal|champions|"
    r"ricardinho|bruno coelho|jo[ãa]o matos|higor|f[úu]tbol sala", re.I)


def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            return r.read()
    except Exception:
        return None


def unwrap_google(link):
    if "google.com/url" in link:
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(link).query)
        for k in ("url", "q"):
            if k in qs:
                return qs[k][0]
    return link


def limpa(t):
    t = re.sub(r"^\s*<!\[CDATA\[\s*", "", t)
    t = re.sub(r"^RT by @\w+:\s*", "", t)
    t = re.sub(r"\s*\]\]>\s*$", "", t)
    return re.sub(r"\s+", " ", html_mod.unescape(html_mod.unescape(t))).strip()


def parse_feed(name, raw):
    out = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for it in root.iter("item"):
        t = limpa(it.findtext("title") or "")
        l = (it.findtext("link") or "").strip()
        d = it.findtext("pubDate")
        w = None
        if d:
            try:
                w = email.utils.parsedate_to_datetime(d)
            except Exception:
                pass
        if t and l:
            out.append({"title": t, "link": l, "when": w, "source": name})
    for e in root.findall("a:entry", ns):
        t = limpa(re.sub(r"<[^>]+>", "", e.findtext("a:title", "", ns)))
        le = e.find("a:link", ns)
        l = unwrap_google(le.get("href", "")) if le is not None else ""
        d = e.findtext("a:published", "", ns) or e.findtext("a:updated", "", ns)
        w = None
        if d:
            try:
                w = datetime.fromisoformat(d.replace("Z", "+00:00"))
            except Exception:
                pass
        if t and l:
            out.append({"title": t, "link": l, "when": w, "source": name})
    return out


def key_of(it):
    dom = urllib.parse.urlparse(it["link"]).netloc.replace("www.", "")
    slug = re.sub(r"[^a-z0-9]+", "-", it["title"].lower())[:60].strip("-")
    return f"{dom} {slug}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def texto_proprio():
    txt = []
    for u in ("https://www.zonatecnicafutsal.com", "https://www.futsalportugal.com"):
        raw = fetch(u)
        if raw:
            txt.append(re.sub(r"<[^>]+>", " ", raw.decode("utf-8", "ignore")).lower())
    return " ".join(txt)


NOME_RE = re.compile(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][\wáéíóúâêôãõç]+)+")


def main():
    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)
    proprio = texto_proprio()

    itens, ok = [], 0
    for name, url, filt in FEEDS:
        raw = fetch(url)
        if not raw:
            continue
        ok += 1
        req = {"FUTSAL": FUTSAL_RE, "TEMA": TEMA_RE}.get(filt)
        for it in parse_feed(name, raw):
            if not it["when"] or it["when"] < corte:
                continue
            if RUIDO.search(it["title"]):
                continue
            if req and not req.search(it["title"]):
                continue
            frases = [m.group(0).lower() for m in NOME_RE.finditer(it["title"])]
            if proprio and any(f in proprio for f in frases if len(f) >= 9):
                continue  # já publicado nos sites do Carlos
            it["key"] = key_of(it)
            itens.append(it)

    uniq = {}
    for it in sorted(itens, key=lambda x: x["when"], reverse=True):
        uniq.setdefault(it["key"], it)
    itens = list(uniq.values())
    for it in itens:
        it["prio"] = 1 if PRIO_PT.search(it["title"]) else 0
    # PT-relevante primeiro; dentro de cada grupo, mais recente primeiro
    itens.sort(key=lambda x: (x["prio"], x["when"]), reverse=True)
    itens = itens[:MAX_ITENS]

    LX = timezone(timedelta(hours=1))  # hora de Lisboa (verão)
    stamp = agora.astimezone(LX)
    meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    data = f"{stamp.day} {meses[stamp.month-1]} {stamp.year} · {stamp:%H:%M}"

    cards = []
    for it in itens:
        w = it["when"].astimezone(LX)
        tag = ' · 🇵🇹 PARA TI' if it.get("prio") else ''
        cards.append(f'''    <div class="card">
      <div class="k">{w:%H:%M} · {esc(it["source"])}{tag}</div>
      <h3><a href="{esc(it["link"])}" target="_blank" rel="noopener">{esc(it["title"])}</a></h3>
      <p>{esc(it["source"])} · {w:%d/%m %H:%M}</p>
    </div>''')
    grid = "\n".join(cards) if cards else '<div class="card"><h3>Sem novidades nas últimas 48h</h3></div>'

    html = f'''<!DOCTYPE html>
<html lang="pt"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radar Futsal — atualiza sozinho</title>
<style>
 :root{{--bg:#000;--panel:#111318;--ink:#eef1f6;--muted:#9aa3b2;--line:#23262e;--acc:#f26430}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;line-height:1.5}}
 .wrap{{max-width:1080px;margin:0 auto;padding:20px 20px 64px}}
 header{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px}}
 h1{{font-size:22px;margin:0}} .sub{{color:var(--muted);font-size:13px}}
 .stamp{{margin-left:auto;color:var(--muted);font-size:12px}} .stamp b{{color:var(--ink)}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:20px}}
 .card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}}
 .k{{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--acc)}}
 .card h3{{font-size:15px;margin:6px 0}} .card h3 a{{color:var(--ink);text-decoration:none}}
 .card h3 a:hover{{text-decoration:underline}} .card p{{margin:0;font-size:12px;color:var(--muted)}}
 footer{{margin-top:34px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}}
</style></head><body><div class="wrap">
<header>
 <h1>🏐 Radar Futsal</h1>
 <span class="sub">atualiza-se sozinho de 30 em 30 min · sem PC ligado</span>
 <span class="stamp">Recolha de <b>{data}</b> (Lisboa) · {len(itens)} notícias · {ok}/{len(FEEDS)} fontes</span>
</header>
<div class="grid">
{grid}
</div>
<footer>Radar Futsal · gerado automaticamente no GitHub Actions a partir de feeds oficiais de futsal. As notícias já publicadas em zonatecnicafutsal.com / futsalportugal.com são omitidas.</footer>
</div></body></html>'''

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK: {len(itens)} itens · {ok}/{len(FEEDS)} fontes · {data}")


if __name__ == "__main__":
    main()
