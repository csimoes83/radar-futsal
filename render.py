"""Geração do painel do Radar Futsal (cloud) — timeline + tabelas Por fonte + pesquisa/filtros.
Importado por scan.py. Recebe os itens já filtrados e o por_fonte agrupado."""
from datetime import timezone, timedelta

LX = timezone(timedelta(hours=1))  # Lisboa (verão)
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


# (nome do cartão, cor, tag, [fontes], [filtros])
CARDS = [
    ("Imprensa PT", "#c1112b", "🇵🇹 Jornais", ["zerozero", "Record"], ["pt", "jornais"]),
    ("Liga Placard", "#007d3c", "🇵🇹 M + F", ["Famalicão"], ["pt"]),
    ("Espanha · clubes", "#ffb300", "🇪🇸 Liga Prime",
     ["Palma Futsal", "ElPozo Murcia", "Movistar Inter", "Jimbee Cartagena",
      "Valdepeñas", "Osasuna Magna", "Peñíscola", "Santa Coloma"], ["es"]),
    ("Brasil · LNF", "#127a4b", "🇧🇷 Liga + clubes",
     ["LNF Brasil", "Magnus", "Pato Futsal"], ["br"]),
    ("Croácia", "#1e5fd6", "🇭🇷 CROfutsal", ["CROfutsal", "Futsal Dinamo"], ["mundo"]),
    ("Itália · Serie A", "#009246", "🇮🇹 Liga", ["Itália C5", "Meta Catania"], ["mundo"]),
    ("Confederações", "#8e44ad", "🌐 Continental", ["CONMEBOL", "OFC Oceânia"], ["mundo"]),
    ("𝕏 / Twitter", "#000000", "📱 contas-chave",
     ["X · Palma", "X · Magnus", "X · Jimbee", "X · Barça FS", "X · LNFS",
      "X · UEFA Futsal", "X · RFEF", "X · ElPozo", "X · Pato", "X · Alzira FS",
      "X · Fahey", "X · KSA Futsal"], ["social"]),
]


def render(itens, por_fonte, data, ok, nfeeds):
    # timeline (Novo, PT primeiro)
    tl = []
    for it in itens:
        w = it["when"].astimezone(LX)
        tag = ' · 🇵🇹 PARA TI' if it.get("prio") else ''
        tl.append(f'''    <div class="card" data-f="{'pt' if it.get('prio') else 'mundo'}">
      <div class="k">{w:%H:%M} · {esc(it["source"])}{tag}</div>
      <h3><a href="{esc(it["link"])}" target="_blank" rel="noopener">{esc(it["title"])}</a></h3>
      <p>{esc(it["source"])} · {w:%d/%m %H:%M}</p>
    </div>''')
    timeline = "\n".join(tl) if tl else '<div class="card"><h3>Sem novidades nas últimas 48h</h3></div>'

    # tabelas Por fonte
    src_cards = []
    for nome, cor, tag, fontes, filtros in CARDS:
        itens_c = []
        for f in fontes:
            itens_c += por_fonte.get(f, [])
        itens_c = sorted(itens_c, key=lambda x: x["when"], reverse=True)[:5]
        if not itens_c:
            continue
        lis = "\n".join(
            f'      <li><a href="{esc(i["link"])}" target="_blank" rel="noopener">'
            f'{esc(i["title"][:95])}</a> <span class="t">· {i["when"].astimezone(LX):%d/%m}</span></li>'
            for i in itens_c)
        dot = f'background:{cor}' + ('' if cor != '#000000' else ';border:1px solid var(--line)')
        src_cards.append(
            f'''  <div class="src" data-f="{','.join(filtros)}">
    <div class="src-head"><span class="dot" style="{dot}"></span>
      <span class="name">{esc(nome)}</span><span class="tag">{tag}</span></div>
    <ul>
{lis}
    </ul>
  </div>''')
    fontes_html = "\n".join(src_cards)

    return f'''<!DOCTYPE html>
<html lang="pt"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Radar Futsal — atualiza sozinho</title>
<style>
 :root{{--bg:#000;--panel:#111318;--ink:#eef1f6;--muted:#9aa3b2;--line:#23262e;--acc:#f26430;--chip:#181b22}}
 *{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;line-height:1.5}}
 .wrap{{max-width:1080px;margin:0 auto;padding:20px 20px 64px}}
 header{{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--line);padding-bottom:14px}}
 h1{{font-size:22px;margin:0}} .sub{{color:var(--muted);font-size:13px}}
 .stamp{{margin-left:auto;color:var(--muted);font-size:12px}} .stamp b{{color:var(--ink)}}
 .controls{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:14px}}
 .search{{flex:1 1 220px;padding:9px 14px;border-radius:10px;border:1px solid var(--line);background:var(--panel);color:var(--ink);font-size:14px;outline:none}}
 .chip{{padding:6px 12px;border-radius:20px;border:1px solid var(--line);background:var(--panel);color:var(--muted);font-size:12.5px;cursor:pointer}}
 .chip.active{{background:var(--acc);border-color:var(--acc);color:#fff}}
 .chip.refresh{{color:var(--acc);border-color:var(--acc);font-weight:700}}
 .chip.refresh:active{{transform:scale(.96)}}
 .sec{{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:26px 0 12px;font-weight:600}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}}
 .card{{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:16px}}
 .k{{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--acc)}}
 .card h3{{font-size:15px;margin:6px 0}} .card h3 a{{color:var(--ink);text-decoration:none}}
 .card h3 a:hover,.src li a:hover{{text-decoration:underline}} .card p{{margin:0;font-size:12px;color:var(--muted)}}
 .sources{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
 .src{{background:var(--panel);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
 .src-head{{padding:13px 16px;border-bottom:1px solid var(--line);display:flex;align-items:center;gap:10px}}
 .dot{{width:9px;height:9px;border-radius:50%}} .src-head .name{{font-weight:700;font-size:14.5px}}
 .src-head .tag{{margin-left:auto;font-size:11px;color:var(--muted);background:var(--chip);padding:3px 9px;border-radius:20px}}
 .src ul{{list-style:none;margin:0;padding:8px 0}} .src li{{padding:8px 16px;font-size:13.4px;border-bottom:1px solid var(--line)}}
 .src li:last-child{{border-bottom:0}} .src li a{{color:var(--acc);text-decoration:none}} .src li .t{{font-size:11px;color:var(--muted)}}
 .hidden{{display:none!important}}
 footer{{margin-top:34px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:16px}}
</style></head><body><div class="wrap">
<header>
 <h1>🏐 Radar Futsal</h1>
 <span class="sub">atualiza-se sozinho · sem PC ligado</span>
 <span class="stamp">Recolha de <b>{data}</b> (Lisboa) · {len(itens)} novidades · {ok}/{nfeeds} fontes</span>
</header>
<div class="controls">
 <input id="q" class="search" type="search" placeholder="🔍 Procurar clube, jogador, país…">
 <button id="refresh" class="chip refresh" title="Recarregar a recolha mais recente">↻ Atualizar</button>
 <button class="chip active" data-f="all">Tudo</button>
 <button class="chip" data-f="pt">🇵🇹 PT</button>
 <button class="chip" data-f="es">🇪🇸 ES</button>
 <button class="chip" data-f="br">🇧🇷 BR</button>
 <button class="chip" data-f="mundo">🌍 Mundo</button>
 <button class="chip" data-f="jornais">📰 Jornais</button>
 <button class="chip" data-f="social">𝕏 Redes</button>
</div>
<div class="sec">🆕 Novo · últimas 48h (o teu 🇵🇹 primeiro)</div>
<div class="grid" id="timeline">
{timeline}
</div>
<div class="sec">Por fonte</div>
<div class="sources" id="fontes">
{fontes_html}
</div>
<footer>Radar Futsal · gerado no GitHub Actions a partir de feeds oficiais. Omite o que já publicaste em zonatecnicafutsal.com / futsalportugal.com.</footer>
</div>
<script>
(function(){{
 var q=document.getElementById('q');
 function apply(){{
  var s=(q.value||'').toLowerCase().trim();
  var f=document.querySelector('.chip.active').dataset.f;
  document.querySelectorAll('#timeline .card').forEach(function(c){{
   var okF=(f==='all')||(c.dataset.f||'').indexOf(f)>=0||f==='mundo';
   var okS=!s||c.textContent.toLowerCase().indexOf(s)>=0;
   c.classList.toggle('hidden', !(okF&&okS));
  }});
  document.querySelectorAll('#fontes .src').forEach(function(c){{
   var okF=(f==='all')||(c.dataset.f||'').split(',').indexOf(f)>=0;
   var okS=!s||c.textContent.toLowerCase().indexOf(s)>=0;
   c.classList.toggle('hidden', !(okF&&okS));
  }});
 }}
 q.addEventListener('input',apply);
 var refresh=document.getElementById('refresh');
 refresh.addEventListener('click',function(){{
  refresh.textContent='↻ A atualizar…';
  location.reload(true);
 }});
 document.querySelectorAll('.chip').forEach(function(ch){{
  if(ch.id==='refresh')return;
  ch.addEventListener('click',function(){{
   document.querySelectorAll('.chip').forEach(function(x){{if(x.id!=='refresh')x.classList.remove('active')}});
   ch.classList.add('active');apply();}});}});
 // auto-atualiza a cada 5 min enquanto o painel estiver aberto
 setInterval(function(){{location.reload(true);}}, 5*60*1000);
}})();
</script>
</body></html>'''
