import asyncio
import configparser
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(process)d %(thread)d %(name)s:%(lineno)d %(levelname)s %(message)s')
import os
from pathlib import Path
import sanic
from sanic import Sanic
from .gfwlist2pac import gfwlist2pac


logger = logging.getLogger(__package__)
app = Sanic(__package__)

CACHE_DIR = Path('~/.cache/pac-server').expanduser()
CONFIG_DIR = Path('~/.config/pac-server').expanduser()
CONFIG_FILE = CONFIG_DIR / 'config.ini'

default_config = configparser.ConfigParser(allow_no_value=True)
default_config['server'] = {
    'host': '127.0.0.1',
    'port': '1091'
}
default_config['pac'] = {
    'path': '/pac',
    'proxy': 'PROXY 127.0.0.1:8118;',
    'gfwlist': 'https://github.com/gfwlist/gfwlist/raw/master/gfwlist.txt',
    'precise': 'no',
}
default_config['user-rules'] = {
    '||google.com': '',
    '||google.co.jp': '',
    '||google.co.hk': '',
    '||bbc.co.uk': '',
    '||googleapis.com': '',
    '||googlesyndication.com': '',
    '||github.com': '',
    '||wikipedia.org': '',
}

g_config = {}


async def generate_pac_task():
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                gfwlist2pac,
                str(CACHE_DIR / g_config['pac']['path'].lstrip('/')),
                g_config['pac']['proxy'],
                g_config['pac']['gfwlist'],
                g_config['user-rules'],
                g_config['precise']
            )
        except Exception as e:
            logger.exception(e)
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
    if not (CONFIG_FILE).exists():
        with open(CONFIG_FILE, 'w') as f:
            default_config.write(f)

    config = configparser.ConfigParser(allow_no_value=True)
    config.read(CONFIG_FILE)
    g_config['server'] = {}
    g_config['server']['host'] = config.get('server', 'host', fallback=default_config['server']['host'])
    g_config['server']['port'] = config.getint('server', 'port', fallback=int(default_config['server']['port']))
    g_config['pac'] = {}
    g_config['pac']['path'] = config.get('pac', 'path', fallback=default_config['pac']['path'])
    g_config['pac']['proxy'] = config.get('pac', 'proxy', fallback=default_config['pac']['proxy'])
    g_config['pac']['gfwlist'] = config.get('pac', 'gfwlist', fallback=default_config['pac']['gfwlist'])
    g_config['pac']['precise'] = config.get('pac', 'precise', fallback=default_config['pac']['precise'])
    g_config['user-rules'] = []
    if 'user-rules' in config:
        for user_rule in config['user-rules']:
            g_config['user-rules'].append(user_rule)
    g_config['precise'] = config.getboolean('pac', 'precise', fallback=False)

    app.run(host=g_config['server']['host'], port=g_config['server']['port'], workers=1)


if __name__ == '__main__':
    main()
