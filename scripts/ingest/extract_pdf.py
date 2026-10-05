"""Чужой PDF -> ingest/raw.txt (текст по страницам через pdfplumber).

Если извлекаемого текста почти нет — печатает предупреждение: презентация
картиночная, её должен прочитать субагент source-extractor визуально.

Использование: python scripts/ingest/extract_pdf.py <file.pdf> [--слаг имя]
"""
import os
import sys
from pathlib import Path

import pdfplumber

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import вынуть_слаг, сырой  # noqa: E402


def main(pdf_path, слаг=None):
    os.makedirs("ingest", exist_ok=True)
    out = сырой(слаг)
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            chunks.append(f"## Страница {i}\n\n{text}")
    full = "\n\n".join(chunks)
    with open(out, "w", encoding="utf-8") as f:
        f.write(full)

    stripped = full.replace("#", "").replace("Страница", "").strip()
    if len(stripped) < 200:
        print(
            "ВНИМАНИЕ: текста почти нет — презентация, видимо, картиночная. "
            "Субагент должен прочитать страницы PDF визуально."
        )
    print(f"Извлечено {len(full)} символов -> {out}")


if __name__ == "__main__":
    слаг, аргументы = вынуть_слаг(sys.argv[1:])
    if not аргументы:
        sys.exit("Укажите путь к PDF")
    main(аргументы[0], слаг)
