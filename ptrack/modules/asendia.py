import datetime
from dataclasses import dataclass
from typing import Optional

import requests

from .models import TrackingIdentifier, PackageState, TrackingUpdateItem, TrackingState, TrackingSupplier


@dataclass
class AsendiaConfig:
    # these three values can be read straight form the webapp inspection
    # they appear to be constant
    api_key = '32337AB0-45DD-44A2-8601-547439EF9B55'
    tracking_key = 'AE654169-0B14-45F9-8498-A8E464E13D26'
    auth_header = 'Basic Q3VzdEJyYW5kLlRyYWNraW5nQGFzZW5kaWEuY29tOjJ3cmZzelk4cXBBQW5UVkI='


class AsendiaTracking(TrackingSupplier):
    name = 'asendia'
    config: AsendiaConfig

    def get_details_for(self, details: TrackingIdentifier) -> Optional[TrackingState]:
        resp = requests.get(
            "https://a1reportapi.asendiaprod.com/api/A1/TrackingBranded/Tracking",
            params={
                'trackingKey': self.config.tracking_key,
                'trackingNumber': details.number
            },
            headers={
                'Authorization': self.config.auth_header,
                'X-AsendiaOne-ApiKey': self.config.api_key
            }
        )

        if not resp.ok:
            self.logger.error("Error connection to asendia: {} {}".format(
                resp.status_code,
                resp.content[:200]
            ))
            return None

        json = resp.json()
        return self._create_tracking_result_from_json(json, details)

    def _create_tracking_result_from_json(self, json: dict, id: TrackingIdentifier):
        progress = (
            json['trackingBrandedSummary']['trackingProgress']['completed'],
            json['trackingBrandedSummary']['trackingProgress']['total']
        )

        return TrackingState(
            id=id,
            state=_get_state(progress[0]),
            short_description=_description(json),
            additional_info="",
            last_update=_last_update(json),
            progress=(
                json['trackingBrandedSummary']['trackingProgress']['completed'],
                json['trackingBrandedSummary']['trackingProgress']['total']
            ),
            is_delivered=progress[0] == progress[1],
            is_retoure=False,
            is_express=False,
            updates=_process_updates(json)
        )


def _get_state(state_number: int):
    if state_number == 0:
        return PackageState.ANNOUNCED
    if state_number == 1:
        return PackageState.ARRIVED_AT_INGRES
    if state_number == 2:
        return PackageState.ON_THE_WAY
    if state_number == 3:
        return PackageState.ARRIVED_AT_DESTINATION
    if state_number == 4:
        return PackageState.OUT_FOR_DELIVERY
    return PackageState.ON_THE_WAY


def _description(json: dict):
    tracking = json['trackingBrandedDetail']
    if len(tracking) == 0:
        return "Unknown"
    return tracking[0].get('eventDescription', None) or "Unknown"


def _last_update(json: dict):
    tracking = json['trackingBrandedDetail']
    if len(tracking) == 0:
        return datetime.datetime(1970, 1, 1)
    return datetime.datetime.fromisoformat(tracking[0]['eventOn'])


def _process_updates(json: dict):
    return sorted(
        [TrackingUpdateItem(
            item['eventDescription'],
            datetime.datetime.fromisoformat(item['eventOn']),
            _process_location(item['eventLocationDetails'])
        ) for item in json['trackingBrandedDetail']],
        key=lambda item: item.when,
        reverse=True
    )


def _process_location(item: dict):
    if item['city'] is not None:
        if item['province'] is not None:
            if item['countryIso2'] is not None:
                return "{city}, {province}, {countryIso2}".format(**item)
        if item['countryIso2'] is not None:
            return "{city}, {countryIso2}".format(**item)
        return item['city']
    return item['countryName']
