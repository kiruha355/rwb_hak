#!/usr/bin/env python3
"""Check the explainer's paths, anchors and pinned repo links in a Git tree.

Usage: python3 docs/phase-20261028/check-publication.py REF
No network, browser or working-tree link substitutions.
"""
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit
import json
import posixpath
import subprocess
import sys

ref = sys.argv[1]
entry = 'docs/phase-20261028/index.html'


def git(*args):
    return subprocess.check_output(['git', *args])


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            if attrs['id'] in self.ids:
                raise ValueError('Duplicate anchor: ' + attrs['id'])
            self.ids.add(attrs['id'])
        if tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])


paths = set(git('ls-tree', '-r', '--name-only', '-z', ref).decode().split('\0'))
parser = Links()
parser.feed(git('show', f'{ref}:{entry}').decode())
errors = []
checked = []
for href in parser.links:
    url = urlsplit(href)
    path = unquote(url.path)
    if not url.scheme and not url.netloc:
        target = posixpath.normpath(str(PurePosixPath(entry).parent / path)) if path else entry
        if target not in paths:
            errors.append(f'Missing target-tree file: {href}')
        elif url.fragment and target == entry and unquote(url.fragment) not in parser.ids:
            errors.append(f'Missing anchor: {href}')
        checked.append(href)
    elif url.netloc == 'github.com' and path.startswith('/kiruha355/rwb_hak/blob/'):
        suffix = path.split('/blob/', 1)[1]
        sha, filename = suffix.split('/', 1)
        try:
            git('cat-file', '-e', f'{sha}:{filename}')
            checked.append(href)
        except subprocess.CalledProcessError:
            errors.append(f'Missing pinned repo blob: {href}')
    elif url.scheme == 'file':
        errors.append(f'Local filesystem URL in shared page: {href}')
print(json.dumps({'ref': git('rev-parse', ref).decode().strip(), 'entry': entry,
                  'scope': 'git_tree_paths_internal_anchors_pinned_repo_blobs',
                  'checked': len(checked), 'errors': errors}, ensure_ascii=False, indent=2))
raise SystemExit(bool(errors))
