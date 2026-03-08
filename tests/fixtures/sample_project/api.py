"""Fake API routes for the sample project."""

from .main import Greeter

_greeter = Greeter(prefix="Hi")


def handle_greet(request: dict) -> dict:
    name = request.get("name", "stranger")
    return {"message": _greeter.greet(name)}
