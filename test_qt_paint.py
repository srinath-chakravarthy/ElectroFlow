#!/usr/bin/env python3
import os, sys

# Force layer-backed views and software path BEFORE Qt
os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
os.environ.setdefault("QT_OPENGL", "software")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsRectItem
from PySide6.QtGui import QBrush, QPen, QColor

# Optional: try one at a time if still blank
# QApplication.setAttribute(Qt.AA_UseSoftwareOpenGL, True)

app = QApplication(sys.argv)

w = QMainWindow()
w.setWindowTitle("Qt paint test")
w.resize(800, 500)

scene = QGraphicsScene()
rect = QGraphicsRectItem(0, 0, 300, 150)
rect.setBrush(QBrush(QColor(170, 200, 255)))
rect.setPen(QPen(Qt.black, 2))
scene.addItem(rect)

view = QGraphicsView(scene)
w.setCentralWidget(view)
w.show()

sys.exit(app.exec())
