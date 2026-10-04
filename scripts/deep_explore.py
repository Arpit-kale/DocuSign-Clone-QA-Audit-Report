#!/usr/bin/env python3
"""Deep explore clone HTML for each known route."""
import requests
from requests.auth import HTTPBasicAuth
import re, json
from auth_config import get_http_credentials

auth = HTTPBasicAuth(*get_http_credentials())

routes = [
    '/send/home',
    '/send/documents',
    '/send/templates',
]

for route in routes:
    r = requests.get('http://13.207.185.159' + route, auth=auth, timeout=15, verify=False)
    html = r.text
    print(f'\n{"="*60}')
    print(f'ROUTE: {route}  ({r.status_code})')
    print(f'{"="*60}')
    
    # Extract visible text content patterns
    # Strip scripts and style tags first
    html_clean = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    html_clean = re.sub(r'<style[^>]*>.*?</style>', '', html_clean, flags=re.DOTALL)
    
    # Extract text nodes
    texts = re.findall(r'>([^<]{3,100})<', html_clean)
    texts = [t.strip() for t in texts if t.strip() and not t.strip().startswith('{')]
    print('Visible text fragments:')
    for t in texts[:40]: print(f'  "{t}"')
    
    # Extract buttons
    buttons = re.findall(r'<button[^>]*>(.*?)</button>', html, re.DOTALL)
    print('\nButtons:')
    for b in buttons[:20]:
        btxt = re.sub(r'<[^>]+>', '', b).strip()
        if btxt: print(f'  [{btxt}]')
    
    # Extract links
    links = re.findall(r'href="(/send/[^"]*?)"', html)
    print('\nLinks to /send/...:')
    for l in sorted(set(links)): print(f'  {l}')
    
    print()
