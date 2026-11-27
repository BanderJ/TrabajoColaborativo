"""MODELO · Préstamo.

Prestar, devolver y renovar. Cada operación sigue los mismos pasos:
  1. buscar los datos   2. revisar las reglas   3. guardar el cambio
"""
from datetime import date, timedelta

from models.db import consultar, ejecutar
from models.errores import ReglaDeNegocio
from models.lector import Lector
from models.libro import Libro

# Cada préstamo junto con su libro y su lector
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

# Qué muestra cada pestaña de la pantalla de préstamos: (filtro, orden)
VISTAS = {
    "activos":   ("p.devuelto_en IS NULL", "p.vence_en"),
    "vencidos":  ("p.devuelto_en IS NULL AND p.vence_en < current_date", "p.vence_en"),
    "historial": ("p.devuelto_en IS NOT NULL", "p.devuelto_en DESC"),
}


class Prestamo:
    PLAZOS = (7, 14, 21)      # Días que se puede llevar un libro
    PLAZO_NORMAL = 14
    DIAS_RENOVACION = 7       # Cuánto suma cada renovación
    MAX_RENOVACIONES = 2

    # ----- Consultas -------------------------------------------------------

    @staticmethod
    def obtener(prestamo_id):
        filas = consultar(_CONSULTA + " WHERE p.id = %s", (prestamo_id,))
        return filas[0] if filas else None

    @staticmethod
    def listar(vista="activos", texto=""):
        filtro, orden = VISTAS.get(vista, VISTAS["activos"])
        valores = []
        if texto:
            filtro += " AND (l.titulo ILIKE %s OR r.nombre ILIKE %s OR r.codigo ILIKE %s)"
            valores = [f"%{texto}%"] * 3
        return consultar(f"{_CONSULTA} WHERE {filtro} ORDER BY {orden}", valores)

    @staticmethod
    def del_libro(libro_id):
        return consultar(_CONSULTA + " WHERE l.id = %s ORDER BY p.prestado_en DESC", (libro_id,))

    @staticmethod
    def del_lector(lector_id):
        return consultar(_CONSULTA + " WHERE r.id = %s ORDER BY p.prestado_en DESC", (lector_id,))

    @staticmethod
    def proximos_a_vencer(limite=6):
        return consultar(_CONSULTA + " WHERE p.devuelto_en IS NULL ORDER BY p.vence_en LIMIT %s", (limite,))

    @staticmethod
    def actividad_reciente(limite=8):
        """Los últimos préstamos y devoluciones, mezclados y del más nuevo al más viejo."""
        return consultar("""
            SELECT 'prestamo' AS tipo, p.prestado_en AS cuando, l.id AS libro_id, l.titulo,
                   r.id AS lector_id, r.nombre AS lector
              FROM prestamos p JOIN libros l ON l.id = p.libro_id JOIN lectores r ON r.id = p.lector_id
            UNION ALL
            SELECT 'devolucion', p.devuelto_en, l.id, l.titulo, r.id, r.nombre
              FROM prestamos p JOIN libros l ON l.id = p.libro_id JOIN lectores r ON r.id = p.lector_id
             WHERE p.devuelto_en IS NOT NULL
             ORDER BY cuando DESC
             LIMIT %s
        """, (limite,))

    @staticmethod
    def resumen():
        """Los números del panel y del menú lateral."""
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
        libro = Libro.obtener(libro_id) if libro_id else None
        lector = Lector.obtener(lector_id) if lector_id else None

        # Las reglas de la biblioteca
        if not libro:
            raise ReglaDeNegocio("Elige un libro del catálogo.")
        if not lector:
            raise ReglaDeNegocio("Elige un lector registrado.")
        if dias not in Prestamo.PLAZOS:
            raise ReglaDeNegocio("Elige un plazo válido.")
        if libro["prestamo_id"]:
            raise ReglaDeNegocio(f"«{libro['titulo']}» ya está prestado.")
        if lector["vencidos"]:
            raise ReglaDeNegocio(f"{lector['nombre']} tiene libros vencidos: primero debe devolverlos.")
        if lector["activos"] >= Lector.MAX_PRESTAMOS:
            raise ReglaDeNegocio(f"{lector['nombre']} ya tiene {Lector.MAX_PRESTAMOS} libros, el máximo permitido.")

        vence_en = date.today() + timedelta(days=dias)
        ejecutar(
            "INSERT INTO prestamos (libro_id, lector_id, vence_en) VALUES (%s, %s, %s)",
            (libro_id, lector_id, vence_en),
        )
        return {"titulo": libro["titulo"], "lector": lector["nombre"], "vence_en": vence_en}

    @staticmethod
    def devolver(prestamo_id):
        prestamo = Prestamo.obtener(prestamo_id)
        if not prestamo or prestamo["devuelto_en"]:
            raise ReglaDeNegocio("Ese préstamo ya estaba cerrado.")

        ejecutar("UPDATE prestamos SET devuelto_en = now() WHERE id = %s", (prestamo_id,))
        return prestamo

    @staticmethod
    def renovar(prestamo_id):
        prestamo = Prestamo.obtener(prestamo_id)
        if not prestamo or prestamo["devuelto_en"]:
            raise ReglaDeNegocio("Ese préstamo ya está cerrado.")
        if prestamo["vencido"]:
            raise ReglaDeNegocio("Un préstamo vencido no se renueva: primero hay que devolver el libro.")
        if prestamo["renovaciones"] >= Prestamo.MAX_RENOVACIONES:
            raise ReglaDeNegocio(f"Este préstamo ya se renovó {Prestamo.MAX_RENOVACIONES} veces, el máximo permitido.")

        vence_en = prestamo["vence_en"] + timedelta(days=Prestamo.DIAS_RENOVACION)
        ejecutar(
            "UPDATE prestamos SET vence_en = %s, renovaciones = renovaciones + 1 WHERE id = %s",
            (vence_en, prestamo_id),
        )
        return {"titulo": prestamo["titulo"], "vence_en": vence_en}
