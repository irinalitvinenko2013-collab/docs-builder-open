"""Кроп фото под круглую рамку на странице «Об авторе».

Вход:  любое фото (по умолчанию — то, что указано в профиле как «фото_автора»).
Выход: assets/профиль/фото-круг.jpg (620×620).

Запуск:
    .venv/bin/python scripts/prep_photo.py                  # фото из активного профиля
    .venv/bin/python scripts/prep_photo.py путь/к/фото.jpg   # любое другое фото

Кроп берётся по центру верхней трети — там обычно лицо. Вышло не так — скажите системе
«подвинь кроп выше/ниже», она поправит два числа в вызове.
"""
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "assets" / "профиль" / "фото-круг.jpg"
РАЗМЕР = 620


def найти_фото():
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser()
    готовое = sorted((ROOT / "assets" / "профиль").glob("фото.*"))
    if готовое:
        return готовое[0]
    print(
        "⛔ Не нашла фото. Положите его в профиль (поле «фото_автора») и запеките профиль,\n"
        "   или укажите файл прямо: scripts/prep_photo.py путь/к/фото.jpg"
    )
    sys.exit(1)


def main():
    src = найти_фото()
    im = Image.open(src).convert("RGB")
    w, h = im.size
    сторона = min(w, h)
    cx = w // 2
    top = max(0, int(h * 0.06)) if h > w else (h - сторона) // 2
    top = min(top, h - сторона)
    crop = im.crop((cx - сторона // 2, top, cx - сторона // 2 + сторона, top + сторона))
    crop = crop.resize((РАЗМЕР, РАЗМЕР), Image.LANCZOS)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    crop.save(OUT, quality=90, optimize=True)
    print(f"Круглое фото готово: {OUT.relative_to(ROOT)}  (из {src.name})")


if __name__ == "__main__":
    main()
