"""Sample project entry point for Tessera integration tests."""


def greet(name: str) -> str:
    return f"Hello, {name}!"


class Greeter:
    def __init__(self, prefix: str = "Hello") -> None:
        self.prefix = prefix

    def greet(self, name: str) -> str:
        return f"{self.prefix}, {name}!"


if __name__ == "__main__":
    g = Greeter()
    print(g.greet("world"))
