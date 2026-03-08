"""Utility helpers used by the sample project."""

from .main import greet


def shout(name: str) -> str:
    return greet(name).upper()


def whisper(name: str) -> str:
    return greet(name).lower()
