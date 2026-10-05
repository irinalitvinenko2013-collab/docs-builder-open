"""Рендер guide.html -> output/output.pdf через Playwright (Chromium).

print_background=True ОБЯЗАТЕЛЕН — иначе пропадут фоны и градиенты.

Использование: render.py [src.html] [out.pdf] — по умолчанию guide.html -> output/output.pdf.
"""
import os
import sys
from playwright.sync_api import sync_playwright

SRC = sys.argv[1] if len(sys.argv) > 1 else "guide.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "output/output.pdf"


def main():
    был_раньше = os.path.exists(OUT)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    url = "file://" + os.path.abspath(SRC)
    with sync_playwright() as p:
        # Обычный запуск браузера. В некоторых песочницах (например, когда систему ведёт
        # Codex на macOS) дочерние процессы Chromium не могут зарегистрироваться в системе
        # и запуск падает. Тогда повторяем в однопроцессном режиме: медленнее, но работает.
        # Найдено живым прогоном на Codex 22.08.2026.
        try:
            browser = p.chromium.launch()
        except Exception as ошибка:
            print(f"[render] обычный запуск браузера не удался ({type(ошибка).__name__}),"
                  " пробую однопроцессный режим — так бывает под песочницей")
            browser = p.chromium.launch(args=["--single-process"])
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        # дождаться графиков/схем, если они есть (флаг ставит guide.html); иначе быстрый тайм-аут
        try:
            page.wait_for_function("window.__chartsReady === true", timeout=5000)
        except Exception:
            pass
        # перерисовать графики Chart.js фирменными шрифтами после загрузки @font-face
        # (canvas рисуется в момент new Chart() — до готовности шрифтов получается fallback)
        page.evaluate(
            """async () => {
              await document.fonts.ready;
              if (window.Chart) {
                if (Chart.defaults && Chart.defaults.font)
                  Chart.defaults.font.family = "'Open Sans','Montserrat',sans-serif";
                document.querySelectorAll('canvas').forEach((cv) => {
                  const ch = Chart.getChart ? Chart.getChart(cv) : null;
                  if (ch) {
                    if (ch.options && ch.options.font) ch.options.font.family = "'Open Sans',sans-serif";
                    ch.update('none');
                  }
                });
              }
            }"""
        )
        page.wait_for_timeout(800)  # дать дорисоваться шрифтам/градиентам
        page.pdf(
            path=OUT,
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()
    print(f"PDF готов: {OUT}")
    if был_раньше:
        print(
            "↻ Файл перезаписан. Если он открыт во вкладке VS Code, там останется "
            "СТАРАЯ картинка:\n  встроенный просмотр PDF читает файл один раз. "
            "Обновить: Ctrl+Shift+P → Developer: Reload Window."
        )


if __name__ == "__main__":
    main()
