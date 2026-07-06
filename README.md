# Albion Market Test

Aplicación pequeña de escritorio para consultar precios del mercado de Albion Online usando Tkinter y la API pública de Albion Online Data Project.

## Requisitos

- Python 3.12 o superior.
- Windows.
- Conexión a internet.

## Instalación

Desde esta carpeta:

```bash
pip install -r requirements.txt
python main.py
```

Si en Windows tienes varias versiones de Python instaladas, también puedes usar:

```bash
py -3.12 -m pip install -r requirements.txt
py -3.12 main.py
```

## Modo desarrollo con reinicio automatico

Si vas a editar el codigo y quieres que la ventana se reinicie automaticamente al guardar cambios en archivos `.py`, usa:

```bash
.venv\Scripts\python.exe dev_run.py
```

Este modo vigila `main.py`, `config.py`, `api_client.py`, `models.py` y cualquier otro archivo `.py` del proyecto.

## Uso

1. Elige el servidor: Americas, Europe o Asia.
2. Elige la ciudad. Por defecto se consulta solo `Bridgewatch` para que la peticion sea mas liviana.
3. Escribe un producto si quieres limitar la consulta, por ejemplo `guja`, `glaive`, `t6 guja`, `guja fisurante`, `adepts heron spear` o `lanza garza`.
4. Filtra por `Tier`, `Encantamiento` y `Calidad` si necesitas una consulta mas precisa.
5. Pulsa `Actualizar precios`.
6. Pulsa los encabezados de la tabla para ordenar por tier, ciudad, precio, calidad o estado.
7. Activa `Actualización automática` si quieres repetir la consulta cada 30 segundos, 60 segundos o 5 minutos.

La aplicacion puede consultar el catalogo completo incluido en `catalog.py` o solo los productos manuales de `config.py`. Cuando escribes en `Buscar producto`, ese texto filtra el catalogo antes de llamar a la API, por lo que la consulta es menos pesada. Los filtros de tier y encantamiento tambien reducen los IDs enviados. El filtro de calidad se envia a la API como `qualities`. La tabla muestra nombre en ingles y nombre en español cuando el catalogo local lo tiene. Las fechas que entrega la API se convierten a la zona horaria local del equipo.

## Cantidad de unidades

El endpoint publico de precios actuales (`/api/v2/stats/prices`) entrega precios minimos/maximos y fechas por item, ciudad y calidad. No entrega la cantidad total de unidades activas en venta o compra para una orden actual.

Por eso las columnas de cantidad se mantienen seguras, pero normalmente quedaran vacias. Para saber unidades activas exactas haria falta un endpoint de libro de ordenes activo, y ese dato no esta documentado en la API publica usada por esta app.

## Albion Data Client

La app puede intentar abrir Albion Data Client al iniciar. Esto se configura en `config.py`:

```python
DATA_CLIENT_AUTO_START = True
DATA_CLIENT_PATHS = [
    r"C:\Program Files\Albion Data Client\albiondata-client.exe",
    r"C:\Program Files (x86)\Albion Data Client\albiondata-client.exe",
]
```

Si Albion Data Client esta instalado en otra carpeta, agrega esa ruta a `DATA_CLIENT_PATHS`.

Albion Data Client no compra, vende ni toca el juego. Su funcion es leer datos de mercado que cargas en Albion Online y subirlos al Albion Online Data Project.

## Agregar productos o ciudades

Edita `config.py`.

Para agregar productos manuales al modo `Solo seleccionados`:

```python
ITEMS = [
    "T4_BAG",
    "T4_CAPE",
    "T4_ORE",
    "T5_ORE",
]
```

Para mostrar nombres legibles y poder buscarlos por texto:

```python
ITEM_NAMES = {
    "T4_BAG": "Adept's Bag",
    "T4_CAPE": "Adept's Cape",
    "T4_ORE": "Iron Ore",
    "T5_ORE": "Titanium Ore",
}
```

Para agregar ciudades:

```python
LOCATIONS = [
    "Bridgewatch",
    "Martlock",
    "Caerleon",
    "Thetford",
]
```

Guarda el archivo y vuelve a ejecutar `python main.py`.

## Actualizar el catalogo oficial

El catalogo principal se genera desde el metadata oficial recomendado por Albion Online Data Project.

Para actualizarlo:

```bash
.venv\Scripts\python.exe update_catalog.py
```

Esto crea o reemplaza `data/items_catalog.json` con nombres en ingles y español. La app usa ese archivo para buscar armas, cascos, armaduras, botas, offhands, bolsas, capas, monturas, herramientas y recursos.

## Estado de los datos

- `Reciente`: el dato más nuevo tiene menos de 5 minutos.
- `Precaución`: el dato más nuevo tiene entre 5 y 30 minutos.
- `Desactualizado`: el dato más nuevo tiene más de 30 minutos.
- `Sin datos`: no hay precio válido o falta la fecha de actualización.

Algunas respuestas del endpoint de precios pueden no incluir cantidades de órdenes. En ese caso la columna de cantidad queda vacía de forma segura.
