import logging
from collections.abc import Callable
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

_RDP_AUTH_CHANNEL = 'Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational'

_RDP_SESSION_CHANNEL = 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational'

logger = logging.getLogger('bw.monitor')


def _parse_xml(xml: str) -> ElementTree.Element:
    try:
        return ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise RemoteConnectionEventParseError(
            f'Invalid XML: {error}',
        ) from error


def _namespace(root: ElementTree.Element) -> str:
    if root.tag.startswith('{'):
        return root.tag.split('}', 1)[0] + '}'
    return ''


def _local_name(element: ElementTree.Element) -> str:
    return element.tag.rsplit('}', 1)[-1]


def _system_fields(
    root: ElementTree.Element,
) -> tuple[int, datetime, str]:
    namespace = _namespace(root)

    event_id = root.findtext(
        f'./{namespace}System/{namespace}EventID',
    )
    if event_id is None:
        raise RemoteConnectionEventMissingField('EventID')

    time_created = root.find(
        f'./{namespace}System/{namespace}TimeCreated',
    )
    if time_created is None:
        raise RemoteConnectionEventMissingField('TimeCreated')

    system_time = time_created.get('SystemTime')
    if system_time is None:
        raise RemoteConnectionEventMissingField('SystemTime')

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

    return parsed_event_id, timestamp, namespace


def _event_xml_params(
    root: ElementTree.Element,
) -> dict[str, str | None]:
    """
    Extract the fields from an EventXML/UserData payload.

    This handles namespaced and unnamespaced XML.
    """
    params: dict[str, str | None] = {}

    for element in root.iter():
        if _local_name(element) != 'EventXML':
            continue

        for child in element:
            params[_local_name(child)] = child.text

        break

    return params


def _session_params(
    root: ElementTree.Element,
) -> dict[str, str | None]:
    """
    Extract fields from LocalSessionManager EventData.

    Unlike event 1149, LocalSessionManager events generally use
    EventData rather than the EventXML structure.
    """
    params: dict[str, str | None] = {}

    for element in root.iter():
        if _local_name(element) != 'EventData':
            continue

        for child in element:
            name = child.get('Name')
            if name is not None:
                params[name] = child.text

        break

    return params


def parse_authentication_success(xml: str) -> RemoteConnectionEvent:
    """
    TerminalServices-RemoteConnectionManager event 1149.

    A user successfully authenticated to the RDP listener.
    """
    root = _parse_xml(xml)

    event_id, timestamp, _ = _system_fields(root)
    params = _event_xml_params(root)

    return RemoteConnectionEvent(
        timestamp=timestamp,
        protocol='rdp',
        action='authentication_success',
        username=params.get('Param1', 'Unknown'),
        domain=params.get('Param2', 'Unknown'),
        source_ip=params.get('Param3', 'Unknown'),
        source='windows',
        source_event_id=event_id,
    )


def parse_session_logon(xml: str) -> RemoteConnectionEvent:
    """
    TerminalServices-LocalSessionManager event 21.

    An RDP session was successfully logged on.
    """
    root = _parse_xml(xml)

    event_id, timestamp, _ = _system_fields(root)
    params = _session_params(root)

    return RemoteConnectionEvent(
        timestamp=timestamp,
        protocol='rdp',
        action='session_start',
        username=params.get('UserName', 'Unknown'),
        domain=params.get('DomainName', 'Unknown'),
        source_ip=params.get('ClientAddress', 'Unknown'),
        source='windows',
        source_event_id=event_id,
    )


def parse_session_reconnect(xml: str) -> RemoteConnectionEvent:
    """
    TerminalServices-LocalSessionManager event 25.

    An existing RDP session was reconnected.
    """
    root = _parse_xml(xml)

    event_id, timestamp, _ = _system_fields(root)
    params = _session_params(root)

    return RemoteConnectionEvent(
        timestamp=timestamp,
        protocol='rdp',
        action='reconnect',
        username=params.get('UserName', 'Unknown'),
        domain=params.get('DomainName', 'Unknown'),
        source_ip=params.get('ClientAddress', 'Unknown'),
        source='windows',
        source_event_id=event_id,
    )


def parse_session_disconnect(xml: str) -> RemoteConnectionEvent:
    """
    TerminalServices-LocalSessionManager event 24.

    An RDP session was disconnected.
    """
    root = _parse_xml(xml)

    event_id, timestamp, _ = _system_fields(root)
    params = _session_params(root)

    return RemoteConnectionEvent(
        timestamp=timestamp,
        protocol='rdp',
        action='disconnect',
        username=params.get('UserName', 'Unknown'),
        domain=params.get('DomainName', 'Unknown'),
        source_ip=params.get('ClientAddress', 'Unknown'),
        source='windows',
        source_event_id=event_id,
    )


def parse_session_logoff(xml: str) -> RemoteConnectionEvent:
    """
    TerminalServices-LocalSessionManager event 23.

    An RDP session was logged off.
    """
    root = _parse_xml(xml)

    event_id, timestamp, _ = _system_fields(root)
    params = _session_params(root)

    return RemoteConnectionEvent(
        timestamp=timestamp,
        protocol='rdp',
        action='session_end',
        username=params.get('UserName', 'Unknown'),
        domain=params.get('DomainName', 'Unknown'),
        source_ip=params.get('ClientAddress', 'Unknown'),
        source='windows',
        source_event_id=event_id,
    )


_PARSERS: dict[int, Callable[[str], RemoteConnectionEvent]] = {
    21: parse_session_logon,
    23: parse_session_logoff,
    24: parse_session_disconnect,
    25: parse_session_reconnect,
    1149: parse_authentication_success,
}


class RemoteConnectionMonitor(Monitor):
    _AUTH_CHANNEL = 'Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational'
    _SESSION_CHANNEL = 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational'

    _AUTH_QUERY = '*[System[EventID=1149]]'
    _SESSION_QUERY = '*[System[EventID=21 or EventID=23 or EventID=24 or EventID=25]]'

    def __init__(self, subscriptions) -> None:
        self._subscriptions = subscriptions

    @classmethod
    def subscribe(cls) -> Self:
        monitor = cls([])

        monitor._subscriptions = [
            win32evtlog.EvtSubscribe(
                cls._AUTH_CHANNEL,
                win32evtlog.EvtSubscribeToFutureEvents,
                Query=cls._AUTH_QUERY,
                Callback=monitor._on_event,
            ),
            win32evtlog.EvtSubscribe(
                cls._SESSION_CHANNEL,
                win32evtlog.EvtSubscribeToFutureEvents,
                Query=cls._SESSION_QUERY,
                Callback=monitor._on_event,
            ),
        ]

        return monitor

    @staticmethod
    def _parse_event(xml: str) -> RemoteConnectionEvent:
        root = _parse_xml(xml)
        event_id, _, _ = _system_fields(root)

        parser = _PARSERS.get(event_id)
        if parser is None:
            raise RemoteConnectionEventInvalidField(
                'EventID',
                str(event_id),
            )

        return parser(xml)

    def _on_event(self, action, context, event_handle) -> None:
        if action != win32evtlog.EvtSubscribeActionDeliver:
            return

        xml = win32evtlog.EvtRender(
            event_handle,
            win32evtlog.EvtRenderEventXml,
        )

        event = self._parse_event(xml)
        self.publish(event)

    def close(self) -> None:
        for subscription in self._subscriptions:
            subscription.Close()

        self._subscriptions = []
