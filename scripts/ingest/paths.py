"""Имена файлов источника — под слаг работы.

Рядом может идти другая работа: если все складывают текст в один общий
`ingest/raw.txt`, вторая молча затирает первую. Поэтому каждая работа ведёт
свои файлы под коротким именем — слагом: `ingest/raw-<слаг>.txt`,
`ingest/normalized-<слаг>.md`.

Слаг передаётся аргументом `--слаг имя` (или `--slug imya`). Без него имена
остаются прежними — одиночная работа ничего не замечает.
"""


def вынуть_слаг(argv):
    """Достаёт --слаг/--slug из списка аргументов и возвращает (слаг, остальное)."""
    слаг = None
    остальное = []
    i = 0
    while i < len(argv):
        арг = argv[i]
        if арг in ("--слаг", "--slug"):
            if i + 1 >= len(argv):
                raise SystemExit("После --слаг нужно короткое имя работы, например: --слаг oplata")
            слаг = argv[i + 1].strip()
            i += 2
            continue
        if арг.startswith("--слаг=") or арг.startswith("--slug="):
            слаг = арг.split("=", 1)[1].strip()
            i += 1
            continue
        остальное.append(арг)
        i += 1
    return (слаг or None), остальное


def сырой(слаг=None):
    return f"ingest/raw-{слаг}.txt" if слаг else "ingest/raw.txt"


def нормализованный(слаг=None):
    return f"ingest/normalized-{слаг}.md" if слаг else "ingest/normalized.md"
