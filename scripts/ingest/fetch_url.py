"""URL -> ingest/raw.txt (основной текст статьи).

Движок выкачки: **Firecrawl** (основной — тянет JS/SPA) с откатом на
**trafilatura**. Firecrawl используется, если его CLI есть в PATH, авторизован
и не отключён переменной `FIRECRAWL_DISABLE=1`. При любой осечке (нет сети /
авторизации / кредитов либо пустой результат) — молча откатываемся на
trafilatura. В логе печатается, какой движок сработал.

Использование: python scripts/ingest/fetch_url.py <URL> [--слаг имя]
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import trafilatura

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import вынуть_слаг, сырой  # noqa: E402

FIRECRAWL_TIMEOUT = 90  # сек — это сетевой вызов


def fetch_firecrawl(url):
    """Firecrawl scrape -> markdown, либо None при любой осечке.

    stdin закрыт: неавторизованный firecrawl не виснет на запросе логина,
    а сразу выходит с ненулевым кодом — это и есть сигнал к откату.
    """
    if shutil.which("firecrawl") is None:
        return None
    if os.environ.get("FIRECRAWL_DISABLE") == "1":
        return None

    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False)
    tmp.close()
    try:
        proc = subprocess.run(
            ["firecrawl", "scrape", url,
             "--only-main-content", "-f", "markdown", "-o", tmp.name],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=FIRECRAWL_TIMEOUT,
        )
        if proc.returncode != 0:
            return None
        with open(tmp.name, encoding="utf-8") as f:
            text = f.read().strip()
        return text or None
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def fetch_trafilatura(url):
    """trafilatura -> markdown, либо None."""
    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        return None
    return trafilatura.extract(
        downloaded,
        include_links=True,
        include_tables=True,
        output_format="markdown",
    ) or None


def main(url, слаг=None):
    os.makedirs("ingest", exist_ok=True)
    out = сырой(слаг)

    text = fetch_firecrawl(url)
    engine = "firecrawl"
    if not text:
        text = fetch_trafilatura(url)
        engine = "trafilatura"
    if not text:
        sys.exit(f"Не удалось извлечь основной текст со страницы: {url}")

    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Извлечено {len(text)} символов -> {out} (движок: {engine})")


if __name__ == "__main__":
    слаг, аргументы = вынуть_слаг(sys.argv[1:])
    if not аргументы:
        sys.exit("Укажите URL")
    main(аргументы[0], слаг)
