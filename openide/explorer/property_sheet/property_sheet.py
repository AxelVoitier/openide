from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING, Generic, TypeVar

from openide.explorer.property_sheet.sheet_table import SheetTable
from openide.nodes import AnyNode

if TYPE_CHECKING:
    from weakref import ReferenceType

N = TypeVar('N', bound=AnyNode)


class SortingMode(Enum):
    Unsorted = auto()
    SortedByName = auto()


class PropertySheet(Generic[N]):
    __INIT_DELAY = 70
    """Init delay for second change of the selected nodes"""

    __MAX_DELAY = 150
    """Maximum delay for repeated change of the selected nodes"""

    def __init__(self) -> None:
        super().__init__()

        self.__sorting_mode = SortingMode.Unsorted
        """Holds the sort mode for the property sheet"""
        self.__show_desc = False
        """Tracks whether the description area should be shown"""
        self.__stored_node: ReferenceType[N] | None = None
        """Temporary storage for the last selected node in the case the property
     * sheet was removed temporarily from a container (winsys DnD)"""

        self._table = SheetTable()

        self.__init()
        self.__init_actions()

    def __init(self) -> None:
        pass

    def __init_actions(self) -> None:
        pass
