from flask import Flask
from provider import load_funcx_provider


def create_app(config: dict = None) -> Flask:
    app = Flask(__name__)
    return load_funcx_provider(app, config)
