from datetime import datetime

from typing_extensions import override


class Event:
    __count = 0

    def __init__(self) -> None:
        Event.__count += 1
        self._index = self.__count
        print(f'Creating event, index={self._index}, count={self.__count}')
        self._date = datetime.now()

    @property
    def date(self) -> datetime:
        return self._date

    @property
    def index(self) -> int:
        return self._index

    @override  # object
    def __str__(self) -> str:
        return f'{self.index} - {self.date}'
