#!/usr/bin/env python3
"""Git credential response for the configured GitHub host; never log secrets."""
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


def response(prompt, token):
    urls = re.findall(r"https://[^'\s]+", prompt)
    if len(urls) != 1:
        raise ValueError('Unsupported credential destination')
    parsed = urlsplit(urls[0])
    if parsed.hostname != 'github.com' or parsed.port not in (None, 443):
        raise ValueError('Unsupported credential destination')
    if prompt.startswith('Username'):
        return 'x-access-token'
    if prompt.startswith('Password'):
        return token
    raise ValueError('Unsupported credential prompt')


def main():
    filename = os.environ.get('WWL_GITHUB_TOKEN_FILE')
    if not filename:
        result = subprocess.run(['git', 'config', '--get', 'wwl.githubTokenFile'],
                                capture_output=True, text=True, check=True)
        filename = result.stdout.strip()
    path = Path(filename)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('Credential file unavailable')
    token = path.read_text().strip()
    if not token or any(c.isspace() for c in token):
        raise ValueError('Invalid credential file format')
    print(response(sys.argv[1] if len(sys.argv) > 1 else '', token))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('WWL: GitHub credential unavailable or destination refused', file=sys.stderr)
        sys.exit(1)
