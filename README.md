# Albion Market Test

Aplicacion pequena de escritorio para consultar precios del mercado de Albion Online usando Tkinter y la API publica de Albion Online Data Project.

Incluye dos pestañas:

- `Mercado`: consulta precios actuales por servidor, ciudad, producto, tier, encantamiento y calidad.
- `Utilidad`: fase 1 de calculadora de crafteo para comparar costo de materiales contra precio de venta por ciudad.

## Requisitos

- Python 3.12 o superior.
- Windows.
- Conexion a internet.

## Instalacion

Desde esta carpeta:

```bash
pip install -r requirements.txt
python main.py
```

Si en Windows tienes varias versiones de Python instaladas, tambien puedes usar el entorno virtual del proyecto:

```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe main.py
```

## Modo desarrollo con reinicio automatico

Si vas a editar el codigo y quieres que la ventana se reinicie automaticamente al guardar cambios en archivos `.py`, usa:

```bash
.venv\Scripts\python.exe dev_run.py
```

Este modo vigila los archivos `.py` del proyecto.

## Uso: Mercado

1. Elige el servidor: Americas, Europe o Asia.
2. Elige la ciudad. Por defecto se consulta solo `Bridgewatch` para que la peticion sea mas liviana.
3. Escribe un producto si quieres limitar la consulta, por ejemplo `guja`, `glaive`, `t6 guja`, `guja fisurante`, `adepts heron spear` o `lanza garza`.
4. Filtra por `Tier`, `Encantamiento` y `Calidad` si necesitas una consulta mas precisa.
5. Pulsa `Actualizar precios`.
6. Pulsa los encabezados de la tabla para ordenar por tier, ciudad, precio, calidad o estado.
7. Activa `Actualizacion automatica` si quieres repetir la consulta cada 30 segundos, 60 segundos o 5 minutos.

La tabla muestra nombre en ingles y nombre en espanol cuando el catalogo local lo tiene. Las fechas que entrega la API se convierten a la zona horaria local del equipo.

## Uso: Utilidad

La pestaña `Utilidad` compara una receta contra precios de mercado.

1. Elige servidor.
2. Busca un item fabricable, por ejemplo `rift glaive`, `guja fisurante`, `jacket`, `bolsa` o `sword`.
3. Filtra por tier y encantamiento.
4. Selecciona la receta.
5. Elige la ciudad donde compras materiales.
6. Escribe cantidad a fabricar.
7. Ajusta `Retorno %`, `Fee/u` de estacion e `Impuesto %`.
8. Pulsa `Calcular utilidad`.

La fase 1 usa:

- Recetas oficiales extraidas de `ao-bin-dumps`.
- Precio minimo de venta de materiales en la ciudad seleccionada.
- Precio minimo de venta del item final en cada ciudad configurada.
- Calidad normal para materiales y producto final.
- Retorno manual aplicado solo a materiales retornables.
- Fee de estacion manual por unidad.
- Impuesto manual sobre la venta.

Todavia no automatiza bonos por ciudad, nutricion de estacion, foco exacto por especializacion, calidad esperada ni impuestos personalizados por premium. Esos puntos quedan preparados para fases siguientes.

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

## Actualizar catalogo y recetas

El catalogo de nombres se genera desde el metadata oficial recomendado por Albion Online Data Project:

```bash
.venv\Scripts\python.exe update_catalog.py
```

Las recetas de crafteo se generan desde el dump oficial `items.json`:

```bash
.venv\Scripts\python.exe update_recipes.py
```

Estos comandos crean o reemplazan:

- `data/items_catalog.json`
- `data/recipes.json`

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

## Cantidad de unidades

El endpoint publico de precios actuales (`/api/v2/stats/prices`) entrega precios minimos/maximos y fechas por item, ciudad y calidad. No entrega la cantidad total de unidades activas en venta o compra para una orden actual.

Por eso las columnas de cantidad se mantienen seguras, pero normalmente quedaran vacias. Para saber unidades activas exactas haria falta un endpoint de libro de ordenes activo, y ese dato no esta documentado en la API publica usada por esta app.

## Estado de los datos

- `Reciente`: el dato mas nuevo tiene menos de 5 minutos.
- `Precaucion`: el dato mas nuevo tiene entre 5 y 30 minutos.
- `Desactualizado`: el dato mas nuevo tiene mas de 30 minutos.
- `Sin datos`: no hay precio valido o falta la fecha de actualizacion.

Algunas respuestas del endpoint de precios pueden no incluir cantidades de ordenes. En ese caso la columna de cantidad queda vacia de forma segura.
