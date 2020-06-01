import asyncio
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(process)d %(thread)d %(name)s:%(lineno)d %(levelname)s %(message)s')
import os
from pathlib import Path
import sanic
from sanic import Sanic
from .gfwlist2pac import gfwlist2pac


logger = logging.getLogger(__package__)
app = Sanic(__package__)

CONFIG_DIR = Path('~/.config/pac-server').expanduser()
CACHE_DIR = Path('~/.cache/pac-server').expanduser()


async def generate_pac_task():
    while True:
        await asyncio.get_event_loop().run_in_executor(None, gfwlist2pac, str(CACHE_DIR / 'pac'), 'PROXY 127.0.0.1:8118;')
        await asyncio.sleep(60)


@app.listener('before_server_start')
async def run_generate_pac_task(app, loop):
    asyncio.ensure_future(generate_pac_task(), loop=loop)


@app.route('/<filename>', methods=['GET'])
async def get_file(request, filename):
    try:
        return await sanic.response.file(str((CACHE_DIR / filename)), headers={'Access-Control-Allow-Origin': request.remote_addr})
    except FileNotFoundError:
        return sanic.response.text('404 Not Found', 404, headers={'Access-Control-Allow-Origin': request.remote_addr})


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(CONFIG_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=12345, workers=1)
