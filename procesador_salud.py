"""Lectura y validación de los CSV exportados por Simple Health Export CSV.

Usa solo la librería estándar (csv) — sin pandas ni dependencias pesadas,
pensado para correr ligero en máquinas modestas.

La detección de paseos se basa en `WalkingSpeed` (la marcha real que detecta
Apple), no en agrupar pasos: así distingue con fidelidad cuándo caminaste de
verdad, cuándo diste pasitos sueltos y cuándo estuviste sentado.
"""
import os
import csv
import glob
from collections import defaultdict
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Parámetros de la línea de tiempo (basada en WalkingSpeed):
GAP_TRAMO       = timedelta(minutes=5)  # hueco entre muestras -> nuevo tramo
CAMINATA_MIN_MIN = 3                    # duración mínima (min) para ser "caminata"
SENTADO_MIN_MIN  = 5                    # hueco mínimo (min) para mostrarlo como "sentado"
SENTADO_MAX_MIN  = 180                  # hueco mayor (noche/inactividad) no se muestra

# Identificadores HealthKit -> archivo que buscamos dentro de la carpeta
ARCHIVOS_METRICA = {
    "pasos":           "StepCount",
    "cal_activas":     "ActiveEnergyBurned",
    "distancia":       "DistanceWalkingRunning",
    "pisos":           "FlightsClimbed",
    "velocidad_marcha": "WalkingSpeed",
}


class ErrorCarpetaInvalida(Exception):
    """La ruta soltada no es una carpeta."""


class ErrorSinPasos(Exception):
    """La carpeta no contiene el CSV de pasos."""


def nivel_caminata(kmh):
    """Nivel de la caminata según velocidad de marcha (tabla de salud)."""
    if kmh < 3.5:
        return "recreativo"
    if kmh < 5.0:
        return "saludable"
    if kmh < 6.5:
        return "optimo"
    return "power"


@dataclass
class Segmento:
    tipo: str               # "walk" | "sit" | "short_walk"
    inicio: object          # datetime local
    fin: object             # datetime local
    minutos: int = 0
    kmh: float = 0.0       # solo para "walk"/"short_walk"
    nivel: str = ""         # solo para "walk": recreativo/saludable/optimo/power
    calorias: int = 0       # calorías activas quemadas en ese tramo (solo "walk")


@dataclass
class DatoDia:
    fecha: object           # datetime.date
    pasos: int = 0
    cal_activas: int = 0
    distancia_km: float = 0.0
    pisos: int = 0
    linea_tiempo: list = field(default_factory=list)   # Segmento ordenados por hora
    num_caminatas: int = 0
    minutos_caminata: int = 0


@dataclass
class DatosSalud:
    dias: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)


def _buscar_csv(carpeta, identificador):
    coincidencias = glob.glob(os.path.join(carpeta, f"*{identificador}*.csv"))
    return coincidencias[0] if coincidencias else None


def _leer_filas(ruta):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        lineas = archivo.readlines()
    if lineas and lineas[0].lower().startswith("sep="):
        lineas = lineas[1:]
    return list(csv.DictReader(lineas))


def _dt_local(cadena_fecha):
    # Formato de origen: "2026-08-01 03:12:00 +0000" (UTC) -> hora local del sistema.
    return datetime.strptime(cadena_fecha.strip(), "%Y-%m-%d %H:%M:%S %z").astimezone()


def _construir_linea_tiempo(muestras_velocidad, muestras_calorias=()):
    """Construye la línea de tiempo de un día a partir de muestras de marcha.

    `muestras_velocidad`: lista de (inicio, fin, kmh) del día.
    `muestras_calorias`:  lista de (inicio, fin, kcal) de calorías activas del día,
                          para sumar las quemadas dentro de cada caminata.
    Agrupa las muestras contiguas (hueco <= GAP_TRAMO) en tramos de caminata,
    intercala los "sentado" (huecos >= SENTADO_MIN_MIN) y marca como "short_walk"
    los tramos demasiado cortos para ser una caminata completa.
    """
    muestras_velocidad = sorted(muestras_velocidad)
    if not muestras_velocidad:
        return []

    # Agrupar muestras de marcha en tramos
    tramos = []
    tramo_actual = None
    for ini, fin, vel in muestras_velocidad:
        if tramo_actual is None:
            tramo_actual = [ini, fin, [vel]]
        elif ini - tramo_actual[1] <= GAP_TRAMO:
            tramo_actual[1] = fin
            tramo_actual[2].append(vel)
        else:
            tramos.append(tramo_actual)
            tramo_actual = [ini, fin, [vel]]
    if tramo_actual:
        tramos.append(tramo_actual)

    # Construir segmentos, intercalando los "sentado"
    segmentos = []
    fin_anterior = None
    for ini, fin, velocidades in tramos:
        if fin_anterior is not None:
            hueco_min = (ini - fin_anterior).total_seconds() / 60
            if SENTADO_MIN_MIN <= hueco_min <= SENTADO_MAX_MIN:
                segmentos.append(Segmento("sit", fin_anterior, ini, int(round(hueco_min))))
        duracion_min = (fin - ini).total_seconds() / 60
        kmh = round(sum(velocidades) / len(velocidades), 1)
        if duracion_min >= CAMINATA_MIN_MIN:
            # Calorías del tramo: prorrateo por solapamiento con la ventana [ini, fin].
            kcal = 0.0
            for ini_cal, fin_cal, cal in muestras_calorias:
                solapamiento = (min(fin_cal, fin) - max(ini_cal, ini)).total_seconds()
                duracion_bloque = (fin_cal - ini_cal).total_seconds()
                if solapamiento > 0 and duracion_bloque > 0:
                    kcal += cal * (solapamiento / duracion_bloque)
                elif solapamiento > 0:
                    kcal += cal
            segmentos.append(Segmento("walk", ini, fin, int(round(duracion_min)), kmh,
                                      nivel_caminata(kmh), int(round(kcal))))
        else:
            segmentos.append(Segmento("short_walk", ini, fin, int(round(duracion_min)), kmh))
        fin_anterior = fin
    return segmentos


def cargar_carpeta(carpeta):
    """Lee una carpeta de export y devuelve un DatosSalud agregado por día.

    Lanza ErrorCarpetaInvalida o ErrorSinPasos si la carpeta no es válida.
    """
    if not os.path.isdir(carpeta):
        raise ErrorCarpetaInvalida(
            "Eso no es una carpeta.\nArrastra la carpeta del export de "
            "Simple Health Export CSV."
        )

    csv_pasos = _buscar_csv(carpeta, ARCHIVOS_METRICA["pasos"])
    if not csv_pasos:
        raise ErrorSinPasos(
            "Esta carpeta no contiene datos de pasos (StepCount).\n"
            "¿Es el export correcto de Simple Health Export CSV?"
        )

    pasos       = defaultdict(float)
    cal_activas = defaultdict(float)
    distancia   = defaultdict(float)
    pisos       = defaultdict(float)
    advertencias = []

    for fila in _leer_filas(csv_pasos):
        try:
            pasos[_dt_local(fila["startDate"]).date()] += float(fila["value"])
        except (KeyError, ValueError):
            continue

    muestras_calorias = defaultdict(list)

    def acumular(clave, destino, etiqueta, muestras=None):
        ruta = _buscar_csv(carpeta, ARCHIVOS_METRICA[clave])
        if not ruta:
            advertencias.append(etiqueta)
            return
        for fila in _leer_filas(ruta):
            try:
                inicio = _dt_local(fila["startDate"])
                valor  = float(fila["value"])
            except (KeyError, ValueError):
                continue
            destino[inicio.date()] += valor
            if muestras is not None:
                try:
                    fin = _dt_local(fila["endDate"])
                except (KeyError, ValueError):
                    fin = inicio
                muestras[inicio.date()].append((inicio, fin, valor))

    acumular("cal_activas", cal_activas, "calorías activas", muestras=muestras_calorias)
    acumular("distancia",   distancia,   "distancia")
    acumular("pisos",       pisos,       "pisos")

    # Muestras de marcha real (WalkingSpeed) por día -> línea de tiempo
    muestras_velocidad = defaultdict(list)
    csv_velocidad = _buscar_csv(carpeta, ARCHIVOS_METRICA["velocidad_marcha"])
    if not csv_velocidad:
        advertencias.append("velocidad de marcha")
    else:
        for fila in _leer_filas(csv_velocidad):
            try:
                inicio = _dt_local(fila["startDate"])
                fin    = _dt_local(fila["endDate"])
                kmh    = float(fila["value"])
            except (KeyError, ValueError):
                continue
            muestras_velocidad[inicio.date()].append((inicio, fin, kmh))

    datos = DatosSalud(advertencias=advertencias)
    for dia in sorted(pasos):
        linea_tiempo = _construir_linea_tiempo(
            muestras_velocidad.get(dia, []),
            muestras_calorias.get(dia, [])
        )
        caminatas = [s for s in linea_tiempo if s.tipo == "walk"]
        datos.dias.append(DatoDia(
            fecha=dia,
            pasos=int(round(pasos[dia])),
            cal_activas=int(round(cal_activas.get(dia, 0))),
            distancia_km=round(distancia.get(dia, 0.0), 1),
            pisos=int(round(pisos.get(dia, 0))),
            linea_tiempo=linea_tiempo,
            num_caminatas=len(caminatas),
            minutos_caminata=sum(s.minutos for s in caminatas),
        ))
    return datos
