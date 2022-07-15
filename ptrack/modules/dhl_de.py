import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .models import TrackingState, TrackingIdentifier, TrackingSupplier, TrackingUpdateItem, PackageState


@dataclass()
class DHL_DE_Config:
    user_agent: str = "Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0"
    timeout: int = 10


def _cut_json_string_from_response(resp: str):
    start_identifier = 'initialState: JSON.parse("'
    end_identifier = '"),'
    json_start = resp.index(start_identifier) + len(start_identifier)
    return resp[
           json_start:resp.index(end_identifier, json_start)
           ].replace('\\"', '"')


def _info_from_json_obj(data: dict, id: TrackingIdentifier) -> TrackingState:
    obj = data['sendungen'][0]
    details = obj['sendungsdetails']
    verlauf = details['sendungsverlauf']

    items = []
    for item in verlauf.get('events', []):
        ort = item.get('ort', None)
        items.append(
            TrackingUpdateItem(
                text=item.get('status', ""),
                when=datetime.fromisoformat(item['datum']),
                where=ort if ort else None
            )
        )
    return TrackingState(
        id=id,
        state=_get_package_state(details),
        short_description=verlauf.get('kurzStatus', "Status offen"),
        additional_info=verlauf.get('aktuellerStatus', "Wir erwarten Ihre Sendungsdaten in Kürze."),
        last_update=datetime.fromisoformat(verlauf['datumAktuellerStatus']) if 'datumAktuellerStatus' in verlauf else datetime(1970, 1, 1, 0, 0, 0),
        progress=(int(verlauf['fortschritt']), int(verlauf['maximalFortschritt'])),
        is_delivered=details['istZugestellt'],
        is_retoure=details['retoure'],
        is_express=details['expressSendung'],
        updates=sorted(items, key=lambda x: x.when, reverse=True)
    )

def _get_package_state(details: dict):
    if 'zustellung' in details:
        zustellung = details['zustellung']
        if zustellung.get('zugestelltAnEmpfaenger', False):
            return PackageState.DELIVERED
        if zustellung.get('benachrichtigtInFiliale', False):
            return PackageState.READY_FOR_COLLECTION

    if details['istZugestellt']:
        return PackageState.DELIVERED
    state_number = details.get('sendungsverlauf', {}).get('fortschritt', 0)
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




class DHL_DE(TrackingSupplier):
    name = "dhl"
    config: DHL_DE_Config

    def get_details_for(self, details: TrackingIdentifier) -> Optional[TrackingState]:
        try:
            result = subprocess.check_output([
                'curl', '-s',
                f'https://www.dhl.de/int-verfolgen/search?language=de&lang=de&domain=de&piececode={details.number}',
                '-H', f'User-Agent: {self.config.user_agent}'
            ], timeout=self.config.timeout, stderr=subprocess.DEVNULL).decode()
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout during request for {}".format(details.number))
            return None
        except subprocess.SubprocessError as err:
            self.logger.exception("Error during HTTP request for {}:".format(
                details.number,
            ))
            return None

        if 'window.__INITIAL_APP_STATE__' not in result:
            self.logger.error("Could not fetch info for {}: Response of {}".format(
                details.number,
                result[:50]
            ))
            return None

        json_string = _cut_json_string_from_response(result)

        try:
            data = json.loads(json_string)
            return _info_from_json_obj(data, details)
        except:
            self.logger.exception('Error processing json:')
            return None
