#!/usr/bin/env python3
"""Explore the clone routes and HTML structure."""
import requests
from requests.auth import HTTPBasicAuth
import re

from auth_config import get_http_credentials

auth = HTTPBasicAuth(*get_http_credentials())

# Get more of the home page
r = requests.get('http://13.207.185.159/send/home', auth=auth, timeout=15, verify=False)
html = r.text

# Extract nav links
nav_links = re.findall(r'href="(/[^"]*?)"', html)
nav_links = list(set(nav_links))
print('Nav links found:')
for l in sorted(nav_links): print(' ', l)

print()
# Extract JS chunk references
chunks = re.findall(r'app/([^"]*?)/page', html)
print('App routes from chunks:')
for c in sorted(set(chunks)): print(' ', c)

print()
print('--- Title / Meta ---')
title_m = re.search(r'<title>(.*?)</title>', html)
desc_m = re.search(r'name="description" content="(.*?)"', html)
print('Title:', title_m.group(1) if title_m else 'N/A')
print('Desc:', desc_m.group(1) if desc_m else 'N/A')

print()
print('--- Key HTML structure (first 200 chars per element) ---')
# Find main content areas
body_start = html.find('<body')
if body_start > 0:
    body_html = html[body_start:body_start+5000]
    print(body_html[:3000])
