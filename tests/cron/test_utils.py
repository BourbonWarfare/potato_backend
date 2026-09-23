import pytest

from bw.cron.utils import backoff


@pytest.fixture(scope='session')
def return_value_1():
    return 'result'


@pytest.mark.asyncio
async def test__backoff__returns_sync_function_result(return_value_1):
    """Test that backoff returns the result of a successful sync function."""
    # Not yet reviewed

    @backoff()
    def wrapped():
        return return_value_1

    assert await wrapped() == return_value_1


@pytest.mark.asyncio
async def test__backoff__returns_async_function_result(return_value_1):
    """Test that backoff returns the result of a successful async function."""
    # Not yet reviewed

    @backoff()
    async def wrapped():
        return return_value_1

    assert await wrapped() == return_value_1


@pytest.mark.asyncio
async def test__backoff__retries_until_success(mocker, return_value_1):
    """Test that backoff retries failures until the function succeeds."""
    # Not yet reviewed
    sleep = mocker.patch('bw.cron.utils.asyncio.sleep')
    mocker.patch('bw.cron.utils.random.random', return_value=0)
    calls = {'count': 0}

    @backoff(delay=1, retries=3)
    async def wrapped():
        calls['count'] += 1
        if calls['count'] < 2:
            raise ValueError('try again')
        return return_value_1

    assert await wrapped() == return_value_1
    assert calls['count'] == 2
    sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test__backoff__raises_after_retries_exhausted(mocker):
    """Test that backoff raises the final exception after retries are exhausted."""
    # Not yet reviewed
    sleep = mocker.patch('bw.cron.utils.asyncio.sleep')
    mocker.patch('bw.cron.utils.random.random', return_value=0)

    @backoff(delay=1, retries=2)
    async def wrapped():
        raise ValueError('failed')

    with pytest.raises(ValueError):
        await wrapped()

    sleep.assert_called_once_with(1)


@pytest.mark.asyncio
async def test__backoff__caps_delay_at_max_delay(mocker):
    """Test that backoff caps retry delay at max_delay."""
    # Not yet reviewed
    sleep = mocker.patch('bw.cron.utils.asyncio.sleep')
    mocker.patch('bw.cron.utils.random.random', return_value=0)
    calls = {'count': 0}

    @backoff(delay=2, retries=4, max_delay=3)
    async def wrapped():
        calls['count'] += 1
        if calls['count'] < 4:
            raise ValueError('try again')
        return 'done'

    assert await wrapped() == 'done'
    assert [call.args[0] for call in sleep.call_args_list] == [2, 3, 3]
