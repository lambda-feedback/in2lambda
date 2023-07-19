from panflute.containers import ListContainer
from panflute.elements import (
    BulletList,
    Plain,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

def body_from_json(c: List[Any]) -> TableBody: ...
def cell_from_json(
    c: List[Union[List[str], str, int, List[Plain], List[BulletList]]]
) -> TableCell: ...
def colspec_to_json(c: Union[str, float]) -> Dict[str, Union[str, float]]: ...
def count_columns_in_row(row: ListContainer) -> int: ...
def row_from_json(
    c: List[
        List[
            Union[
                str,
                List[Union[List[str], str, int, List[Plain], List[BulletList]]],
                List[Union[List[str], str, int, List[Plain]]],
                List[str],
            ]
        ]
    ]
) -> TableRow: ...
def table_from_json(c: List[List[Any]]) -> Table: ...

class Caption:
    def __init__(self, *args, short_caption=...) -> None: ...
    def to_json(
        self,
    ) -> List[
        Optional[
            Union[
                List[
                    Union[
                        Dict[str, str],
                        Dict[
                            str,
                            Union[
                                str,
                                List[
                                    Union[
                                        Dict[str, str],
                                        Dict[str, Union[str, List[Dict[str, str]]]],
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

class Table:
    def __init__(
        self,
        *args,
        head=...,
        foot=...,
        caption=...,
        colspec=...,
        identifier=...,
        classes=...,
        attributes=...
    ) -> None: ...
    def _set_table_width(self) -> None: ...
    def _slots_to_json(self) -> List[List[Any]]: ...
    def _validate_cols(self, block: Union[TableFoot, TableHead]) -> None: ...
    def _validate_colspec(self) -> None: ...

class TableBody:
    def __init__(
        self,
        *args,
        head=...,
        row_head_columns=...,
        identifier=...,
        classes=...,
        attributes=...
    ) -> None: ...
    def _slots_to_json(self) -> List[Any]: ...

class TableCell:
    def __init__(
        self,
        *args,
        alignment=...,
        rowspan=...,
        colspan=...,
        identifier=...,
        classes=...,
        attributes=...
    ) -> None: ...
    def to_json(self) -> List[Any]: ...

class TableFoot:
    def __init__(self, *args, identifier=..., classes=..., attributes=...) -> None: ...
    def to_json(
        self,
    ) -> List[
        List[
            Union[
                str,
                Any,
                List[
                    List[
                        Union[
                            str,
                            List[
                                Union[
                                    List[str],
                                    Dict[str, str],
                                    int,
                                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                                ]
                            ],
                        ]
                    ]
                ],
            ]
        ]
    ]: ...

class TableHead:
    def __init__(self, *args, identifier=..., classes=..., attributes=...) -> None: ...
    def to_json(
        self,
    ) -> List[
        List[
            Union[
                str,
                List[str],
                List[
                    List[
                        Union[
                            str,
                            List[
                                Union[
                                    List[str],
                                    Dict[str, str],
                                    int,
                                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                                    List[
                                        Dict[
                                            str,
                                            Union[
                                                str,
                                                List[
                                                    Union[
                                                        Dict[str, str],
                                                        Dict[
                                                            str,
                                                            Union[
                                                                str,
                                                                List[Dict[str, str]],
                                                            ],
                                                        ],
                                                    ]
                                                ],
                                            ],
                                        ]
                                    ],
                                ]
                            ],
                        ]
                    ]
                ],
                Any,
                List[
                    List[
                        Union[
                            str,
                            List[
                                Union[
                                    List[str],
                                    Dict[str, str],
                                    int,
                                    List[Dict[str, Union[str, List[Dict[str, str]]]]],
                                ]
                            ],
                        ]
                    ]
                ],
            ]
        ]
    ]: ...

class TableRow:
    def __init__(self, *args, identifier=..., classes=..., attributes=...) -> None: ...
    def to_json(
        self,
    ) -> List[
        List[
            Union[
                str,
                List[
                    Union[
                        List[str],
                        Dict[str, str],
                        int,
                        List[Dict[str, Union[str, List[Dict[str, str]]]]],
                    ]
                ],
                List[
                    Union[
                        List[str],
                        Dict[str, str],
                        int,
                        List[Dict[str, Union[str, List[Dict[str, str]]]]],
                        List[
                            Dict[
                                str,
                                Union[
                                    str,
                                    List[
                                        Union[
                                            Dict[str, str],
                                            Dict[str, Union[str, List[Dict[str, str]]]],
                                        ]
                                    ],
                                ],
                            ]
                        ],
                    ]
                ],
                List[str],
                List[
                    Union[
                        List[str],
                        Dict[str, str],
                        int,
                        List[Dict[str, Union[str, List[Dict[str, str]]]]],
                        List[
                            Dict[
                                str,
                                Union[
                                    str,
                                    List[
                                        List[
                                            Dict[str, Union[str, List[Dict[str, str]]]]
                                        ]
                                    ],
                                ],
                            ]
                        ],
                    ]
                ],
            ]
        ]
    ]: ...
