# Одна команда на каждое действие. Без этого файла сборка жила в голове
# и каждый раз собиралась заново.
PY ?= python3
DECK ?= prime

.PHONY: help setup check data test selfcheck refs render deck clean

help:
	@echo "make setup           зависимости python и node плюс chromium"
	@echo "make check           все проверки репозитория перед выпуском"
	@echo "make data            гигиена json в rating/data и остальных папках"
	@echo "make test            тесты движка рейтинга"
	@echo "make refs            замер и сверка эталонных кадров в refs"
	@echo "make render DECK=gb  собрать одну деку из build/decks"
	@echo "make clean           убрать временные файлы сборки"

setup:
	$(PY) -m pip install -r requirements.txt
	npm install
	npx playwright install chromium

check: data selfcheck test

data:
	$(PY) ops/validate_data.py

selfcheck:
	$(PY) ops/selfcheck.py

# тесты в этом репозитории запускаются как скрипты и печатают свой итог,
# через unittest discover они не видны: внутри простые функции с assert
test:
	cd rating && for t in test_*.py; do echo "== $$t"; $(PY) $$t; done

refs:
	$(PY) refs/analyze.py
	$(PY) refs/verify.py

render:
	$(PY) build/gen.py build/decks/$(DECK).json
	node build/render.js build/html/$(DECK).html build/out $(DECK)_
	$(PY) build/lint.py build/html/$(DECK).html build/theme.css
	$(PY) build/qa.py build/out build/html/$(DECK).html build/theme.css

deck: render

clean:
	rm -rf build/html build/out build/final __pycache__ rating/__pycache__ refs/manifest.json
