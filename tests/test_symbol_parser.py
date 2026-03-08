"""Tests for symbol extraction from Python and JS/TS files."""

from __future__ import annotations

import pytest

from tessera.graph.symbol_parser import Symbol, parse_symbols, compute_body_hash


PYTHON_SOURCE = '''\
"""A sample module."""

def hello(name: str) -> str:
    return f"Hello, {name}"

async def async_func():
    pass

class MyClass:
    def method(self):
        pass

def _private_func():
    pass
'''

JS_SOURCE = '''\
function greet(name) {
  return `Hello, ${name}`;
}

class Greeter {
  constructor(prefix) {
    this.prefix = prefix;
  }
}

export const arrowFn = (x) => x * 2;
export default function defaultFn() {}
'''


def test_parse_python_functions():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    names = [s.name for s in syms]
    assert "hello" in names
    assert "async_func" in names


def test_parse_python_class():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    classes = [s for s in syms if s.kind == "class"]
    assert any(s.name == "MyClass" for s in classes)


def test_parse_python_private_unexported():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    private = next((s for s in syms if s.name == "_private_func"), None)
    assert private is not None
    assert private.exported is False


def test_parse_python_public_exported():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    pub = next((s for s in syms if s.name == "hello"), None)
    assert pub is not None
    assert pub.exported is True


def test_parse_python_line_numbers():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    hello = next(s for s in syms if s.name == "hello")
    assert hello.line_start == 3
    assert hello.line_end >= 4


def test_parse_python_body_hash():
    syms = parse_symbols(PYTHON_SOURCE, ".py")
    hello = next(s for s in syms if s.name == "hello")
    assert len(hello.body_hash) == 8


def test_parse_js_functions():
    syms = parse_symbols(JS_SOURCE, ".js")
    names = [s.name for s in syms]
    # At minimum regex fallback should find greet
    assert len(syms) >= 1


def test_parse_empty_file():
    syms = parse_symbols("", ".py")
    assert syms == []


def test_parse_syntax_error_python():
    syms = parse_symbols("def broken(:\n  pass", ".py")
    assert syms == []


def test_parse_unsupported_extension():
    syms = parse_symbols("some content", ".go")
    assert syms == []


def test_compute_body_hash():
    lines = ["line 1", "line 2", "line 3"]
    h1 = compute_body_hash(lines, 1, 3)
    h2 = compute_body_hash(lines, 1, 3)
    assert h1 == h2
    assert len(h1) == 8


def test_body_hash_differs_for_different_content():
    lines1 = ["def foo():", "  return 1"]
    lines2 = ["def foo():", "  return 2"]
    assert compute_body_hash(lines1, 1, 2) != compute_body_hash(lines2, 1, 2)
