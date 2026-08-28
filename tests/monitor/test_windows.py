import pytest
import win32evtlog

from bw.error.monitor import (
    RemoteConnectionEventInvalidField,
    RemoteConnectionEventMissingField,
    RemoteConnectionEventParseError,
)
from bw.monitor.windows import RemoteConnectionMonitor


@pytest.fixture
def event_xml():
    return """<?xml version="1.0"?>
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-TerminalServices-RemoteConnectionManager" Guid="{00000000-0000-0000-0000-000000000000}"/>
    <EventID>1149</EventID>
    <Version>0</Version>
    <Level>4</Level>
    <Task>0</Task>
    <Opcode>0</Opcode>
    <Keywords>0x0000000000000000</Keywords>
    <TimeCreated SystemTime="2026-08-28T03:44:47.915229300Z"/>
    <EventRecordID>51175961</EventRecordID>
    <Correlation ActivityID="{00000000-0000-0000-0000-000000000000}"/>
    <Execution ProcessID="872" ThreadID="375024"/>
    <Channel>Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational</Channel>
    <Computer>Bourbon Warfare Computer Server</Computer>
    <Security UserID="0-0-0-00"/>
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
def subscription(mocker):
    return mocker.Mock()


@pytest.fixture
def monitor(mocker, subscription):
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        return_value=subscription,
    )
    return RemoteConnectionMonitor.subscribe()


def test__remote_connection_monitor__subscribes(mocker, subscription):
    subscribe = mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        return_value=subscription,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    assert monitor is not None
    subscribe.assert_called_once()


def test__remote_connection_monitor__publishes_rdp_event(
    mocker,
    event_xml,
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
        return_value=event_xml,
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


def test__remote_connection_monitor__closes_subscription(mocker, subscription):
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        return_value=subscription,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    monitor.close()

    subscription.Close.assert_called_once()


def test__remote_connection_monitor__close_is_idempotent(mocker, subscription):
    mocker.patch(
        'bw.monitor.windows.win32evtlog.EvtSubscribe',
        return_value=subscription,
    )

    monitor = RemoteConnectionMonitor.subscribe()

    monitor.close()
    monitor.close()

    subscription.Close.assert_called_once()
