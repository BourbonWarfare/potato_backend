import json

import pytest

from bw.response import JsonResponse


@pytest.mark.asyncio
async def test__json_response__supports_setting_json_values():
    response = JsonResponse({'mission': 'foobar'})

    response['creation_date_display'] = '2026-09-07 16:20'

    assert response['creation_date_display'] == '2026-09-07 16:20'
    assert json.loads(await response.get_data(as_text=True))['creation_date_display'] == '2026-09-07 16:20'
