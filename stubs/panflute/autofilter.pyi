from io import StringIO
from panflute.elements import Doc
from typing import (
    List,
    Optional,
)

def autorun_filters(
    filters: List[str], doc: Doc, search_dirs: List[str], verbose: bool
) -> Doc: ...
def get_filter_dirs(hardcoded: bool = ...) -> List[str]: ...
def stdio(
    filters: Optional[List[str]] = ...,
    search_dirs: Optional[List[str]] = ...,
    data_dir: bool = ...,
    sys_path: bool = ...,
    panfl_: bool = ...,
    input_stream: Optional[StringIO] = ...,
    output_stream: Optional[StringIO] = ...,
) -> None: ...
