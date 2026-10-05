"""Сетка в долях поверх скриншота — чтобы точно снять координаты кнопки.

Зачем: рамки «куда жать» задаются долями (0..1) от размера картинки. На глаз промахиваешься
на 3–5 %, и рамка съезжает мимо мелкой кнопки. По сетке координата снимается точно.

Запуск:
    .venv/bin/python scripts/make_grid.py input/шаги/01.png
    .venv/bin/python scripts/make_grid.py input/шаги/01.png --шаг 0.02   # мельче сетка
    .venv/bin/python scripts/make_grid.py input/шаги/ --шаг 0.05         # всю папку

Выход: assets/сетка/<имя>.png — та же картинка с подписанной сеткой.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ВЫХОД = ROOT / "assets" / "сетка"


def шрифт(размер):
    for путь in (
        ROOT / "assets" / "fonts" / "Montserrat.ttf",
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ):
        if путь.exists():
            try:
                return ImageFont.truetype(str(путь), размер)
            except Exception:
                pass
    return ImageFont.load_default()


def нарисовать(источник, шаг):
    картинка = Image.open(источник).convert("RGB")
    W, H = картинка.size
    рисунок = ImageDraw.Draw(картинка, "RGBA")
    ф = шрифт(max(11, int(W * 0.009)))

    доля = 0.0
    while доля <= 1.0001:
        x = int(доля * W)
        y = int(доля * H)
        крупная = abs(доля * 10 - round(доля * 10)) < 1e-6      # каждые 0.1 — ярче
        цвет = (255, 0, 0, 190) if крупная else (0, 120, 255, 110)
        рисунок.line([(x, 0), (x, H)], fill=цвет, width=2 if крупная else 1)
        рисунок.line([(0, y), (W, y)], fill=цвет, width=2 if крупная else 1)
        if крупная:
            подпись = f"{доля:.1f}"
            рисунок.rectangle([x + 2, 2, x + 34, 20], fill=(255, 255, 255, 220))
            рисунок.text((x + 4, 3), подпись, fill=(200, 0, 0), font=ф)
            рисунок.rectangle([2, y + 2, 36, y + 20], fill=(255, 255, 255, 220))
            рисунок.text((4, y + 3), подпись, fill=(200, 0, 0), font=ф)
        доля += шаг

    ВЫХОД.mkdir(parents=True, exist_ok=True)
    путь = ВЫХОД / (источник.stem + ".png")
    картинка.save(путь)
    print(f"  ✓ {путь.relative_to(ROOT)}  ({W}×{H})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("путь", help="картинка или папка с картинками")
    ap.add_argument("--шаг", type=float, default=0.02, help="шаг сетки в долях (по умолчанию 0.02)")
    args = ap.parse_args()

    цель = Path(args.путь).expanduser()
    if not цель.exists():
        print(f"\n⛔ Нет такого пути: {цель}\n")
        sys.exit(1)

    картинки = (
        sorted(p for p in цель.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
        if цель.is_dir()
        else [цель]
    )
    if not картинки:
        print(f"\n⛔ В папке {цель} нет картинок.\n")
        sys.exit(1)

    print(f"→ рисую сетку с шагом {args.шаг} на {len(картинки)} картинк(ах)")
    for к in картинки:
        нарисовать(к, args.шаг)
    print(
        f"\n✅ Готово. Откройте файл из {ВЫХОД.relative_to(ROOT)}/ и считайте координаты кнопки:\n"
        "   лево, верх, право, низ — четыре числа от 0 до 1. Их и передайте в annotate_shots.py."
    )


if __name__ == "__main__":
    main()
