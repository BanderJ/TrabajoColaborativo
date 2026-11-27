"""MODELO · Préstamo.

Prestar, devolver y renovar, con las reglas de la biblioteca:
  - un libro solo se presta si no tiene un préstamo abierto
  - un lector con libros vencidos no puede pedir otro
  - nadie tiene más de Lector.MAX_PRESTAMOS libros a la vez
  - un préstamo se renueva como máximo MAX_RENOVACIONES veces, y nunca si ya venció
"""
from psycopg import errors

from models.db import conectar, consultar
from models.errores import ReglaDeNegocio
from models.lector import Lector

_CONSULTA = """
    SELECT p.id, p.prestado_en, p.vence_en, p.devuelto_en, p.renovaciones,
           (p.vence_en - current_date) AS dias_restantes,
           (p.devuelto_en IS NULL AND p.vence_en < current_date) AS vencido,
           (p.devuelto_en::date > p.vence_en) AS devuelto_tarde,
           l.id AS libro_id, l.titulo, l.autor, l.genero,
           r.id AS lector_id, r.nombre AS lector, r.codigo
      FROM prestamos p
      JOIN libros   l ON l.id = p.libro_id
      JOIN lectores r ON r.id = p.lector_id
"""

# Qué muestra cada pestaña de la pantalla de préstamos
VISTAS = {
    "activos":   ("p.devuelto_en IS NULL", "p.vence_en, p.id"),
    "vencidos":  ("p.devuelto_en IS NULL AND p.vence_en < current_date", "p.vence_en, p.id"),
    "historial": ("p.devuelto_en IS NOT NULL", "p.devuelto_en DESC"),
}


class Prestamo:
    PLAZOS = (7, 14, 21)
    PLAZO_NORMAL = 14
    DIAS_RENOVACION = 7
    MAX_RENOVACIONES = 2

    # ----- Consultas -------------------------------------------------------

    @staticmethod
    def listar(vista="activos", texto=""):
        condicion, orden = VISTAS.get(vista, VISTAS["activos"])
        valores = []
        if texto:
            condicion += " AND (l.titulo ILIKE %s OR r.nombre ILIKE %s OR r.codigo ILIKE %s)"
            valores = [f"%{texto}%"] * 3
        return consultar(f"{_CONSULTA} WHERE {condicion} ORDER BY {orden}", valores)

    @staticmethod
    def del_libro(libro_id):
        return consultar(_CONSULTA + " WHERE l.id = %s ORDER BY p.prestado_en DESC", (libro_id,))

    @staticmethod
    def del_lector(lector_id):
        return consultar(
            _CONSULTA + " WHERE r.id = %s ORDER BY p.devuelto_en IS NOT NULL, p.prestado_en DESC",
            (lector_id,),
        )

    @staticmethod
    def proximos_a_vencer(limite=6):
        return consultar(_CONSULTA + " WHERE p.devuelto_en IS NULL ORDER BY p.vence_en LIMIT %s", (limite,))

    @staticmethod
    def actividad_reciente(limite=8):
        return consultar("""
            SELECT * FROM (
                SELECT 'prestamo' AS tipo, p.prestado_en AS cuando,
                       l.id AS libro_id, l.titulo, r.id AS lector_id, r.nombre AS lector
                  FROM prestamos p JOIN libros l ON l.id = p.libro_id JOIN lectores r ON r.id = p.lector_id
                UNION ALL
                SELECT 'devolucion', p.devuelto_en,
                       l.id, l.titulo, r.id, r.nombre
                  FROM prestamos p JOIN libros l ON l.id = p.libro_id JOIN lectores r ON r.id = p.lector_id
                 WHERE p.devuelto_en IS NOT NULL
            ) AS eventos
            ORDER BY cuando DESC
            LIMIT %s
        """, (limite,))

    @staticmethod
    def resumen():
        fila = consultar("""
            SELECT (SELECT COUNT(*) FROM libros)   AS libros,
                   (SELECT COUNT(*) FROM lectores) AS lectores,
                   COUNT(*) FILTER (WHERE devuelto_en IS NULL) AS activos,
                   COUNT(*) FILTER (WHERE devuelto_en IS NULL AND vence_en < current_date) AS vencidos,
                   COUNT(*) FILTER (WHERE devuelto_en IS NULL
                                      AND vence_en BETWEEN current_date AND current_date + 3) AS por_vencer,
                   COUNT(*) FILTER (WHERE prestado_en >= date_trunc('month', now())) AS del_mes
              FROM prestamos
        """)[0]
        fila["disponibles"] = fila["libros"] - fila["activos"]
        return fila

    # ----- Operaciones -----------------------------------------------------

    @staticmethod
    def prestar(libro_id, lector_id, dias):
        """Registra un préstamo si se cumplen todas las reglas. Devuelve sus datos."""
        if dias not in Prestamo.PLAZOS:
            raise ReglaDeNegocio("Elige un plazo válido.")
        with conectar() as con:
            lector = con.execute("""
                SELECT r.nombre,
                       COUNT(p.id) FILTER (WHERE p.devuelto_en IS NULL) AS activos,
                       COUNT(p.id) FILTER (WHERE p.devuelto_en IS NULL AND p.vence_en < current_date) AS vencidos
                  FROM lectores r LEFT JOIN prestamos p ON p.lector_id = r.id
                 WHERE r.id = %s GROUP BY r.id
            """, (lector_id,)).fetchone()
            if not lector:
                raise ReglaDeNegocio("Elige un lector registrado.")
            if lector["vencidos"]:
                raise ReglaDeNegocio(
                    f"{lector['nombre']} tiene {lector['vencidos']} libro(s) vencido(s): primero debe devolverlos."
                )
            if lector["activos"] >= Lector.MAX_PRESTAMOS:
                raise ReglaDeNegocio(
                    f"{lector['nombre']} ya tiene {Lector.MAX_PRESTAMOS} libros, el máximo permitido."
                )

            libro = con.execute("""
                SELECT l.titulo, p.id AS abierto
                  FROM libros l LEFT JOIN prestamos p ON p.libro_id = l.id AND p.devuelto_en IS NULL
                 WHERE l.id = %s
            """, (libro_id,)).fetchone()
            if not libro:
                raise ReglaDeNegocio("Elige un libro del catálogo.")
            if libro["abierto"]:
                raise ReglaDeNegocio(f"«{libro['titulo']}» ya está prestado.")

            try:
                nuevo = con.execute("""
                    INSERT INTO prestamos (libro_id, lector_id, vence_en)
                    VALUES (%s, %s, current_date + %s::int)
                    RETURNING vence_en
                """, (libro_id, lector_id, dias)).fetchone()
            except errors.UniqueViolation:
                # Otra persona lo prestó en el mismo instante: la base de datos lo impide
                raise ReglaDeNegocio(f"«{libro['titulo']}» ya está prestado.") from None
        return {"titulo": libro["titulo"], "lector": lector["nombre"], "vence_en": nuevo["vence_en"]}

    @staticmethod
    def devolver(prestamo_id):
        filas = consultar("""
            UPDATE prestamos p SET devuelto_en = now()
              FROM libros l
             WHERE p.id = %s AND p.devuelto_en IS NULL AND l.id = p.libro_id
            RETURNING l.titulo, GREATEST(current_date - p.vence_en, 0) AS dias_tarde
        """, (prestamo_id,))
        if not filas:
            raise ReglaDeNegocio("Ese préstamo ya estaba cerrado.")
        return filas[0]

    @staticmethod
    def renovar(prestamo_id):
        with conectar() as con:
            p = con.execute("""
                SELECT p.devuelto_en, p.renovaciones, (p.vence_en < current_date) AS vencido, l.titulo
                  FROM prestamos p JOIN libros l ON l.id = p.libro_id
                 WHERE p.id = %s
                   FOR UPDATE OF p
            """, (prestamo_id,)).fetchone()
            if not p or p["devuelto_en"]:
                raise ReglaDeNegocio("Ese préstamo ya está cerrado.")
            if p["vencido"]:
                raise ReglaDeNegocio("Un préstamo vencido no se renueva: primero hay que devolver el libro.")
            if p["renovaciones"] >= Prestamo.MAX_RENOVACIONES:
                raise ReglaDeNegocio(
                    f"«{p['titulo']}» ya se renovó {Prestamo.MAX_RENOVACIONES} veces, el máximo permitido."
                )
            nuevo = con.execute("""
                UPDATE prestamos
                   SET vence_en = vence_en + %s::int, renovaciones = renovaciones + 1
                 WHERE id = %s
                RETURNING vence_en
            """, (Prestamo.DIAS_RENOVACION, prestamo_id)).fetchone()
        return {"titulo": p["titulo"], "vence_en": nuevo["vence_en"]}
