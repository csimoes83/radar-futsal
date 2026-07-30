#!/usr/bin/env python3
"""Recolha LOCAL de Instagram (grátis, sem Apify, sem login) — corre no Mac do Carlos.
Usa o IP residencial + endpoint web_profile_info (sem cookies). Roda pelas contas
em lotes para não bater no limite, junta os posts recentes em ig_cache.json e
faz push para o repo. O scan.py (cloud) lê o ig_cache.json e mostra no painel.
Só stdlib."""
import json, os, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "ig_cache.json")
POS = os.path.join(ROOT, "ig_pos.txt")
HANDLES = os.path.join(ROOT, "ig_handles.txt")

LOTE = 8             # contas por corrida (gentil, para não aquecer o IP)
ESPACO = 6.0        # segundos entre contas
RETRIES = 1          # 1 tentativa extra em falha intermitente
JANELA_H = 72        # manter posts das últimas 72h na cache
UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148")
HDRS = {"x-ig-app-id": "936619743392459", "User-Agent": UA}


def carrega_handles():
    hs, vistos = [], set()
    for ln in open(HANDLES, encoding="utf-8"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and ln not in vistos:
            vistos.add(ln); hs.append(ln)
    return hs


def fetch_conta(user):
    url = ("https://i.instagram.com/api/v1/users/web_profile_info/?username="
           + urllib.parse.quote(user))
    for _ in range(1 + RETRIES):
        try:
            req = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(req, timeout=15) as r:
                d = json.loads(r.read())
            u = d["data"]["user"]
            return u["edge_owner_to_timeline_media"]["edges"]
        except Exception:
            time.sleep(2.5)
    return None


def posts_recentes(user, edges, corte):
    """Devolve itens no MESMO formato que o scan.py lê da cache:
    title / source / link / when(iso). code fica para deduplicação."""
    out = []
    for e in edges or []:
        n = e["node"]
        ts = n.get("taken_at_timestamp")
        if not ts:
            continue
        w = datetime.fromtimestamp(ts, tz=timezone.utc)
        if w < corte:
            continue
        caps = n.get("edge_media_to_caption", {}).get("edges", [])
        cap = (caps[0]["node"]["text"] if caps else "").replace("\n", " ").strip()
        if not cap:
            continue
        code = n.get("shortcode", "")
        out.append({
            "code": code,
            "title": cap[:120],
            "source": "IG · @" + user,
            "link": f"https://www.instagram.com/p/{code}/" if code
                    else f"https://www.instagram.com/{user}/",
            "when": w.isoformat(),
        })
    return out


def main():
    handles = carrega_handles()
    try:
        pos = int(open(POS).read().strip())
    except Exception:
        pos = 0
    pos %= len(handles)
    lote = [handles[(pos + i) % len(handles)] for i in range(min(LOTE, len(handles)))]

    agora = datetime.now(timezone.utc)
    corte = agora - timedelta(hours=JANELA_H)

    # cache existente (dict por code; ignora itens antigos sem code)
    cache = {}
    try:
        for p in json.load(open(CACHE, encoding="utf-8")):
            c = p.get("code") or p.get("link", "")
            if c:
                cache[c] = p
    except Exception:
        pass

    ok = fail = novos = 0
    for user in lote:
        edges = fetch_conta(user)
        if edges is None:
            fail += 1
        else:
            ok += 1
            for p in posts_recentes(user, edges, corte):
                key = p.get("code") or p["link"]
                if key not in cache:
                    novos += 1
                cache[key] = p
        time.sleep(ESPACO)

    # podar > janela e gravar
    vivos = [p for p in cache.values()
             if datetime.fromisoformat(p["when"]) >= corte]
    vivos.sort(key=lambda x: x["when"], reverse=True)
    json.dump(vivos, open(CACHE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)

    nova_pos = (pos + len(lote)) % len(handles)
    open(POS, "w").write(str(nova_pos))
    print(f"IG local: lote {pos}->{nova_pos} · {ok} OK / {fail} falha · "
          f"+{novos} novos · cache {len(vivos)} posts")


if __name__ == "__main__":
    main()
