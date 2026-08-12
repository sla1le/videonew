---
name: echorate
description: Сборка выпусков для TikTok-канала ЭХО. Русские рэперы в виде футбольных карточек: расчёт рейтинга по формулам, вёрстка кадров на HTML и CSS, рендер в PNG через headless Chromium.
---

# ECHORATE

## Когда грузить это

Любая задача про канал ЭХО, карточки артистов, рейтинги, золотой мяч, дуэли, деки под вертикальное видео 3:4.

## Быстрый старт

```bash
make doctor              # проверить среду: python, node, chromium, magick, vale
make setup               # поставить зависимости и браузер
make check               # все обязательные проверки репозитория
make prose               # расширенная проверка текста
make render DECK=tm2004  # собрать и отрендерить деку
make desc                # линтер описаний
```

Новая тема начинается с копии заготовки:

```bash
cp build/decks/_template.json build/decks/тема.json
make render DECK=тема
```

Если make недоступен, те же шаги руками:

```bash
python3 build/gen.py build/decks/тема.json
node build/render.js build/html/тема.html build/out/тема
python3 build/lint.py build/html/тема.html build/theme.css
python3 build/qa.py build/out/тема build/html/тема.html build/theme.css
python3 ops/slop.py build/decks/тема.json build/decks/тема.desc.txt
python3 ops/neuroslop.py build/decks/тема.json build/decks/тема.desc.txt
python3 ops/desclint.py build/decks/тема.desc.txt
```

Проверка кода счётчика и аналитики:

```bash
python3 rating/test_rating.py
python3 analytics/report.py --check
```

## Порядок работы

1. Прочитать `AGENTS.md`. Это точка входа: команды, конвейер, схема деки. Сразу за ним `prompts/master-prompt.md`, там правила проекта целиком.
2. Посмотреть `ops/analytics.md` и `ops/top10-videos.md`. Свежий счёт печатает `analytics/report.py`.
3. Проверить по `formats/formats.md`, кто уже был героем, какой механизм ещё не использовался и какая у выпуска цель.
4. Собрать данные и сразу записать источники в `ops/factcheck.md`.
5. Выставить оценки. ТЕКСТЫ, ЗВУК и ПОДАЧА ставятся руками. ХИТЫ, ЛАЙВЫ и ВЛИЯНИЕ считает движок из `rating/`.
6. Сверить результат с `ops/corrections.md`. Зафиксированные значения БЫЛО не меняются тихо.
7. Написать тексты по `prompts/style-rules.md`, затем прогнать `make prose`. Агент исправляет только отмеченные фрагменты.
8. Драматургию взять из `prompts/deck-logic.md`. Для графиков и схем читать `prompts/visual-system.md` вместе с `prompts/design-rules.md`.
9. Сверстать и отрендерить по `build/README.md`.
10. Прогнать `make check` и `make render`, потом посмотреть контактку глазами.
11. Пройти `ops/checklist.md` целиком перед выдачей.
12. Отдать PNG, описание по `ops/description.md` и отчёт по цифрам. Хештегов ноль или один.

## Какой движок для какой задачи

| Задача | Файл |
|---|---|
| Лиговая карточка на сегодня | `rating/core.py`, обёртка `rating/calc_single.py` |
| Артист без концертов | `rating/live.py` |
| Итог одного года | `rating/season.py` |
| Пиковый год артиста | `rating/prime.py` |
| Подбор пары для дуэли | `rating/matchup.py` |
| Турнир альбомов | `rating/worldcup.py` |
| Спецформаты и награды | `rating/formats.py` |
| Сводка по каналу | `analytics/report.py` |
| Точный стоп-лист текста | `ops/slop.py` |
| Структурный антислоп | `ops/neuroslop.py` |
| Проверка русского | `ops/languagetool.py` |

Веса, пороги и правила лежат в `rating/data/model.json`. Версия модели 4.1.

## Текстовый фильтр

Основной порядок:

```text
черновик
-> slop.py
-> neuroslop.py
-> точечная правка
-> LanguageTool при наличии
-> финальный текст
```

`ops/slop.py` блокирует точные запрещённые фразы. `ops/neuroslop.py` считает редакционный `neuroslop_score` от 0 до 100 и ловит ритм, повторы, шаблонные контрасты, избыток двоеточий и абстрактные финалы. Порог CI равен 65.

Vale подключён через `.vale.ini` и `styles/ECHO/`. Он удобен в редакторе, но обязательная CI-сборка от установленного Vale не зависит.

LanguageTool работает через локальный HTTP-сервер. Обвязка лежит в `ops/languagetool.py`. Автоматические исправления текста запрещены.

Полное описание в `ops/text-tools.md`.

## Визуальная система

Базовая геометрия и шрифты лежат в `prompts/design-rules.md`. Графики, схемы и сложные сравнения дополнительно подчиняются `prompts/visual-system.md`.

Ключевые правила:

- внутренние SVG-примитивы строятся на сетке 4 px;
- на кадре максимум два фокусных элемента;
- один цветовой акцент имеет конкретный смысл;
- radar ECHORATE держит все шесть осей и максимум две серии;
- line, bar, timeline и quadrant имеют свои бюджеты сложности;
- тени, градиенты и неоновое свечение запрещены;
- схема используется только когда она быстрее текста или таблицы.

Источник цветов один: `build/theme.css`.

## Жёсткие границы

Эти вещи не обсуждаются и не обходятся.

- Длинное тире и эмодзи запрещены везде, включая ответы в чате.
- Схемы через отрицание запрещены. Полный список в `prompts/style-rules.md`.
- Стоп-лист машинных фраз гоняет `ops/slop.py`, структурный почерк гоняет `ops/neuroslop.py`.
- Каждая цифра на кадре имеет источник в данных. На сам кадр источник не выносится.
- Под каждым баллом на кадре стоит своя причина. Поле `why`, класс `.rsn`.
- Строка объёма оценки стоит в первых двух кадрах. Поле `scope`, класс `.sco`.
- Базовая длина шесть или семь кадров. Восьмой кадр требует отдельной функции.
- ЛАЙВЫ не выдумываются. Нет концертов, ось выбрасывается по правилу `live_blocked`.
- Каждый выпуск приносит новый механизм.
- Перед выдачей каждый кадр просматривается глазами.

## Карта файлов

| Путь | Когда читать |
|---|---|
| `AGENTS.md` | всегда, первым |
| `prompts/master-prompt.md` | сразу вторым, правила проекта |
| `prompts/style-rules.md` | перед написанием текстов |
| `ops/text-tools.md` | когда чистишь машинный почерк и русский |
| `prompts/deck-logic.md` | перед сборкой деки |
| `prompts/design-rules.md` | перед вёрсткой |
| `prompts/visual-system.md` | перед графиком, схемой или сложным сравнением |
| `Makefile` | когда нужна команда |
| `README.md` | когда нужен общий обзор репозитория |
| `CHANGELOG.md` | когда надо понять, что менялось |
| `rating/README.md` | перед любым расчётом |
| `rating/data/model.json` | когда нужны веса и пороги |
| `build/README.md` | перед сборкой и рендером |
| `build/svg.md` | когда нужны рукописные пометки |
| `formats/formats.md` | когда выбираешь формат выпуска |
| `formats/new-formats-2026.md` | когда нужен свежий механизм |
| `formats/worldcup-albums.md` | когда собираешь турнир альбомов |
| `formats/iceberg.md` | когда собираешь айсберг |
| `formats/card-spec.md` | когда верстаешь карточку артиста |
| `iceberg/schema.json` | когда собираешь айсберг |
| `analytics/report.py` | когда нужен свежий счёт по каналу |
| `analytics/posts.json` | когда нужны объединённые цифры выпусков |
| `analytics/snapshots/` | когда нужен исходный снимок конкретной записи |
| `ops/analytics.md` | когда решаешь, что снимать дальше |
| `ops/top10-videos.md` | когда нужен разбор своих удачных выпусков |
| `ops/checklist.md` | перед каждой выдачей |
| `ops/tiktok.md` | когда думаешь про охват и досмотр |
| `ops/audience.md` | когда думаешь про поведение зрителя |
| `ops/description.md` | когда пишешь описание под видео |
| `ops/publishing.md` | когда выкладываешь |
| `ops/corrections.md` | всегда перед выдачей |
| `ops/mistakes.md` | когда что-то сломалось |
| `ops/factcheck.md` | когда нужна цифра или дата |
| `ops/backlog.md` | когда нет задачи от автора |
| `ops/prompt-fixes-v4.md` | когда правишь сами промпты |
| `refs/README.md` | покадровый разбор эталонных выпусков |
| `refs/design-canon.md` | когда сомневаешься в графике |
| `refs/frames.csv` | когда нужен разбор эталона по кадрам |

Сборщики: `build/gen.py` для деки, `build/gen_card.py` для одиночной карточки, `build/gen_prime.py` для прайма, `build/gen_worldcup.py` для турнира альбомов, `build/gen_deck_example.py` как пример вызова. Рендер: `build/shot.js` и `build/render.js`, поиск браузера в `build/browser.js`, фото готовит `build/prep_img.py`.

Стили: `build/theme.css` общий, `build/deck.css`, `build/card.css`, `build/worldcup.css`.

Проверки лежат в `build/lint.py`, `build/qa.py`, `ops/desclint.py`, `ops/slop.py`, `ops/neuroslop.py`, `ops/selfcheck.py`, `ops/validate_data.py`, `rating/test_rating.py`, `refs/verify.py`. Руками их звать не нужно, они вызываются из `make check` и `make render`.

## Среда

Python 3 с PIL, Node 20 и выше с playwright. Chromium приезжает из playwright, поиск браузера живёт в `build/browser.js` и проверяется командой `make doctor`.

`magick` из ImageMagick опционален: он нужен для контактки и обработки фото, без него рендер деки проходит.

Vale и LanguageTool тоже опциональны. Встроенные `slop.py` и `neuroslop.py` остаются обязательными и работают на стандартной библиотеке Python.

Шрифты только с кириллицей: Arial, Arial Black, Impact, Georgia. Oswald, Bebas, Roboto, Montserrat, Inter, Nimbus Sans Narrow и Noto Sans недоступны.
