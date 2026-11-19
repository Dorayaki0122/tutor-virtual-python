# Punto de entrada de la aplicación: interfaz Gradio del tutor de Python.
# Laura Álvarez Zamora - 13/11/2026

import gradio as gr

from constants import Constants
from pipeline import pipeline
from utils.file_utils import read_yaml
from utils.ollama_utils import get_available_models

# --- Inicialización (se ejecuta una sola vez al arrancar) ---

# Carga la configuración inicial desde config.yml.
config = read_yaml("config.yml")

# Modelos disponibles en Ollama.
modelos_instalados = get_available_models()

# Añade el modelo configurado si no está en la lista.
if config.model_name not in modelos_instalados:
    modelos_instalados.insert(0, config.model_name)



# --- Interfaz de Gradio ---

with gr.Blocks(title="Tutor de Python con IA Local") as demo:
    gr.Markdown("# Tutor Virtual de Python", elem_id="app-title")
    gr.Markdown("Asistente pedagogico local: explica conceptos, corrige codigo y propone ejercicios.")

    with gr.Row():
        # Columna izquierda: parámetros de la consulta.
        with gr.Column(scale=1):
            gr.Markdown("### Configuracion")
            selector_modelo = gr.Dropdown(
                choices=modelos_instalados,
                value=config.model_name,
                label="Modelo local (Ollama)",
            )
            # Los textos deben coincidir con las claves de INSTRUCCIONES_POR_MODO (constants.py).
            selector_modo = gr.Radio(
                choices=[
                    "Explicar concepto",
                    "Corregir / Depurar error",
                    "Generar ejercicio practico",
                ],
                value=config.default_mode,
                label="Modo de Consulta",
            )
            # Valores bajos: respuestas más deterministas; altos: más variadas.
            slider_temp = gr.Slider(
                minimum=0.0,
                maximum=1.0,
                value=config.temperature,
                step=0.05,
                label="Temperatura (Creatividad vs Precision)",
            )
            # Tamaño de la ventana de contexto (num_ctx): más alto admite documentos más largos.
            slider_contexto = gr.Slider(
                minimum=2048,
                maximum=32768,
                value=config.context_length,
                step=1024,
                label="Contexto (tokens)",
            )
            # type="filepath": la función recibe la ruta del archivo como texto.
            subida_archivo = gr.File(
                label="Subir script, notas o apuntes (.py, .txt, .pdf, .docx)",
                file_types=[".py", ".txt", ".pdf", ".docx"],
                type="filepath",
            )
            caja_salida_codigo = gr.Textbox(
                value=config.output_directory,
                placeholder="Vacio: el codigo no se guarda",
                label="Carpeta donde guardar el codigo generado",
            )

        # Columna derecha: entrada del estudiante y respuesta del tutor.
        with gr.Column(scale=2):
            gr.Markdown("### Consulta")
            caja_duda = gr.Textbox(
                lines=3,
                placeholder="Escribe tu duda aqui...",
                label="Cual es tu duda?",
            )
            # Editor de código con colores de Python.
            caja_codigo = gr.Code(
                language="python",
                label="Codigo Python opcional",
                lines=6,
            )
            boton_enviar = gr.Button("Consultar al Profesor", variant="primary")

            gr.Markdown("### Explicacion del Profesor")
            # Muestra la respuesta con formato Markdown y las fórmulas LaTeX ($...$, $$...$$, \(...\) y \[...\]).
            caja_salida = gr.Markdown(
                label="Respuesta",
                latex_delimiters=[
                    {"left": "$$", "right": "$$", "display": True},
                    {"left": "$", "right": "$", "display": False},
                    {"left": "\\(", "right": "\\)", "display": False},
                    {"left": "\\[", "right": "\\]", "display": True},
                ],
            )

    # Al pulsar el botón se ejecuta el pipeline; cada yield actualiza la caja de respuesta (streaming).
    # El orden de inputs debe coincidir con PipelineConfig.load_parameters.
    boton_enviar.click(
        fn=pipeline,
        inputs=[
            caja_duda,
            selector_modo,
            caja_codigo,
            subida_archivo,
            selector_modelo,
            slider_temp,
            slider_contexto,
            caja_salida_codigo,
        ],
        outputs=caja_salida,
    )

# Arranca la aplicación web con el tema "soft", el estilo propio y el modo claro.
if __name__ == "__main__":
    demo.queue().launch(theme="soft", css=Constants.CUSTOM_CSS, js=Constants.LIGHT_MODE_JS)
