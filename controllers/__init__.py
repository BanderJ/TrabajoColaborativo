"""CONTROLADORES · uno por módulo de la biblioteca.

  panel.py      el inicio con los indicadores
  libros.py     el catálogo
  prestamos.py  prestar, devolver y renovar
  lectores.py   las personas registradas

Cada integrante puede trabajar en un archivo distinto, en su propia rama,
sin pisar el trabajo de los demás.
"""
from flask import render_template, request

from models.prestamo import Prestamo


def destino_seguro(por_defecto):
    """A dónde volver después de un formulario: solo a páginas de esta misma app."""
    volver = request.form.get("volver") or request.args.get("volver") or ""
    return volver if volver.startswith("/") and not volver.startswith("//") else por_defecto


def registrar(app):
    from controllers import lectores, libros, panel, prestamos

    for modulo in (panel, libros, prestamos, lectores):
        app.register_blueprint(modulo.bp)

    @app.context_processor
    def contadores_del_menu():
        # Los números del menú lateral (por ejemplo, cuántos préstamos están vencidos)
        return {"menu": Prestamo.resumen()}

    @app.errorhandler(404)
    def no_encontrado(_error):
        return render_template("error.html"), 404
