#!/bin/bash

set -e -u -x

rm -rf venv
find . -name __pycache__ -print -exec rm -rf \{\} \; || true
find . -name \*.pyc -print -exec rm -f \{\} \; || true
find . -name \*.pyo -print -exec rm -f \{\} \; || true
rm -rf build dist .eggs
PYTHON=$(which python3)

$PYTHON -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install --upgrade pytest
venv/bin/pip install  --editable .
# venv3/bin/pip install --no-deps . --force-reinstall

set +x
echo
echo
echo "To run hstk under this venv:"
echo "$ source venv/bin/activate"
echo
echo "You can edit the src files here and the edits will be automatically picked up"
echo "inside the venv"
echo
echo "to verify pytest, after venv/bin/activate"
echo "$ pytest"
