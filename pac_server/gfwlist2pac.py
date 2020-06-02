#!/usr/bin/python3
import base64
import json
import logging
import urllib.parse, urllib.request
from argparse import ArgumentParser
from pathlib import Path

__all__ = ['gfwlist2pac']
logger = logging.getLogger(__name__)


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('--gfwlist', dest='gfwlist',
                        help='path to gfwlist', metavar='GFWLIST',
                        default='https://github.com/gfwlist/gfwlist/raw/master/gfwlist.txt')
    parser.add_argument('-o', '--output', dest='output', required=True,
                        help='path to output pac', metavar='PAC')
    parser.add_argument('--proxy', dest='proxy', required=True,
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


def combine_lists(content, user_rules=()):
    gfwlist = content.splitlines(False)
    if user_rules:
        gfwlist.extend(user_rules)
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


def gfwlist2pac(pac, proxy, gfwlist, user_rules=(), precise=False):
    gfwlist_parts = urllib.parse.urlsplit(gfwlist)
    if not gfwlist_parts.scheme or not gfwlist_parts.netloc:
        # It's not a URL, deal it as local file
        logger.info('Reading gfwlist from %s' % gfwlist)
        with open(gfwlist, 'r') as f:
            content = f.read()
    else:
        # Yeah, it's a URL, try to download it
        logger.info('Downloading gfwlist from %s' % gfwlist)
        content = urllib.request.urlopen(gfwlist, timeout=10).read().decode()

    content = decode_gfwlist(content)
    gfw_list = combine_lists(content, user_rules)
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
    if args.user_rule:
        user_rule_parts = urllib.parse.urlsplit(args.user_rule)
        if not user_rule_parts.scheme or not user_rule_parts.netloc:
            # It's not a URL, deal it as local file
            logger.info('Reading user rules from %s' % args.user_rule)
            with open(args.user_rule, 'r') as f:
                user_rules = f.read().splitlines(False)
        else:
            # Yeah, it's a URL, try to download it
            logger.info('Downloading user rules from %s' % args.user_rule)
            user_rules = urllib.request.urlopen(args.user_rule, timeout=10).read().decode().splitlines(False)
    else:
        user_rules = []

    gfwlist2pac(args.output, args.proxy, args.gfwlist, user_rules, args.precise)
