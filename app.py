import json
from datetime import date
from typing import Literal, Optional, Dict, Any

import streamlit as st
from google import genai

from models import (
    Receta,
    MenuSemanal,
    receta_json_schema,
    menu_semanal_json_schema,
)
from recetario import (
    init_db,
    guardar_receta_db,
    obtener_recetas_guardadas,
    guardar_menu_semanal,
    obtener_menus_semanales,
)

# Inicialización de la base de datos
init_db()

# Carga de la api y manejo de error si no está configurada
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("Falta la API key. Añádela en .streamlit/secrets.toml")
    st.stop()

# Si da fallo la api y está correctamente añadida probar esto:
#   import os
#   os.environ["GEMINI_API_KEY"] = api_key

# Inicializamos el cliente
client = genai.Client()

# Prompt receta
def _build_prompt_receta(ingredientes: str, tiempo: int, comentarios: str, es_reintento: bool) -> str:
    nota_reintento = ""
    if es_reintento:
        nota_reintento = (
            "\nNOTA: Al usuario no le gustó la propuesta anterior. "
            "Genera una receta COMPLETAMENTE DISTINTA a tu intento previo usando los mismos parámetros. "
            "No añadas ingredientes imposibles de encontrar."
        )

    return f"""
Actúa como un chef experto.

El usuario te indica:
- Ingredientes disponibles: {ingredientes}
- Tiempo máximo para cocinar: {tiempo} minutos
- Restricciones o comentarios: {comentarios}

Debes devolver UNA receta para UNA sola persona (raciones_base=1).

Responde ÚNICAMENTE en formato JSON que cumpla este esquema (no añadas comentarios ni markdown fuera del JSON):
- tipo: "receta"
- titulo: string
- raciones_base: 1
- tiempo_min: entero > 0
- ingredientes: lista de objetos con:
  - nombre: string (en singular, sin mayúsculas superfluas)
  - cantidad: número > 0 referido a UNA persona
  - unidad: string (por ejemplo: "g", "ml", "ud", "cda")
  - nota: string opcional
- pasos: lista de strings, cada uno describiendo un paso de la receta.
{nota_reintento}
""".strip()

# Prompt menu semanal
def _build_prompt_menu_semanal(
    comentarios: str,
    comidas_por_dia: int,
    semana_inicio: date,
    calorias_por_dia: int,
) -> str:
    return f"""
Actúa como un chef experto y planificador de menús.

Debes generar un MENÚ SEMANAL COMPLETO para UNA sola persona (todas las cantidades serán por 1 persona).

Parámetros del usuario:
- Fecha de inicio de la semana (lunes): {semana_inicio.isoformat()}
- Número de comidas por día: {comidas_por_dia}
- Calorías objetivo aproximadas por día: {calorias_por_dia}
- Restricciones o comentarios: {comentarios}

Reglas:
- Genera exactamente 7 días consecutivos a partir de la fecha de inicio.
- Cada día debe tener exactamente `comidas_por_dia` comidas.
- Intenta que el total de calorías diarias esté lo más cerca posible de las calorías objetivo sin sobrepasarlas de forma clara.
- Las comidas pueden ser de tipo "desayuno", "comida", "cena" o similares, pero siempre especifica el tipo.
- No repitas exactamente la misma receta demasiadas veces; puedes reaprovechar ideas pero con variaciones.
- Todas las cantidades deben ser para UNA persona.

Responde ÚNICAMENTE en formato JSON que cumpla este esquema (no añadas comentarios ni markdown fuera del JSON):
- tipo: "menu_semanal"
- week_start: string en formato "YYYY-MM-DD"
- comidas_por_dia: entero > 0
- dias: lista de 7 elementos, cada uno con:
  - fecha: string "YYYY-MM-DD"
  - comidas: lista de longitud `comidas_por_dia` con objetos:
    - tipo: string ("desayuno", "comida", "cena", etc.)
    - receta:
        - titulo: string
        - tiempo_min: entero > 0
        - ingredientes: lista de ingredientes (misma estructura que en una receta normal)
        - pasos: lista de strings
- lista_compra: lista de objetos con:
  - nombre: string
  - cantidad: número > 0 (para UNA persona sumando todo el menú)
  - unidad: string
  - notas: lista opcional de strings.
""".strip()


def generar(
    tipo: Literal["receta", "menu_semanal"],
    *,
    ingredientes: Optional[str] = None,
    tiempo_min: Optional[int] = None,
    comentarios: str = "",
    comidas_por_dia: Optional[int] = None,
    semana_inicio: Optional[date] = None,
    calorias_por_dia: Optional[int] = None,
    es_reintento: bool = False,
) -> Dict[str, Any]:
    if tipo == "receta":
        if not ingredientes or tiempo_min is None:
            raise ValueError("Para generar una receta se necesitan ingredientes y tiempo_min.")
        prompt = _build_prompt_receta(ingredientes, tiempo_min, comentarios, es_reintento)
        schema = receta_json_schema()
        target_model = Receta
    else:
        if comidas_por_dia is None or semana_inicio is None or calorias_por_dia is None:
            raise ValueError("Para generar un menú semanal se necesitan comidas_por_dia, semana_inicio y calorias_por_dia.")
        prompt = _build_prompt_menu_semanal(comentarios, comidas_por_dia, semana_inicio, calorias_por_dia)
        schema = menu_semanal_json_schema()
        target_model = MenuSemanal

    try:
        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": schema,
            },
        )
        raw = respuesta.text
        data = json.loads(raw)
        # Validamos con Pydantic; si falla, dejamos que la excepción suba para poder mostrar error en UI.
        parsed = target_model.model_validate(data)
        return json.loads(parsed.model_dump_json())
    except Exception:
        st.error("Error al generar contenido con IA. Revisa la API key o inténtalo de nuevo.")
        raise


# Inicializar el estado de la sesión
if "receta_actual" not in st.session_state:
    st.session_state.receta_actual = None
if "intentos_rechazados" not in st.session_state:
    st.session_state.intentos_rechazados = 0
if "menu_semanal_actual" not in st.session_state:
    st.session_state.menu_semanal_actual = None
if "modo" not in st.session_state:
    st.session_state.modo = "Receta"


def _render_receta(receta_data: Dict[str, Any]) -> str:
    """Renderiza una receta JSON en markdown para mostrarla al usuario. Devuelve el título."""
    titulo = receta_data.get("titulo", "Receta generada")
    ingredientes = receta_data.get("ingredientes", [])
    pasos = receta_data.get("pasos", [])

    md = f"# {titulo}\n\n"
    md += "### 🛒 Ingredientes (para 1 persona)\n"
    for ing in ingredientes:
        nombre = ing.get("nombre")
        cantidad = ing.get("cantidad")
        unidad = ing.get("unidad")
        nota = ing.get("nota")
        detalle = f"- {cantidad} {unidad} de {nombre}"
        if nota:
            detalle += f" ({nota})"
        md += detalle + "\n"

    md += "\n### 👩‍🍳 Instrucciones a seguir\n"
    for i, paso in enumerate(pasos, start=1):
        md += f"{i}. {paso}\n"

    st.markdown(md)
    return titulo


def _render_menu_semanal(menu_data: Dict[str, Any], personas: int) -> None:
    st.markdown("### 📅 Menú semanal (1 persona)")
    dias = menu_data.get("dias", [])
    for dia in dias:
        fecha = dia.get("fecha")
        st.markdown(f"#### {fecha}")
        for comida in dia.get("comidas", []):
            tipo = comida.get("tipo")
            receta = comida.get("receta", {})
            st.markdown(f"**{tipo.capitalize()}**: {receta.get('titulo')}")

    st.markdown("---")
    st.markdown("### 🧺 Lista de la compra")
    lista = menu_data.get("lista_compra", [])
    for item in lista:
        nombre = item.get("nombre")
        cantidad = item.get("cantidad", 0) * max(personas, 1)
        unidad = item.get("unidad")
        notas = item.get("notas") or []
        extra = f" ({'; '.join(notas)})" if notas else ""
        st.markdown(f"- {cantidad} {unidad} de {nombre}{extra}")


# Interfaz de Usuario
st.title("👨‍🍳 Tu Chef Personal con IA")
st.divider()
st.subheader("Dime qué tienes en la nevera o planifiquemos tu semana.")

with st.sidebar:
    st.header("🍽️ Mi Recetario")
    st.write("Tus recetas guardadas:")
    recetas_guardadas = obtener_recetas_guardadas()
    if not recetas_guardadas:
        st.info("Aún no has guardado ninguna receta.")
    else:
        for receta in recetas_guardadas:
            titulo, fecha, contenido = receta
            with st.expander(f"🍽️ {titulo[:25]}..."):
                st.caption(f"Guardada el: {fecha}")
                try:
                    data = json.loads(contenido)
                    if isinstance(data, dict) and data.get("tipo") == "receta":
                        _render_receta(data)
                    else:
                        st.code(contenido, language="json")
                except (json.JSONDecodeError, TypeError):
                    if contenido.strip().startswith("{"):
                        st.code(contenido, language="json")
                    else:
                        st.markdown(contenido)

    st.markdown("---")
    st.header("📅 Menús semanales guardados")
    menus = obtener_menus_semanales()
    if not menus:
        st.info("Aún no has guardado ningún menú semanal.")
    else:
        for week_start, comidas_por_dia, menu_json, lista_json, created_at in menus:
            with st.expander(f"📅 Semana: {week_start} ({comidas_por_dia} comidas/día)"):
                st.caption(f"Creado el: {created_at}")
                try:
                    menu_data = json.loads(menu_json)
                    _render_menu_semanal(menu_data, personas=1)
                except Exception:
                    st.markdown("No se ha podido mostrar el menú guardado.")

# Selector de modo: dos columnas con botones que ocupan todo el espacio
col_receta, col_menu = st.columns(2)
with col_receta:
    if st.button("🍳 **Receta**", use_container_width=True, type="primary" if st.session_state.modo == "Receta" else "secondary"):
        st.session_state.modo = "Receta"
        st.rerun()
with col_menu:
    if st.button("📅 **Menú semanal**", use_container_width=True, type="primary" if st.session_state.modo == "Menú semanal" else "secondary"):
        st.session_state.modo = "Menú semanal"
        st.rerun()

st.markdown("---")

# Formulario de entrada según modo
if st.session_state.modo == "Receta":
    with st.container():
        ingredientes = st.text_input("Ingredientes disponibles (ej. pollo, arroz, cebolla)")
        tiempo = st.number_input(
            "Tiempo disponible (en minutos)",
            min_value=5,
            max_value=180,
            value=30,
            step=5,
        )
        comentarios = st.text_area("Alergias o comentarios (ej. sin lactosa, soy alérgico al tomate)")

        if st.button("Generar Receta", type="primary"):
            if ingredientes:
                with st.spinner("El chef está pensando..."):
                    try:
                        st.session_state.receta_actual = generar(
                            "receta",
                            ingredientes=ingredientes,
                            tiempo_min=tiempo,
                            comentarios=comentarios,
                        )
                        st.session_state.intentos_rechazados = 0
                    except Exception:
                        st.session_state.receta_actual = None
            else:
                st.warning("Por favor, introduce al menos un ingrediente.")

    if st.session_state.receta_actual:
        st.markdown("---")
        titulo_receta = _render_receta(st.session_state.receta_actual)
        st.markdown("---")

        st.write("¿Qué te parece esta receta?")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("👍 Me encanta, me la quedo"):
                # Mantenemos compatibilidad guardando el markdown generado
                st.success("¡Receta guardada con éxito! Revisa la barra lateral. 🍳")
                # De momento guardamos el JSON como texto en el recetario clásico
                guardar_receta_db(titulo_receta, ingredientes, int(tiempo), json.dumps(st.session_state.receta_actual, ensure_ascii=False))
                st.session_state.receta_actual = None
                st.rerun()

        with col2:
            if st.button("👎 No me convence, dame otra"):
                st.session_state.intentos_rechazados += 1
                with st.spinner("Buscando una alternativa..."):
                    try:
                        st.session_state.receta_actual = generar(
                            "receta",
                            ingredientes=ingredientes,
                            tiempo_min=tiempo,
                            comentarios=comentarios,
                            es_reintento=True,
                        )
                    except Exception:
                        st.session_state.receta_actual = None
                st.rerun()

else:
    with st.container():
        today = date.today()
        comidas_por_dia = st.number_input(
            "Comidas por día",
            min_value=1,
            max_value=5,
            value=3,
            step=1,
        )
        calorias_por_dia = st.number_input(
            "Calorías objetivo por día",
            min_value=800,
            max_value=5000,
            value=2000,
            step=50,
        )
        comentarios = st.text_area(
            "Preferencias / restricciones para el menú (ej. vegetariano, sin lactosa, rápido entre semana)"
        )
        personas = st.number_input(
            "Número de personas para calcular la lista de la compra",
            min_value=1,
            max_value=10,
            value=1,
            step=1,
        )

        if st.button("Generar menú semanal", type="primary"):
            with st.spinner("Planificando tu semana..."):
                try:
                    semana_inicio = today
                    menu = generar(
                        "menu_semanal",
                        comentarios=comentarios,
                        comidas_por_dia=int(comidas_por_dia),
                        semana_inicio=semana_inicio,
                        calorias_por_dia=int(calorias_por_dia),
                    )
                    st.session_state.menu_semanal_actual = menu
                    guardar_menu_semanal(
                        week_start=menu.get("week_start"),
                        comidas_por_dia=int(comidas_por_dia),
                        menu_json=json.dumps(menu, ensure_ascii=False),
                        lista_compra_json=json.dumps(menu.get("lista_compra", []), ensure_ascii=False),
                    )
                except Exception:
                    st.session_state.menu_semanal_actual = None

    if st.session_state.menu_semanal_actual:
        _render_menu_semanal(st.session_state.menu_semanal_actual, personas=int(personas))