from hug.output_format import OutputFormat
from typing import Callable, TypeVar

T = TypeVar('T', bound=Callable)

def get(route, output: OutputFormat) -> Callable[[T], T]: ...
