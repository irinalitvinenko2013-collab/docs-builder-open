#!/usr/bin/env bash
# Разовая установка окружения для агента-верстальщика PDF.
# Идемпотентно: можно запускать повторно. Создаёт .venv (изолированно),
# ставит зависимости, шрифты и Chromium. Запуск: bash scripts/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."

# 1. Выбрать базовый python со стабильными колёсами (3.10–3.13; системный 3.14 — без них)
pick_python() {
  for c in python3.12 python3.11 python3.13 python3.10 python python3; do
    command -v "$c" >/dev/null 2>&1 || continue
    ver=$("$c" -c 'import sys;print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null || echo 0)
    if [ "$ver" -ge 310 ] && [ "$ver" -lt 314 ]; then echo "$c"; return; fi
  done
  for c in python python3; do command -v "$c" >/dev/null 2>&1 && { echo "$c"; return; }; done
}

# 2. venv
# ⚠️ Windows кладёт python в .venv/Scripts/, а не в .venv/bin/ — а вся документация системы
# и все команды агентов написаны через .venv/bin/python (99 мест). Поэтому на Windows мы
# создаём .venv/bin/python как маленькую обёртку к .venv/Scripts/python.exe: один файл вместо
# правки всей документации, и одинаковая команда на обеих системах.
venv_python() {
  if [ -x .venv/bin/python ]; then echo .venv/bin/python
  elif [ -x .venv/Scripts/python.exe ]; then echo .venv/Scripts/python.exe
  elif [ -f .venv/Scripts/python.exe ]; then echo .venv/Scripts/python.exe
  fi
}

if [ -z "$(venv_python)" ]; then
  BASE=$(pick_python)
  if [ -z "${BASE:-}" ]; then
    echo "[setup] ❌ не нашёл Python. Поставьте Python 3.12 и запустите установку снова."
    exit 1
  fi
  echo "[setup] базовый python: $BASE ($($BASE --version 2>&1))"
  "$BASE" -m venv .venv
fi

REAL=$(venv_python)
if [ -z "${REAL:-}" ]; then
  echo "[setup] ❌ окружение создалось, но python в нём не найден (ни .venv/bin, ни .venv/Scripts)."
  exit 1
fi

# Мостик для Windows: .venv/bin/python → .venv/Scripts/python.exe
if [ ! -e .venv/bin/python ] && [ -e .venv/Scripts/python.exe ]; then
  echo "[setup] Windows: делаю .venv/bin/python мостиком к .venv/Scripts/python.exe"
  mkdir -p .venv/bin
  printf '#!/bin/sh\nexec "$(dirname "$0")/../Scripts/python.exe" "$@"\n' > .venv/bin/python
  chmod +x .venv/bin/python
fi

VPY=$(venv_python)
[ -x .venv/bin/python ] && VPY=.venv/bin/python

# 3. зависимости
echo "[setup] зависимости…"
"$VPY" -m pip install -q --upgrade pip
"$VPY" -m pip install -q playwright pillow pypdf trafilatura pdfplumber google-genai pymupdf
echo "[setup] распознавание речи (локальное)…"
"$VPY" -m pip install -q faster-whisper av

# 4. Chromium (в общий кэш, быстро если уже скачан)
# Установка изредка зависает намертво — например, когда Chromium уже в кэше, а команда всё
# равно ждёт сеть. Поэтому ограничиваем время и НЕ роняем установку: остальные шаги важнее,
# а браузер можно доставить отдельной командой. Найдено живым прогоном на Codex 22.08.2026.
echo "[setup] Chromium…"
CHROMIUM_TIMEOUT=${CHROMIUM_TIMEOUT:-600}
if command -v timeout >/dev/null 2>&1; then
  timeout "$CHROMIUM_TIMEOUT" "$VPY" -m playwright install chromium || CHROMIUM_FAILED=1
elif command -v gtimeout >/dev/null 2>&1; then
  gtimeout "$CHROMIUM_TIMEOUT" "$VPY" -m playwright install chromium || CHROMIUM_FAILED=1
else
  "$VPY" -m playwright install chromium || CHROMIUM_FAILED=1
fi
if [ "${CHROMIUM_FAILED:-0}" = "1" ]; then
  echo "[setup] ⚠️  браузер не доустановился (долго или нет сети) — остальное поставлю."
  echo "[setup]     Доставить потом: .venv/bin/python -m playwright install chromium"
fi

# 5. шрифты
echo "[setup] шрифты…"
mkdir -p assets/fonts
[ -f assets/fonts/Montserrat.ttf ] || curl -sL -o assets/fonts/Montserrat.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/montserrat/Montserrat%5Bwght%5D.ttf"
[ -f assets/fonts/OpenSans.ttf ]   || curl -sL -o assets/fonts/OpenSans.ttf   "https://raw.githubusercontent.com/google/fonts/main/ofl/opensans/OpenSans%5Bwdth,wght%5D.ttf"
[ -f assets/fonts/PTSans.ttf ]     || curl -sL -o assets/fonts/PTSans.ttf     "https://raw.githubusercontent.com/google/fonts/main/ofl/ptsans/PT_Sans-Web-Regular.ttf"
[ -f assets/fonts/Lora.ttf ]       || curl -sL -o assets/fonts/Lora.ttf       "https://raw.githubusercontent.com/google/fonts/main/ofl/lora/Lora%5Bwght%5D.ttf"
[ -f assets/fonts/Inter.ttf ]      || curl -sL -o assets/fonts/Inter.ttf      "https://raw.githubusercontent.com/google/fonts/main/ofl/inter/Inter%5Bopsz,wght%5D.ttf"
[ -f assets/fonts/PlayfairDisplay.ttf ] || curl -sL -o assets/fonts/PlayfairDisplay.ttf "https://raw.githubusercontent.com/google/fonts/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"

# 6. векторные библиотеки локально (рендер не зависит от сети)
echo "[setup] vendor (Chart.js, Mermaid)…"
mkdir -p assets/vendor assets/generated
[ -f assets/vendor/chart.min.js ]   || curl -sL -o assets/vendor/chart.min.js   "https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"
[ -f assets/vendor/mermaid.min.js ] || curl -sL -o assets/vendor/mermaid.min.js "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"

# 7. ключ Gemini (для AI-иллюстраций) — необязательно; нет ключа → векторный fallback
if [ -f .claude/settings.local.json ] && grep -q '"GEMINI_API_KEY": *"[^"]' .claude/settings.local.json 2>/dev/null; then
  echo "[setup] GEMINI_API_KEY найден в settings.local.json — AI-иллюстрации включены"
else
  echo "[setup] GEMINI_API_KEY не задан → AI-картинки пропускаются (впишите ключ в .claude/settings.local.json)"
fi

echo "[setup] Готово. Дальше: .venv/bin/python scripts/selftest.py — проверить, что всё работает"
echo "[setup] (python окружения: $VPY)"
