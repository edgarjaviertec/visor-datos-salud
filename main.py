"""HealthViewer — visor de pasos y calorías estilo Pedometer++.

Arrastra la carpeta exportada por Simple Health Export CSV y visualiza
tus pasos diarios con las calorías activas, distancia y pisos.
"""
import sys
from PySide6.QtWidgets import QApplication
from ventana_principal import VentanaPrincipal


def iniciar():
    aplicacion = QApplication(sys.argv)
    aplicacion.setApplicationName("HealthViewer")
    ventana = VentanaPrincipal()
    ventana.show()
    sys.exit(aplicacion.exec())


if __name__ == "__main__":
    iniciar()
