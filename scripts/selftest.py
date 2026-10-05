"""Самопроверка системы: всё ли на месте и собирается ли PDF.

Собирает крошечный пробный документ в цветах активного профиля и рендерит его в
output/самопроверка.pdf. Если этот файл получился — значит работает всё: окружение,
шрифты, тема из профиля, браузер, рендер и подсчёт ссылок.

Запуск:  .venv/bin/python scripts/selftest.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
ПРОБНИК = ROOT / "самопроверка.html"
ТЕМА = ROOT / "context" / "theme.css"
PDF = ROOT / "output" / "самопроверка.pdf"

СТРАНИЦА = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="UTF-8">
<link rel="stylesheet" href="context/theme.css">
<style>
*{box-sizing:border-box;margin:0;padding:0;}
@page{size:A4;margin:0;}
body{font-family:var(--font-body);font-size:10.5pt;line-height:1.55;}
.page{width:210mm;height:297mm;position:relative;overflow:hidden;display:flex;flex-direction:column;}
.page + .page{page-break-before:always;}
.light{background:linear-gradient(155deg,var(--warm-white),var(--cream));color:var(--ink);}
.dark{background:linear-gradient(155deg,var(--navy),var(--graphite));color:var(--warm-white);}
.pad{padding:20mm 18mm;flex:1;}
h1{font-family:var(--font-heading);font-weight:800;font-size:26pt;margin-bottom:10mm;}
.kicker{font-family:var(--font-heading);font-weight:700;font-size:9pt;letter-spacing:.18em;
  text-transform:uppercase;color:var(--gold);margin-bottom:6mm;}
.light em{color:var(--burgundy);font-style:normal;}
.dark em{color:var(--gold);font-style:normal;}
a{color:var(--burgundy);}
.swatch{display:flex;gap:4mm;flex-wrap:wrap;margin-top:8mm;}
.swatch div{width:26mm;height:16mm;border-radius:3mm;border:1px solid rgba(var(--ink-rgb),.15);
  font-size:7.5pt;display:flex;align-items:flex-end;padding:2mm;color:#fff;}
</style></head><body>
<section class="page light"><div class="pad">
  <div class="kicker">Самопроверка</div>
  <h1>Система <em>работает</em></h1>
  <p>Если вы видите этот файл — собрано всё: окружение, шрифты, цвета профиля, браузер и рендер.</p>
  <p style="margin-top:6mm;">Заголовки набраны шрифтом заголовков из профиля, текст — шрифтом текста.
  Кликабельная ссылка для проверки: <a href="https://example.com">пример ссылки</a>.</p>
  <div class="swatch">
    <div style="background:var(--navy)">тёмный 1</div>
    <div style="background:var(--graphite)">тёмный 2</div>
    <div style="background:var(--burgundy)">акцент</div>
    <div style="background:var(--red-mid)">акцент средний</div>
    <div style="background:var(--gold)">тёплый</div>
    <div style="background:var(--ink)">текст</div>
  </div>
</div></section>
<section class="page dark"><div class="pad">
  <div class="kicker">Тёмная страница</div>
  <h1>И <em>тёмная</em> тоже</h1>
  <p style="color:var(--gold-soft);">Градиент, акцентное слово и подписи — в цветах вашего профиля.</p>
</div></section>
</body></html>
"""


def шаг(описание, команда):
    print(f"→ {описание}")
    готово = subprocess.run(команда, cwd=ROOT, capture_output=True, text=True)
    if готово.returncode != 0:
        print(готово.stdout.strip())
        print(готово.stderr.strip())
        print(f"\n⛔ Не прошло: {описание}")
        print("   Что делать — в файле ЕСЛИ-СЛОМАЛОСЬ.md. Или скажите системе:")
        print("   «самопроверка не проходит, вот что она пишет» — и вставьте эти строки.\n")
        sys.exit(1)
    return готово.stdout.strip()


def проверить_шрифты():
    """Дойдут ли шрифты профиля до документа.

    Тихая поломка: путь в теме битый, браузер молча печатает системным шрифтом —
    ни ошибки, ни предупреждения, а документ выходит чужим. Пути в theme.css
    считаются ОТ САМОГО ФАЙЛА (он лежит в context/), так и проверяем.
    """
    if not ТЕМА.exists():
        return
    пропали = []
    for адрес in re.findall(r"url\(['\"]?([^'\")]+)['\"]?\)", ТЕМА.read_text(encoding="utf-8")):
        if адрес.startswith(("http://", "https://", "data:")):
            continue
        if not (ТЕМА.parent / адрес).resolve().exists():
            пропали.append(адрес)
    if пропали:
        print("\n⛔ Шрифты профиля не доедут до документа — вот эти файлы не находятся:")
        for адрес in пропали:
            print(f"   {адрес}  (ищется от папки context/)")
        print("   Документ собрался бы, но чужим шрифтом и молча. Скажите системе:")
        print("   «шрифты из профиля не находятся» — и покажите эти строки.\n")
        sys.exit(1)


def проверить_сшивку_шагов():
    """Кадр шага обязан принадлежать тому экрану, о котором говорит подпись.

    Проверка на выдуманном примере, без видео: человек говорит «открываем настройки»
    пять секунд, на шестой экран сменился. Кадр должен остаться на первом экране —
    иначе в инструкции подпись будет про одно, а картинка про следующее окно.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from screencast_steps import моменты_по_речи
    except ImportError:
        return
    куски = [{"start": 0.0, "end": 5.8, "text": "Открываем настройки и нажимаем изменить"}]
    моменты = моменты_по_речи(куски, длительность=16.0, смены=[6.0, 12.0])
    if not моменты or моменты[0]["время"] >= 6.0:
        print("\n⛔ Кадры для пошаговых инструкций встают не к своим шагам.")
        print("   Подпись будет про один экран, а картинка — про следующий.")
        print("   Покажите системе эти строки: сломана привязка в scripts/screencast_steps.py\n")
        sys.exit(1)


def main():
    if not Path(PY).exists():
        print("⛔ Окружение не установлено. Запустите один раз: bash scripts/setup.sh")
        sys.exit(1)

    профили = [
        д for д in (ROOT / "профили").iterdir()
        if д.is_dir() and not д.name.startswith("_") and (д / "profile.json").exists()
    ] if (ROOT / "профили").exists() else []
    if профили:
        шаг("собираю тему из профиля", [PY, "scripts/brand_build.py"])
    else:
        print("→ профиля ещё нет — проверяюсь на образце (это нормально до настройки)")
        шаг("собираю тему из образца", [PY, "scripts/brand_build.py", "_шаблон"])
    print("→ проверяю, что шрифты профиля на месте")
    проверить_шрифты()
    print("→ проверяю сшивку кадров с шагами инструкции")
    проверить_сшивку_шагов()
    ПРОБНИК.write_text(СТРАНИЦА, encoding="utf-8")
    шаг("рендерю пробный документ", [PY, "scripts/render.py", str(ПРОБНИК.name), str(PDF.relative_to(ROOT))])
    ссылки = шаг("считаю кликабельные ссылки", [PY, "scripts/check_links.py", str(PDF.relative_to(ROOT))])
    ПРОБНИК.unlink(missing_ok=True)

    print("\n✅ Всё работает.")
    print(f"   Пробный документ: {PDF.relative_to(ROOT)}")
    if ссылки:
        print(f"   Ссылки: {ссылки}")
    if not профили:
        print("   ⚠️  Пробник собран на образце: своего профиля ещё нет.")
        print("       Скажите «настрой профиль» — и документы пойдут в ваших цветах.")
    print("   Дальше: принесите системе текст, статью, запись или ссылку — и попросите документ.")


if __name__ == "__main__":
    main()
