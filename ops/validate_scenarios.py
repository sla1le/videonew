from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "## Паспорт",
    "## Конфликт",
    "## Правила",
    "## Кадры",
    "## Фактчек",
    "## Ассеты",
    "## Вердикт",
    "## CTA",
    "## Запреты",
    "## Критерий отмены",
]


def main() -> int:
    files = sorted((ROOT / "content").glob("20??-??-??/*/scenario.md"))
    errors = []
    if not files:
        errors.append("content: не найден ни один сценарий")

    for path in files:
        text = path.read_text(encoding="utf-8")
        missing = [heading for heading in REQUIRED if heading not in text]
        if missing:
            errors.append(f"{path.relative_to(ROOT)}: пропущено {', '.join(missing)}")
        if "claim_id" not in text:
            errors.append(f"{path.relative_to(ROOT)}: нет claim_id")
        if "asset_id" not in text:
            errors.append(f"{path.relative_to(ROOT)}: нет asset_id")
        if "\u2014" in text:
            errors.append(f"{path.relative_to(ROOT)}: найдено длинное тире")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"Сценарии: {len(files)}. Структура корректна.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
