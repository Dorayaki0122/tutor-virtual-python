# Pipeline del tutor: configuración, inferencia y post-procesamiento de la respuesta.
# Laura Álvarez Zamora - 19/11/2026

import json
import time
from collections.abc import Iterator

from httpx import ConnectError, TimeoutException
from ollama import ResponseError

from constants import Constants
from models.pipeline_config import PipelineConfig
from utils.file_utils import read_text_from_document, read_yaml, write_to_file
from utils.ollama_utils import ollama_chat
from utils.utils import tokenize_text


# Recibe los valores de la interfaz y envía a la interfaz la respuesta del tutor según se genera.
# Cada yield actualiza la caja de respuesta; return termina el pipeline.
def pipeline(*params: str | float | None) -> Iterator[str]:
    # 1. Fase de configuración
    # Valores iniciales de config.yml, sustituidos por los elegidos en la interfaz.
    config = read_yaml("config.yml")
    config.load_parameters(list(params))

    # Validación: se requiere al menos una duda, código o archivo.
    if config.question == "" and config.code == "" and config.input_document_path == "":
        yield "Por favor, escribe una duda o adjunta codigo para que el profesor pueda responder."
        return

    # Lee el documento adjunto, si lo hay.
    contexto_documental = ""
    if config.input_document_path != "":
        try:
            contexto_documental = read_text_from_document(config.input_document_path)
        except Exception as error:
            # Archivo ilegible (codificación no UTF-8, formato no soportado, PDF de imágenes...).
            yield f"Error al leer el archivo adjunto: {error}"
            return

    user_prompt = construir_prompt_usuario(config, contexto_documental)

    # Validación: la consulta y la respuesta deben caber en el 75 % de la ventana de contexto.
    aviso_contexto = comprobar_contexto(config, user_prompt)
    if aviso_contexto != "":
        yield aviso_contexto
        return

    # 2. Fase de inferencia (streaming)
    aviso_generando = f"*Generando respuesta con {config.model_name}...*"
    yield aviso_generando
    inicio = time.time()
    model_response = ""
    try:
        # Une los fragmentos según llegan y muestra la explicación y el código que se van generando.
        for fragmento in ollama_chat(config, user_prompt):
            texto = fragmento.message.content
            if texto:
                model_response += texto
                yield f"{construir_vista_parcial(model_response)}\n\n{aviso_generando}"

    except ResponseError as error:
        # Ollama responde con error (modelo no encontrado, falta de memoria, etc.).
        yield f"Error de Ollama: {error.error}"
        return

    except ConnectError:
        yield "No se puede conectar con Ollama: comprueba que el servicio esta encendido."
        return

    except TimeoutException:
        yield "La peticion ha superado el tiempo de espera."
        return

    duracion = time.time() - inicio

    # 3. Fase de post-procesamiento
    # Sustituye el JSON por la respuesta ya validada y con formato.
    resultado = process_model_response(model_response, config.output_directory)

    # Añade el tiempo y el modelo utilizado.
    yield f"{resultado}\n\n---\n*Tiempo de respuesta: {duracion:.2f} s | Modelo: {config.model_name}*"


# Construye lo que se muestra durante el streaming: la explicación y, cuando empieza, el código.
def construir_vista_parcial(model_response: str) -> str:
    vista = extraer_campo_parcial(model_response, "explanation", 0)

    # El código se busca después de file_name para no confundirlo con la palabra "code" de la explicación.
    posicion_file_name = model_response.find('"file_name"')
    if posicion_file_name != -1:
        codigo = extraer_campo_parcial(model_response, "code", posicion_file_name)
        if codigo.strip() != "":
            vista += f"\n\n```python\n{codigo}\n```"

    return vista


# Lee el texto de un campo del JSON aunque esté incompleto, buscando la clave a partir de la posición desde.
def extraer_campo_parcial(model_response: str, campo: str, desde: int) -> str:
    clave = f'"{campo}"'
    posicion = model_response.find(clave, desde)
    if posicion == -1:
        return ""

    # Comillas que abren el valor del campo.
    inicio = model_response.find('"', posicion + len(clave))
    if inicio == -1:
        return ""

    try:
        # Si el valor ya está cerrado, raw_decode lee solo ese texto y descarta el resto del JSON.
        valor, _ = json.JSONDecoder().raw_decode(model_response, inicio)
        return str(valor)
    except json.decoder.JSONDecodeError:
        pass

    texto = model_response[inicio:]
    try:
        # Si el valor sigue abierto, se cierran las comillas para poder leerlo (convierte \n, \" ...).
        return str(json.loads(texto + '"'))
    except json.decoder.JSONDecodeError:
        pass

    try:
        # El fragmento puede acabar a mitad de un escape (la \ de \n): se prueba sin el último carácter.
        return str(json.loads(texto[:-1] + '"'))
    except json.decoder.JSONDecodeError:
        return ""


# Construye el mensaje de usuario: modo, extensión máxima, consulta, código y documento adjunto.
def construir_prompt_usuario(config: PipelineConfig, contexto_documental: str) -> str:
    # Extensión objetivo: el 80 % de num_predict, para que la respuesta no se corte.
    tokens_objetivo = int(config.num_predict * 0.8)
    palabras_max = max(100, int(tokens_objetivo * 0.75))

    texto = f"QUERY MODE: {config.mode}\n"
    if config.mode in Constants.INSTRUCCIONES_POR_MODO:
        texto += f"MODE INSTRUCTIONS: {Constants.INSTRUCCIONES_POR_MODO[config.mode]}\n"
    texto += f"MAXIMUM LENGTH: about {tokens_objetivo} tokens (about {palabras_max} words), code included.\n"
    texto += f"\nSTUDENT QUESTION:\n{config.question}\n"

    if config.code != "":
        # Código en bloque Markdown.
        texto += f"\n--- STUDENT CODE ---\n```python\n{config.code}\n```\n"

    if contexto_documental.strip() != "":
        texto += f"\n--- ATTACHED DOCUMENT ---\n{contexto_documental.strip()}\n"

    return texto


# Devuelve un aviso si la consulta y la respuesta superan el 75 % del contexto; si caben, devuelve "".
def comprobar_contexto(config: PipelineConfig, user_prompt: str) -> str:
    try:
        # Conteo aproximado con tiktoken (cada modelo usa su propio tokenizador).
        tokens_entrada = len(tokenize_text(Constants.SYSTEM_PROMPT + user_prompt))
    except Exception as error:
        # La primera vez tiktoken descarga la codificación: sin internet no se puede contar.
        print(f"No se pudieron contar los tokens: {error}")
        return ""

    limite = int(config.context_length * 0.75)
    if tokens_entrada + config.num_predict > limite:
        return (
            f"La consulta ocupa unos {tokens_entrada} tokens y la respuesta puede ocupar "
            f"{config.num_predict}: supera el 75 % del contexto ({limite} de {config.context_length}). "
            "Sube el contexto o adjunta un documento mas corto."
        )

    return ""


# Valida la respuesta JSON del modelo, guarda el código si procede y devuelve el texto para la interfaz.
def process_model_response(model_response: str, output_directory: str) -> str:
    # Validación básica: comprueba que la respuesta tiene contenido.
    if model_response.strip() == "":
        return "Aviso: el modelo devolvio una respuesta vacia."

    # Validación de JSON y de claves.
    try:
        response_data: dict[str, object] = json.loads(model_response)
        explanation = response_data["explanation"]
        file_name = response_data["file_name"]
        code = response_data["code"]

    except json.decoder.JSONDecodeError:
        # Suele ocurrir cuando la respuesta se corta al llegar a num_predict.
        return "El modelo no devolvio un JSON valido (puede que la respuesta se haya cortado). Prueba de nuevo o elige otro modelo."

    except (KeyError, TypeError):
        # Falta alguna clave o el JSON no es un objeto.
        return "El JSON del modelo no tiene los campos esperados (explanation, file_name, code)."

    # Comprobación de tipos: los tres campos deben ser texto.
    if not isinstance(explanation, str) or not isinstance(file_name, str) or not isinstance(code, str):
        return "El JSON del modelo tiene campos con un tipo incorrecto: deben ser texto."

    # Validación semántica básica: debe haber explicación o código.
    if explanation.strip() == "" and code.strip() == "":
        return "Aviso: el modelo devolvio un JSON sin explicacion ni codigo."

    resultado = explanation.strip()

    if code.strip() != "":
        resultado += f"\n\n```python\n{code.strip()}\n```"

        # Guarda el código solo si se ha indicado una carpeta de salida.
        if output_directory != "":
            resultado += "\n\n" + guardar_codigo(output_directory, file_name, code)

    return resultado


# Guarda el código generado en la carpeta de salida y devuelve un mensaje con el resultado.
def guardar_codigo(output_directory: str, file_name: str, code: str) -> str:
    # La app se ejecuta en Linux: una ruta de Windows (con \) crearía una carpeta con un nombre extraño.
    if "\\" in output_directory:
        return "*Usa una ruta de Linux (por ejemplo /home/usuario/carpeta)*"

    # Solo el nombre del archivo, sin carpetas, para no escribir fuera de la carpeta de salida.
    nombre_archivo = file_name.strip().replace("\\", "/").split("/")[-1]
    if not nombre_archivo.endswith(".py"):
        nombre_archivo = "codigo_generado.py"

    try:
        ruta = write_to_file(output_directory, nombre_archivo, code.strip() + "\n")
        return f"*Codigo guardado en: {ruta}*"
    except OSError as error:
        return f"*No se pudo guardar el codigo: {error}*"
