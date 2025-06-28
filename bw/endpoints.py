from bw.server import app
from bw.web_utils import json_api
from bw.response import JsonResponse


@app.post('/')
@json_api
async def test_post(test: int):
    print(test)
    return JsonResponse({'test': test})


@app.get('/')
async def test_get():
    return 'hello!'
