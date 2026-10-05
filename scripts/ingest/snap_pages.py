"""Снять кадры прямо со страниц сервиса — когда записи экрана нет, а скриншоты нужны.

Работает в два шага, и первый нужен только для закрытой зоны (личный кабинет).

  ── Публичные страницы: логин не нужен вообще ──────────────────────────────
  .venv/bin/python scripts/ingest/snap_pages.py \\
      "https://пример.рф/signup"  "страница регистрации" \\
      "https://пример.рф/pricing" "выбор тарифа"

  ── Закрытая зона: сначала входите ВЫ, руками ──────────────────────────────
  1) .venv/bin/python scripts/ingest/snap_pages.py --вход https://пример.рф
     Откроется обычное окно браузера. Войдите в свой аккаунт как всегда —
     пароль никуда не передаётся и нигде не сохраняется. Потом нажмите Enter.
  2) .venv/bin/python scripts/ingest/snap_pages.py --сессия \\
      "https://пример.рф/account" "личный кабинет"

  ── Пачкой по спеке (её удобно писать нейросети) ───────────────────────────
  .venv/bin/python scripts/ingest/snap_pages.py --спека ingest/страницы.json
  [{"адрес": "https://…", "имя": "страница регистрации", "ждать": 2,
    "скрыть": [".cookie-banner"], "вся_страница": false}]

Выход: input/шаги/NN-имя.png — оттуда их берёт обычная сборка документа.
Ключи: --сессия (ходить залогиненным) · --вся-страница · --ширина/--высота ·
       --ждать N (секунд на дозагрузку) · --скрыть "селектор" (баннеры кук и чаты).

🔒 Границы — прочитайте, это не формальность:
   • Логинитесь ВЫ, в видимом окне. Скрипт не спрашивает и не хранит паролей.
   • Снимайте только своё. Чужой личный кабинет — не ваш материал.
   • Кадры из закрытой зоны почти всегда содержат личное: имя, почту, суммы.
     Перед сдачей документа пройдитесь по ним и замажьте — annotate_shots.py.
   • Сессия лежит в output/браузер-профиль/ — это ключи от вашего аккаунта.
     Папка не уезжает на полку и её нельзя никому отдавать.
"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("\n⛔ Не установлен playwright. Выполните: .venv/bin/pip install playwright"
          " && .venv/bin/playwright install chromium\n")
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[2]
ВЫХОД = ROOT / "input" / "шаги"
ПРОФИЛЬ = ROOT / "output" / "браузер-профиль"


def стоп(текст):
    print("\n⛔ " + текст + "\n")
    sys.exit(1)


def нет_браузера(ошибка):
    """Установщик ставит Chromium мягко: не скачался — установка всё равно проходит.
    Значит сюда можно прийти без браузера, и человек должен увидеть, что делать,
    а не питоновскую ошибку."""
    текст = str(ошибка)
    if "Executable doesn" in текст or "playwright install" in текст:
        стоп("Не хватает браузера — без него снимать нечем.\n"
             "   Поставьте одной командой:\n"
             "   .venv/bin/python -m playwright install chromium")
    raise ошибка


def имя_файла(номер, подпись):
    чистое = re.sub(r"[^\w\s-]", "", подпись, flags=re.UNICODE).strip()
    чистое = re.sub(r"\s+", "-", чистое) or "кадр"
    return f"{номер:02d}-{чистое[:50]}.png"


def снять(страница, задача, номер):
    адрес = задача["адрес"]
    print(f"  → {адрес}")
    страница.goto(адрес, wait_until="domcontentloaded", timeout=60000)
    try:
        страница.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    страница.wait_for_timeout(int(float(задача.get("ждать", 1.5)) * 1000))

    for селектор in задача.get("скрыть", []):
        try:
            страница.eval_on_selector_all(
                селектор, "els => els.forEach(e => e.style.display='none')")
        except Exception:
            pass

    файл = ВЫХОД / имя_файла(номер, задача.get("имя") or f"кадр-{номер}")
    страница.screenshot(path=str(файл), full_page=bool(задача.get("вся_страница")))
    print(f"    ✓ {файл.relative_to(ROOT)}")
    return файл


def режим_входа(адрес, ширина, высота):
    ПРОФИЛЬ.mkdir(parents=True, exist_ok=True)
    print("\n>>> Открываю обычное окно браузера.")
    print(">>> Войдите в свой аккаунт как всегда — пароль остаётся между вами и сайтом.")
    print(">>> Когда войдёте, вернитесь сюда и нажмите Enter.\n")
    with sync_playwright() as pw:
        try:
            ctx = pw.chromium.launch_persistent_context(
                str(ПРОФИЛЬ), headless=False,
                viewport={"width": ширина, "height": высота}, device_scale_factor=2,
            )
        except Exception as e:
            нет_браузера(e)
        стр = ctx.pages[0] if ctx.pages else ctx.new_page()
        стр.goto(адрес, wait_until="domcontentloaded", timeout=60000)
        try:
            input()
        except EOFError:
            print(">>> Терминал без ввода — жду 3 минуты.")
            стр.wait_for_timeout(180000)
        ctx.close()
    print("\n✅ Вход сохранён в output/браузер-профиль/ — эта папка никуда не уезжает.")
    print("   Дальше снимайте с ключом --сессия.\n")


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("пары", nargs="*", help="адрес подпись адрес подпись …")
    ap.add_argument("--спека", help="JSON со списком страниц")
    ap.add_argument("--вход", help="открыть видимое окно и дождаться вашего входа")
    ap.add_argument("--сессия", action="store_true", help="ходить под сохранённым входом")
    ap.add_argument("--вся-страница", action="store_true", dest="вся")
    ap.add_argument("--ждать", type=float, default=1.5)
    ap.add_argument("--скрыть", action="append", default=[])
    ap.add_argument("--ширина", type=int, default=1440)
    ap.add_argument("--высота", type=int, default=900)
    a = ap.parse_args()

    if a.вход:
        return режим_входа(a.вход, a.ширина, a.высота)

    if a.спека:
        задачи = json.loads(Path(a.спека).read_text(encoding="utf-8"))
    else:
        if not a.пары or len(a.пары) % 2:
            стоп("Нужны пары «адрес подпись». Пример:\n   snap_pages.py "
                 '"https://пример.рф/signup" "страница регистрации"')
        задачи = [{"адрес": a.пары[i], "имя": a.пары[i + 1]}
                  for i in range(0, len(a.пары), 2)]

    for з in задачи:
        з.setdefault("ждать", a.ждать)
        з.setdefault("вся_страница", a.вся)
        з.setdefault("скрыть", a.скрыть)

    ВЫХОД.mkdir(parents=True, exist_ok=True)
    print(f"\n→ снимаю страниц: {len(задачи)}"
          + ("  (под вашим входом)" if a.сессия else "  (без входа)"))

    сняты = []
    with sync_playwright() as pw:
        try:
            if a.сессия:
                if not ПРОФИЛЬ.exists():
                    стоп("Сохранённого входа нет. Сначала:\n"
                         "   snap_pages.py --вход https://адрес-сервиса")
                ctx = pw.chromium.launch_persistent_context(
                    str(ПРОФИЛЬ), headless=True,
                    viewport={"width": a.ширина, "height": a.высота}, device_scale_factor=2)
                стр = ctx.pages[0] if ctx.pages else ctx.new_page()
                закрыть = ctx.close
            else:
                бр = pw.chromium.launch(headless=True)
                ctx = бр.new_context(viewport={"width": a.ширина, "height": a.высота},
                                     device_scale_factor=2)
                стр = ctx.new_page()
                закрыть = бр.close
        except SystemExit:
            raise
        except Exception as e:
            нет_браузера(e)

        for н, з in enumerate(задачи, 1):
            try:
                сняты.append(снять(стр, з, н))
            except Exception as e:
                print(f"    ⚠️ не вышло: {str(e).splitlines()[0][:120]}")
        закрыть()

    print(f"\n✅ Готово: {len(сняты)} из {len(задачи)} — в input/шаги/")
    print("   Пролистайте их глазами: если снимали залогиненным, там почти наверняка")
    print("   есть ваше имя, почта или суммы. Замазать — scripts/annotate_shots.py.\n")


if __name__ == "__main__":
    main()
