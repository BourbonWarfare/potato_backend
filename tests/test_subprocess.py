import pytest

from bw.subprocess.command import Command, define_process


class MockCommand(Command):
    COMMAND = 'mock_command'

    @classmethod
    def locate(cls) -> str:
        return cls.COMMAND


class MockSubcommand1(MockCommand):
    COMMAND = 'subcommand1'


class MockSubcommand2(MockCommand):
    COMMAND = 'subcommand2'


class MockSubSubcommand(MockSubcommand1):
    COMMAND = 'subsub'


class MockSubcommandKeywordArg(MockCommand):
    COMMAND = 'kwarg'
    KEYWORD_ARGUMENTS = {
        'option1': int,
        'option2': str | None,
        'option_3': str,
        'option-4': str,
    }


class MockSubcommandPositionalArg(MockCommand):
    COMMAND = 'arg'
    POSITIONAL_ARGUMENTS = (str, str | None)


class MockSubcommandPositionalKwarg(MockCommand):
    COMMAND = 'both'
    POSITIONAL_ARGUMENTS = (str, str | None)
    KEYWORD_ARGUMENTS = {
        'option1': int,
        'option2': str | None,
        'option_3': str,
        'option-4': str,
    }


@pytest.fixture
def mock_command():
    yield define_process(MockCommand)


def test___python_keyword_arguments__success(mock_command):
    assert mock_command.kwarg._python_keyword_arguments() == {
        'option1': int,
        'option2': str | None,
        'option_3': str,
        'option_4': str,
    }


def test___validate_arguments__returns_kwargs_to_adjust(mock_command):
    assert mock_command.kwarg._validate_arguments(option1=123, option2=None, option_3='value3', option_4='value4') == ['option_4']


def test___validate_arguments__differing_kwargs_len(mock_command):
    with pytest.raises(TypeError):
        mock_command.kwarg._validate_arguments(option1=123, option2=None, option_3='value3', option_4='value4', option_5='value5')


def test___validate_arguments__differing_kwarg(mock_command):
    with pytest.raises(TypeError):
        mock_command.kwarg._validate_arguments(option1=123, option2=None, option_3='value3', option_5='value5')


def test___validate_arguments__kwargs_bad_type_raises(mock_command):
    with pytest.raises(TypeError):
        mock_command.kwarg._validate_arguments(option1='123', option2=None, option_3='value3', option_4='value4')


def test___validate_arguments__kwargs_can_exclude_optional(mock_command):
    mock_command.kwarg._validate_arguments(option1=123, option_3='value3', option_4='value4')


def test___validate_arguments__differing_arg(mock_command):
    with pytest.raises(TypeError):
        mock_command.arg._validate_arguments('123', None, '456')


def test___validate_arguments__args_bad_type_raises(mock_command):
    with pytest.raises(TypeError):
        mock_command.arg._validate_arguments(123, None)


def test___validate_arguments__args_can_exclude_optional(mock_command):
    mock_command.arg._validate_arguments('123')


def test___get_command__kwarg_returns_correct_command(mock_command):
    command = mock_command.kwarg._get_command(option1=123, option2=None, option_3='value3', option_4='value4')
    assert command == [
        'mock_command',
        'kwarg',
        '--option1',
        '123',
        '--option2',
        'None',
        '--option_3',
        'value3',
        '--option-4',
        'value4',
    ]


def test___get_command__arg_returns_correct_command(mock_command):
    command = mock_command.arg._get_command('123', '456')
    assert command == ['mock_command', 'arg', '123', '456']


def test___get_command__arg_kwarg_returns_correct_command(mock_command):
    command = mock_command.both._get_command('abc', 'def', option1=123, option2=None, option_3='value3', option_4='value4')
    assert command == [
        'mock_command',
        'both',
        '--option1',
        '123',
        '--option2',
        'None',
        '--option_3',
        'value3',
        '--option-4',
        'value4',
        'abc',
        'def',
    ]
