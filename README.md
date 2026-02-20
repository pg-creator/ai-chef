# AI-CHEF

Aplicación web construida con **Streamlit** que genera recetas personalizadas utilizando la API de Gemini a partir de:
- ingredientes disponibles,
- tiempo de cocinado,
- alergias/restricciones del usuario.

Además, incluye un **recetario** persistente donde puedes guardar tus recetas favoritas en una base de datos **SQLite**.

## 🎯 Objetivo del proyecto
Crear un asistente de cocina práctico que:
1. Proponga recetas reales con lo que tienes en la nevera.
2. Respete restricciones (alergias, preferencias, “sin X”, etc.).
3. Permita guardar recetas y revisarlas fácilmente.

## 🧰 Tecnologías utilizadas

### Interfaz
- **Streamlit**: interfaz web rápida, formularios, sidebar y estado de sesión.

### IA / API
- **Google Gen AI SDK** (Gemini): generación de recetas mediante `generate_content`.
- Model: `gemini-2.5-flash` (configurable). 

### Lenguaje
- **Python**

### Base de datos
- **SQLite**: guardado local de recetas (`recetario.db`).
- Funciones: inicialización, inserción y consulta de recetas.

## ✨ Funcionalidades
- Generación de recetas en Markdown (nombre, ingredientes e instrucciones).
- Botones de feedback:
  - 👍 Guardar receta en el recetario
  - 👎 Generar alternativa
- Recetario en barra lateral con recetas guardadas y fecha.

---

> [!IMPORTANT]
> Para poder utilizar o probar es necesario que introduzcas tu clave API de Gemini en .streamlit/secrets.toml.
> Si quieres probarlo pero no tienes API, puedes contactarme para ver el funcionamiento!





## Roadmap
Están desarrollándose nuevas funcionalidades para la aplicación tales como:

- Reconocimiento por foto: detectar ingredientes desde una imagen (nevera / tickets / productos).
- Sistema de preferencias: construir una base de datos más grande basada en gustos del usuario
(recetas guardadas, likes/dislikes, restricciones recurrentes).
- Persistencia avanzada: migración a una BD más robusta (PostgreSQL/Firebase) para perfiles y multiusuario.
- Salida estructurada (JSON) para máxima fiabilidad y renderizado perfecto en UI.
