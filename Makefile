.PHONY: setup profile check pdf clean

setup:          ## разовая установка окружения
	bash scripts/setup.sh

profile:        ## запечь активный профиль (цвета, шрифты, данные автора)
	.venv/bin/python scripts/brand_build.py

check:          ## самопроверка: собрать пробную страницу в цветах профиля
	.venv/bin/python scripts/selftest.py

pdf:            ## отрендерить guide.html -> output/output.pdf
	.venv/bin/python scripts/render.py

clean:          ## убрать результаты сборки (профили не трогаем)
	rm -rf qa-* output/*.pdf guide-*.html самопроверка.html
