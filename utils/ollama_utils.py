# Cliente de la API local de Ollama: lista de modelos y consulta en streaming.
# Laura Álvarez Zamora - 19/11/2026

from collections.abc import Iterator

from ollama import ChatResponse, Client

from constants import Constants
from models.pipeline_config import PipelineConfig

HOST: str = "http://localhost:11434"


# Obtiene la lista de modelos instalados en Ollama.
def get_available_models() -> list[str]:
    try:
        cliente = Client(host=HOST)
        respuesta = cliente.list()
        nombres: list[str] = []

        for modelo in respuesta.models:
            # Comprueba que el modelo tiene nombre antes de añadirlo.
            if modelo.model:
                nombres.append(modelo.model)

        return nombres

    except Exception:
        # Ollama apagado o sin respuesta: lista vacía.
        return []


# Envía la consulta en streaming y devuelve los fragmentos de la respuesta según se generan.
# Los errores de Ollama (ResponseError, ConnectError, TimeoutException) aparecen al recorrer los
# fragmentos, por eso se gestionan en pipeline.py.
def ollama_chat(config: PipelineConfig, generation_prompt: str) -> Iterator[ChatResponse]:
    # Mensajes con el rol de cada uno: instrucciones fijas del tutor y consulta del estudiante.
    mensajes: list[dict[str, str]] = [
        {"role": "system", "content": Constants.SYSTEM_PROMPT},
        {"role": "user", "content": generation_prompt},
    ]

    # Parámetros de generación del modelo.
    opciones: dict[str, float | int] = {
        "temperature": config.temperature,
        "num_ctx": config.context_length,
        "num_predict": config.num_predict,
    }

    # El cliente se crea en la función que hace la llamada.
    cliente = Client(host=HOST, timeout=300)
    # Se ignora porque la librería ollama declara el parámetro tools de chat con un Callable sin tipo, no por un fallo de este código.
    return cliente.chat(  # pyright: ignore[reportUnknownMemberType]
        model=config.model_name,
        messages=mensajes,
        options=opciones,
        stream=True,
        format="json",
        # Desactiva el razonamiento previo de los modelos thinking: gasta tokens de num_predict y corta el JSON.
        think=False,
    )
