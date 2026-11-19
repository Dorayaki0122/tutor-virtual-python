# Modelo de datos con todos los parámetros de una consulta al pipeline.
# Laura Álvarez Zamora - 19/11/2026

from dataclasses import dataclass


# Parámetros del pipeline con sus valores por defecto.
@dataclass
class PipelineConfig:
    # Valores iniciales (se cargan desde config.yml).
    model_name: str = "granite4.1:8b"  # Modelo de Ollama.
    temperature: float = 0.3  # Aleatoriedad (0 a 2).
    context_length: int = 16384  # Tamaño de la ventana de contexto (num_ctx).
    num_predict: int = 1500  # Número máximo de tokens de la respuesta.
    output_directory: str = ""  # Carpeta donde se guarda el código (vacía: no se guarda).
    default_mode: str = "Explicar concepto"  # Modo de consulta inicial.

    # Valores de cada consulta (se reciben de la interfaz).
    question: str = ""
    mode: str = ""
    code: str = ""
    input_document_path: str = ""

    # Carga los valores de la interfaz, en el mismo orden que la lista inputs del botón.
    def load_parameters(self, parameters: list[str | float | None]) -> None:
        self.question = str(parameters[0] or "").strip()
        self.mode = str(parameters[1] or self.default_mode)
        self.code = str(parameters[2] or "").strip()
        self.input_document_path = str(parameters[3] or "")
        self.model_name = str(parameters[4] or self.model_name)
        self.temperature = float(parameters[5] or 0)
        self.context_length = int(parameters[6] or self.context_length)
        self.output_directory = str(parameters[7] or "").strip()
