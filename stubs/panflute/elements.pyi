from panflute.base import MetaValue
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

def _decode_citation(
    dct: Dict[str, Union[str, List[Union[Str, Space]], int]]
) -> Citation: ...
def _decode_definition_item(item: List[List[Any]]) -> DefinitionItem: ...
def builtin2meta(val: Any) -> Any: ...
def from_json(data: Dict[str, Any]) -> Any: ...

class BlockQuote:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Any]]: ...

class BulletList:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[List[Dict[str, Any]]]: ...

class Citation:
    def __init__(
        self,
        id: str,
        mode: str = ...,
        prefix: List[Union[Str, Space, Any]] = ...,
        suffix: Union[str, List[Union[Str, Space]]] = ...,
        hash: int = ...,
        note_num: int = ...,
    ) -> None: ...
    def to_json(
        self,
    ) -> Dict[str, Union[int, Dict[str, str], List[Dict[str, str]], str]]: ...

class Cite:
    def __init__(self, *args, citations=...) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        List[Dict[str, Union[int, Dict[str, str], List[Dict[str, str]], str]]]
    ]: ...

class Code:
    def __init__(
        self,
        text: str,
        identifier: str = ...,
        classes: List[Any] = ...,
        attributes: List[Any] = ...,
    ) -> None: ...
    def _slots_to_json(self) -> List[Union[List[str], str]]: ...

class CodeBlock:
    def __init__(
        self,
        text: str,
        identifier: str = ...,
        classes: List[Union[str, Any]] = ...,
        attributes: Union[Dict[Any, Any], List[Any]] = ...,
    ) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[Union[List[str], str, List[Union[List[str], str]]]]: ...

class Definition:
    def __init__(self, *args) -> None: ...
    def to_json(
        self,
    ) -> List[
        Dict[
            str,
            Union[
                str,
                List[Dict[str, str]],
                List[
                    List[
                        Union[
                            int,
                            Dict[str, str],
                            List[Dict[str, Union[str, List[Dict[str, str]]]]],
                        ]
                    ]
                ],
                List[Union[List[str], str]],
                List[Dict[str, Union[str, List[Dict[str, str]]]]],
            ],
        ]
    ]: ...

class DefinitionItem:
    def __init__(
        self,
        term: List[Union[Emph, Str, Space, Type[Space]]],
        definitions: List[Definition],
    ) -> None: ...
    def __repr__(self) -> str: ...
    def to_json(
        self,
    ) -> List[
        List[
            Union[
                Dict[str, Union[str, List[Dict[str, str]]]],
                List[
                    Union[
                        Dict[str, Union[str, List[Dict[str, str]]]],
                        Dict[str, Union[str, List[Union[List[str], str]]]],
                        Dict[
                            str,
                            Union[
                                str, List[Dict[str, Union[str, List[Dict[str, str]]]]]
                            ],
                        ],
                    ]
                ],
                Dict[str, str],
                List[
                    Union[
                        Dict[str, Union[str, List[Dict[str, str]]]],
                        Dict[
                            str,
                            Union[
                                str,
                                List[
                                    List[
                                        Union[
                                            int,
                                            Dict[str, str],
                                            List[
                                                Dict[
                                                    str,
                                                    Union[str, List[Dict[str, str]]],
                                                ]
                                            ],
                                        ]
                                    ]
                                ],
                            ],
                        ],
                    ]
                ],
                List[Dict[str, Union[str, List[Dict[str, str]]]]],
            ]
        ]
    ]: ...

class DefinitionList:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        List[
            List[
                Union[
                    Dict[str, Union[str, List[Dict[str, str]]]],
                    List[
                        Union[
                            Dict[str, Union[str, List[Dict[str, str]]]],
                            Dict[str, Union[str, List[Union[List[str], str]]]],
                            Dict[
                                str,
                                Union[
                                    str,
                                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                                ],
                            ],
                        ]
                    ],
                    Dict[str, str],
                    List[
                        Union[
                            Dict[str, Union[str, List[Dict[str, str]]]],
                            Dict[
                                str,
                                Union[
                                    str,
                                    List[
                                        List[
                                            Union[
                                                int,
                                                Dict[str, str],
                                                List[
                                                    Dict[
                                                        str,
                                                        Union[
                                                            str, List[Dict[str, str]]
                                                        ],
                                                    ]
                                                ],
                                            ]
                                        ]
                                    ],
                                ],
                            ],
                        ]
                    ],
                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                ]
            ]
        ]
    ]: ...

class Div:
    def __init__(self, *args, identifier=..., classes=..., attributes=...) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        List[
            Union[
                str,
                Dict[
                    str,
                    Union[
                        str,
                        List[
                            List[
                                Union[
                                    str,
                                    Dict[
                                        str,
                                        Union[
                                            str,
                                            List[
                                                List[
                                                    Union[
                                                        str,
                                                        Dict[
                                                            str,
                                                            Union[
                                                                str,
                                                                List[Dict[str, str]],
                                                            ],
                                                        ],
                                                    ]
                                                ]
                                            ],
                                        ],
                                    ],
                                ]
                            ]
                        ],
                    ],
                ],
                Dict[
                    str,
                    Union[
                        str,
                        List[
                            List[
                                Union[str, Dict[str, Union[str, List[Dict[str, str]]]]]
                            ]
                        ],
                    ],
                ],
                Dict[str, Union[str, List[Dict[str, str]]]],
            ]
        ]
    ]: ...

class Doc:
    def __eq__(self, other: Doc) -> bool: ...
    def __init__(self, *args, metadata=..., format=..., api_version=...) -> None: ...
    def to_json(self) -> Dict[str, Any]: ...

class Emph:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[Dict[str, Union[str, List[List[Union[Dict[str, str], str]]]]]]: ...

class Figure:
    def __init__(
        self, *args, caption=..., identifier=..., classes=..., attributes=...
    ) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        List[
            Optional[
                Union[
                    str,
                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                    Dict[
                        str,
                        Union[
                            str,
                            List[
                                Dict[
                                    str,
                                    Union[str, List[List[Union[Dict[str, str], str]]]],
                                ]
                            ],
                        ],
                    ],
                ]
            ]
        ]
    ]: ...

class Header:
    def __init__(
        self, *args, level=..., identifier=..., classes=..., attributes=...
    ) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        Union[
            int,
            List[str],
            List[
                Union[
                    Dict[str, str],
                    Dict[str, Union[str, List[List[Union[Dict[str, str], str]]]]],
                ]
            ],
            List[Union[Dict[str, str], Dict[str, Union[str, List[Dict[str, str]]]]]],
            List[Dict[str, str]],
        ]
    ]: ...

class HorizontalRule:
    def to_json(self) -> Dict[str, str]: ...

class Image:
    def __init__(
        self, *args, url=..., title=..., identifier=..., classes=..., attributes=...
    ) -> None: ...
    def _slots_to_json(self) -> List[List[Union[Dict[str, str], str]]]: ...

class LineBreak:
    def to_json(self) -> Dict[str, str]: ...

class Link:
    def __init__(
        self, *args, url=..., title=..., identifier=..., classes=..., attributes=...
    ) -> None: ...
    def _slots_to_json(self) -> List[List[Union[str, List[str], Dict[str, str]]]]: ...

class ListItem:
    def __init__(self, *args) -> None: ...
    def to_json(self) -> List[Dict[str, Any]]: ...

class Math:
    def __init__(self, text: str, format: str = ...) -> None: ...
    def _slots_to_json(self) -> List[Union[Dict[str, str], str]]: ...

class MetaBlocks:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        Dict[
            str,
            Union[
                str,
                List[
                    Union[Dict[str, str], Dict[str, Union[str, List[Dict[str, str]]]]]
                ],
                List[Dict[str, str]],
            ],
        ]
    ]: ...

class MetaBool:
    def __init__(self, boolean: bool) -> None: ...
    def _slots_to_json(self) -> bool: ...

class MetaInlines:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[Dict[str, Union[str, List[str], List[Dict[str, str]]]]]: ...

class MetaList:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        Dict[
            str,
            Union[
                str,
                List[Dict[str, str]],
                Dict[str, Dict[str, Union[str, List[Dict[str, str]]]]],
                List[Dict[str, Union[str, List[str]]]],
            ],
        ]
    ]: ...

class MetaMap:
    def __getitem__(self, i: str) -> MetaValue: ...
    def __init__(self, *args, **kwargs) -> None: ...
    def __setitem__(self, i: str, v: Any) -> None: ...
    def _slots_to_json(
        self,
    ) -> Dict[
        str,
        Union[
            Dict[str, Union[str, List[Dict[str, Union[str, List[Dict[str, str]]]]]]],
            Dict[str, Union[str, List[Dict[str, str]]]],
            Dict[str, Union[str, bool]],
            Dict[
                str,
                Union[
                    str,
                    List[
                        Union[
                            Dict[
                                str,
                                Union[
                                    str,
                                    Dict[
                                        str, Dict[str, Union[str, List[Dict[str, str]]]]
                                    ],
                                ],
                            ],
                            Dict[str, Union[str, List[Dict[str, str]]]],
                        ]
                    ],
                ],
            ],
        ],
    ]: ...

class MetaString:
    def __init__(self, text: str) -> None: ...
    def _slots_to_json(self) -> str: ...

class Note:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        Dict[
            str,
            Union[
                str,
                List[Dict[str, str]],
                List[Union[List[str], str]],
                List[
                    Union[
                        Dict[str, str],
                        Dict[str, Union[str, List[Dict[str, str]]]],
                        Dict[str, Union[str, List[List[Union[Dict[str, str], str]]]]],
                        Dict[str, Union[str, List[Union[List[str], str]]]],
                    ]
                ],
            ],
        ]
    ]: ...

class OrderedList:
    def __init__(self, *args, start=..., style=..., delimiter=...) -> None: ...
    def _slots_to_json(self) -> List[List[Any]]: ...

class Para:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Any]]: ...

class Plain:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Any]]: ...

class Quoted:
    def __init__(self, *args, quote_type=...) -> None: ...
    def _slots_to_json(
        self,
    ) -> List[
        Union[
            Dict[str, str],
            List[Dict[str, Union[str, List[List[Union[Dict[str, str], str]]]]]],
            List[Dict[str, Union[str, List[Union[List[str], str]]]]],
            List[Dict[str, str]],
            List[
                Union[
                    Dict[
                        str,
                        Union[str, List[Union[Dict[str, str], List[Dict[str, str]]]]],
                    ],
                    Dict[str, str],
                ]
            ],
        ]
    ]: ...

class RawBlock:
    def __init__(self, text: str, format: str = ...) -> None: ...
    def _slots_to_json(self) -> List[str]: ...

class RawInline:
    def __init__(self, text: str, format: str = ...) -> None: ...
    def _slots_to_json(self) -> List[str]: ...

class SoftBreak:
    def to_json(self) -> Dict[str, str]: ...

class Space:
    def to_json(self) -> Dict[str, str]: ...

class Span:
    def __init__(self, *args, identifier=..., classes=..., attributes=...) -> None: ...

class Str:
    def __init__(self, text: str) -> None: ...
    def __repr__(self) -> str: ...
    def _slots_to_json(self) -> str: ...

class Strikeout:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]: ...

class Strong:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]: ...

class Subscript:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, str]]: ...

class Superscript:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]: ...

class Underline:
    def __init__(self, *args) -> None: ...
    def _slots_to_json(self) -> List[Dict[str, str]]: ...
