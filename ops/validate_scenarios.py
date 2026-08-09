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
    "## Карточки участников",
    "## Вердикт",
    "## CTA",
    "## Запреты",
    "## Критерий отмены",
]
CARD_ENGINES = {"rating/echorate.py", "rating/season.py", "rating/prime.py"}


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
        card_section = text.split("## Карточки участников", 1)
        if len(card_section) == 2:
            card_section = card_section[1].split("## Вердикт", 1)[0]
            fields = {}
            for line in card_section.splitlines():
                line = line.strip()
                if line.startswith("- card_") and ":" in line:
                    key, value = line[2:].split(":", 1)
                    fields[key.strip()] = value.strip()
            for key in ("card_engine", "card_holders", "card_frames"):
                if not fields.get(key):
                    errors.append(f"{path.relative_to(ROOT)}: нет {key} в контракте карт")
            engine = fields.get("card_engine")
            if engine and engine not in CARD_ENGINES:
                errors.append(f"{path.relative_to(ROOT)}: неизвестный card_engine {engine}")
            if "golden-ball" in path.as_posix():
                lower = card_section.lower()
                if "золот" not in lower or "мини-карт" not in lower:
                    errors.append(f"{path.relative_to(ROOT)}: ЗМ требует золотую карту и мини-карты")
        if "\u2014" in text:
            errors.append(f"{path.relative_to(ROOT)}: найдено длинное тире")

    if errors:
        print("\n".join(errors))
        return 1
    print(f"Сценарии: {len(files)}. Структура корректна.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
