from typing import Dict, Callable

# Each generator is a function: (config: dict) -> list[dict]
REGISTRY: Dict[str, Callable[[dict], list[dict]]] = {}

def register(name: str):
    """Decorator to register generators by name."""
    def decorator(fn):
        REGISTRY[name] = fn
        return fn
    return decorator