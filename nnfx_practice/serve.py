"""Trusted-LAN WSGI dashboard; never loads private settings or a broker."""

import argparse
from pathlib import Path

from waitress import serve

from .dashboard import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/var/lib/nnfx-practice'))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8878)
    args = parser.parse_args()
    serve(create_app(args.root), host=args.host, port=args.port, threads=4)


if __name__ == '__main__':
    main()
