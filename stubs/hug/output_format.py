from typing import Any, Mapping, Protocol

# Lax definition for now, may want to pin it down
class OutputFormat(Protocol):
    def __call__(**kwargs) -> Any: ...

def accept(kinds: Mapping[str, OutputFormat]) -> OutputFormat: ...
def json(**kwargs) -> Any: ...
def html(content: str, **kwargs) -> Any: ...
