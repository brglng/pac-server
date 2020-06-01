#!/usr/bin/env python3
from setuptools import setup

setup(
    name='pac-server',
    version='0.1.0',

    packages=['pac_server'],
    package_data={'pac_server': ['resources/*']},
    exclude_package_data={'': ['.git', '.gitignore']},

    install_requires=[
        'aiohttp>=3.6,<4',
        'cchardet>=2.1,<3',
        'aiodns>=2.0,<3',
        'sanic>-19.0',
    ],

    author='Zhaosheng Pan',
    author_email='zhaosheng.pan@sololand.moe',
    description='Simple PAC Server',
    url='http://github.com/brglng/pac-server',

    zip_safe=False,

    entry_points={
        'console_scripts': [
            'pac-server = pac_server.__main__:main',
        ]
    }
)
