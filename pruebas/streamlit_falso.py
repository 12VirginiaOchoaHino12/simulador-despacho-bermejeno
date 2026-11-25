"""Streamlit simulado para la prueba de humo de las paginas (no abre ninguna interfaz).

Devuelve valores por defecto para cada widget y permite 'pulsar' botones por su texto.
Sirve para detectar errores de codigo (nombres, tipos, columnas) sin necesidad de un navegador.
"""
from datetime import date
from unittest.mock import MagicMock


class _Contexto:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False  # no traga excepciones


class _Estado(dict):
    __getattr__ = dict.get

    def __setattr__(self, k, v):
        self[k] = v


class StreamlitFalso:
    def __init__(self, pulsar=(), textos=None):
        self.pulsar = set(pulsar)
        self.textos = textos or {}
        self.session_state = _Estado()
        self.llamadas = []
        self.errores = []
        self.sidebar = self

    # -- contenedores
    def columns(self, n):
        n = n if isinstance(n, int) else len(n)
        return [self for _ in range(n)]

    def tabs(self, nombres):
        return [_Contexto() for _ in nombres]

    def form(self, *a, **k):
        return _Contexto()

    def expander(self, *a, **k):
        return _Contexto()

    def spinner(self, *a, **k):
        return _Contexto()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    # -- entradas
    def button(self, etiqueta, *a, **k):
        return etiqueta in self.pulsar

    form_submit_button = button

    def checkbox(self, etiqueta, value=False, **k):
        return value

    def selectbox(self, etiqueta, opciones, index=0, **k):
        opciones = list(opciones)
        return self.textos.get(etiqueta, opciones[index] if opciones else None)

    def radio(self, etiqueta, opciones, **k):
        return list(opciones)[0]

    def multiselect(self, etiqueta, opciones, default=None, **k):
        return list(default or [])

    def number_input(self, etiqueta, min_value=None, max_value=None, value=None, step=None, **k):
        if etiqueta in self.textos:
            return self.textos[etiqueta]
        return value if value is not None else (min_value if min_value is not None else 0)

    def text_input(self, etiqueta, value="", **k):
        return self.textos.get(etiqueta, value)

    def date_input(self, etiqueta, value=None, **k):
        return value or date.today()

    def file_uploader(self, *a, **k):
        return None

    # -- salidas (solo se registran)
    def error(self, msg, *a, **k):
        self.errores.append(str(msg))

    def __getattr__(self, nombre):
        if nombre.startswith("__"):
            raise AttributeError(nombre)
        def llamada(*a, **k):
            self.llamadas.append(nombre)
            return MagicMock()
        return llamada
