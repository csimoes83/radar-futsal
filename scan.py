#!/usr/bin/env python3
"""Radar Futsal — motor CLOUD (corre no GitHub Actions, sem Mac).
Lê feeds RSS/Atom datados, filtra 48h, deduplica, escreve index.html autónomo.
Sem dependências externas (só stdlib). Estado de dedup persiste em seen.json (commitado)."""
import email.utils, html as html_mod, json, os, re, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
import render as R
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
    ("X · ElPozo", "https://nitter.net/ElPozoMurcia_FS/rss", None),
    ("X · Pato", "https://nitter.net/patofutsal/rss", None),
    ("X · Alzira FS", "https://nitter.net/AlziraFS/rss", None),
    ("X · Fahey", "https://nitter.net/jamiefahey1/rss", "FUTSAL"),
    ("X · KSA Futsal", "https://nitter.net/futsal_KSA2030/rss", None),
    ("OFC Oceânia", "https://www.oceaniafootball.com/feed/", "FUTSAL"),
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



# ---- Instagram via Apify (opcional; ativa-se com APIFY_TOKEN nos GitHub Secrets) ----
def _load_ig_handles():
    p = os.path.join(ROOT, "ig_handles.txt")
    try:
        linhas = open(p, encoding="utf-8").read().splitlines()
    except Exception:
        return ["ligaplacard", "foconofutsal", "magnusfutsal", "futsalrfef"]
    hs, vistos = [], set()
    for ln in linhas:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln not in vistos:
            vistos.add(ln); hs.append(ln)
    return hs

IG_HANDLES = _load_ig_handles()

def instagram_apify():
    """Puxa os últimos posts das contas-chave via Apify. Vazio se não houver token."""
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if not token:
        return []
    # poupança: só consultar o IG 4x/dia (08/12/16/20 UTC) para caber no tier grátis;
    # mas em disparo manual (workflow_dispatch) corre sempre, p/ forçar/testar sweeps
    manual = os.environ.get("GITHUB_EVENT_NAME", "") == "workflow_dispatch"
    if not manual and datetime.now(timezone.utc).hour not in (8, 12, 16, 20):
        return []
    url = ("https://api.apify.com/v2/acts/sones~instagram-posts-scraper-lowcost/"
           "run-sync-get-dataset-items?token=" + urllib.parse.quote(token))
    newer = (datetime.now(timezone.utc) - timedelta(hours=JANELA_H)).strftime("%Y-%m-%d")
    body = json.dumps({
        "usernames": IG_HANDLES, "postsPerProfile": 2, "newerThan": newer,
    }).encode()
    req = urllib.request.Request(url, data=body,
                                headers={**UA, "Content-Type": "application/json"})
    out = []
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read())
    except Exception as e:
        print("IG/Apify falhou:", e)
        return []
    def g(p, *keys):
        for k in keys:
            v = p.get(k)
            if v:
                return v
        return ""
    for p in data:
        cap = str(g(p, "caption", "text", "title")).strip()
        user = g(p, "ownerUsername", "username", "owner_username", "ownerUserName")
        ts = g(p, "timestamp", "takenAt", "taken_at", "takenAtTimestamp")
        code = g(p, "shortCode", "code", "shortcode")
        if not cap or not ts:
            continue
        try:
            if isinstance(ts, (int, float)):
                w = datetime.fromtimestamp(ts, tz=timezone.utc)
            else:
                w = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue
        out.append({"title": cap[:120], "when": w, "source": "IG · @" + user,
                    "link": f"https://www.instagram.com/p/{code}/" if code
                            else f"https://www.instagram.com/{user}/"})
    return out


def main():
    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)
    proprio = texto_proprio()

    itens, ok = [], 0
    ig_itens = instagram_apify()
    if ig_itens:
        ok += 1
        for it in ig_itens:
            if not it["when"] or it["when"] < corte:
                continue
            if RUIDO.search(it["title"]):
                continue
            frases = [m.group(0).lower() for m in NOME_RE.finditer(it["title"])]
            if proprio and any(f in proprio for f in frases if len(f) >= 9):
                continue
            it["key"] = key_of(it)
            itens.append(it)
    por_fonte = {}
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
            por_fonte.setdefault(name, []).append(it)  # p/ tabelas Por fonte
            frases = [m.group(0).lower() for m in NOME_RE.finditer(it["title"])]
            if proprio and any(f in proprio for f in frases if len(f) >= 9):
                continue  # já publicado -> fora da timeline
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

    html = R.render(itens, por_fonte, data, ok, len(FEEDS))

    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"OK: {len(itens)} itens · {ok}/{len(FEEDS)} fontes · {data}")


if __name__ == "__main__":
    main()
