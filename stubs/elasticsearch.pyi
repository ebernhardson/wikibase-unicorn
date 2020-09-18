from typing import Mapping, Optional, Sequence, Union


class Elasticsearch:
    def __init__(self, hosts: Optional[Union[str, Sequence[str]]] = None, **kwargs) -> None: ...
    def search(self, index: str, body: Union[str, Mapping]) -> Mapping: ...
