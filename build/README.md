# Сборка

Кадры собираются HTML и CSS, потом снимаются headless Chromium в PNG. Данные хранятся отдельно от вёрстки.

## Требования

- Python 3.11 или новее
- Pillow
- Node.js и playwright
- Chromium, по умолчанию `/usr/local/bin/chromium`
- ImageMagick с командой `magick`

Шрифты с кириллицей: Arial, Arial Black, Impact, Georgia. Не использовать Oswald, Bebas, Roboto, Montserrat, Inter, Nimbus Sans Narrow, Noto Sans.

## Рабочий каталог выпуска

```text
work/
  gen_card.py
  gen_deck.py
  card.css
  deck.css
  photos/
  html/
  assets/
  out/
```

`build/gen_card.py` и `build/gen_deck_example.py` это стартовые шаблоны. Для нового выпуска копировать их в рабочий каталог и править там.

## Одна команда

```bash
bash build/run.sh /absolute/path/to/work gm_
```

Скрипт генерирует карточки, собирает деку, снимает PNG, прогоняет QA и делает `probe.png`.

## Ручная сборка

```bash
python3 gen_card.py
cp card.css html/
rm -rf html/photos
cp -r photos html/photos
rm -f assets/*.png
node /path/to/build/shot.js html/cards.html assets card_ .wrap 1080 1350

python3 gen_deck.py
cp deck.css html/
rm -rf html/photos html/assets
cp -r photos html/photos
cp -r assets html/assets
rm -f out/*.png
node /path/to/build/shot.js html/slides.html out gm_ .s 1080 1440

python3 /path/to/build/qa.py out html/slides.html deck.css
magick montage out/*.png -tile 7x1 -geometry 330x440+6+6 -background '#cccccc' probe.png
```

## Обязательный визуальный QA

После рендера открыть `probe.png` глазами. Автоматический чекер не увидит плохой кроп лица, слабую иерархию или одинаковую композицию соседних кадров.

Проверить:

1. лицо не отрезано;
2. текст читается с масштаба телефона;
3. на первом кадре есть фото и хук;
4. доминирующий элемент меняется;
5. нет случайной пустоты;
6. карточка занимает 70 до 85 процентов ширины;
7. ровно три рукописные пометки;
8. в дуэли счёт появляется после раскрытия обеих сторон.

## Частые поломки

`net::ERR_FILE_NOT_FOUND`: перед рендером удалить `html/photos` и `html/assets`, потом скопировать каталоги заново.

`BROKEN SHORTHANDS`: в CSS встретился `font:` без семейства. Использовать `font-size`, `line-height`, `font-weight`, `font-family` отдельно.

Большой вертикальный гэп: увеличить высоту фото или padding содержательного блока. Два `margin-top:auto` подряд почти всегда рвут кадр.

Кириллица сломалась после архивации: создавать zip через Python `zipfile`, при необходимости кодировать имя как `n.encode('cp437').decode('cp866')`.

Chromium пишет `Floss manager not present`: это шум stderr, рендер обычно успешен. Можно фильтровать через `grep -v Floss`.

## Границы QA

```text
максимальный гэп внутри тела  110 px
низ тела                       1290 px
верх контента                  40 px
левое поле                     60 px
правое поле                    1010 px
```

Автоматический чекер лежит в `qa.py`. Визуальный просмотр остаётся обязательным.
