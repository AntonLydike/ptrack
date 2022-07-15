from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from logging import getLogger, Logger
from typing import Dict, Protocol
from typing import Optional, Tuple, List
import enum


class IsDataclass(Protocol):
    # as already noted in comments, checking for this attribute is currently
    # the most reliable way to ascertain that something is a dataclass
    __dataclass_fields__: Dict


@dataclass(frozen=True, unsafe_hash=True)
class TrackingIdentifier:
    number: str
    postcode: Optional[str] = None
    source: Optional[str] = None
    readable_name: Optional[str] = None


class PackageState(enum.Enum):
    ANNOUNCED = 0
    ARRIVED_AT_INGRES = 1
    ON_THE_WAY = 2
    ARRIVED_AT_DESTINATION = 3
    OUT_FOR_DELIVERY = 4
    DELIVERED = 5
    # special statuses
    CUSTOMS = 100
    READY_FOR_COLLECTION = 101


@dataclass
class TrackingUpdateItem:
    text: str
    when: datetime
    where: Optional[str]


@dataclass(frozen=True)
class TrackingState:
    id: TrackingIdentifier
    state: PackageState
    short_description: str
    additional_info: str
    last_update: datetime
    progress: Tuple[int, int]
    is_delivered: bool
    is_retoure: Optional[bool]
    is_express: Optional[bool]
    updates: List[TrackingUpdateItem]

    def pretty_print(self):
        return "{}: {}\n{}{}{}".format(
            self.id.number,
            self.short_description,
            ' ' * (len(self.id.number) + 2),
            self.additional_info,
            '\n\n' + self.pretty_print_updates()
        )

    def pretty_print_updates(self):
        if len(self.updates) == 0:
            return ""
        return "Updates:\n" + '\n\n'.join(
            "  {:%Y-%m-%d %H:%M}: {}\n{}{}".format(
                update.when, update.where if update.where else '?',
                ' ' * 20, update.text,
            ) for update in self.updates
        )


class TrackingSupplier(ABC):
    name: str
    config: IsDataclass
    logger: Logger

    def __init__(self, config: IsDataclass):
        self.config = config
        self.logger = getLogger(".".join(__name__.split('.')[:-1] + [self.__class__.__name__]))

    @abstractmethod
    def get_details_for(self, details: TrackingIdentifier) -> Optional[TrackingState]:
        """
        Get the state of a package.

        :param details: the tracking details of the package
        """
        pass
