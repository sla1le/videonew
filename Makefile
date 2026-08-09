# Одна команда на каждое действие. Без этого файла сборка жила в голове
# и каждый раз собиралась заново.
#
# Быстрый старт: make doctor, make setup, make check, make render

# bash с -e нужен, чтобы упавший тест внутри цикла валил цель.
# Со стандартным /bin/sh падение теста терялось и make check был зелёным.
SHELL := /bin/bash
.SHELLFLAGS := -e -o pipefail -c

PY ?= python3
DECK ?= tm2004
OUT := build/out/$(DECK)
PROBE := build/probe_$(DECK).png

.PHONY: help doctor setup check data selfcheck test desc slop verify refs render probe cards deck clean

help:
	@echo "make doctor              что стоит в системе: python, node, chromium, magick"
	@echo "make setup               зависимости python и node плюс chromium"
	@echo "make check               все проверки репозитория перед выпуском"
	@echo "make render DECK=$(DECK)   собрать деку из build/decks и снять кадры"
	@echo "make cards               рейтинговые карточки лиги 1080 на 1350"
	@echo "make desc                линтер описаний build/decks/*.desc.txt"
	@echo "make slop                стоп-лист машинных фраз по декам и описаниям"
	@echo "make refs                перемерить и сверить эталонные кадры"
	@echo "make clean               убрать временные файлы сборки"
	@echo ""
	@echo "деки в build/decks:"
	@ls build/decks/*.json | sed 's|build/decks/||; s|\.json||; s|^|  |'

doctor:
	@$(PY) --version || echo "python НЕТ"
	@$(PY) -c "import PIL; print('pillow', PIL.__version__)" || echo "pillow НЕТ, нужен make setup"
	@node --version || echo "node НЕТ"
	@node -e "require('playwright'); console.log('playwright есть')" || echo "playwright НЕТ, нужен make setup"
	@node build/browser.js || echo "chromium НЕТ"
	@command -v magick > /dev/null && echo "magick есть" || echo "magick НЕТ, контактка будет пропущена"

setup:
	$(PY) -m pip install -r requirements.txt
	npm install
	npx playwright install chromium
	@echo ""
	@echo "готово. Проверь среду: make doctor"

check: data selfcheck test desc slop verify
	@echo ""
	@echo "ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ"

data:
	$(PY) ops/validate_data.py

selfcheck:
	$(PY) ops/selfcheck.py

# тесты в этом репозитории запускаются как скрипты и печатают свой итог,
# через unittest discover они не видны: внутри простые функции с assert
test:
	cd rating && for t in test_*.py; do echo "== $$t"; $(PY) $$t; done

desc:
	$(PY) ops/desclint.py build/decks

slop:
	$(PY) ops/slop.py build/decks

verify:
	$(PY) refs/verify.py

refs:
	$(PY) refs/analyze.py
	$(PY) refs/verify.py

render:
	$(PY) build/gen.py build/decks/$(DECK).json
	rm -rf $(OUT)
	node build/render.js build/html/$(DECK).html $(OUT)
	$(PY) build/lint.py build/html/$(DECK).html build/theme.css
	$(PY) build/qa.py $(OUT) build/html/$(DECK).html build/theme.css
	@$(MAKE) --no-print-directory probe DECK=$(DECK)

probe:
	@if command -v magick > /dev/null 2>&1; then \
		magick montage $(OUT)/*.png -tile x1 -geometry 330x440+6+6 -background '#cccccc' $(PROBE); \
		echo "контактка: $(PROBE). Посмотри её глазами, шаг обязательный"; \
	else \
		echo "magick не найден. Кадры в $(OUT), посмотри их глазами"; \
	fi

cards:
	$(PY) rating/echorate.py --write
	$(PY) build/gen_card.py rating/data/league.json build/html/cards.html build/photos
	cp build/card.css build/html/card.css
	rm -rf build/html/photos
	if [ -d build/photos ]; then cp -r build/photos build/html/photos; fi
	rm -rf build/out/cards
	node build/shot.js build/html/cards.html build/out/cards card_ .wrap 1080 1350
	@echo "карточки: build/out/cards"

deck: render

clean:
	rm -rf build/html build/out build/final __pycache__ rating/__pycache__ refs/manifest.json
	rm -f build/probe_*.png
