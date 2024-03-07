#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#


from abc import ABC
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple
import xml.etree.ElementTree as ET


import requests
from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from airbyte_cdk.sources.streams.http.auth import NoAuth


# Basic full refresh stream
class MeteoredStream(HttpStream, ABC):
    url_base = "http://api.meteored.cl/index.php"

    def __init__(self, config: Mapping[str, Any], **kwargs):
        super().__init__()
        self.affiliate_id = config["affiliate_id"]
        self.pais = config["pais"]
        self.api_lang = config["api_lang"]

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {}

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        yield {}


class Localidades(MeteoredStream):
    primary_key = "localidad"

    def stream_slices(
        self, *, sync_mode: SyncMode, cursor_field: List[str] = None, stream_state: Mapping[str, Any] = None
    ) -> Iterable[Optional[Mapping[str, Any]]]:
        response = requests.get(f"{self.url_base}?api_lang={self.api_lang}&pais={self.pais}&affiliate_id={self.affiliate_id}")
        name_elements = ET.fromstring(response.content).findall(".//location/data")
        urls_region: List[str] = [element.find("url").text for element in name_elements]

        all_localidad_ids = list()
        for url_region in urls_region:
            response = requests.get(f"{url_region}&affiliate_id={self.affiliate_id}")
            name_elements = ET.fromstring(response.content).findall(".//data/name")
            localidad_ids = [{"localidad_id": element.get("id")} for element in name_elements]
            all_localidad_ids += localidad_ids

        return all_localidad_ids

    def path(
        self, stream_state: Mapping[str, Any] = None, stream_slice: Mapping[str, Any] = None, next_page_token: Mapping[str, Any] = None
    ) -> str:
        return f"?api_lang={self.api_lang}&localidad={stream_slice.get('localidad_id')}&affiliate_id={self.affiliate_id}&v=3"

    def parse_response(
        self,
        response: requests.Response,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, Any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> Iterable[Mapping]:
        return [response.json()]


# Source
class SourceMeteored(AbstractSource):
    def check_connection(self, logger, config) -> Tuple[bool, any]:
        return True, None

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        auth = NoAuth()
        return [Localidades(authenticator=auth, config=config)]
