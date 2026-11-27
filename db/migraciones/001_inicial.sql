-- 001 · Estructura inicial de la Biblioteca
-- Se aplica sola la primera vez que arranca la app (python app.py).

CREATE TABLE libros (
    id         SERIAL PRIMARY KEY,
    titulo     VARCHAR(120) NOT NULL,
    autor      VARCHAR(80)  NOT NULL,
    anio       SMALLINT,
    creado_en  TIMESTAMP    NOT NULL DEFAULT now()
);

CREATE TABLE prestamos (
    id           SERIAL PRIMARY KEY,
    libro_id     INT          NOT NULL REFERENCES libros (id),
    lector       VARCHAR(60)  NOT NULL,
    prestado_en  TIMESTAMP    NOT NULL DEFAULT now(),
    devuelto_en  TIMESTAMP
);

INSERT INTO libros (titulo, autor, anio) VALUES
    ('Los ríos profundos',     'José María Arguedas',       1958),
    ('La ciudad y los perros', 'Mario Vargas Llosa',        1963),
    ('Cien años de soledad',   'Gabriel García Márquez',    1967),
    ('El principito',          'Antoine de Saint-Exupéry',  1943),
    ('Código limpio',          'Robert C. Martin',          2008),
    ('Pro Git',                'Scott Chacon y Ben Straub', 2014);

INSERT INTO prestamos (libro_id, lector)
SELECT id, 'María' FROM libros WHERE titulo = 'La ciudad y los perros';
