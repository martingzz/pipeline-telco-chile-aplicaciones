"""
config.py — Configuración central del prototipo Deep Gravity Chile.

Ubicación esperada: <raíz del prototipo>/deepgravity/preprocessing/config.py

Este módulo centraliza rutas, esquema de lectura y parámetros metodológicos
del prototipo. Su función no es meramente organizativa: implementa la capa de
estandarización de esquema descrita en el Módulo I del manuscrito, que impone
un esquema mínimo común de lectura sobre la fuente disponible.

El pipeline NO exige un esquema de origen particular. Exige que la fuente sea
transformable a la representación canónica declarada en COLUMN_MAP. Cualquier
fuente de telefonía móvil que contenga identificador seudonimizado, marca
temporal y coordenadas puede alimentar el procedimiento completando el mapeo
correspondiente. Los códigos administrativos son opcionales: la asignación
territorial se resuelve mediante la DPA 2023.

------------------------------------------------------------------------------
NIVELES DE EJECUCIÓN
------------------------------------------------------------------------------
Nivel 1 — Infraestructura territorial: reproducible sin restricciones.
    Requiere únicamente fuentes públicas (OpenStreetMap, DPA 2023, Censo 2024).

Nivel 2 — Procedimiento telco: reejecutable sobre fuentes equivalentes.
    Requiere una fuente de telefonía móvil con la estructura mínima descrita
    arriba. La fuente utilizada en el proyecto es confidencial y no forma parte
    de esta entrega.
------------------------------------------------------------------------------
"""

from pathlib import Path
import os

# =============================================================================
# 1. RAÍZ DEL DIRECTORIO DEL PROTOTIPO
# =============================================================================

# config.py vive en <prototipo>/deepgravity/preprocessing/, de modo que la raíz
# del directorio del prototipo son dos niveles hacia arriba. Todas las rutas de
# este archivo se resuelven dentro de dicho directorio: el prototipo es
# autocontenido y no depende de la ubicación del repositorio que lo aloja.
PROTOTYPE_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# 2. FUENTES EXTERNAS (no incluidas en la entrega)
# =============================================================================
#
# Las fuentes externas no forman parte de la entrega. Puede definirse su
# ubicación mediante la variable de entorno DGCL_DATA_DIR o editando el valor
# por defecto. Con el valor por defecto, el directorio external_data/ se crea
# dentro del directorio del prototipo, de modo que la fuente queda dentro del
# árbol del proyecto; definir DGCL_DATA_DIR hacia una ubicación externa la
# mantiene fuera de él.

EXTERNAL_DATA_DIR = Path(
    os.environ.get("DGCL_DATA_DIR", PROTOTYPE_ROOT / "external_data")
).resolve()

# --- Fuente de telefonía móvil (Nivel 2) -------------------------------------
# Directorio que contiene los archivos .parquet de la fuente telco.
TELCO_PARQUET_DIR = EXTERNAL_DATA_DIR / "telco"
TELCO_PARQUET_GLOB = "*.parquet"

# --- Fuentes públicas (Nivel 1) ----------------------------------------------
# DPA 2023: https://geoportal.cl  (capa comunal, shapefile)
DPA_COMUNAS_SHP = EXTERNAL_DATA_DIR / "dpa2023" / "COMUNAS" / "COMUNAS_v1.shp"

# OpenStreetMap: extracto nacional desde https://download.openstreetmap.fr
OSM_PBF = EXTERNAL_DATA_DIR / "osm" / "chile.osm.pbf"

# Censo 2024: https://censo2024.ine.gob.cl/resultados/
CENSO_XLSX = (
    EXTERNAL_DATA_DIR
    / "censo2024"
    / "D1_Poblacion-censada-por-sexo-y-edad-en-grupos-quinquenales.xlsx"
)
CENSO_SHEET = 2      # hoja con población por comuna
CENSO_HEADER = 3     # fila de encabezado (0-based)


# =============================================================================
# 3. RUTAS INTERNAS DEL PROTOTIPO
# =============================================================================

DG_ROOT = PROTOTYPE_ROOT / "deepgravity"
CHILE_DIR = DG_ROOT / "data" / "chile"
PROCESSED_DIR = CHILE_DIR / "processed"
RESULTS_DIR = DG_ROOT / "results"
IMGS_DIR = PROTOTYPE_ROOT / "imgs"

# Productos territoriales (Nivel 1, regenerables desde fuentes públicas)
OUTPUT_AREAS_SHP = CHILE_DIR / "output_areas.shp"
OUTPUT_AREAS_GEOJSON = CHILE_DIR / "output_areas.geojson"
TESSELLATION_SHP = CHILE_DIR / "tessellation.shp"
TESSELLATION_GEOJSON = CHILE_DIR / "tessellation.geojson"
FEATURES_CSV = CHILE_DIR / "features.csv"
FEATURES_RAW_CSV = CHILE_DIR / "features_raw.csv"

# Productos derivados de la fuente telco (Nivel 2, NO distribuidos)
FLOWS_CSV = CHILE_DIR / "flows.csv"

for _d in (CHILE_DIR, PROCESSED_DIR, RESULTS_DIR, IMGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# =============================================================================
# 4. ESQUEMA CANÓNICO Y MAPEO DE LECTURA (Módulo I — estandarización)
# =============================================================================
#
# Esquema canónico del pipeline, según la Tabla 3.1 del manuscrito.
#
# Campos obligatorios:
#   user_id_anon    identificador seudonimizado del dispositivo
#   event_ts        marca temporal del evento
#   lat_obs         latitud observada
#   lon_obs         longitud observada
#
# Campos opcionales (no requeridos por el procedimiento; la asignación
# territorial se resuelve mediante la DPA 2023):
#   codigo_region   código administrativo regional
#   codigo_comuna   código administrativo comunal
#
# COLUMN_MAP traduce los nombres de campo de SU fuente a este esquema.
# Complete las claves con los nombres efectivos de la fuente que utilizará.
# Si la fuente ya emplea los nombres canónicos, el mapeo puede quedar vacío.

CANONICAL_COLUMNS = [
    "user_id_anon",
    "event_ts",
    "lat_obs",
    "lon_obs",
]

OPTIONAL_COLUMNS = [
    "codigo_region",
    "codigo_comuna",
]

COLUMN_MAP = {
    "<campo_identificador>": "user_id_anon",
    "<campo_timestamp>": "event_ts",
    "<campo_latitud>": "lat_obs",
    "<campo_longitud>": "lon_obs",
    "<campo_codigo_region>": "codigo_region",
    "<campo_codigo_comuna>": "codigo_comuna",
}

# Nombres canónicos usados con mayor frecuencia en el código
COL_USER = "user_id_anon"
COL_TS = "event_ts"
COL_LAT = "lat_obs"
COL_LON = "lon_obs"
COL_REGION = "codigo_region"
COL_COMUNA = "codigo_comuna"


# =============================================================================
# 5. PARÁMETROS METODOLÓGICOS
# =============================================================================

# --- Módulo I: saneamiento ---------------------------------------------------

# Umbral de resolución de colisiones usuario-timestamp (metros).
# Pares simultáneos separados por <= DELTA_H_M se fusionan por promedio de
# coordenadas; separaciones mayores y grupos de tamaño distinto de 2 se
# descartan como inconsistentes.
DELTA_H_M = 300

# Ventana horaria declarada como dominio temporal de la aplicación [h0, h1).
HOUR_WINDOW = (7, 23)

# Evidencia observacional basal mínima por usuario.
MIN_RECORDS_PER_USER = 2

# Identificadores excluidos por volumen y estructura incompatibles con
# movilidad humana ordinaria.
#
# La REGLA de exclusión pertenece al pipeline; los VALORES concretos dependen
# de cada fuente, su período de observación y la política de captura del
# proveedor. Esta lista se entrega vacía: complétela con los identificadores
# que su propio diagnóstico de la distribución de registros por usuario
# justifique excluir, y documente la decisión.
ANOMALOUS_USER_IDS = []

# --- Módulo II: asignación territorial e indexación --------------------------

CRS_LATLON = "EPSG:4326"      # geográfico, para cruce espacial e indexación
CRS_METRIC = "EPSG:32719"     # UTM 19S, para medición de distancias locales

# Tolerancia máxima del mecanismo de snap-in-place (metros).
DELTA_S_M = 200

# --- Teselación (Módulo V, rama territorial) ---------------------------------

TILE_SIZE_KM = 25


# =============================================================================
# 6. UTILIDADES
# =============================================================================

def require(path, descripcion, nivel=2, detalle=None):
    """
    Verifica la disponibilidad de un insumo y entrega un mensaje explícito
    cuando no está presente.

    nivel=1   fuente pública, descargable sin autorización
    nivel=2   fuente de telefonía móvil, provista por el usuario

    detalle   texto que sustituye al mensaje por defecto del nivel. Se utiliza
              cuando el insumo ausente no es una fuente externa sino un
              producto de una etapa anterior del procedimiento, caso en que la
              indicación correcta es ejecutar dicha etapa y no obtener una
              fuente.
    """
    path = Path(path)
    if path.exists():
        return path

    if detalle is None:
        if nivel == 1:
            detalle = (
                "Es una fuente pública. Descárguela y ubíquela en la ruta "
                "indicada, o ajuste config.py / la variable DGCL_DATA_DIR."
            )
        else:
            detalle = (
                "Es una fuente de telefonía móvil provista por el usuario. No "
                "forma parte de esta entrega. El procedimiento opera sobre "
                "cualquier fuente con la estructura mínima declarada en "
                "CANONICAL_COLUMNS; complete COLUMN_MAP en consecuencia."
            )

    raise FileNotFoundError(
        f"No se encontró {descripcion}.\n  Ruta esperada: {path}\n  {detalle}"
    )


def apply_column_map(df, column_map=None, strict=True):
    """
    Estandarización de esquema (Módulo I).

    Renombra las columnas de la fuente hacia el esquema canónico del pipeline
    y verifica que los campos mínimos estén presentes.
    """
    column_map = COLUMN_MAP if column_map is None else column_map

    activo = {
        origen: destino
        for origen, destino in column_map.items()
        if origen in df.columns
    }
    df = df.rename(columns=activo)

    faltantes = [c for c in CANONICAL_COLUMNS if c not in df.columns]
    if faltantes and strict:
        raise KeyError(
            "La fuente no pudo transformarse al esquema canónico del pipeline.\n"
            f"  Campos ausentes: {faltantes}\n"
            f"  Columnas disponibles: {list(df.columns)}\n"
            "  Complete COLUMN_MAP en config.py con los nombres de campo de "
            "su fuente."
        )
    return df


def describe_config():
    """Resumen legible de la configuración activa."""
    lineas = [
        "Deep Gravity Chile — configuración activa",
        f"  Raíz del prototipo   : {PROTOTYPE_ROOT}",
        f"  Fuentes externas     : {EXTERNAL_DATA_DIR}",
        f"  Datos del caso       : {CHILE_DIR}",
        "",
        "  Disponibilidad de fuentes:",
        f"    Telco (Nivel 2)    : {'sí' if TELCO_PARQUET_DIR.exists() else 'no'}",
        f"    DPA 2023 (Nivel 1) : {'sí' if DPA_COMUNAS_SHP.exists() else 'no'}",
        f"    OSM .pbf (Nivel 1) : {'sí' if OSM_PBF.exists() else 'no'}",
        f"    Censo 2024 (N. 1)  : {'sí' if CENSO_XLSX.exists() else 'no'}",
        "",
        f"  Umbral de colisiones : {DELTA_H_M} m",
        f"  Tolerancia de snap   : {DELTA_S_M} m",
        f"  Ventana horaria      : [{HOUR_WINDOW[0]:02d}:00, {HOUR_WINDOW[1]:02d}:00)",
        f"  Tamaño de tesela     : {TILE_SIZE_KM} km",
    ]
    return "\n".join(lineas)


if __name__ == "__main__":
    print(describe_config())