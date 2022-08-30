import dataclasses
from datetime import datetime
from typing import Optional, List, Tuple
from bs4 import BeautifulSoup, ResultSet, Tag
from dateutil.parser import parse

import requests

from ptrack.modules import TrackingSupplier, TrackingIdentifier, TrackingState, TrackingUpdateItem, PackageState

PROGRESS_TO_STATE = {
    0: PackageState.ANNOUNCED,
    1: PackageState.ANNOUNCED,
    2: PackageState.ON_THE_WAY,
    3: PackageState.ARRIVED_AT_DESTINATION,
    4: PackageState.OUT_FOR_DELIVERY,
    5: PackageState.DELIVERED
}


@dataclasses.dataclass
class GLS_Config:
    base_url = "https://api.gls-pakete.de/trackandtrace?lang={lang}&match={id}"
    lang = "de"


class GLS(TrackingSupplier):
    config: GLS_Config

    def __init__(self, config: GLS_Config):
        super().__init__(config)

    def get_details_for(self, details: TrackingIdentifier) -> Optional[TrackingState]:
        resp = requests.get(self.config.base_url.format(lang=self.config.lang, id=details.number))

        if not resp.ok:
            return None

        data = resp.json().get("content", None)
        if not data or not details.number in data:
            self.logger.error("malformed JSON response")
            return None
        data = data[details.number]

        return self._parse_gls_response_html(data['html'], details)

    def _parse_gls_response_html(self, html: str, details: TrackingIdentifier) -> Optional[TrackingState]:
        soup = BeautifulSoup(html, "lxml")
        table = soup.select_one("table.data_table")
        if table is None:
            self.logger.error("more than one data_table?!")
            return None

        tracking_data: List[TrackingUpdateItem] = []
        for line in table.select("tbody > tr"):
            tds = line.select("td")
            tracking_data.append(TrackingUpdateItem(tds[2].text.strip(), self._get_datetime_from_tds(tds), tds[3].text.strip()))

        tracking_data = sorted(tracking_data, key=lambda x: x.when, reverse=True)

        progress = self._get_progress(soup)
        description, additional_info = self._get_state_text(soup)

        return TrackingState(
            details,
            PROGRESS_TO_STATE[progress[0]],
            description,
            additional_info,
            tracking_data[0].when if tracking_data else datetime(1970, 1, 1, 0, 0, 0),
            progress,
            progress[0] == progress[1],
            None,
            None,
            tracking_data
        )

    def _get_progress(self, soup: BeautifulSoup) -> Tuple[int, int]:
        base = soup.select_one(".ce_icon_box_container")
        return len(base.select('.status--complete')) + len(base.select('.status--current')), len(base.select('.ce_icon_box'))

    def _get_datetime_from_tds(self, tds: ResultSet[Tag]):
        return parse(tds[0].text.strip() + ' ' + tds[1].text.strip())

    def _get_state_text(self, soup: BeautifulSoup):
        candidates = soup.select(".container.pt-20px .col-12 p.lead strong")
        if len(candidates) == 2:
            return candidates[0].text.strip(), "Arriving at " + candidates[1].text.strip()
        if len(candidates) == 1:
            return candidates[0].text.strip(), ""
        return "Announced", ""

