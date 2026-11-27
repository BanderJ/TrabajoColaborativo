"""MODELO · Lector.

Las personas registradas que pueden pedir libros, con su carnet (código).
"""
import re

from models.db import consultar, ejecutar
from models.errores import ReglaDeNegocio

# Cada lector con sus préstamos: abiertos, vencidos y el total histórico
_CONSULTA = """
    SELECT r.id, r.nombre, r.codigo, r.email, r.creado_en,
           COUNT(p.id) FILTER (WHERE p.devuelto_en IS NULL) AS activos,
           COUNT(p.id) FILTER (WHERE p.devuelto_en IS NULL AND p.vence_en < current_date) AS vencidos,
           COUNT(p.id) AS total
      FROM lectores r
      LEFT JOIN prestamos p ON p.lector_id = r.id
"""

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Lector:
    CAMPOS = ("nombre", "email")
    MAX_PRESTAMOS = 3  # Regla: nadie puede tener más de 3 libros a la vez

    @staticmethod
    def buscar(texto=""):
        donde, valores = "", []
        if texto:
            donde = " WHERE r.nombre ILIKE %s OR r.codigo ILIKE %s OR r.email ILIKE %s"
            valores = [f"%{texto}%"] * 3
        return consultar(_CONSULTA + donde + " GROUP BY r.id ORDER BY r.nombre", valores)

    @staticmethod
    def obtener(lector_id):
        filas = consultar(_CONSULTA + " WHERE r.id = %s GROUP BY r.id", (lector_id,))
        return filas[0] if filas else None

    @staticmethod
    def validar(datos):
        limpios = {campo: (datos.get(campo) or "").strip() for campo in Lector.CAMPOS}
        errores = {}
        if not limpios["nombre"]:
            errores["nombre"] = "Escribe el nombre completo."
        elif len(limpios["nombre"]) > 60:
            errores["nombre"] = "Máximo 60 caracteres."
        if limpios["email"] and not _EMAIL.match(limpios["email"]):
            errores["email"] = "Ese correo no parece válido."
        limpios["email"] = limpios["email"] or None
        return limpios, errores

    @staticmethod
    def crear(datos):
        """El código de carnet (L-0001, L-0002...) lo pone la base de datos."""
        fila = consultar(
            "INSERT INTO lectores (nombre, email) VALUES (%s, %s) RETURNING id",
            (datos["nombre"], datos["email"]),
        )
        return fila[0]["id"]

    @staticmethod
    def actualizar(lector_id, datos):
        ejecutar(
            "UPDATE lectores SET nombre = %s, email = %s WHERE id = %s",
            (datos["nombre"], datos["email"], lector_id),
        )

    @staticmethod
    def eliminar(lector_id):
        lector = Lector.obtener(lector_id)
        # Regla: un lector con préstamos no se borra
        if lector["total"]:
            raise ReglaDeNegocio("Este lector tiene préstamos en su historial: no se puede borrar.")
        ejecutar("DELETE FROM lectores WHERE id = %s", (lector_id,))
