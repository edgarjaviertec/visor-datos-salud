"""Gráfico de barras diarias estilo Pedometer++ dibujado a mano con QPainter."""
from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtCore import Qt, Signal, QRectF, QRect
from PySide6.QtGui import (QPainter, QColor, QFont, QPen, QBrush,
                            QFontMetrics, QPalette)
from tema import naranja_color, fmt_pasos

VERDE      = QColor("#30d158")
ROJO       = QColor("#ff453a")
LINEA_META = QColor("#30d158")
INTERIOR   = QColor(20, 20, 20, 180)   # texto dentro de la barra (siempre sobre color)
_FUENTE    = "Helvetica"


class GraficaBarras(QWidget):
    diaSeleccionado = Signal(int)

    def __init__(self, meta=10000, parent=None):
        super().__init__(parent)
        self.meta = meta
        self.dias = []
        self.seleccionado = -1
        self.bajo_cursor = -1
        self._rects_barras = []
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def cargar_datos(self, dias, meta=None):
        if meta is not None:
            self.meta = meta
        self.dias = dias
        self.seleccionado = len(dias) - 1 if dias else -1
        self.setMinimumWidth(max(len(self.dias) * 66, 200))
        self.update()

    def _dibujar_escalera(self, p, x, y, tam, color):
        # Escalera de 3 escalones ascendentes hacia la derecha (estilo Pedometer++).
        p.save()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(color))
        ancho_escalon = tam / 3.0
        for k, hf in enumerate((0.45, 0.72, 1.0)):
            alto_escalon = tam * hf
            p.drawRect(QRectF(x + k * ancho_escalon, y + tam - alto_escalon,
                              ancho_escalon + 0.5, alto_escalon))
        p.restore()

    def _color_para(self, pasos):
        if pasos >= self.meta:
            return VERDE
        if pasos < self.meta * 0.3:
            return ROJO
        return naranja_color()

    def _indice_en(self, x):
        for rect, indice in self._rects_barras:
            if rect.left() <= x <= rect.right():
                return indice
        return -1

    def mousePressEvent(self, event):
        indice = self._indice_en(event.position().toPoint().x())
        if indice != -1:
            self.seleccionado = indice
            self.diaSeleccionado.emit(indice)
            self.update()

    def mouseMoveEvent(self, event):
        indice = self._indice_en(event.position().toPoint().x())
        if indice != self.bajo_cursor:
            self.bajo_cursor = indice
            self.update()

    def leaveEvent(self, event):
        if self.bajo_cursor != -1:
            self.bajo_cursor = -1
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        paleta      = self.palette()
        color_fondo = paleta.color(QPalette.ColorRole.Window)
        color_texto = paleta.color(QPalette.ColorRole.WindowText)
        color_tenue = paleta.color(QPalette.ColorRole.PlaceholderText)

        p.fillRect(self.rect(), color_fondo)
        if not self.dias:
            return

        margen_sup, margen_inf = 44, 42
        margen_izq = margen_der = 10
        alto_zona     = h - margen_sup - margen_inf
        ancho_zona    = w - margen_izq - margen_der
        num_dias      = len(self.dias)
        ancho_columna = ancho_zona / num_dias
        ancho_barra   = min(ancho_columna * 0.60, 46)

        max_pasos  = max([d.pasos for d in self.dias] + [self.meta])
        escala_max = max_pasos * 1.12 or 1
        base_y     = margen_sup + alto_zona

        y_meta = base_y - (self.meta / escala_max) * alto_zona
        p.setPen(QPen(LINEA_META, 1.5))
        p.drawLine(margen_izq, int(y_meta), w - margen_der, int(y_meta))

        self._rects_barras = []
        fuente_valor   = QFont(_FUENTE, 11, QFont.Weight.Bold)
        fuente_pequena = QFont(_FUENTE, 8)
        fuente_fecha   = QFont(_FUENTE, 10)

        for i, d in enumerate(self.dias):
            cx          = margen_izq + ancho_columna * i + ancho_columna / 2
            alto_barra  = (d.pasos / escala_max) * alto_zona
            x_barra     = cx - ancho_barra / 2
            y_barra     = base_y - alto_barra
            color       = self._color_para(d.pasos)
            relleno     = color.lighter(130) if i == self.bajo_cursor else color
            rect_columna = QRect(int(cx - ancho_columna / 2), margen_sup,
                                 int(ancho_columna), int(alto_zona))
            self._rects_barras.append((rect_columna, i))

            fondo_columna = QRectF(cx - ancho_columna / 2, margen_sup - 4,
                                   ancho_columna, alto_zona + margen_inf)
            if i == self.seleccionado:
                p.fillRect(fondo_columna, QColor(128, 128, 128, 20))
            elif i == self.bajo_cursor:
                p.fillRect(fondo_columna, QColor(128, 128, 128, 10))

            radio = min(ancho_barra / 2, 9)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(relleno))
            p.drawRoundedRect(QRectF(x_barra, y_barra, ancho_barra, max(alto_barra, 3)),
                              radio, radio)
            if alto_barra > radio:
                p.drawRect(QRectF(x_barra, y_barra + radio, ancho_barra, alto_barra - radio))

            p.setFont(fuente_valor)
            p.setPen(color)
            p.drawText(QRectF(cx - ancho_columna / 2, y_barra - 22, ancho_columna, 20),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                       fmt_pasos(d.pasos))

            if alto_barra > 42:
                p.setFont(fuente_pequena)
                p.setPen(INTERIOR)
                metricas    = QFontMetrics(fuente_pequena)
                texto_num   = str(d.pisos)
                ancho_texto = metricas.horizontalAdvance(texto_num)
                tam_icono   = 9.0
                separacion  = 3.0
                ancho_total = ancho_texto + separacion + tam_icono
                x_inicio    = x_barra + (ancho_barra - ancho_total) / 2
                y_fila      = base_y - 34
                p.drawText(QRectF(x_inicio, y_fila, ancho_texto + 1, 15),
                           Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                           texto_num)
                self._dibujar_escalera(p, x_inicio + ancho_texto + separacion,
                                       y_fila + 3, tam_icono, INTERIOR)
                p.drawText(QRectF(x_barra, base_y - 20, ancho_barra, 15),
                           Qt.AlignmentFlag.AlignCenter, f"{d.distancia_km:g}km")

            p.setFont(fuente_fecha)
            p.setPen(color_texto if i == self.seleccionado else color_tenue)
            p.drawText(QRectF(cx - ancho_columna / 2, base_y + 6, ancho_columna, 20),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       d.fecha.strftime("%d/%m"))
        p.end()
