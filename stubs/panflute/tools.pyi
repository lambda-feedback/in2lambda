from panflute.base import (
    Element,
    MetaValue,
)
from panflute.elements import (
    Doc,
    Para,
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

def _get_metadata(
    self: Doc,
    key: str = ...,
    default: Optional[Union[bool, int]] = ...,
    builtin: bool = ...,
) -> Any: ...
def _replace_keyword(
    self: Doc, keyword: str, replacement: Union[Str, Para], count: int = ...
) -> Doc: ...
def convert_text(
    text: Union[Doc, str, List[Para]],
    input_format: str = ...,
    output_format: str = ...,
    standalone: bool = ...,
    extra_args: None = ...,
    pandoc_path: None = ...,
) -> Union[List[Para], str, Doc]: ...
def get_option(
    options: Optional[Union[Dict[str, None], Dict[str, int]]] = ...,
    local_tag: Optional[str] = ...,
    doc: Optional[Doc] = ...,
    doc_tag: Optional[str] = ...,
    default: Optional[Union[str, int]] = ...,
    error_on_none: bool = ...,
) -> Union[str, int]: ...
def inner_convert_text(
    text: str,
    input_format: str,
    output_format: str,
    extra_args: List[Union[str, Any]],
    pandoc_path: None = ...,
) -> str: ...
def meta2builtin(meta: MetaValue) -> Any: ...
def run_pandoc(
    text: str = ..., args: Optional[List[str]] = ..., pandoc_path: None = ...
) -> str: ...
def stringify(element: Any, newlines: bool = ...) -> str: ...
def yaml_filter(
    element: Element,
    doc: Doc,
    tag: Optional[str] = ...,
    function: Optional[Callable] = ...,
    tags: None = ...,
    strict_yaml: bool = ...,
) -> None: ...

class PandocVersion:
    def __init__(self) -> None: ...
    def __str__(self) -> str: ...
    @property
    def _repr(self) -> str: ...
    @property
    def data_dir(self) -> List[str]: ...
    @property
    def version(self) -> Tuple[int, Ellipsis]: ...
