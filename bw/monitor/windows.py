from datetime import datetime
from typing import Self
from xml.etree import ElementTree

import win32evtlog

from bw.error.monitor import (
    RemoteConnectionEventInvalidField,
    RemoteConnectionEventMissingField,
    RemoteConnectionEventParseError,
)
from bw.monitor.monitor import Monitor
from bw.web_event.monitor import RemoteConnectionEvent


class RemoteConnectionMonitor(Monitor):
    _CHANNEL = 'Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational'
    _QUERY = '*[System[EventID=1149]]'

    def __init__(self, subscription) -> None:
        self._subscription = subscription

    @classmethod
    def subscribe(cls) -> Self:
        monitor = cls(None)

        monitor._subscription = win32evtlog.EvtSubscribe(
            cls._CHANNEL,
            win32evtlog.EvtSubscribeToFutureEvents,
            Query=cls._QUERY,
            Callback=monitor._on_event,
        )

        return monitor

    def _on_event(self, action, context, event_handle) -> None:
        if action != win32evtlog.EvtSubscribeActionDeliver:
            return

        xml = win32evtlog.EvtRender(
            event_handle,
            win32evtlog.EvtRenderEventXml,
        )

        event = self._parse_event(xml)
        self.publish(event)

    @staticmethod
    def _parse_event(xml: str) -> RemoteConnectionEvent:
        try:
            root = ElementTree.fromstring(xml)
        except ElementTree.ParseError as error:
            raise RemoteConnectionEventParseError(f'Invalid XML: {error}') from error

        # ElementTree represents a namespaced tag as:
        # {namespace}tag
        #
        # Use the namespace from the document when one is present,
        # otherwise use ordinary unqualified element names. This allows
        # the parser to handle both real Windows event XML and the
        # minimal unnamespaced XML used by the validation tests.
        namespace = ''
        if root.tag.startswith('{'):
            namespace = root.tag.split('}', 1)[0] + '}'

        event_id = root.findtext(f'./{namespace}System/{namespace}EventID')
        if event_id is None:
            raise RemoteConnectionEventMissingField('EventID')

        time_created = root.find(f'./{namespace}System/{namespace}TimeCreated')
        if time_created is None:
            raise RemoteConnectionEventMissingField('TimeCreated')

        system_time = time_created.get('SystemTime')
        if system_time is None:
            raise RemoteConnectionEventMissingField('SystemTime')

        params = {}

        user_data = root.find(f'./{namespace}UserData')
        if user_data is not None:
            for element in user_data.iter():
                if element.tag.rsplit('}', 1)[-1] == 'EventXML':
                    for param in element:
                        params[param.tag.rsplit('}', 1)[-1]] = param.text
                    break

        try:
            parsed_event_id = int(event_id)
        except ValueError as error:
            raise RemoteConnectionEventInvalidField(
                'EventID',
                event_id,
            ) from error

        try:
            timestamp = datetime.fromisoformat(system_time)
        except ValueError as error:
            raise RemoteConnectionEventInvalidField(
                'SystemTime',
                system_time,
            ) from error

        return RemoteConnectionEvent(
            timestamp=timestamp,
            protocol='rdp',
            action='authentication_success',
            username=params.get('Param1', 'Unknown'),
            domain=params.get('Param2', 'Unknown'),
            source_ip=params.get('Param3', 'Unknown'),
            source='windows',
            source_event_id=parsed_event_id,
        )

    def close(self) -> None:
        if self._subscription is not None:
            self._subscription.Close()
            self._subscription = None
