"""Conexión con PostgreSQL y migraciones.

La dirección de la base de datos está en el archivo .env (DATABASE_URL),
que cada integrante tiene en su computadora y que NO se sube a GitHub.
"""
import os
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from psycopg.rows import dict_row

MIGRACIONES = Path(__file__).resolve().parent.parent / "db" / "migraciones"


def conectar():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)


def consultar(sql, parametros=()):
    """Ejecuta un SELECT y devuelve las filas como diccionarios."""
    with conectar() as con:
        return con.execute(sql, parametros).fetchall()


def ejecutar(sql, parametros=()):
    """Ejecuta un INSERT, UPDATE o DELETE y devuelve cuántas filas cambió."""
    with conectar() as con:
        return con.execute(sql, parametros).rowcount


def nombre_de_la_base():
    return urlparse(os.getenv("DATABASE_URL", "")).path.lstrip("/") or "sin configurar"


def migrar():
    """Aplica, en orden, los archivos de db/migraciones que la base todavía no tiene."""
    with conectar() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS migraciones ("
            " nombre TEXT PRIMARY KEY,"
            " aplicada_en TIMESTAMP NOT NULL DEFAULT now())"
        )
        hechas = {fila["nombre"] for fila in con.execute("SELECT nombre FROM migraciones")}
        for archivo in sorted(MIGRACIONES.glob("*.sql")):
            if archivo.name in hechas:
                continue
            con.execute(archivo.read_text(encoding="utf-8"))
            con.execute("INSERT INTO migraciones (nombre) VALUES (%s)", (archivo.name,))
            print(f"  Migración aplicada: {archivo.name}")


def migraciones_aplicadas():
    """Los archivos de db/migraciones que esta base ya tiene, en orden."""
    return consultar("SELECT nombre, aplicada_en FROM migraciones ORDER BY nombre")


def reiniciar():
    """Borra las tablas de la demo (solo para volver a ensayar)."""
    with conectar() as con:
        con.execute("DROP TABLE IF EXISTS prestamos, lectores, libros, migraciones CASCADE")
