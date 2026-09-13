"""Colores y utilidades de presentacion compartidas entre widgets."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication

GRIS = "#888888"


def _es_oscuro():
    return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark


def naranja_hex():
    return "#ff8c1a" if _es_oscuro() else "#c05500"


def naranja_color():
    return QColor("#ff8c1a") if _es_oscuro() else QColor("#c05500")


def fmt_pasos(n):
    return f"{n:,}".replace(",", ".")
