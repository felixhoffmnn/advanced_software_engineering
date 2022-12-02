import datetime
import os
from typing import Any, Final

from loguru import logger
from requests import JSONDecodeError

from aswe.api.event.event_data import EventLocation, ReducedEvent
from aswe.api.event.event_params import EventApiEventParams
from aswe.utils.request import http_request


class EventApi:
    """Crawler Class retrieves data from
    [ticketmaster](https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/)

    * TODO: Add Attributes section
    """

    _BASE_URL: Final[str] = "https://app.ticketmaster.com/discovery/v2/"
    _API_KEY: str = os.getenv("EVENT_API_KEY", "")

    def __init__(self) -> None:
        self._validate_api_key()

    def _validate_api_key(self) -> None:
        if self._API_KEY == "":
            raise Exception("EVENT_API_KEY was not loaded into system")

    def _reduce_events(self, events: dict[Any, Any]) -> list[ReducedEvent]:
        if "_embedded" in events:
            reduced_events: list[ReducedEvent] = []

            for event in events["_embedded"]["events"]:
                # ? remove if too few event can be found ----------------------
                # ! skip offsale or cancelled events --------------------------
                if event["dates"]["status"]["code"] in ["offsale", "cancelled"]:
                    continue
                # ! -----------------------------------------------------------

                try:
                    utc_start_datetime = datetime.datetime.strptime(
                        event["dates"]["start"]["dateTime"], "%Y-%m-%dT%H:%M:%SZ"
                    )
                    berlin_tz_start_datetime = utc_start_datetime + datetime.timedelta(hours=1)
                    berlin_tz_start_as_string = berlin_tz_start_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

                    single_event = ReducedEvent(
                        id=event["id"],
                        name=event["name"],
                        start=berlin_tz_start_as_string,
                        status=event["dates"]["status"]["code"],
                        location=EventLocation(
                            name=event["_embedded"]["venues"][0]["name"],
                            city=event["_embedded"]["venues"][0]["city"]["name"],
                            address=event["_embedded"]["venues"][0]["address"]["line1"],
                        ),
                    )

                    reduced_events.append(single_event)
                except Exception as err:
                    logger.error(err)

            return reduced_events

        return []

    def events(self, query_params: EventApiEventParams) -> list[ReducedEvent] | None:
        """Retrieves Events that fulfil given query parameters

        Parameters
        ----------
        query_params : EventApiEventParams
            Query Parameters API should filter for.

        Returns
        -------
        list[dict[Any, Any]] | None
            List of events

        """

        if not query_params.validate_fields():
            raise Exception("Given Event Api Event Params are invalid")

        url = f"{self._BASE_URL}events?apikey={self._API_KEY}&{query_params.concat_to_query()}"

        response = http_request(url)

        if response:
            try:
                response_json: dict[str, Any] = response.json()
                reduced_events = self._reduce_events(response_json)

                return reduced_events
            except (AttributeError, JSONDecodeError):
                logger.error("Event API returned invalid Json")

        return None
