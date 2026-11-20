"""Network Topology Tree & Connected Server Discovery Engine for Ghost-OS.

Extracts enterprise and local network infrastructure relationships:
- Domain / Workgroup membership (Active Directory Domain vs Workgroup)
- Active DNS Servers, DHCP Gateway, and Default Router
- Active Server Connections (Established TCP sessions to Database, File, Cloud, and AD servers)
- Subnet Neighbor Discovery (ARP / Neighbor cache listing other systems on the network)
"""

import platform
import re
import socket
import subprocess
from typing import Dict, List, Optional

from ghost_core.schemas.scan import (
    ConnectedServerSpec,
    DiscoveredNeighborSpec,
    NetworkTopologyTreeSpec,
)


KNOWN_PORT_SERVICES: Dict[int, str] = {
    53: "DNS Name Server",
    80: "HTTP Web Server",
    88: "Kerberos / Active Directory KDC",
    102: "Siemens S7 Industrial Controller",
    139: "NetBIOS Session Service",
    389: "Active Directory / LDAP Directory Server",
    443: "HTTPS / Cloud Gateway Server",
    445: "Microsoft-DS / SMB Enterprise File Share",
    502: "Modbus TCP Industrial Controller",
    636: "LDAPS Secure Directory Server",
    1433: "Microsoft SQL Server Database",
    1521: "Oracle Database Server",
    3306: "MySQL Database Server",
    3389: "Windows Remote Desktop (RDP) Server",
    5432: "PostgreSQL Database Server",
    44818: "EtherNet/IP Rockwell Industrial Server",
}


class NetworkTopologyScanner:
    """Discovers connected servers, local subnet neighbors, and domain topology."""

    @classmethod
    def scan_topology(cls) -> NetworkTopologyTreeSpec:
        """Runs native platform network discovery."""
        current_os = platform.system()
        if current_os == "Windows":
            return cls.scan_windows_topology()
        elif current_os == "Linux":
            return cls.scan_linux_topology()
        return cls.create_simulated_topology()

    @classmethod
    def scan_windows_topology(cls) -> NetworkTopologyTreeSpec:
        """Interrogates Windows network configuration, ARP cache, and TCP socket tables."""
        domain = "WORKGROUP"
        dns_servers: List[str] = []
        gateway: Optional[str] = None
        dhcp: Optional[str] = None

        # 1. Query Domain & Computer System
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Domain"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                domain = res.stdout.strip()
        except Exception:
            pass

        # 2. Query DNS & Default Gateway via NetworkAdapterConfiguration
        try:
            ps_net = """
            Get-CimInstance Win32_NetworkAdapterConfiguration | Where-Object { $_.IPEnabled -eq $true } | 
            Select-Object DNSServerSearchOrder, DefaultIPGateway, DHCPServer | ConvertTo-Json -Compress
            """
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_net], capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                import json
                data = json.loads(res.stdout)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    dns_list = item.get("DNSServerSearchOrder")
                    if dns_list:
                        dns_servers.extend(dns_list if isinstance(dns_list, list) else [dns_list])
                    gw_list = item.get("DefaultIPGateway")
                    if gw_list and not gateway:
                        gateway = gw_list[0] if isinstance(gw_list, list) else gw_list
                    if item.get("DHCPServer") and not dhcp:
                        dhcp = item.get("DHCPServer")
        except Exception:
            pass

        # 3. Discover Active Connected Servers via netstat
        connected_servers: List[ConnectedServerSpec] = []
        try:
            res = subprocess.run(["netstat", "-n", "-p", "tcp"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    if "ESTABLISHED" in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            remote_endpoint = parts[2]
                            if ":" in remote_endpoint:
                                ip, port_str = remote_endpoint.rsplit(":", 1)
                                if ip not in ("127.0.0.1", "0.0.0.0", "::1"):
                                    try:
                                        port = int(port_str)
                                        srv_type = KNOWN_PORT_SERVICES.get(port, f"Remote TCP Service (Port {port})")
                                        connected_servers.append(ConnectedServerSpec(
                                            server_address=remote_endpoint,
                                            service_type=srv_type,
                                            state="ESTABLISHED",
                                        ))
                                    except ValueError:
                                        pass
        except Exception:
            pass

        # 4. Discover Subnet Neighbors via ARP Table
        subnet_neighbors: List[DiscoveredNeighborSpec] = []
        try:
            res = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    match = re.search(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F-]{17})\s+([a-zA-Z]+)", line)
                    if match:
                        ip, mac, arp_type = match.groups()
                        if not ip.endswith(".255") and not ip.startswith("224.") and not ip.startswith("239."):
                            dev_type = "Default Gateway Router" if ip == gateway else "Network Host / Node"
                            subnet_neighbors.append(DiscoveredNeighborSpec(
                                ip_address=ip,
                                mac_address=mac.replace("-", ":").upper(),
                                device_type=dev_type,
                            ))
        except Exception:
            pass

        return NetworkTopologyTreeSpec(
            domain_or_workgroup=domain,
            dns_servers=list(set(dns_servers)),
            default_gateway=gateway,
            dhcp_server=dhcp,
            connected_servers=connected_servers[:15],
            subnet_neighbors=subnet_neighbors[:25],
            active_connections_count=len(connected_servers),
        )

    @classmethod
    def scan_linux_topology(cls) -> NetworkTopologyTreeSpec:
        """Parses Linux ip route, resolv.conf, and arp tables."""
        dns_servers: List[str] = []
        gateway: Optional[str] = None
        # Read resolv.conf
        try:
            with open("/etc/resolv.conf", "r") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        dns_servers.append(line.split()[1])
        except Exception:
            pass

        # Parse ip route default
        try:
            res = subprocess.run(["ip", "route"], capture_output=True, text=True, timeout=2)
            if res.returncode == 0 and res.stdout:
                for line in res.stdout.splitlines():
                    if line.startswith("default via"):
                        gateway = line.split()[2]
                        break
        except Exception:
            pass

        return NetworkTopologyTreeSpec(
            domain_or_workgroup="LOCAL",
            dns_servers=dns_servers,
            default_gateway=gateway,
            connected_servers=[],
            subnet_neighbors=[],
            active_connections_count=0,
        )

    @staticmethod
    def create_simulated_topology() -> NetworkTopologyTreeSpec:
        """Provides simulated enterprise topology for testing."""
        return NetworkTopologyTreeSpec(
            domain_or_workgroup="ENTERPRISE.CORP",
            dns_servers=["10.0.0.10", "10.0.0.11", "1.1.1.1"],
            default_gateway="10.0.0.1",
            dhcp_server="10.0.0.10",
            connected_servers=[
                ConnectedServerSpec(
                    server_address="10.0.0.10:389",
                    service_type="Active Directory / LDAP Directory Server",
                    state="ESTABLISHED",
                    remote_hostname="dc01.enterprise.corp",
                ),
                ConnectedServerSpec(
                    server_address="10.0.0.25:445",
                    service_type="Microsoft-DS / SMB Enterprise File Share",
                    state="ESTABLISHED",
                    remote_hostname="fileshare.enterprise.corp",
                ),
                ConnectedServerSpec(
                    server_address="10.0.0.40:1433",
                    service_type="Microsoft SQL Server Database",
                    state="ESTABLISHED",
                    remote_hostname="db-cluster.enterprise.corp",
                ),
                ConnectedServerSpec(
                    server_address="192.168.10.50:102",
                    service_type="Siemens S7 Industrial Controller",
                    state="ESTABLISHED",
                    remote_hostname="simatic-s7-cell01",
                ),
            ],
            subnet_neighbors=[
                DiscoveredNeighborSpec(ip_address="10.0.0.1", mac_address="00:1A:2B:3C:4D:01", device_type="Default Gateway Router"),
                DiscoveredNeighborSpec(ip_address="10.0.0.10", mac_address="00:1A:2B:3C:4D:10", device_type="Domain Controller Server"),
                DiscoveredNeighborSpec(ip_address="10.0.0.25", mac_address="00:1A:2B:3C:4D:25", device_type="Storage NAS / SAN Appliance"),
                DiscoveredNeighborSpec(ip_address="10.0.0.88", mac_address="00:1A:2B:3C:4D:88", device_type="Network Laser Multifunction Printer"),
            ],
            active_connections_count=4,
        )
