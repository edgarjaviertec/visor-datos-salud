"""Pantalla inicial: zona para arrastrar la carpeta del export, con validación."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

BORDE_INACTIVO = "#4da6ff"
BORDE_ACTIVO   = "#30d158"
BORDE_ERROR    = "#ff453a"
TEXTO_INICIAL  = "Arrastra aquí la carpeta del export\nde Simple Health Export CSV"


class ZonaArrastre(QWidget):
    carpetaSoltada = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        contenedor = QVBoxLayout(self)
        contenedor.setContentsMargins(30, 30, 30, 30)
        contenedor.setSpacing(16)

        self.zone = QLabel(TEXTO_INICIAL)
        self.zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.zone.setFont(QFont("Helvetica", 15, QFont.Weight.Bold))
        self.zone.setWordWrap(True)
        self._aplicar_borde(BORDE_INACTIVO)
        contenedor.addWidget(self.zone, stretch=1)

        self.hint = QLabel("También puedes usar el botón de abajo")
        self.hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        contenedor.addWidget(self.hint)

        self.browse = QPushButton("Examinar carpeta…")
        self.browse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse.clicked.connect(self._explorar)
        contenedor.addWidget(self.browse, alignment=Qt.AlignmentFlag.AlignCenter)

    def _aplicar_borde(self, color, color_texto=None):
        texto_css = f"color:{color_texto};" if color_texto else ""
        self.zone.setStyleSheet(
            f"border:2px dashed {color};border-radius:12px;"
            f"background:palette(base);{texto_css}padding:40px;")

    def _explorar(self):
        carpeta = QFileDialog.getExistingDirectory(self, "Elige la carpeta del export")
        if carpeta:
            self.carpetaSoltada.emit(carpeta)

    def mostrar_error(self, mensaje):
        self.zone.setText("⚠️  " + mensaje)
        self._aplicar_borde(BORDE_ERROR)

    def reiniciar_texto(self):
        self.zone.setText(TEXTO_INICIAL)
        self._aplicar_borde(BORDE_INACTIVO)

    # --- Drag & drop ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._aplicar_borde(BORDE_ACTIVO)

    def dragLeaveEvent(self, event):
        self._aplicar_borde(BORDE_INACTIVO)

    def dropEvent(self, event):
        self._aplicar_borde(BORDE_INACTIVO)
        urls = event.mimeData().urls()
        if urls:
            self.carpetaSoltada.emit(urls[0].toLocalFile())
