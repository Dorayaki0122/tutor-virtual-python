# Utilidades de archivos: leer documentos, guardar código generado y cargar config.yml.
# Laura Álvarez Zamora - 19/11/2026

import os
from pathlib import Path

import yaml
from officeparserpy import parse_office

from models.pipeline_config import PipelineConfig


# Extrae el texto de un documento: TXT y PY se leen tal cual; PDF, DOCX, etc. con officeparserpy.
def read_text_from_document(document_path: str) -> str:
    if document_path.endswith(".txt") or document_path.endswith(".py"):
        with open(document_path, "r", encoding="utf-8") as document_file:
            return document_file.read()

    with open(document_path, "rb") as document_file:
        document_bytes = document_file.read()

    return parse_office(document_bytes)


# Guarda el código en output_directory/file_name y devuelve la ruta del archivo.
def write_to_file(output_directory: str, file_name: str, content: str) -> str:
    # Crea la carpeta si no existe.
    os.makedirs(output_directory, exist_ok=True)
    file_path = os.path.join(output_directory, file_name)

    with open(file_path, "w", encoding="utf-8") as output_file:
        output_file.write(content)

    return file_path


# Carga config.yml; si hay errores, usa los valores por defecto.
def read_yaml(file_name: str = "config.yml") -> PipelineConfig:
    por_defecto = PipelineConfig()

    # Ruta relativa a la carpeta del proyecto, no a la carpeta desde la que se ejecuta.
    ruta_completa = Path(__file__).parent.parent / file_name

    try:
        # Lee el archivo YAML como un diccionario.
        with open(ruta_completa, "r", encoding="utf-8") as yaml_file:
            datos = yaml.safe_load(yaml_file)

        # Si falta una clave, se usa su valor por defecto.
        config = PipelineConfig(
            model_name=str(datos.get("model", por_defecto.model_name)),
            temperature=float(datos.get("temperature", por_defecto.temperature)),
            context_length=int(datos.get("context_length", por_defecto.context_length)),
            num_predict=int(datos.get("num_predict", por_defecto.num_predict)),
            output_directory=str(datos.get("output_path", por_defecto.output_directory)),
            default_mode=str(datos.get("default_mode", por_defecto.default_mode)),
        )

    except FileNotFoundError:
        print(f"No existe '{file_name}'; se usan los valores por defecto.")
        return por_defecto

    except Exception as error:
        # YAML mal escrito, vacío o con valores que no son números.
        print(f"Error al leer '{file_name}': {error}. Se usan los valores por defecto.")
        return por_defecto

    # Validación básica: los valores deben estar en un rango válido.
    if config.model_name.strip() == "":
        print("El modelo no puede estar vacio; se usan los valores por defecto.")
        return por_defecto
    if config.temperature < 0 or config.temperature > 2:
        print("La temperatura debe estar entre 0 y 2; se usan los valores por defecto.")
        return por_defecto
    if config.context_length <= 0 or config.num_predict <= 0:
        print("context_length y num_predict deben ser mayores que 0; se usan los valores por defecto.")
        return por_defecto

    return config
