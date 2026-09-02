# Condiciones metodológicas para el uso de datos de telefonía móvil en estudios sociales y urbanos en Chile

Repositorio de código asociado a la tesis de Martín Alonso González Henríquez, para optar a los títulos de Ingeniero Civil Industrial y Magíster en Ciencia de Datos, Universidad de Chile, Facultad de Ciencias Físicas y Matemáticas, 2026.

La tesis es metodológica y no modelística: su objeto no es la movilidad urbana ni el teletrabajo, sino las condiciones bajo las cuales los registros de telefonía móvil pueden convertirse en insumos analíticamente defendibles. Los dos prototipos que este repositorio contiene no son sus resultados: son evidencia metodológica situada sobre una arquitectura de tratamiento del dato, y su documentación completa se encuentra en el manuscrito.

---

## Criterio de publicación

**Se publica el procedimiento completo; no se publican los artefactos ni las salidas derivadas de la fuente de telefonía móvil.**

Este criterio único rige ambos directorios y responde a dos condiciones. La primera es el acuerdo de confidencialidad bajo el cual se accedió a la fuente. La segunda es de orden metodológico: el manuscrito registra, para cada producto de las ramas relacional y conductual, las restricciones de uso legítimo que condicionan su difusión. En el caso del prototipo de segmentación, esas restricciones son sustantivas — los productos que asocian un identificador seudonimizado con anclas residenciales y laborales inferidas constituyen un cuasi-identificador — y la exclusión de esos archivos de esta entrega es su aplicación efectiva.

En consecuencia, no forman parte del repositorio:

- los registros de telefonía móvil y cualquier derivado suyo;
- las salidas de las corridas documentadas, incluidos los conjuntos serializados, los productos intermedios, las figuras generadas y los registros de ejecución;
- los cuadernos con resultados de ejecución: se entregan sin salidas.

Todo el código que produce esos objetos sí se publica. Las cifras de las corridas documentadas figuran en el manuscrito y, para el primer prototipo, en su guía técnica de montaje.

---

## Contenido

```
pipeline-telco-chile-aplicaciones/
├── README.md
├── LICENSE
├── 01-prototipo-deepgravity-chile/
│   ├── Informe_Montaje_Deep_Gravity_Chile.pdf
│   ├── README_original_DeepGravity.md      (original, renombrado)
│   ├── CITATION.cff                        (original)
│   ├── osm_query.yaml                      (original)
│   ├── plots.ipynb                         (original)
│   ├── imgs/                               (original)
│   ├── requirements_venv_dg.txt
│   ├── requirements_venv_dg_markdowns.txt
│   ├── requirements_POIs.txt
│   └── deepgravity/
│       ├── main.py                         (modificado)
│       ├── data_loader.py, utils.py, models/, __init__.py   (originales)
│       ├── results/                        (vacío)
│       ├── preprocessing/
│       │   ├── config.py
│       │   ├── preprocesamiento_POIs.ipynb
│       │   ├── preprocesamiento_trazas_telco.ipynb
│       │   └── processed.ipynb
│       └── data/
│           ├── new_york/                   (original)
│           └── chile/
└── 02-prototipo-segmentacion-modalidad-laboral-chile/
    ├── environment.yml
    └── Prototipo_Oficial_MdSpML.ipynb
```

### Prototipo 1 — Deep Gravity Chile

Implementación de referencia de la **rama territorial-relacional** del pipeline. Adapta el repositorio oficial de Deep Gravity a la Provincia de Santiago: construye las unidades territoriales, la teselación, los atributos derivados de OpenStreetMap y la matriz de transiciones comunales, entrena el modelo y audita sus predicciones.

Su documentación operativa completa está en `Informe_Montaje_Deep_Gravity_Chile.pdf`: estructura de la entrega, insumos, modificaciones respecto del repositorio original, orden de ejecución, configuración de la corrida, controles de verificación y limitaciones de interpretación.

### Prototipo 2 — Modelo de Segmentación por Modalidad Laboral

Implementación de referencia de la **rama conductual-individualizada** del pipeline. Recorre la cadena completa desde trazas de telefonía móvil hasta segmentos de modalidad laboral: saneamiento, indexación espacial, construcción de permanencias y desplazamientos, filtro de elegibilidad, anclas residencial y laboral, variables conductuales, agrupamiento, integración de contexto territorial, validación interna y análisis de sensibilidad.

Se entrega como un cuaderno único y autocontenido. Cada sección incluye la justificación metodológica de sus decisiones y las advertencias de interpretación que corresponden a sus productos.

---

## Niveles de ejecución

Los niveles se definen por el **tipo de fuente que requieren**, no por el grado de acceso de quien utiliza el repositorio.

**Nivel 1 — Infraestructura territorial.** Reproducible sin restricciones a partir de fuentes públicas: el extracto nacional de OpenStreetMap, la cartografía DPA 2023 y los resultados del Censo 2024.

**Nivel 2 — Procedimiento telco.** Reejecutable sobre cualquier fuente de telefonía móvil que contenga identificador seudonimizado, marca temporal y coordenadas. El pipeline no exige un esquema de origen particular: exige que la fuente sea transformable a la representación canónica declarada en el manuscrito. Los nombres de campo se declaran en la configuración de cada prototipo.

La proporción entre ambos niveles difiere sustantivamente entre los dos prototipos, y conviene tenerlo presente antes de ejecutar:

| | Nivel 1 | Nivel 2 |
|---|---|---|
| **Prototipo 1** | Toda la cadena territorial: `preprocesamiento_POIs.ipynb` y los chunks iniciales de `processed.ipynb`. Los productos correspondientes se incluyen en la entrega, de modo que pueden usarse sin regenerarlos. | `preprocesamiento_trazas_telco.ipynb`, el resto de `processed.ipynb` y `main.py`. |
| **Prototipo 2** | Únicamente la ingesta del catálogo de puntos de interés (Sección 11.1). | El resto del cuaderno. |

En ambos casos, la ausencia de la fuente de telefonía móvil no impide inspeccionar el procedimiento: impide reproducir la corrida documentada, que no es el propósito de esta entrega.

---

## Fuentes externas

Las fuentes externas no forman parte del repositorio. Se ubican fuera del árbol versionado, en un directorio que el usuario crea en su propio entorno.

| Fuente | Nivel | Dónde obtenerla |
|---|---|---|
| Extracto nacional de OpenStreetMap (`chile.osm.pbf`) | 1 | `download.openstreetmap.fr/extracts/south-america/` |
| Cartografía DPA 2023, capa comunal | 1 | Geoportal de Chile (`geoportal.cl`) |
| Censo 2024, población por comuna | 1 | `censo2024.ine.gob.cl/resultados/` (solo Prototipo 1) |
| Fuente de telefonía móvil | 2 | Provista por el usuario |

Cada prototipo resuelve la ubicación de estas fuentes mediante una variable de entorno, o editando el valor por defecto de su archivo de configuración:

- **Prototipo 1:** `DGCL_DATA_DIR`, con el valor por defecto `external_data/` dentro del directorio del prototipo. Las rutas y parámetros se centralizan en `deepgravity/preprocessing/config.py`.
- **Prototipo 2:** `MDSPML_DATA_DIR`, con el valor por defecto `external_data/` dentro del directorio del prototipo. Las rutas y parámetros se centralizan en la clase `ExperimentConfig`, en la Sección 0 del cuaderno.

Ambos prototipos esperan la misma organización de subdirectorios:

```
external_data/
├── telco/                              *.parquet
├── dpa2023/COMUNAS/COMUNAS_v1.shp
├── osm/chile.osm.pbf
└── censo2024/*.xlsx                    (solo Prototipo 1)
```

Cuando una fuente no se encuentra, ambos prototipos emiten un mensaje que indica la ruta esperada y si corresponde a una fuente pública descargable o a una fuente provista por el usuario.

---

## Cómo empezar

**Prototipo 1.** Consulte `Informe_Montaje_Deep_Gravity_Chile.pdf`, que documenta los tres entornos, el orden de ejecución y los controles de verificación. Los tres cuadernos importan `config.py` desde `deepgravity/preprocessing/`, por lo que deben ejecutarse teniendo ese directorio como directorio de trabajo.

**Prototipo 2.** Cree el entorno desde `environment.yml` y abra el cuaderno **teniendo el directorio del prototipo como directorio de trabajo**: de ello dependen la ubicación de las fuentes externas y la del directorio de artefactos que la ejecución genera. La primera celda imprime un resumen de la configuración activa y de la disponibilidad de cada fuente.

En ambos casos conviene leer antes la sección correspondiente del manuscrito: los prototipos son evidencia sobre una propuesta metodológica, y sus resultados solo son interpretables dentro de ella.

---

## Licencia y atribución

Este repositorio combina componentes sujetos a dos regímenes distintos.

### Componentes desarrollados en el marco de la tesis

Se distribuyen bajo **licencia MIT**, declarada en el archivo `LICENSE` de la raíz.

Comprenden, en el primer prototipo, los cuadernos de `preprocessing/`, `config.py`, los productos territoriales de `data/chile/`, los archivos de dependencias y la guía técnica de montaje; y, en el segundo, la totalidad del directorio.

### Código heredado del repositorio de Deep Gravity

**La licencia MIT no alcanza a estos archivos.**

El primer prototipo se desarrolló a partir del repositorio oficial de Deep Gravity (`github.com/scikit-mobility/DeepGravity/`), que no incorpora un archivo de licencia en su árbol de GitHub. Sus autores, no obstante, depositaron el código en Zenodo bajo licencia **Creative Commons Attribution 4.0 International** (CC BY 4.0):

> F. Simini, G. Barlacchi, M. Luca, L. Pappalardo. *Deep Gravity*. Zenodo (2021). https://doi.org/10.5281/zenodo.5573573

Los archivos heredados se rigen por esos términos (https://creativecommons.org/licenses/by/4.0/), que autorizan su redistribución y adaptación bajo tres condiciones: atribuir a los autores, enlazar la licencia e indicar los cambios realizados. Esta entrega las cumple: conserva `CITATION.cff` y el README original sin modificación, enlaza la licencia aquí y en la Sección 2 de la guía técnica, y documenta en esa misma sección la única modificación de código fuente realizada.

El README original solicita además citar el artículo asociado:

> F. Simini, G. Barlacchi, M. Luca, L. Pappalardo. *A Deep Gravity model for mobility flows generation*. Nature Communications 12, 6576 (2021). https://doi.org/10.1038/s41467-021-26752-4

Los archivos heredados están identificados como tales en el árbol de contenidos de este documento y en la Sección 3 de la guía técnica.

### Fuentes de datos

OpenStreetMap, la División Político-Administrativa 2023 y el Censo 2024 se rigen por sus propios términos de uso, que este repositorio no modifica.

---

## Cómo citar

González Henríquez, M. A. (2026). *Condiciones metodológicas para el uso de datos de telefonía móvil en estudios sociales y urbanos en Chile*. Tesis para optar a los títulos de Ingeniero Civil Industrial y Magíster en Ciencia de Datos, Universidad de Chile.
