import pytest
import win32evtlog

from bw.error.monitor import (
    RemoteConnectionEventInvalidField,
    RemoteConnectionEventMissingField,
    RemoteConnectionEventParseError,
)
from bw.monitor.windows import RemoteConnectionMonitor


@pytest.fixture
def authentication_success_xml():
    return """<?xml version="1.0"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-TerminalServices-RemoteConnectionManager"/>
    <EventID>1149</EventID>
    <TimeCreated SystemTime="2026-08-28T03:44:47.915229300Z"/>
  </System>
  <UserData>
    <EventXML xmlns="Event_NS">
      <Param1>test-user</Param1>
      <Param2>TEST-DOMAIN</Param2>
      <Param3>192.168.1.42</Param3>
    </EventXML>
  </UserData>
</Event>
"""


@pytest.fixture
def session_xml():
    return """<?xml version="1.0"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-TerminalServices-LocalSessionManager"/>
    <EventID>21</EventID>
    <TimeCreated SystemTime="2026-08-28T03:44:47.915229300Z"/>
  </System>
  <EventData>
    <Data Name="UserName">test-user</Data>
    <Data Name="DomainName">TEST-DOMAIN</Data>
    <Data Name="ClientAddress">192.168.1.42</Data>
  </EventData>
</Event>
"""


@pytest.fixture
def subscription(mocker):
    return mocker.Mock()


@pytest.fixture
def subscriptions(mocker):
    return [mocker.Mock(), mocker.Mock()]


def test__remote_connection_monitor__subscribes_to_authentication_events(
    mocker,
    subscriptions,
):
    subscribe = mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=subscriptions,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    assert monitor is not None

    assert subscribe.call_count == 2

    auth_call = subscribe.call_args_list[0]

    assert auth_call.args[0] == ('Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational')
    assert auth_call.args[1] == win32evtlog.EvtSubscribeToFutureEvents
    assert auth_call.kwargs['Query'] == '*[System[EventID=1149]]'


def test__remote_connection_monitor__subscribes_to_session_events(
    mocker,
    subscriptions,
):
    subscribe = mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=subscriptions,
    )

    RemoteConnectionMonitor.subscribe()

    session_call = subscribe.call_args_list[1]

    assert session_call.args[0] == ('Microsoft-Windows-TerminalServices-LocalSessionManager/Operational')
    assert session_call.args[1] == win32evtlog.EvtSubscribeToFutureEvents
    assert session_call.kwargs['Query'] == ('*[System[EventID=21 or EventID=23 or EventID=24 or EventID=25]]')


def test__remote_connection_monitor__publishes_authentication_success(
    mocker,
    authentication_success_xml,
    subscription,
):
    callback = None

    def capture_subscription(*args, **kwargs):
        nonlocal callback
        callback = kwargs['Callback']
        return subscription

    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=capture_subscription,
    )
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtRender',
        return_value=authentication_success_xml,
    )

    monitor = RemoteConnectionMonitor.subscribe()
    monitor.publish = mocker.Mock()

    callback(
        win32evtlog.EvtSubscribeActionDeliver,
        None,
        mocker.sentinel.event_handle,
    )

    monitor.publish.assert_called_once()

    event = monitor.publish.call_args.args[0]

    assert event.protocol == 'rdp'
    assert event.action == 'authentication_success'
    assert event.username == 'test-user'
    assert event.domain == 'TEST-DOMAIN'
    assert event.source_ip == '192.168.1.42'
    assert event.source == 'windows'
    assert event.source_event_id == 1149


@pytest.mark.parametrize(
    ('event_id', 'action'),
    [
        (21, 'session_start'),
        (23, 'session_end'),
        (24, 'disconnect'),
        (25, 'reconnect'),
    ],
)
def test__remote_connection_monitor__publishes_session_event(
    mocker,
    session_xml,
    subscription,
    event_id,
    action,
):
    xml = session_xml.replace(
        '<EventID>21</EventID>',
        f'<EventID>{event_id}</EventID>',
    )

    callback = None

    def capture_subscription(*args, **kwargs):
        nonlocal callback
        callback = kwargs['Callback']
        return subscription

    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=capture_subscription,
    )
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtRender',
        return_value=xml,
    )

    monitor = RemoteConnectionMonitor.subscribe()
    monitor.publish = mocker.Mock()

    callback(
        win32evtlog.EvtSubscribeActionDeliver,
        None,
        mocker.sentinel.event_handle,
    )

    monitor.publish.assert_called_once()

    event = monitor.publish.call_args.args[0]

    assert event.protocol == 'rdp'
    assert event.action == action
    assert event.username == 'test-user'
    assert event.domain == 'TEST-DOMAIN'
    assert event.source_ip == '192.168.1.42'
    assert event.source == 'windows'
    assert event.source_event_id == event_id


def test__remote_connection_monitor__ignores_non_delivery_events(
    mocker,
    subscription,
):
    callback = None

    def capture_subscription(*args, **kwargs):
        nonlocal callback
        callback = kwargs['Callback']
        return subscription

    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=capture_subscription,
    )

    monitor = RemoteConnectionMonitor.subscribe()
    monitor.publish = mocker.Mock()

    callback(
        win32evtlog.EvtSubscribeActionError,
        None,
        mocker.sentinel.error,
    )

    monitor.publish.assert_not_called()


def test__remote_connection_monitor__rejects_invalid_xml(subscription):
    with pytest.raises(RemoteConnectionEventParseError):
        RemoteConnectionMonitor._parse_event('<not valid xml')


def test__remote_connection_monitor__rejects_missing_event_id():
    xml = """<Event>
    <System>
        <TimeCreated SystemTime="2026-08-25T20:15:30+00:00" />
    </System>
</Event>
"""

    with pytest.raises(RemoteConnectionEventMissingField):
        RemoteConnectionMonitor._parse_event(xml)


def test__remote_connection_monitor__rejects_missing_timestamp():
    xml = """<Event>
    <System>
        <EventID>1149</EventID>
    </System>
</Event>
"""

    with pytest.raises(RemoteConnectionEventMissingField):
        RemoteConnectionMonitor._parse_event(xml)


def test__remote_connection_monitor__rejects_missing_system_time():
    xml = """<Event>
    <System>
        <EventID>1149</EventID>
        <TimeCreated />
    </System>
</Event>
"""

    with pytest.raises(RemoteConnectionEventMissingField):
        RemoteConnectionMonitor._parse_event(xml)


def test__remote_connection_monitor__rejects_invalid_event_id():
    xml = """<Event>
    <System>
        <EventID>not-an-id</EventID>
        <TimeCreated SystemTime="2026-08-25T20:15:30+00:00" />
    </System>
</Event>
"""

    with pytest.raises(RemoteConnectionEventInvalidField):
        RemoteConnectionMonitor._parse_event(xml)


def test__remote_connection_monitor__rejects_invalid_timestamp():
    xml = """<Event>
    <System>
        <EventID>1149</EventID>
        <TimeCreated SystemTime="not-a-timestamp" />
    </System>
</Event>
"""

    with pytest.raises(RemoteConnectionEventInvalidField):
        RemoteConnectionMonitor._parse_event(xml)


def test__remote_connection_monitor__closes_all_subscriptions(
    mocker,
    subscriptions,
):
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=subscriptions,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    monitor.close()

    for subscription in subscriptions:
        subscription.Close.assert_called_once()


def test__remote_connection_monitor__close_is_idempotent(
    mocker,
    subscriptions,
):
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        side_effect=subscriptions,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    monitor.close()
    monitor.close()

    for subscription in subscriptions:
        subscription.Close.assert_called_once()
