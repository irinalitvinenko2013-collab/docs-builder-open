"""ingest/raw.txt -> ingest/normalized.md (или те же имена со слагом работы).

Базовая нормализация: схлопывает лишние пустые строки и хвостовые пробелы.
Тонкую структуру (заголовки, списки, ссылки) досверяет субагент source-extractor.

Использование:
    python scripts/ingest/normalize.py                 # ingest/raw.txt -> ingest/normalized.md
    python scripts/ingest/normalize.py --слаг oplata   # raw-oplata.txt -> normalized-oplata.md
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import вынуть_слаг, нормализованный, сырой  # noqa: E402


def normalize(text):
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)   # хвостовые пробелы
    text = re.sub(r"\n{3,}", "\n\n", text)   # не больше одной пустой строки подряд
    return text.strip() + "\n"


def main(слаг=None):
    src = сырой(слаг)
    out = нормализованный(слаг)
    if not Path(src).exists():
        sys.exit(
            f"Нет файла {src} — сначала положите туда текст источника "
            "(fetch_url.py, extract_pdf.py или просто скопируйте текст)."
        )
    with open(src, encoding="utf-8") as f:
        raw = f.read()
    with open(out, "w", encoding="utf-8") as f:
        f.write(normalize(raw))
    print(f"Нормализовано -> {out}")


if __name__ == "__main__":
    слаг, _ = вынуть_слаг(sys.argv[1:])
    main(слаг)
