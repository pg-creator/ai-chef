import sqlite3
from datetime import datetime

# Definimos el nombre de la base de datos
DB_NAME = "recetario.db"

# Definimos la lógica de nuestro recetario
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS recetas_guardadas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            ingredientes_base TEXT,
            tiempo INTEGER,
            receta_completa TEXT,
            fecha TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_receta_db(titulo, ingredientes, tiempo, receta_completa):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
        INSERT INTO recetas_guardadas (titulo, ingredientes_base, tiempo, receta_completa, fecha)
        VALUES (?, ?, ?, ?, ?)
    ''', (titulo, ingredientes, tiempo, receta_completa, fecha_actual))
    conn.commit()
    conn.close()

def obtener_recetas_guardadas():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT titulo, fecha, receta_completa FROM recetas_guardadas ORDER BY id DESC')
    datos = c.fetchall()
    conn.close()
    return datos