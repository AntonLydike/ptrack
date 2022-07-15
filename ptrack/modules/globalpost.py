import datetime
import json
from dataclasses import dataclass
from typing import Optional

import requests

from .helpers import find_substring
from .models import TrackingState, TrackingIdentifier, TrackingSupplier, TrackingUpdateItem, PackageState


@dataclass
class GlobalPostSettings:
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'


def _parse_event_position(info: dict, prefix: str):
    return ", ".join(filter(lambda x: x, [
        info[prefix + 'EventCity'],
        info[prefix + 'EventState'],
        info[prefix + 'EventCountry']
    ])) or None


class GlobalPostTracking(TrackingSupplier):
    name = 'globalpost'
    config: GlobalPostSettings

    def get_details_for(self, details: TrackingIdentifier) -> Optional[TrackingState]:
        resp = requests.get(
            'https://www.goglobalpost.com/track-detail/',
            params={
                't': details.number
            },
            headers={
                'User-Agent': self.config.user_agent
            }
        )

        if not resp.ok:
            self.logger.error("Could not fetch GlobalPost info for {}: {}\n{}".format(
                details.number,
                resp.status_code,
                resp.text[:200]
            ))
            return None

        raw_json = find_substring(resp.text, 'var trackingData = ', ';\n')
        info = json.loads(raw_json)

        long_status = find_substring(resp.text, '<span class="sidebar-right-ele text-normal">', '</span>').strip()

        #TODO: the extracted JSON only contains information on the first update and the last update as far as I can tell. TO get all stops we have to parse HTML unfortunately.
        #TODO: The is_delivered and progress values are just hardcoded at the moment, we need to get them from the page somehow. Maybe we can use the large progess par up top?

        return TrackingState(
            id=details,
            state=PackageState.ON_THE_WAY,
            short_description=info['lastEventDesc'],
            additional_info=long_status,
            last_update=_parse_global_post_date_time_string(info['lastEventDate']),
            progress=(2, 5),
            is_delivered=False,
            is_retoure=False,
            is_express=False,
            updates=[
                TrackingUpdateItem(
                    text=info['lastEventDesc'],
                    when=_parse_global_post_date_time_string(info['lastEventDate']),
                    where=_parse_event_position(info, 'last')
                ),
                TrackingUpdateItem(
                    text=info['firstEventDesc'],
                    when=_parse_global_post_date_time_string(info['firstEventDate']),
                    where=_parse_event_position(info, 'first')
                ),
            ]
        )


def _parse_global_post_date_time_string(dtstring: str) -> datetime.datetime:
    date, time = dtstring.split(' - ', 1)
    if date.strip().lower() == 'today':
        date = datetime.date.today()
    else:
        date = datetime.datetime.strptime(date.strip().lower(), '%b %d, %Y').date()

    return datetime.datetime.combine(
        date,
        datetime.datetime.strptime(time.strip().upper(), '%I:%M %p').time()
    )
