"""AI-иллюстрация через Gemini — адаптер для агента-верстальщика PDF.

Поток: pdf-builder пишет бренд-промпт (сцена + палитра + культурный код) и зовёт этот
скрипт. Скрипт обращается к Gemini, сохраняет фото в assets/generated/<slug>.jpg (JPEG, чтобы не
раздувать PDF), опционально применяет мягкий бренд-грейд (Pillow). Лимит ≤4/документ — на
стороне вызывающего.

ЖЁСТКИЕ ТРЕБОВАНИЯ (см. CLAUDE.md §4):
  • Только МАКСИМАЛЬНЫЙ ФОТОРЕАЛИЗМ — фотодиректива PHOTOREAL добавляется к КАЖДОМУ
    промпту автоматически, независимо от вызывающего (никаких рисунков/3D/мультфильма).
  • Только САМАЯ УМНАЯ доступная модель — по умолчанию `gemini-3-pro-image`
    (Gemini 3 Pro Image / «Nano Banana Pro»). Менять на более слабую модель нельзя.

Использование:
    .venv/bin/python scripts/illustrate.py "<промпт>" <slug> [aspect=16:9|4:3|1:1] [grade=soft|none]

Ключ: переменная окружения GEMINI_API_KEY (кладётся в .claude/settings.local.json, не в git).
Нет ключа / ошибка генерации → выход с кодом 2 и сообщением: вызывающий берёт векторную заглушку.
Модель можно переопределить через GEMINI_IMAGE_MODEL, но только на не менее умную/фотореалистичную.
"""
import hashlib
import os
import sys

OUT_DIR = "assets/generated"
# Самая умная доступная модель генерации изображений в Gemini (фотореализм + интеллект).
MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
IMAGE_SIZE = os.environ.get("GEMINI_IMAGE_SIZE", "2K")  # 1K|2K|4K для gemini-*-image
MAX_PX = int(os.environ.get("GEMINI_IMAGE_MAXPX", "1600"))  # кап длинной стороны: PDF не раздуть
NO_KEY_EXIT = 2  # сигнал вызывающему: ключа/генерации нет → векторный fallback

# Фотодиректива — добавляется в КОНЕЦ каждого промпта (последняя инструкция = самая сильная).
PHOTOREAL = (
    "СТИЛЬ — МАКСИМАЛЬНЫЙ ФОТОРЕАЛИЗМ: это настоящая фотография, снятая на полнокадровую "
    "зеркальную камеру, объектив 50mm f/1.8, естественное мягкое освещение, высокий "
    "динамический диапазон, живая текстура кожи и материалов, тонкие детали, резкий фокус, "
    "малая глубина резкости (боке), профессиональная редакционная фотосъёмка, 8K, без "
    "артефактов и искажений. Это НЕ иллюстрация, НЕ рисунок, НЕ 3D-рендер, НЕ мультяшный "
    "стиль, НЕ векторная графика."
)


def _process_and_save(img_bytes, path, grade):
    """Открыть → ужать до MAX_PX → опц. мягкий бренд-грейд → сохранить JPEG.
    JPEG обязателен: фото в PNG раздувает PDF в разы; Chromium встраивает JPEG как DCTDecode.
    Грейд очень мягкий (фотореализм в приоритете, НЕ дуотон)."""
    import io
    from PIL import Image, ImageEnhance
    im = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    if max(im.size) > MAX_PX:                 # ужать большую сторону до MAX_PX (PDF не раздуть)
        im.thumbnail((MAX_PX, MAX_PX), Image.LANCZOS)
    if grade == "soft":
        w, h = im.size
        navy, gold = (13, 27, 42), (200, 169, 126)
        grad = Image.new("RGB", (1, h))
        for y in range(h):
            t = y / max(h - 1, 1)
            grad.putpixel((0, y), tuple(int(navy[i] * (1 - t) + gold[i] * t) for i in range(3)))
        grad = grad.resize((w, h))
        im = Image.blend(im, grad, 0.07)        # 7% тонирование — реализм в приоритете
        im = ImageEnhance.Contrast(im).enhance(1.03)
        im = ImageEnhance.Color(im).enhance(1.04)
    im.save(path, "JPEG", quality=88, optimize=True, progressive=True)


def _via_gemini(client, prompt, aspect):
    """Gemini *-image (generate_content) — самый умный путь. Возвращает bytes."""
    from google.genai import types
    # пробуем от самого качественного конфига к более простому
    configs = [
        dict(response_modalities=["IMAGE"],
             image_config=types.ImageConfig(aspect_ratio=aspect, image_size=IMAGE_SIZE)),
        dict(response_modalities=["IMAGE"],
             image_config=types.ImageConfig(aspect_ratio=aspect)),
        dict(response_modalities=["TEXT", "IMAGE"],
             image_config=types.ImageConfig(aspect_ratio=aspect)),
    ]
    last = None
    for kw in configs:
        try:
            res = client.models.generate_content(
                model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(**kw),
            )
            for part in res.candidates[0].content.parts:
                data = getattr(part, "inline_data", None)
                if data and getattr(data, "data", None):
                    return data.data
            last = RuntimeError("в ответе нет inline-изображения")
        except Exception as e:  # неподдерживаемый параметр и т.п. — пробуем проще
            last = e
    raise last


def _via_imagen(client, prompt, aspect):
    """Imagen (generate_images/predict) — запасной путь, если выбрана imagen-*."""
    from google.genai import types
    res = client.models.generate_images(
        model=MODEL, prompt=prompt,
        config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio=aspect),
    )
    return res.generated_images[0].image.image_bytes


def _generate(prompt, aspect):
    """Возвращает bytes PNG/JPEG от Gemini. Бросает исключение при неудаче."""
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    full = f"{prompt}\n\n{PHOTOREAL}"
    if "imagen" in MODEL.lower():
        return _via_imagen(client, full, aspect)
    return _via_gemini(client, full, aspect)


def main(prompt, slug, aspect="16:9", grade="soft"):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{slug}.jpg")   # фото → JPEG (PDF лёгкий)
    sidecar = os.path.join(OUT_DIR, f"{slug}.prompt")
    # хэш учитывает модель и фотодирективу: смена модели/стиля инвалидирует кэш
    phash = hashlib.sha256((MODEL + PHOTOREAL + prompt + aspect).encode()).hexdigest()[:16]

    # кэш: та же картинка под тот же промпт+модель уже есть → не тратим деньги
    if os.path.exists(out) and os.path.exists(sidecar):
        if open(sidecar, encoding="utf-8").read().strip() == phash:
            print(f"CACHED {out}")
            return 0

    if not os.environ.get("GEMINI_API_KEY"):
        print("NO_KEY: GEMINI_API_KEY не задан — векторный fallback (PDF соберётся без AI-картинки).",
              file=sys.stderr)
        return NO_KEY_EXIT

    try:
        img = _generate(prompt, aspect)
    except Exception as e:  # ошибка сети/SDK/модели — не валим весь PDF
        print(f"GEN_FAIL ({MODEL}): {type(e).__name__}: {e} — векторный fallback.", file=sys.stderr)
        return NO_KEY_EXIT

    try:
        _process_and_save(img, out, grade)
    except Exception as e:
        print(f"SAVE_FAIL: {type(e).__name__}: {e} — векторный fallback.", file=sys.stderr)
        return NO_KEY_EXIT
    with open(sidecar, "w", encoding="utf-8") as f:
        f.write(phash)
    print(f"OK {out}  [{MODEL}]")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit('Использование: illustrate.py "<промпт>" <slug> [aspect] [grade]')
    args = sys.argv[1:]
    sys.exit(main(*args))
