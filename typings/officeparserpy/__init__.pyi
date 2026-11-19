# Tipos propios de officeparserpy: la librería no incluye py.typed y Pyright strict exige stubs.
# Pyright los encuentra por "stubPath": "typings" en pyrightconfig.json.
# Solo se declara la función que usa la aplicación.

def parse_office(file: str | bytes) -> str: ...
