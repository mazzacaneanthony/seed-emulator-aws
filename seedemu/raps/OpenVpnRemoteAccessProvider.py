from seedemu.core import RemoteAccessProvider, Emulator, Network, Node
from seedemu.core.enums import NodeRole
from typing import Dict
from itertools import repeat

OpenVpnRapFileTemplates: Dict[str, str] = {}

with open('ovpn_key') as f:
    OpenVpnRapFileTemplates['ovpn_key'] = f.read()

with open('ovpn_ca.crt'):
    OpenVpnRapFileTemplates['ovpn_ca'] = f.read()

with open('ovpn_cert.crt') as f:
    OpenVpnRapFileTemplates['ovpn_cert'] = f.read()

with open('ovpn_server_config.ovpn') as f:
    OpenVpnRapFileTemplates['ovpn_server_config'] = f.read()

with open('ovpn_startup.sh') as f:
    OpenVpnRapFileTemplates['ovpn_startup_script'] = f.read()

class OpenVpnRemoteAccessProvider(RemoteAccessProvider):

    __cur_port: int
    __naddrs: int

    __ovpn_ca: str
    __ovpn_cert: str
    __ovpn_key: str


    def __init__(self, startPort: int = 65000, naddrs: int = 8, ovpnCa: str = None, ovpnCert: str = None, ovpnKey: str = None):
        """!
        @brief OpenVPN remote access provider constructor.

        if you do not set ca/cert/key, builtin ones will be used. to connect, 
        use the client configuration under misc/ folder. 

        @param startPort (optional) port number to start assigning from for
        port forwarding to the open server. 
        @param naddrs number of IP addresses to assign to client pool.
        @param ovpnCa (optional) CA to use for openvpn.
        @param ovpnCert (optional) server certificate to use for openvpn.
        @param ovpnKey (optional) server key to use for openvpn.
        """
        super().__init__()

        self.__cur_port = startPort
        self.__naddrs = naddrs
        self.__ovpn_ca = ovpnCa
        self.__ovpn_cert = ovpnCert
        self.__ovpn_key = ovpnKey
    
    def getName(self) -> str:
        return 'OpenVpn'

    def configureRemoteAccess(self, emulator: Emulator, netObject: Network, brNode: Node, brNet: Network):
        self._log('setting up OpenVPN remote access for {} in AS{}...'.format(netObject.getName(), brNode.getAsn()))

        brNode.addSoftware('openvpn')
        brNode.addSoftware('bridge-utils')

        addrstart = addrend = netObject.assign(NodeRole.Host)
        for i in repeat(None, self.__naddrs - 1): addrend = netObject.assign(NodeRole.Host)

        brNode.setFile('/ovpn-server.conf', OpenVpnRapFileTemplates['ovpn_server_config'].format(
            addressStart = addrstart,
            addressEnd = addrend,
            addressMask = netObject.getPrefix().netmask,
            key = self.__ovpn_key if self.__ovpn_key != None else OpenVpnRapFileTemplates['ovpn_key'],
            ca = self.__ovpn_ca if self.__ovpn_ca != None else OpenVpnRapFileTemplates['ovpn_ca'],
            cert = self.__ovpn_cert if self.__ovpn_cert != None else OpenVpnRapFileTemplates['ovpn_cert']
        ))

        brNode.setFile('/ovpn_startup.sh', OpenVpnRapFileTemplates['ovpn_startup_script'])

        # note: ovpn_startup will invoke interface_setup, and replace interface_setup script with a dummy. 
        brNode.appendStartCommand('chmod +x /ovpn_startup.sh')
        brNode.appendStartCommand('/ovpn_startup.sh {}'.format(netObject.getName()))

        brNode.appendStartCommand('ip route add default via {} dev {}'.format(brNet.getPrefix()[1], brNet.getName()))

        brNode.joinNetwork(brNet.getName())
        brNode.joinNetwork(netObject.getName())

        brNode.addPort(self.__cur_port, 1194, 'udp')

        self.__cur_port += 1