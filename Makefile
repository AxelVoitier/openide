# WARNING
# This Makefile is only intended to provide aliases for developers.
# Its "build" and "install" commands have nothing to do with the usual "make build install"

.PHONY: install qa style typing tests clean build

install:
	pip install -e .[dev]

qa: style typing tests

style:
	flake8 openide tests

typing:
	mypy openide

tests:
	py.test --cov=openide --cov-report=term-missing -x tests

clean:
	rm -Rf build dist openide.egg-info .pytest_cache

build:
	python setup.py sdist bdist_wheel
