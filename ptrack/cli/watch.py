import os
import re
import time
from datetime import datetime
from typing import Dict

import ptrack.cli.color as color
import ptrack.cli.symbols as symbols
from ptrack.modules import ALL_MODULES
from ptrack.modules.models import TrackingState, TrackingSupplier, TrackingIdentifier, PackageState


def _file_line_split(line: str):
    return [x[0].strip('"') for x in re.findall(r'("(\\"|[^"\\])+"|[^\s]+)', line)]


class PackageWatcher:
    """
    This class contains all state necessary to provide some sort of daemon.

    It reads a number of tracking infos from a file and periodically checks their status

    It also checks the file for changes and adds or removes trackers based on its content
    """
    RESCAN_INTERVAL = 60 * 20  # 20 minute interval scan

    trackers = dict[str, TrackingSupplier]

    tracks: Dict[TrackingIdentifier, TrackingState]
    last_scan: float
    last_file_version: float

    source_file_name: str

    display_mode: str

    def __init__(self, source: str, display_mode='compact'):
        self.tracks = dict()
        self.last_scan = 0
        self.last_file_version = 0
        self.source_file_name = source
        self.display_mode = display_mode

        self.trackers = {
            name: cls(config_cls())
            for name, (cls, config_cls) in ALL_MODULES.items()
        }

        self.tracks = self.load_file()

    def load_file(self):
        """
        load tracking numbers from a file and fetch their statuses if no local
        cache exists for them.

        :return: A new dictionary of trackers
        """
        with open(self.source_file_name, 'r') as f:
            data = {
                _file_line_split(line)[0]: _file_line_split(line)[1:] for line in f
            }
        new_tracks = dict()
        must_rescan = self.should_rescan()
        for id, info in data.items():
            id = TrackingIdentifier(id, source=info[0], readable_name=info[1] if len(info) > 1 else None)
            if must_rescan or id not in self.tracks:
                new_tracks[id] = self.trackers[id.source].get_details_for(id)
            else:
                new_tracks[id] = self.tracks[id]
        if must_rescan:
            self.last_scan = time.time()
        self.last_file_version = os.stat(self.source_file_name).st_mtime
        return new_tracks

    def should_rescan(self) -> bool:
        """
        check if the cached results are no older than RESCAN_INTERVAL seconds
        """
        return self.last_scan + self.RESCAN_INTERVAL < time.time()

    def file_changed(self) -> bool:
        """
        check if the file has changed
        :return:
        """
        last_mod = os.stat(self.source_file_name).st_mtime
        if last_mod != self.last_file_version:
            return True

    def tick(self):
        """
        This represents one update action. It should be called periodically.
        """
        if self.file_changed():
            new_tracks = self.load_file()
        elif self.should_rescan():
            new_tracks = {
                id: self.trackers[id.source].get_details_for(id)
                for id in self.tracks
            }
            self.last_scan = time.time()
        else:
            new_tracks = self.tracks

        output = self.print_diff(new_tracks)
        self.tracks = new_tracks
        return output

    def print_diff(self, new_tracks):
        if self.display_mode == 'compact':
            return self.print_diff_compact(new_tracks)
        elif self.display_mode == 'i3bar':
            return self.print_diff_i3bar(new_tracks)
        elif self.display_mode == 'exhaustive':
            return self.print_exhaustive(new_tracks)

        return self.print_diff_compact(new_tracks)

    def print_diff_compact(self, new_tracks: Dict[TrackingIdentifier, TrackingState]):
        removed = set(self.tracks.keys()) - set(new_tracks.keys())
        added = set(new_tracks.keys()) - set(self.tracks.keys())

        all_tracks: Dict[TrackingIdentifier, TrackingState] = {
            **self.tracks,
            **new_tracks
        }
        print("\033[H\033[2J", end="")
        id: TrackingIdentifier
        for id in sorted(all_tracks.keys(), key=lambda id: id.number):
            info = all_tracks[id]
            if info is None:
                print("{}: not found".format(id.readable_name or id.number))
                continue
            print("{}{:<20}: {} {}{} {}{}".format(
                color.RED if id in removed else (color.GREEN if id in added else ""),
                id.readable_name or id.number,
                print_date_time(info.last_update),
                generate_progress_bar(*info.progress),
                (" " + info.updates[0].where + ',') if len(info.updates) > 0 and info.updates[0].where else "",
                info.short_description,
                color.RESET
            ))

    def print_diff_i3bar(self, new_tracks: Dict[TrackingIdentifier, TrackingState]):
        return " | ".join(
            "{}: {} {}".format(
                id.readable_name or id.number,
                generate_progress_bar(*info.progress),
                get_icon_for(info.state)
            ) for id, info in new_tracks.items() if info is not None
        )

    def print_exhaustive(self, new_tracks: Dict[TrackingIdentifier, TrackingState]):
        for id, info in new_tracks.items():
            print("\n")
            print(info.pretty_print())

def generate_progress_bar(at: int, ttl: int):
    return ('█' * at) + ('░' * (ttl - at))


def print_date_time(dt: datetime):
    if dt < datetime(2000, 1, 1, tzinfo=dt.tzinfo):
        return "??.??. ??:??"
    return dt.strftime('%d.%m. %H:%m')

def get_icon_for(state: PackageState):
    if state == PackageState.ANNOUNCED:
        return symbols.MEGAPHONE
    if state in (PackageState.ARRIVED_AT_INGRES, PackageState.ON_THE_WAY, PackageState.ARRIVED_AT_DESTINATION):
        return symbols.SHIPPING_TRUCK
    if state == PackageState.OUT_FOR_DELIVERY:
        return symbols.DELIVERY_TRUCK
    if state == PackageState.DELIVERED:
        return symbols.CHECKMARK_BOX
    if state == PackageState.CUSTOMS:
        return symbols.CUSTOMS
    if state == PackageState.READY_FOR_COLLECTION:
        return symbols.POSTAL_HORN
    return symbols.QUESTION_MARK