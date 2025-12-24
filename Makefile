.PHONY: help install test coverage coverage-html clean

# Environment variables
export ENV=dev
VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

help:
	@echo "--- Quill the Librarian: Command Shortcuts ---"
	@echo "install        : Create venv and install all dependencies"
	@echo "test           : Run tests using venv (Matches VS Code)"
	@echo "coverage       : Run tests with terminal coverage report"
	@echo "run            : Run the bot using the virtual environment"

$(VENV)/bin/activate: requirements.txt
	@echo "Creating virtual environment..."
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install coverage flake8
	@touch $(VENV)/bin/activate

install: $(VENV)/bin/activate
	@echo "Environment is ready."

test: install
	$(PYTHON) -m unittest discover -v -s ./tests -p "test_*.py"

coverage: install
	$(PYTHON) -m coverage run --source=. -m unittest discover -s ./tests -p "test_*.py"
	$(PYTHON) -m coverage report -m

coverage-html: install
	$(PYTHON) -m coverage run --source=. -m unittest discover -s ./tests -p "test_*.py"
	$(PYTHON) -m coverage html
	@echo "Report generated: open htmlcov/index.html"

run: install
	$(PYTHON) main.py

clean:
	rm -rf __pycache__ */__pycache__ tests/__pycache__
	rm -rf $(VENV)
	rm -f .coverage coverage.xml
	rm -rf htmlcov/