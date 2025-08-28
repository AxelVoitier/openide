# spell-checker:words dunder
# spell-checker:ignore pset

from __future__ import annotations

from enum import Enum, auto
from functools import reduce
from operator import add
from typing import TYPE_CHECKING, ClassVar, Protocol

from listeners import Observable

from openide.nodes import Property

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Sequence
    from typing import Any, TypeAlias, TypeVar

    from openide.nodes import PropertySet

    _T_contra = TypeVar('_T_contra', contravariant=True)

    class SupportsDunderLT(Protocol[_T_contra]):
        def __lt__(self, other: _T_contra, /) -> bool: ...

    class SupportsDunderGT(Protocol[_T_contra]):
        def __gt__(self, other: _T_contra, /) -> bool: ...

    SupportsRichComparison: TypeAlias = SupportsDunderLT[Any] | SupportsDunderGT[Any]


class PropertySetModelChangeType(Enum):
    Insert = auto()
    Remove = auto()
    WholesaleChange = auto()


class PropertySetModelChangeProtocol(Protocol):
    def __call__(
        self,
        source: PropertySetModel,
        type: PropertySetModelChangeType,
        start: int,
        end: int,
        *,
        reordering: bool,
    ) -> Any: ...  # noqa: ANN401


class PropertySetModel:
    __FILTER_HIDDEN_PROPERTIES = True

    __closed_sets: ClassVar[set[str]] = set()
    """Retains the persistent list of sets the user has explicitly closed,
    so they remain closed for other similar nodes"""
    # TODO: Somehow reload closed_sets from persisted preferences

    listeners: Observable[PropertySetModelChangeProtocol]

    def __init__(self, pset: Sequence[PropertySet] | None = None) -> None:
        super().__init__()

        self.__sets: Sequence[PropertySet]
        self.__expanded: list[bool]
        self.__feats: list[Property[Any] | PropertySet] = []
        self.__sort_key: Callable[[Property[Any]], SupportsRichComparison] | None = None

        self.listeners = Observable[PropertySetModelChangeProtocol]()

        self.set_property_sets(pset)

    def set_property_sets(self, sets: Sequence[PropertySet] | None) -> None:
        """Assign the property sets this model will manage"""

        print('>>>> set_property_sets', sets)

        if sets is None:
            sets = []

        with self.listeners.fire(
            source=self,
            type=PropertySetModelChangeType.WholesaleChange,
            start=-1,
            end=-1,
            reordering=False,
        ):
            if not sets:
                self.__sets = sets
                self.__reset_expanded(sets)
                self.__feats.clear()
            else:
                self.__sets = sets
                self.__reset_expanded(sets)
                self.__init()

    @property
    def sort_key(self) -> Callable[[Property[Any]], SupportsRichComparison] | None:
        return self.__sort_key

    @sort_key.setter
    def sort_key(self, key: Callable[[Property[Any]], SupportsRichComparison]) -> None:
        """Set the comparator the model will use for sorting properties"""

        if key != self.__sort_key:
            with self.listeners.fire(
                source=self,
                type=PropertySetModelChangeType.WholesaleChange,
                start=-1,
                end=-1,
                reordering=True,
            ):
                self.__sort_key = key
                self.__feats.clear()
                self.__init()

    @property
    def count(self) -> int:
        """Get the number of feature descriptors (properties and
        property sets) currently represented by the model, not
        including properties belonging to unexpanded property
        sets - in other words, the current number of objects
        a component rendering this model is being asked to display."""

        return len(self.__feats)

    @property
    def set_count(self) -> int:
        """Get the number of property set"""

        return len(self.__sets)

    def get_feature_descriptor(self, index: int) -> Property[Any] | PropertySet | None:
        """Returns either a Node.Property or a Node.PropertySet instance for a given index."""

        if not (0 <= index < len(self.__feats)):
            return None

        return self.__feats[index]

    def index_of(self, fd: Property[Any] | PropertySet) -> int:
        """Get the index, in the model, of a given feature descriptor.

        If it is not currently available (either not part of the model
        at all, or part of an unexpanded property set), returns -1.
        """

        if not self.__feats:
            return -1

        try:
            return self.__feats.index(fd)
        except ValueError:
            return -1

    def is_property(self, index: int) -> bool:
        """Utility method to determine if a given index holds a property"""

        return isinstance(self.get_feature_descriptor(index), Property)

    def __init(self) -> None:
        self.__feats.clear()

        if self.__sort_key is None:
            self.__init_expandable()
        else:
            self.__init_plain()

    def __init_plain(self) -> None:
        if not self.__sets:
            return

        props: list[Property[Any]] = reduce(add, [a_set.properties for a_set in self.__sets])

        assert self.__sort_key is not None  # Only for typing
        props.sort(key=self.__sort_key)

        self.__feats += props

    def __init_expandable(self) -> None:
        if not self.__sets:
            return

        for i, a_set in enumerate(self.__sets):
            # For now, simple logic: always add a given set
            self.__feats.append(a_set)

            if self.__expanded[i]:
                if props := a_set.properties:
                    self.__feats.extend(self.__filter_hidden_props(props))
                else:
                    # If we ever were to conditionally add a_set above,
                    # then we would need to try-except that one
                    self.__feats.remove(a_set)

    def __filter_hidden_props(self, props: Iterable[Property[Any]]) -> Iterator[Property[Any]]:
        if self.__FILTER_HIDDEN_PROPERTIES:
            for prop in props:
                if not prop.is_hidden:
                    yield prop
        else:
            yield from props

    def __reset_expanded(self, sets: Iterable[PropertySet]) -> None:
        self.__expanded = [a_set.display_name not in self.__closed_sets for a_set in self.__sets]

    def __lookup_set(self, fd: PropertySet) -> int:
        if not self.__sets:
            return -1

        try:
            return self.__sets.index(fd)
        except ValueError:
            return -1

    def is_expanded(self, a_set: PropertySet) -> bool:
        """Determines if a given property set is expanded"""

        if (index := self.__lookup_set(a_set)) == -1:
            return False

        return self.__expanded[index]

    def toggle_expanded(self, index: int) -> None:
        """Set the expanded state for a feature descriptor of the given index."""

        fd = self.get_feature_descriptor(index)
        if fd is None:
            msg = f'Invalid index {index}'
            raise ValueError(msg)
        if isinstance(fd, Property):
            msg = 'Cannot expand a property'
            raise ValueError(msg)  # noqa: TRY004

        set_index = self.__lookup_set(fd)
        expanded = self.__expanded[set_index]
        event_type = (
            PropertySetModelChangeType.Insert if expanded else PropertySetModelChangeType.Remove
        )
        props = list(self.__filter_hidden_props(self.__sets[set_index].properties))

        with self.listeners.fire(
            source=self,
            type=event_type,
            start=index + 1,
            end=index + len(props),
            reordering=False,
        ):
            self.__expanded[set_index] = expanded = not expanded

            if (name := fd.display_name) is not None:
                if not expanded:
                    self.__closed_sets.add(name)
                else:
                    self.__closed_sets.remove(name)

            if expanded:
                self.__feats = self.__feats[:index] + props + self.__feats[index + 1 :]
            else:
                self.__feats = self.__feats[:index] + self.__feats[index + 1 + len(props) :]

        # TODO: Save __closed_sets to persistent preferences
