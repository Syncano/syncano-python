#!/bin/bash

sed "s/<USER>/$PYPI_USER/;s/<PASSWORD>/$PYPI_PASSWORD/" < ~/syncano-python/.pypirc.template > ~/.pypirc
python setup.py register -r pypi
python setup.py sdist upload -r pypi
