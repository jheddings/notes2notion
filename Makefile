# Makefile for notes2notion

APPNAME ?= $(shell grep -m1 '^name' "$(BASEDIR)/pyproject.toml" | sed -e 's/name.*"\(.*\)"/\1/')
APPVER ?= $(shell grep -m1 '^version' "$(BASEDIR)/pyproject.toml" | sed -e 's/version.*"\(.*\)"/\1/')

BASEDIR ?= $(PWD)

WITH_VENV = poetry run

################################################################################
.PHONY: venv

venv:
	poetry install --sync
	$(WITH_VENV) pre-commit install --install-hooks --overwrite

################################################################################
.PHONY: static-checks

static-checks: venv
	$(WITH_VENV) pre-commit run --all-files --verbose

################################################################################
.PHONY: preflight

preflight: static-checks

################################################################################
.PHONY: clean

clean:
	find "$(BASEDIR)" -name "*.pyc" -print | xargs rm -f
	find "$(BASEDIR)" -name '__pycache__' -print | xargs rm -Rf

################################################################################
.PHONY: clobber

clobber: clean
	$(WITH_VENV) pre-commit uninstall
	rm -Rf "$(BASEDIR)/.venv"
