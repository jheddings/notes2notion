# Makefile for notes2notion

BASEDIR ?= $(PWD)
APPNAME ?= notes2notion
SRCDIR ?= $(BASEDIR)
VENVDIR ?= $(BASEDIR)/.venv

################################################################################
.PHONY: venv

bin/activate: requirements.txt
	python3 -m venv --prompt "$(APPNAME)" "$(BASEDIR)/.venv"
	"$(BASEDIR)/.venv/bin/pip3" install -r requirements.txt
	"$(BASEDIR)/.venv/bin/pip3" install --upgrade pip

venv: bin/activate

################################################################################
.PHONY: venv-configured

venv-configured:
ifneq ($(VIRTUAL_ENV), $(VENVDIR))
	$(error Must use venv !!)
endif

################################################################################
.PHONY: preflight

preflight: venv-configured
	isort --profile black "$(SRCDIR)"
	black "$(SRCDIR)"

################################################################################
.PHONY: clean

clean:
	rm -f "$(SRCDIR)/*.pyc"
	rm -Rf "$(SRCDIR)/__pycache__"

################################################################################
.PHONY: clobber

# TODO deactivate first
clobber: clean
	rm -Rf "$(VENVDIR)"

