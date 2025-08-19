#!/usr/bin/env python3
import os, sys, numpy as np
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtCore import Qt

# If pure Qt test worked only with software GL, keep this on:
# QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)

app = QApplication(sys.argv)

import pyqtgraph as pg
pg.setConfigOptions(useOpenGL=False, antialias=False, background="w", foreground="k")

class Win(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyqtgraph minimal")
        self.resize(900, 600)
        self.plotw = pg.PlotWidget()
        self.setCentralWidget(self.plotw)
        x = np.linspace(0, 10, 1000)
        y = np.sin(x)
        self.curve = self.plotw.plot(x, y, pen=pg.mkPen((200, 0, 0), width=2))
        # Force autoscale once:
        self.plotw.enableAutoRange()

w = Win()
w.show()
sys.exit(app.exec())
