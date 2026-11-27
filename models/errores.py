"""Errores del negocio.

Cuando una regla de la biblioteca impide una operación (prestar un libro que ya
está prestado, borrar un lector con préstamos...) el Modelo lanza ReglaDeNegocio
con un mensaje claro. El Controlador lo atrapa y se lo muestra al usuario.
"""


class ReglaDeNegocio(Exception):
    pass
