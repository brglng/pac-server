#!/usr/bin/python3
import base64
import json
import logging
import urllib.parse, urllib.request
from argparse import ArgumentParser
from pathlib import Path

__all__ = ['gfwlist2pac']
logger = logging.getLogger(__name__)
GFWLIST_URL = 'https://github.com/gfwlist/gfwlist/raw/master/gfwlist.txt'


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('-g', '--gfwlist', dest='gfwlist',
                        help='path to gfwlist', metavar='GFWLIST')
    parser.add_argument('-o', '--output', dest='output', required=True,
                        help='path to output pac', metavar='PAC')
    parser.add_argument('-p', '--proxy', dest='proxy', required=True,
                        help='the proxy parameter in the pac file, '
                             'for example, "SOCKS5 127.0.0.1:1080;"',
                        metavar='PROXY')
    parser.add_argument('--user-rule', dest='user_rule',
                        help='user rule file, which will be appended to'
                             ' gfwlist')
    parser.add_argument('--precise', dest='precise', action='store_true',
                        help='use adblock plus algorithm instead of O(1)'
                             ' lookup')
    return parser.parse_args()


def decode_gfwlist(content):
    # decode base64 if have to
    try:
        if '.' in content:
            raise Exception()
        return base64.b64decode(content).decode()
    except Exception as e:
        logger.exception(e)
        return content


def get_hostname(something):
    try:
        # quite enough for GFW
        if not something.startswith('http:'):
            something = 'http://' + something
        r = urllib.parse.urlparse(something)
        return r.hostname
    except Exception as e:
        logger.exception(e)
        return None


def add_domain_to_set(s, something):
    hostname = get_hostname(something)
    if hostname is not None:
        s.add(hostname)


def combine_lists(content, user_rule=None):
    builtin_rules = open(Path(__file__).parent / 'resources' / 'builtin.txt').read().splitlines(False)
    gfwlist = content.splitlines(False)
    gfwlist.extend(builtin_rules)
    if user_rule:
        gfwlist.extend(user_rule.splitlines(False))
    return gfwlist


def parse_gfwlist(gfwlist):
    domains = set()
    for line in gfwlist:
        if line.find('.*') >= 0:
            continue
        elif line.find('*') >= 0:
            line = line.replace('*', '/')
        if line.startswith('||'):
            line = line.lstrip('||')
        elif line.startswith('|'):
            line = line.lstrip('|')
        elif line.startswith('.'):
            line = line.lstrip('.')
        if line.startswith('!'):
            continue
        elif line.startswith('['):
            continue
        elif line.startswith('@'):
            # ignore white list
            continue
        add_domain_to_set(domains, line)
    return domains


def reduce_domains(domains):
    # reduce 'www.google.com' to 'google.com'
    # remove invalid domains
    tld_content = open(Path(__file__).parent / 'resources' / 'tld.txt').read()
    tlds = set(tld_content.splitlines(False))
    new_domains = set()
    for domain in domains:
        domain_parts = domain.split('.')
        last_root_domain = None
        for i in range(0, len(domain_parts)):
            root_domain = '.'.join(domain_parts[len(domain_parts) - i - 1:])
            if i == 0:
                if not tlds.__contains__(root_domain):
                    # root_domain is not a valid tld
                    break
            last_root_domain = root_domain
            if tlds.__contains__(root_domain):
                continue
            else:
                break
        if last_root_domain is not None:
            new_domains.add(last_root_domain)
    return new_domains


def generate_pac_fast(domains, proxy):
    # render the pac file
    proxy_content = open(Path(__file__).parent / 'resources' / 'proxy.pac').read()
    domains_dict = {}
    for domain in domains:
        domains_dict[domain] = 1
    proxy_content = proxy_content.replace('__PROXY__', json.dumps(str(proxy)))
    proxy_content = proxy_content.replace('__DOMAINS__',
                                          json.dumps(domains_dict, indent=2))
    return proxy_content


def generate_pac_precise(rules, proxy):
    def grep_rule(rule):
        if rule:
            if rule.startswith('!'):
                return None
            if rule.startswith('['):
                return None
            return rule
        return None
    # render the pac file
    proxy_content = open(Path(__file__).parent / 'resources' / 'abp.js').read()
    rules = filter(grep_rule, rules)
    proxy_content = proxy_content.replace('__PROXY__', json.dumps(str(proxy)))
    proxy_content = proxy_content.replace('__RULES__',
                                          json.dumps(rules, indent=2))
    return proxy_content


def gfwlist2pac(pac, proxy, gfwlist=None, user_rule=None, precise=False):
    if gfwlist:
        gfwlist_parts = urllib.parse.urlsplit(gfwlist)
        if not gfwlist_parts.scheme or not gfwlist_parts.netloc:
            # It's not an URL, deal it as local file
            with open(gfwlist, 'r') as f:
                content = f.read()
        else:
            # Yeah, it's an URL, try to download it
            logger.info('Downloading gfwlist from %s' % gfwlist)
            content = urllib.request.urlopen(gfwlist, timeout=10).read().decode()
    else:
        logger.info('Downloading gfwlist from %s' % GFWLIST_URL)
        content = urllib.request.urlopen(GFWLIST_URL, timeout=10).read().decode()

    if user_rule:
        userrule_parts = urllib.parse.urlsplit(user_rule)
        if not userrule_parts.scheme or not userrule_parts.netloc:
            # It's not an URL, deal it as local file
            with open(user_rule, 'r') as f:
                user_rule = f.read()
        else:
            # Yeah, it's an URL, try to download it
            logger.info('Downloading user rules file from %s' % user_rule)
            user_rule = urllib.request.urlopen(user_rule, timeout=10).read().decode()

    content = decode_gfwlist(content)
    gfw_list = combine_lists(content, user_rule)
    if precise:
        pac_content = generate_pac_precise(gfw_list, proxy)
    else:
        domains = parse_gfwlist(gfw_list)
        domains = reduce_domains(domains)
        pac_content = generate_pac_fast(domains, proxy)

    with open(pac, 'w') as f:
        f.write(pac_content)


if __name__ == '__main__':
    args = parse_args()
    gfwlist2pac(args.output, args.proxy, args.gfwlist, args.user_rule, args.precise)
