"""MODELO · Libro.

Guarda los libros en PostgreSQL y aplica sus reglas.
No sabe nada de HTML ni de botones.
"""
from datetime import date

from models.db import conectar, consultar
from models.errores import ReglaDeNegocio

GENEROS = ("Novela", "Cuento", "Poesía", "Ensayo", "Historia", "Ciencia", "Tecnología", "Infantil")

# Cada libro junto con su préstamo abierto (si lo tiene) y cuántas veces se prestó
_CONSULTA = """
    SELECT l.id, l.titulo, l.autor, l.anio, l.genero, l.creado_en,
           p.id AS prestamo_id, p.prestado_en, p.vence_en,
           (p.vence_en - current_date) AS dias_restantes,
           r.id AS lector_id, r.nombre AS lector,
           (SELECT COUNT(*) FROM prestamos x WHERE x.libro_id = l.id) AS veces_prestado
      FROM libros l
      LEFT JOIN prestamos p ON p.libro_id = l.id AND p.devuelto_en IS NULL
      LEFT JOIN lectores  r ON r.id = p.lector_id
"""


class Libro:
    CAMPOS = ("titulo", "autor", "anio", "genero")

    @staticmethod
    def buscar(texto="", estado="", genero=""):
        filtros, valores = [], []
        if texto:
            filtros.append("(l.titulo ILIKE %s OR l.autor ILIKE %s)")
            valores += [f"%{texto}%", f"%{texto}%"]
        if estado == "disponible":
            filtros.append("p.id IS NULL")
        elif estado == "prestado":
            filtros.append("p.id IS NOT NULL")
        elif estado == "vencido":
            filtros.append("p.vence_en < current_date")
        if genero:
            filtros.append("l.genero = %s")
            valores.append(genero)
        donde = (" WHERE " + " AND ".join(filtros)) if filtros else ""
        return consultar(_CONSULTA + donde + " ORDER BY l.titulo", valores)

    @staticmethod
    def obtener(libro_id):
        filas = consultar(_CONSULTA + " WHERE l.id = %s", (libro_id,))
        return filas[0] if filas else None

    @staticmethod
    def disponibles():
        return consultar(_CONSULTA + " WHERE p.id IS NULL ORDER BY l.titulo")

    @staticmethod
    def generos_en_uso():
        filas = consultar("SELECT DISTINCT genero FROM libros WHERE genero IS NOT NULL ORDER BY genero")
        return [f["genero"] for f in filas]

    @staticmethod
    def mas_prestados(limite=5):
        return consultar("""
            SELECT l.id, l.titulo, l.autor, l.genero, COUNT(p.id) AS veces
              FROM libros l
              JOIN prestamos p ON p.libro_id = l.id
             GROUP BY l.id
             ORDER BY veces DESC, l.titulo
             LIMIT %s
        """, (limite,))

    @staticmethod
    def validar(datos):
        """Limpia lo que llegó del formulario. Devuelve (datos_limpios, errores)."""
        limpios = {campo: (datos.get(campo) or "").strip() for campo in Libro.CAMPOS}
        errores = {}
        if not limpios["titulo"]:
            errores["titulo"] = "Escribe el título."
        if not limpios["autor"]:
            errores["autor"] = "Escribe el autor."
        if limpios["anio"]:
            hoy = date.today().year
            if not limpios["anio"].isdigit() or not 1000 <= int(limpios["anio"]) <= hoy:
                errores["anio"] = f"Usa un año entre 1000 y {hoy}."
        if limpios["genero"] and limpios["genero"] not in GENEROS:
            errores["genero"] = "Elige un género de la lista."
        limpios["anio"] = int(limpios["anio"]) if limpios["anio"] and "anio" not in errores else None
        limpios["genero"] = limpios["genero"] or None
        return limpios, errores

    @staticmethod
    def crear(datos):
        columnas = ", ".join(Libro.CAMPOS)
        marcas = ", ".join(["%s"] * len(Libro.CAMPOS))
        fila = consultar(
            f"INSERT INTO libros ({columnas}) VALUES ({marcas}) RETURNING id",
            [datos[campo] for campo in Libro.CAMPOS],
        )
        return fila[0]["id"]

    @staticmethod
    def actualizar(libro_id, datos):
        cambios = ", ".join(f"{campo} = %s" for campo in Libro.CAMPOS)
        consultar(
            f"UPDATE libros SET {cambios} WHERE id = %s RETURNING id",
            [datos[campo] for campo in Libro.CAMPOS] + [libro_id],
        )

    @staticmethod
    def eliminar(libro_id):
        """Regla: un libro con historial de préstamos no se borra, para no perder ese historial."""
        with conectar() as con:
            usado = con.execute(
                "SELECT COUNT(*) AS n FROM prestamos WHERE libro_id = %s", (libro_id,)
            ).fetchone()["n"]
            if usado:
                raise ReglaDeNegocio(
                    f"Este libro tiene {usado} préstamo(s) registrados: no se puede borrar sin perder el historial."
                )
            con.execute("DELETE FROM libros WHERE id = %s", (libro_id,))
