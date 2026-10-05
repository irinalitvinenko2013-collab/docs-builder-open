"""QA: сколько в PDF живых переходов — наружу и внутри документа.

Считаем отдельно:
  • наружу — /Link с /URI: сайт, почта, телеграм. Это то, ради чего документ
    вообще делают кликабельным;
  • внутри — переходы по документу (/GoTo или /Dest): оглавление, ссылки на
    разделы. Раньше они не считались вовсе, и рабочее оглавление показывало
    «ссылок: 0» — метрика пугала там, где всё было в порядке.

Использование: python scripts/check_links.py [output/output.pdf]
"""
import sys

from pypdf import PdfReader


def count_links(pdf_path):
    """→ (наружу, внутри документа)."""
    reader = PdfReader(pdf_path)
    наружу = внутри = 0
    for page in reader.pages:
        if "/Annots" not in page:
            continue
        for a in page["/Annots"]:
            obj = a.get_object()
            if obj.get("/Subtype") != "/Link":
                continue
            действие = obj.get("/A", {})
            try:
                действие = действие.get_object()
            except AttributeError:
                pass
            if действие.get("/URI"):
                наружу += 1
            elif действие.get("/S") == "/GoTo" or obj.get("/Dest") is not None:
                внутри += 1
    return наружу, внутри


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "output/output.pdf"
    наружу, внутри = count_links(path)
    print(f"Кликабельных ссылок: {наружу}" + (f" · переходов внутри документа: {внутри}" if внутри else ""))
    if наружу == 0 and внутри == 0:
        print("   Ни одной — проверьте, что ссылки стоят анкорами с полным https://,")
        print("   а пункты оглавления ведут на свои разделы (href=\"#sec-N\").")
