#!/bin/zsh
# 🏐 Radar Futsal — ligar à nuvem (GitHub). Duplo-clique. Faz-se UMA vez.
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")"

echo "🏐 RADAR FUTSAL · LIGAR À NUVEM"
echo "──────────────────────────────────────────"
echo "Vou ligar-te ao GitHub (abre o browser p/ entrares) e pôr o radar"
echo "a atualizar-se sozinho de 30/30 min, sem o teu Mac ligado."
echo ""

# 1) Login (abre o browser; escolhe HTTPS quando perguntar)
if ! gh auth status >/dev/null 2>&1; then
  echo "▶ Passo 1/4: iniciar sessão no GitHub…"
  gh auth login --hostname github.com --git-protocol https --web || { echo "❌ Login cancelado."; read "?Enter para fechar"; exit 1; }
fi
USER=$(gh api user --jq .login)
echo "✓ Ligado como: $USER"

# 2) Criar o repositório (público, para o site ser gratuito) e enviar tudo
echo "▶ Passo 2/4: criar o repositório radar-futsal…"
gh repo create radar-futsal --public --source=. --remote=origin --push || {
  echo "(repo talvez já exista — a tentar ligar e enviar)"
  git remote add origin "https://github.com/$USER/radar-futsal.git" 2>/dev/null
  git push -u origin main
}

# 3) Ligar o GitHub Pages (serve o index.html a partir da main)
echo "▶ Passo 3/4: ligar o site (GitHub Pages)…"
gh api -X POST "repos/$USER/radar-futsal/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 \
  || gh api -X PUT "repos/$USER/radar-futsal/pages" -f "source[branch]=main" -f "source[path]=/" >/dev/null 2>&1 \
  || echo "  (se falhar, ativa em Settings → Pages → Branch: main /root)"

# 4) Arrancar a primeira recolha na nuvem já
echo "▶ Passo 4/4: primeira recolha na nuvem…"
gh workflow run scan.yml >/dev/null 2>&1

echo ""
echo "──────────────────────────────────────────"
echo "✅ PRONTO! O teu radar vive agora aqui (dá ~1-2 min a aparecer):"
echo ""
echo "   https://$USER.github.io/radar-futsal/"
echo ""
echo "Atualiza-se sozinho de 30/30 min, mesmo com o Mac desligado."
echo "Podes pôr este link no futsalportugal.com ou nos favoritos do telemóvel."
echo "──────────────────────────────────────────"
read "?Enter para fechar esta janela"
