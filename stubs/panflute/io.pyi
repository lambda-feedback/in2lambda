from io import StringIO
from panflute.elements import Doc
from typing import (
    Callable,
    List,
    Optional,
)

def dump(doc: Doc, output_stream: Optional[StringIO] = ...) -> None: ...
def load(input_stream: Optional[StringIO] = ...) -> Doc: ...
def run_filter(action: Callable, *args, **kwargs) -> Doc: ...
def run_filters(
    actions: List[Callable],
    prepare: None = ...,
    finalize: None = ...,
    input_stream: None = ...,
    output_stream: None = ...,
    doc: Optional[Doc] = ...,
    stop_if: None = ...,
    **kwargs
) -> Doc: ...
