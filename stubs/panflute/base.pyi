from functools import partial
from panflute.containers import ListContainer
from panflute.elements import (
    Definition,
    DefinitionItem,
    Doc,
    Para,
    Space,
    Str,
)
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

class Element:
    def __eq__(self, other: Element) -> bool: ...
    @staticmethod
    def __new__(cls: Any, *args, **kwargs) -> Element: ...
    def __repr__(self) -> str: ...
    def _ica_to_json(self) -> List[Union[str, List[Tuple[str, str]], List[str]]]: ...
    def _set_content(self, value: Any, oktypes: Any) -> None: ...
    def _set_ica(
        self,
        identifier: str,
        classes: List[Union[str, Any]],
        attributes: List[List[str]],
    ) -> None: ...
    def ancestor(self, n: int) -> Optional[Doc]: ...
    @property
    def container(self) -> ListContainer: ...
    @property
    def doc(self) -> Optional[Doc]: ...
    @property
    def next(self) -> Union[DefinitionItem, Str, Definition, Space, Para]: ...
    def offset(self, n: int) -> Any: ...
    @property
    def tag(self) -> str: ...
    def to_json(self) -> Dict[str, Any]: ...
    def walk(
        self,
        action: Union[partial, Callable],
        doc: Optional[Doc] = ...,
        stop_if: Optional[Callable] = ...,
    ) -> Any: ...
