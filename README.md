# Biblioteca MVC

Proyecto de ejemplo del taller **Introducción a Git y GitHub: De Cero a Trabajo Colaborativo Sin USBs**.

Una biblioteca hecha con **Python (Flask)** y **PostgreSQL**, organizada en Modelo, Vista y Controlador. Cada cambio llega por su propia rama y entra a `main` con un Pull Request.

## Qué hace el sistema

| Pantalla | Para qué sirve |
|---|---|
| **Panel** | Indicadores, próximos vencimientos, libros más pedidos, actividad reciente y las migraciones aplicadas en tu base |
| **Catálogo** | Buscar y filtrar libros por estado y género; ficha de cada libro con su historial; agregar, editar y eliminar |
| **Préstamos** | Activos, vencidos e historial; prestar, devolver y renovar |
| **Lectores** | Personas registradas con su carnet, cuántos libros tienen y si pueden pedir otro |

Las reglas de la biblioteca viven en el Modelo y se cumplen siempre: un libro se presta a una sola persona a la vez, cada lector tiene como máximo 3 libros, quien tiene un libro vencido no puede pedir otro, y un préstamo se renueva hasta 2 veces (7 días cada vez) si todavía no venció.

## La arquitectura MVC en este proyecto

| Parte | Dónde | Qué hace |
|---|---|---|
| **Modelo** | `models/libro.py`, `models/lector.py`, `models/prestamo.py` | Habla con PostgreSQL y aplica las reglas del negocio |
| **Vista** | `views/base.html`, `views/panel.html`, `views/libros/`, `views/prestamos/`, `views/lectores/` | Las plantillas HTML que ve el usuario. `views/parciales/ui.html` tiene las piezas reutilizables |
| **Controlador** | `controllers/panel.py`, `controllers/libros.py`, `controllers/prestamos.py`, `controllers/lectores.py` | Reciben cada clic o formulario, le piden al Modelo y eligen la Vista |
| Base de datos | `db/migraciones/*.sql` | La estructura de las tablas, en orden. Se aplican solas al arrancar |
| Arranque | `app.py` | Une las tres partes |

Al pie de cada pantalla aparecen los tres archivos (Modelo, Vista y Controlador) que la dibujan.

Como cada módulo tiene sus propios archivos, cada integrante puede trabajar en uno distinto (por ejemplo, una persona en `lectores`, otra en `libros`) en su propia rama, sin conflictos al hacer merge.

Para agregar una columna se toca todo el recorrido: una **migración** nueva en `db/migraciones/`, el **Modelo** que la lee y la guarda, el **Controlador** que la recibe del formulario y la **Vista** que la muestra.

## Ponerlo en marcha

1. Crea una base de datos vacía en PostgreSQL, por ejemplo `biblioteca`.
2. Copia `.env.example` como `.env` y completa tu contraseña y el nombre de tu base.
3. Instala las dependencias y arranca:

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python app.py
```

4. Abre http://localhost:5000. La primera visita crea las tablas y carga libros, lectores y préstamos de ejemplo.

Para volver a empezar con la base vacía: `.venv\Scripts\python app.py --reiniciar-bd`.

En modo desarrollo la página se recarga sola cuando guardas un archivo o cambias de rama, y la franja de arriba muestra la rama y la base de datos en uso.

## Cómo se trabaja en equipo

1. **Fetch origin** y **Pull origin** para traer lo último de `main`.
2. **Current branch › New branch** con el nombre `feature/lo-que-haces`.
3. Haz tus cambios y pruébalos en tu página local.
4. **Commit to feature/…** con un mensaje que diga qué hiciste.
5. **Publish branch** (o **Push origin** si ya estaba publicada).
6. **Branch › Create pull request**, que alguien lo revise y **Merge pull request**.

Si tu cambio necesita otra columna o tabla, agrégala con un archivo nuevo en `db/migraciones/` (el siguiente número). Nunca edites una migración que ya está en `main`.

## Lo que no se sube

`.env` (tu contraseña y tu base), `.venv/` y `__pycache__/` están en `.gitignore`. Cada integrante tiene su propia base de datos: **Git comparte el código y las migraciones, no los datos.**
