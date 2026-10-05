"""Расшифровка записи — локально, на этом компьютере. Ничего никуда не уезжает.

Вход:  любая запись — голосовое, диктофон, созвон, видео, запись экрана
       (mp3, m4a, wav, ogg, mp4, mov, mkv…).
Выход: ingest/<имя>-расшифровка.md  — текст по абзацам, читаемый человеком
       ingest/<имя>-расшифровка.json — те же куски с таймкодами (нужны для скринкаста)

Запуск:
    .venv/bin/python scripts/transcribe.py input/запись.m4a
    .venv/bin/python scripts/transcribe.py input/экран.mov --модель large-v3
    .venv/bin/python scripts/transcribe.py --модели        # что вообще бывает

Первый запуск качает модель распознавания (средняя — около 1,5 ГБ). Это разово: дальше она
лежит на компьютере и используется мгновенно.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST = ROOT / "ingest"

МОДЕЛИ = {
    "small": "полегче и быстрее, ~0,5 ГБ — годится для чистой записи с петличкой",
    "medium": "средняя, ~1,5 ГБ — по умолчанию: хорошо слышит обычную речь",
    "large-v3": "самая сильная, ~3 ГБ — слышит заметно точнее, но качается дольше и думает медленнее",
}
ПО_УМОЛЧАНИЮ = "medium"


def стоп(текст):
    print("\n⛔ " + текст + "\n")
    sys.exit(1)


def склеить_в_абзацы(куски, пауза=1.2, макс_знаков=700):
    """Собрать куски в человеческие абзацы: рвём по заметной паузе или по длине."""
    абзацы, текущий, прошлый_конец = [], [], None
    for к in куски:
        if текущий and (
            (прошлый_конец is not None and к["start"] - прошлый_конец > пауза)
            or sum(len(t) for t in текущий) > макс_знаков
        ):
            абзацы.append(" ".join(текущий).strip())
            текущий = []
        текущий.append(к["text"].strip())
        прошлый_конец = к["end"]
    if текущий:
        абзацы.append(" ".join(текущий).strip())
    return [а for а in абзацы if а]


def таймкод(секунды):
    м, с = divmod(int(секунды), 60)
    ч, м = divmod(м, 60)
    return f"{ч}:{м:02d}:{с:02d}" if ч else f"{м}:{с:02d}"


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("файл", nargs="?", help="запись: аудио или видео")
    ap.add_argument("--модель", default=ПО_УМОЛЧАНИЮ, choices=list(МОДЕЛИ))
    ap.add_argument("--язык", default="ru")
    ap.add_argument("--модели", action="store_true", help="показать список моделей и выйти")
    args = ap.parse_args()

    if args.модели:
        print("Модели распознавания:")
        for имя, описание in МОДЕЛИ.items():
            метка = "  ← по умолчанию" if имя == ПО_УМОЛЧАНИЮ else ""
            print(f"  {имя:9} — {описание}{метка}")
        print("\nПереключить: --модель large-v3 (или просто скажите системе словами).")
        return

    if not args.файл:
        стоп("Не сказано, что расшифровывать. Пример: scripts/transcribe.py input/запись.m4a")

    источник = Path(args.файл).expanduser()
    if not источник.exists():
        стоп(f"Файла «{источник}» нет. Проверьте имя — и что запись лежит в папке input/.")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        стоп(
            "Не установлен распознаватель речи. Один раз выполните:\n"
            "   bash scripts/setup.sh\n"
            "   (или .venv/bin/pip install faster-whisper)"
        )

    print(f"→ модель «{args.модель}» ({МОДЕЛИ[args.модель]})")
    print("  первый запуск качает её на компьютер — дальше будет быстро")
    модель = WhisperModel(args.модель, device="cpu", compute_type="int8")

    print(f"→ слушаю запись: {источник.name}")
    куски_ген, инфо = модель.transcribe(
        str(источник),
        language=args.язык,
        vad_filter=True,                                   # режем по тишине, а не вслепую
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
    )
    куски = [
        {"start": к.start, "end": к.end, "text": к.text.strip()}
        for к in куски_ген
        if к.text and к.text.strip()
    ]
    if not куски:
        стоп(
            "В записи не нашлось речи. Бывает, если дорожка пустая или очень тихая.\n"
            "   Проверьте, слышно ли что-нибудь, если просто открыть файл."
        )

    имя = re.sub(r"[^\w\-.]+", "-", источник.stem, flags=re.UNICODE).strip("-")
    INGEST.mkdir(exist_ok=True)
    json_путь = INGEST / f"{имя}-расшифровка.json"
    md_путь = INGEST / f"{имя}-расшифровка.md"

    json_путь.write_text(
        json.dumps(
            {"файл": источник.name, "длительность": getattr(инфо, "duration", None), "куски": куски},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    абзацы = склеить_в_абзацы(куски)
    шапка = [
        f"# Расшифровка: {источник.name}",
        "",
        f"> Расшифровано локально, модель «{args.модель}». Длительность записи — "
        f"{таймкод(getattr(инфо, 'duration', 0) or куски[-1]['end'])}.",
        "> Это сырьё, а не документ: тут есть оговорки и повторы. Дальше система приведёт его в порядок.",
        "",
    ]
    md_путь.write_text("\n".join(шапка + [а + "\n" for а in абзацы]), encoding="utf-8")

    слов = sum(len(а.split()) for а in абзацы)
    print(f"\n✅ Готово. Слов: {слов}, кусков: {len(куски)}, абзацев: {len(абзацы)}")
    print(f"   Текст:    {md_путь.relative_to(ROOT)}")
    print(f"   С таймкодами: {json_путь.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
