-- 002 · Lectores registrados, plazos de devolución y géneros
-- Se aplica sola al arrancar. No se edita la 001: la base evoluciona con archivos nuevos.

-- 1. Lectores: cada préstamo pasa a pertenecer a una persona registrada con su carnet
CREATE SEQUENCE lectores_codigo_seq;

CREATE TABLE lectores (
    id         SERIAL PRIMARY KEY,
    nombre     VARCHAR(60)  NOT NULL,
    codigo     VARCHAR(12)  NOT NULL UNIQUE
               DEFAULT 'L-' || lpad(nextval('lectores_codigo_seq')::text, 4, '0'),
    email      VARCHAR(120),
    creado_en  TIMESTAMP    NOT NULL DEFAULT now()
);
ALTER SEQUENCE lectores_codigo_seq OWNED BY lectores.codigo;

-- Los nombres que ya estaban escritos a mano en los préstamos se convierten en lectores
INSERT INTO lectores (nombre)
SELECT DISTINCT lector FROM prestamos ORDER BY lector;

INSERT INTO lectores (nombre, email) VALUES
    ('Jorge Huamán',   'jorge.huaman@correo.edu'),
    ('Lucía Torres',   'lucia.torres@correo.edu'),
    ('Diego Ramos',    'diego.ramos@correo.edu'),
    ('Valeria Rojas',  'valeria.rojas@correo.edu'),
    ('Camila Mendoza', 'camila.mendoza@correo.edu');

-- 2. Préstamos: lector registrado, fecha de vencimiento y renovaciones
ALTER TABLE prestamos
    ADD COLUMN lector_id    INT REFERENCES lectores (id),
    ADD COLUMN vence_en     DATE,
    ADD COLUMN renovaciones SMALLINT NOT NULL DEFAULT 0;

UPDATE prestamos p SET lector_id = r.id FROM lectores r WHERE r.nombre = p.lector;
UPDATE prestamos SET vence_en = prestado_en::date + 14;

ALTER TABLE prestamos
    ALTER COLUMN lector_id SET NOT NULL,
    ALTER COLUMN vence_en  SET NOT NULL,
    DROP COLUMN lector;

-- Regla también en la base: un libro no puede tener dos préstamos abiertos a la vez
CREATE UNIQUE INDEX un_prestamo_abierto_por_libro
    ON prestamos (libro_id) WHERE devuelto_en IS NULL;

-- 3. Libros: género, y más títulos para que el catálogo se vea como uno real
ALTER TABLE libros ADD COLUMN genero VARCHAR(40);

UPDATE libros SET genero = 'Novela'
 WHERE titulo IN ('Los ríos profundos', 'La ciudad y los perros', 'Cien años de soledad');
UPDATE libros SET genero = 'Infantil'   WHERE titulo = 'El principito';
UPDATE libros SET genero = 'Tecnología' WHERE titulo IN ('Código limpio', 'Pro Git');

INSERT INTO libros (titulo, autor, anio, genero)
SELECT n.titulo, n.autor, n.anio, n.genero
  FROM (VALUES
    ('Rayuela',                    'Julio Cortázar',             1963, 'Novela'),
    ('Pedro Páramo',               'Juan Rulfo',                 1955, 'Novela'),
    ('Ficciones',                  'Jorge Luis Borges',          1944, 'Cuento'),
    ('Tradiciones peruanas',       'Ricardo Palma',              1872, 'Cuento'),
    ('Los heraldos negros',        'César Vallejo',              1918, 'Poesía'),
    ('Veinte poemas de amor',      'Pablo Neruda',               1924, 'Poesía'),
    ('Sapiens',                    'Yuval Noah Harari',          2011, 'Historia'),
    ('Breve historia del tiempo',  'Stephen Hawking',            1988, 'Ciencia'),
    ('El programador pragmático',  'Andrew Hunt y David Thomas', 1999, 'Tecnología')
  ) AS n (titulo, autor, anio, genero)
 WHERE NOT EXISTS (SELECT 1 FROM libros l WHERE l.titulo = n.titulo);

-- 4. Historial de ejemplo: préstamos pasados, uno vencido y otros por vencer.
--    Los días son relativos a hoy (negativo = en el pasado).
INSERT INTO prestamos (libro_id, lector_id, prestado_en, vence_en, devuelto_en)
SELECT l.id, r.id,
       now() + make_interval(days => d.prestado),
       current_date + d.vence,
       CASE WHEN d.devuelto IS NULL THEN NULL ELSE now() + make_interval(days => d.devuelto) END
  FROM (VALUES
    ('Cien años de soledad',      'Jorge Huamán',   -60, -46, -48),
    ('Pro Git',                   'Lucía Torres',   -44, -30, -31),
    ('Código limpio',             'Diego Ramos',    -38, -24, -20),
    ('Cien años de soledad',      'Valeria Rojas',  -30, -16, -17),
    ('Rayuela',                   'Camila Mendoza', -28, -14, -15),
    ('El principito',             'Jorge Huamán',   -22,  -8, -12),
    ('Pro Git',                   'Diego Ramos',    -18,  -4,  -6),
    ('Cien años de soledad',      'Lucía Torres',   -15,  -1,  -3),
    ('Sapiens',                   'Valeria Rojas',  -14,   0,  -2),
    -- Préstamos abiertos: usan libros nuevos de esta migración, así nunca chocan con otro abierto
    ('Breve historia del tiempo', 'Lucía Torres',   -19,  -5, NULL::int),
    ('Pedro Páramo',              'Jorge Huamán',   -12,   2, NULL::int),
    ('El programador pragmático', 'Valeria Rojas',   -3,  11, NULL::int),
    ('Ficciones',                 'Camila Mendoza',  -5,   9, NULL::int)
  ) AS d (titulo, lector, prestado, vence, devuelto)
  JOIN libros   l ON l.titulo = d.titulo
  JOIN lectores r ON r.nombre = d.lector
 WHERE d.devuelto IS NOT NULL
    OR NOT EXISTS (SELECT 1 FROM prestamos p WHERE p.libro_id = l.id AND p.devuelto_en IS NULL);
