"""Ventana principal: une la zona de arrastre (pantalla 1) con el dashboard (pantalla 2)."""
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QFrame)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QGuiApplication

from procesador_salud import cargar_carpeta, ErrorCarpetaInvalida, ErrorSinPasos
from zona_arrastre import ZonaArrastre
from grafico_barras import GraficaBarras
from tema import naranja_hex, GRIS, fmt_pasos

META = 10000


class Tablero(QWidget):
    def __init__(self, al_volver, parent=None):
        super().__init__(parent)
        self.datos = None
        self._indice_dia = -1

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 16, 24, 16)
        raiz.setSpacing(4)

        superior = QHBoxLayout()
        self.btn_volver = QPushButton("←  Otra carpeta")
        self.btn_volver.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_volver.setFlat(True)
        self.btn_volver.clicked.connect(al_volver)
        superior.addWidget(self.btn_volver)
        superior.addStretch()
        raiz.addLayout(superior)

        self.lbl_pasos = QLabel("—")
        self.lbl_pasos.setAlignment(Qt.AlignmentFlag.AlignCenter)
        naranja = naranja_hex()
        self.lbl_pasos.setStyleSheet(f"color:{naranja};")
        self.lbl_pasos.setFont(QFont("Helvetica", 44, QFont.Weight.Bold))
        raiz.addWidget(self.lbl_pasos)

        self.lbl_sub = QLabel("")
        self.lbl_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_sub.setStyleSheet(f"color:{naranja};")
        self.lbl_sub.setFont(QFont("Helvetica", 17, QFont.Weight.DemiBold))
        raiz.addWidget(self.lbl_sub)

        self.lbl_detalle = QLabel("")
        self.lbl_detalle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_detalle.setStyleSheet("color:palette(mid);")
        self.lbl_detalle.setFont(QFont("Helvetica", 13))
        raiz.addWidget(self.lbl_detalle)

        self.grafica = GraficaBarras(meta=META)
        self.grafica.diaSeleccionado.connect(self._seleccionar_dia)
        self.area_scroll = QScrollArea()
        self.area_scroll.setWidgetResizable(True)
        self.area_scroll.setWidget(self.grafica)
        self.area_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.area_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        raiz.addWidget(self.area_scroll, stretch=1)

        self.titulo_actividad = QLabel("")
        self.titulo_actividad.setFont(QFont("Helvetica", 12, QFont.Weight.Bold))
        self.titulo_actividad.setStyleSheet("margin-top:4px;")
        raiz.addWidget(self.titulo_actividad)

        self.lbl_actividad = QLabel("")
        self.lbl_actividad.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_actividad.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.lbl_actividad.setStyleSheet("padding:8px 12px;")
        scroll_actividad = QScrollArea()
        scroll_actividad.setWidgetResizable(True)
        scroll_actividad.setWidget(self.lbl_actividad)
        scroll_actividad.setFixedHeight(150)
        scroll_actividad.setFrameShape(QFrame.Shape.NoFrame)
        scroll_actividad.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        raiz.addWidget(scroll_actividad)

        self.lbl_advertencia = QLabel("")
        self.lbl_advertencia.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_advertencia.setStyleSheet("font-size:11px;color:palette(mid);")
        raiz.addWidget(self.lbl_advertencia)

        QGuiApplication.styleHints().colorSchemeChanged.connect(self._actualizar_tema)

    def _actualizar_tema(self):
        naranja = _naranja_hex()
        self.lbl_pasos.setStyleSheet(f"color:{naranja};")
        self.lbl_sub.setStyleSheet(f"color:{naranja};")
        self.grafica.update()
        if self.datos and self._indice_dia >= 0:
            self._llenar_linea_tiempo(self.datos.dias[self._indice_dia])

    def cargar(self, datos):
        self.datos = datos
        self.grafica.cargar_datos(datos.dias, meta=META)
        self.lbl_advertencia.setText(
            "ℹ️ Sin datos de: " + ", ".join(datos.advertencias) if datos.advertencias else "")
        if datos.dias:
            self._seleccionar_dia(len(datos.dias) - 1)
            QTimer.singleShot(0, self._desplazar_al_final)

    def _desplazar_al_final(self):
        barra = self.area_scroll.horizontalScrollBar()
        barra.setValue(barra.maximum())

    def _seleccionar_dia(self, indice):
        self._indice_dia = indice
        d = self.datos.dias[indice]
        pasos = fmt_pasos(d.pasos)
        self.lbl_pasos.setText(pasos)
        self.lbl_sub.setText(f"pasos ({d.cal_activas} calorías)")
        self.lbl_detalle.setText(
            f"{d.distancia_km:g} km   ·   {d.pisos} pisos   ·   "
            f"{d.fecha.strftime('%d/%m/%Y')}")
        self._llenar_linea_tiempo(d)

    # Iconos de calidad de la caminata según nivel (por velocidad de marcha).
    # "power" usa None porque su color es el naranja dinámico del tema.
    NIVELES = {
        "recreativo": ("🐢", "recreativo", "#888888"),
        "saludable":  ("✅", "saludable",  "#30d158"),
        "optimo":     ("💪", "óptimo",     "#30d158"),
        "power":      ("⚡", "power",       None),
    }

    @staticmethod
    def _formato_12h(t):
        return t.strftime("%I:%M %p").lstrip("0")

    def _llenar_linea_tiempo(self, d):
        resumen = (f"   ·   🚶 {d.num_caminatas} caminatas · {d.minutos_caminata} min"
                   if d.num_caminatas else "")
        self.titulo_actividad.setText(f"Actividad del {d.fecha.strftime('%d/%m')}{resumen}")
        if not d.linea_tiempo:
            self.lbl_actividad.setText(
                "<i style='color:#888888'>Sin datos de marcha ese día "
                "(el CSV de WalkingSpeed no tiene muestras).</i>")
            return
        filas = "".join(self._fila_segmento(s) for s in d.linea_tiempo)
        self.lbl_actividad.setText("<table cellspacing='0'>" + filas + "</table>")

    _PI = "padding:2px 12px 2px 0"   # celda icono
    _PD = "padding:2px 16px 2px 0"   # celda dato
    _P0 = "padding:2px 0"            # celda final

    @classmethod
    def _fila_segmento(cls, s):
        naranja = naranja_hex()
        pi, pd, p0 = cls._PI, cls._PD, cls._P0
        if s.tipo == "sit":
            return (
                f"<tr><td style='{pi}'>🪑</td>"
                f"<td colspan='4' style='{p0};color:{GRIS}'>"
                f"<i>sentado ~{s.minutos} min</i></td></tr>")
        if s.tipo == "short_walk":
            return (
                f"<tr><td style='{pi}'>👣</td>"
                f"<td style='{pd};color:{GRIS}'>{cls._formato_12h(s.inicio)}</td>"
                f"<td colspan='3' style='{p0};color:{GRIS}'>caminata corta</td></tr>")
        icono, nombre, color = cls.NIVELES.get(s.nivel, ("🚶", s.nivel, GRIS))
        if color is None:
            color = naranja
        return (
            f"<tr><td style='{pi}'>🚶</td>"
            f"<td style='{pd}'>{cls._formato_12h(s.inicio)}–{cls._formato_12h(s.fin)}</td>"
            f"<td style='{pd};color:{naranja}'><b>{s.minutos} min</b></td>"
            f"<td style='{pd};color:{GRIS}'>{s.kmh:g} km/h</td>"
            f"<td style='{pd};color:{naranja}'>🔥 {s.calorias} cal</td>"
            f"<td style='{p0};color:{color}'>{icono} {nombre}</td></tr>")


class VentanaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HealthViewer")
        self.resize(820, 700)

        self.pila = QStackedWidget()
        self.setCentralWidget(self.pila)

        self.zona_arrastre = ZonaArrastre()
        self.zona_arrastre.carpetaSoltada.connect(self._procesar_carpeta)
        self.tablero = Tablero(al_volver=self._volver)

        self.pila.addWidget(self.zona_arrastre)
        self.pila.addWidget(self.tablero)

    def _procesar_carpeta(self, ruta):
        try:
            datos = cargar_carpeta(ruta)
        except (ErrorCarpetaInvalida, ErrorSinPasos) as e:
            self.zona_arrastre.mostrar_error(str(e))
            return
        if not datos.dias:
            self.zona_arrastre.mostrar_error(
                "No encontré muestras de pasos con fecha válida en esa carpeta.")
            return
        self.tablero.cargar(datos)
        self.pila.setCurrentIndex(1)

    def _volver(self):
        self.zona_arrastre.reiniciar_texto()
        self.pila.setCurrentIndex(0)
