#!/bin/bash

pip3 install -r misc/requirements/requirements-pyqt-5.15.txt
export QT_DEBUG_PLUGINS=1
python3 -c "from PyQt5.QtWidgets import QApplication; app = QApplication([])"
