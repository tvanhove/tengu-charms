#!/usr/bin/python
# source: https://www.howtoforge.com/nat_iptables
# pylint: disable=c0111,c0103
import setup # pylint: disable=F0401
setup.pre_install()

import sys
import subprocess

from charmhelpers.core import hookenv, templating, host
from charmhelpers.core.hookenv import Hooks
from charmhelpers import fetch

from netifaces import AF_INET
import netifaces
import netaddr

HOOKS = Hooks()

@HOOKS.hook('install')
def install():
    hookenv.log('Installing isc-dhcp')
    fetch.apt_update()
    fetch.apt_install(fetch.filter_installed_packages(['isc-dhcp-server']))
    hookenv.log('Configuring isc-dhcp')
    private_network = netaddr.IPNetwork('192.168.14.0/24')
    private_dhcp_range = '192.168.14.150 192.168.14.253'
    dns = ", ".join(get_dns())
    private_if = None
    public_ifs = []
    private_netmask = None
    private_addr = None
    for interface in netifaces.interfaces():
        af_inet = netifaces.ifaddresses(interface).get(AF_INET)
        if af_inet and af_inet[0].get('broadcast'):
            broadcast = netifaces.ifaddresses(interface)[AF_INET][0]['broadcast']
            netmask = netifaces.ifaddresses(interface)[AF_INET][0]['netmask']
            addr = netifaces.ifaddresses(interface)[AF_INET][0]['addr']
            if netaddr.IPAddress(addr) in private_network:
                private_if = interface
                private_addr = addr
                private_netmask = netmask
                private_broadcast = broadcast
            else:
                public_ifs.append(interface)
    assert private_if
    templating.render(
        source='isc-dhcp-server',
        target='/etc/default/isc-dhcp-server',
        context={
            'interfaces': private_if
        }
    )
    templating.render(
        source='dhcpd.conf',
        target='/etc/dhcp/dhcpd.conf',
        context={
            'subnet': private_network.ip,
            'netmask': private_netmask,
            'routers': private_addr,
            'broadcast_address': private_broadcast,
            'domain_name_servers': dns,
            'dhcp_range': private_dhcp_range,
        }
    )
    host.service_restart('isc-dhcp-server')

    for pub_if in public_ifs:
        subprocess.check_output(['iptables', '--table', 'nat', '--append', 'POSTROUTING', '--out-interface', pub_if, '-j', 'MASQUERADE'])
    subprocess.check_output(['iptables', '--append', 'FORWARD', '--in-interface', private_if, '-j', 'ACCEPT'])
    hookenv.status_set('active', 'Ready')


def get_dns():
    dns_ips = []
    with open('/etc/resolv.conf', 'r') as resolvfile:
        lines = resolvfile.readlines()
    for line in lines:
        columns = line.split()
        if columns[0] == 'nameserver':
            dns_ips.extend(columns[1:])
    return dns_ips


def get_routes():
    """ Returns the routes as an array with dicts for each route """
    output = subprocess.check_output(['route', '-n'])
    output = output.split('\n', 1)[-1]
    soutput = output.split('\n', 1)
    [header, table] = soutput[0:2]
    coll_heads = header.lower().split()
    result = []
    for line in table.rstrip().split('\n'):
        coll_contents = line.split()
        r_dict = {}
        for i in range(0, len(coll_heads)):
            r_dict[coll_heads[i]] = coll_contents[i]
        result.append(r_dict)
    return result


def get_gateway_if():
    routes = get_routes()
    for route in routes:
        if route['destination'] == '0.0.0.0':
            return route['iface']


@HOOKS.hook('config-changed')
def configure_forwarders():



if __name__ == "__main__":
    HOOKS.execute(sys.argv)