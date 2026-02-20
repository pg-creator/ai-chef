import streamlit as st
from google import genai
from recetario import init_db, guardar_receta_db, obtener_recetas_guardadas

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

# Inicializar el estado de la sesión
if 'receta_actual' not in st.session_state:
    st.session_state.receta_actual = None
if 'intentos_rechazados' not in st.session_state:
    st.session_state.intentos_rechazados = 0

# Función para llamar y generar la respuesta
def generar_receta(ingredientes, tiempo, comentarios, es_reintento=False):
    prompt = f"""
    Actúa como un chef experto. Tengo los siguientes ingredientes: {ingredientes}.
    Solo tengo {tiempo} minutos para cocinar.
    Ten en cuenta estrictamente las siguientes restricciones o comentarios: {comentarios}.
    
    Por favor, genera una receta deliciosa usando preferiblemente solo los ingredientes que tengo.
    Devuelve el nombre de la receta, la lista de ingredientes exactos a usar y las instrucciones paso a paso.
    Muestra unicamente la receta, no añadas más comentarios a parte de la receta.

    REGLA MUY IMPORTANTE - DEBES RESPONDER EXACTAMENTE CON ESTA ESTRUCTURA DE MARKDOWN:
    
    # [Nombre de la receta muy apetecible]
    
    ### 🛒 Ingredientes a utilizar
    - [Ingrediente 1]
    - [Ingrediente 2]
    
    ### 👩‍🍳 Instrucciones a seguir
    1. [Paso 1]
    2. [Paso 2]
    """
    
    if es_reintento:
        prompt += "\nNOTA: Al usuario no le gustó la propuesta anterior. Genera una receta COMPLETAMENTE DISTINTA a tu intento previo usando los mismos parámetros (puedes quitar algun ingrediente para buscar más recetas pero siempre manteniendo al menos 1 de los ingredientes que te dan, pero no añadir ingredientes)."

    # Usamos la nueva sintaxis del cliente para generar contenido y maneja error de API mal añadida
    try:
        respuesta = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return respuesta.text
    except Exception as e:
        st.error(f"Error al generar receta: Comprueba la API key")
        return None

# Interfaz de Usuario
st.title("👨‍🍳 Tu Chef Personal con IA")
st.divider()
st.subheader("Dime qué tienes en la nevera y yo te diré qué comer hoy.")

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
                st.markdown(contenido)

# Formulario de entrada
with st.container():
    ingredientes = st.text_input("Ingredientes disponibles (ej. pollo, arroz, cebolla)")
    tiempo = st.number_input("Tiempo disponible (en minutos)", min_value=5, max_value=180, value=30, step=5)
    comentarios = st.text_area("Alergias o comentarios (ej. sin lactosa, soy alérgico al tomate)")

    # Botón principal para generar
    if st.button("Generar Receta", type="primary"):
        if ingredientes:
            with st.spinner("El chef está pensando..."):
                st.session_state.receta_actual = generar_receta(ingredientes, tiempo, comentarios)
                st.session_state.intentos_rechazados = 0 # Reiniciamos si hay nueva búsqueda
        else:
            st.warning("Por favor, introduce al menos un ingrediente.")

# Lógica de visualización y botones de Me gusta / No me gusta
if st.session_state.receta_actual:
    st.markdown("---")
    st.markdown(st.session_state.receta_actual)
    st.markdown("---")

    # Saca el nombre de la receta y sino la llama "Receta Generada"
    lineas = st.session_state.receta_actual.strip().split('\n')
    titulo_receta = lineas[0].replace('# ', '').strip() if lineas[0].startswith('#') else "Receta Generada"
    
    st.write("¿Qué te parece esta receta?")
    col1, col2 = st.columns(2)
    
    # Lógica de guardado o búsqueda de una nueva receta
    with col1:
        if st.button("👍 Me encanta, me la quedo"):
            guardar_receta_db(titulo_receta, ingredientes, tiempo, st.session_state.receta_actual)
            st.success("¡Receta guardada con éxito! Revisa la barra lateral. 🍳")
            st.session_state.receta_actual = None
            st.rerun()

            
    with col2:
        if st.button("👎 No me convence, dame otra"):
            # Intentos rechazados lo utilizaremos para generar proximamente mejores recetas intercambiando los ingredientes disponibles
            st.session_state.intentos_rechazados += 1
            with st.spinner("Buscando una alternativa..."):
                st.session_state.receta_actual = generar_receta(
                    ingredientes, 
                    tiempo, 
                    comentarios, 
                    es_reintento=True
                )
            st.rerun() # Forzamos recarga para mostrar la nueva receta