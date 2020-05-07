#!/bin/bash

pip3 install -r misc/requirements/requirements-pyqt-5.15.txt
python3 -c "from PyQt5.QtWidgets import QApplication; app = QApplication([])"
