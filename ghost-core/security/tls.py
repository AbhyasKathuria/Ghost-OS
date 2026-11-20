"""Ghost-OS TLS / HTTPS Security Certificate Subsystem.

Provides on-demand, zero-external-dependency self-signed x509 TLS certificate generation
for encrypting remote dashboard traffic and API calls over local networks.
"""

import datetime
import ipaddress
import os
import socket
from typing import List, Tuple

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


def get_local_ip_addresses() -> List[str]:
    """Enumerates local IPv4 addresses to embed in the certificate Subject Alternative Names (SANs)."""
    ips = ["127.0.0.1"]
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips


def generate_self_signed_cert(
    output_dir: str,
    common_name: str = "Ghost-OS Secure Gateway",
    valid_days: int = 365,
) -> Tuple[str, str]:
    """Generates a RSA-2048 self-signed x509 certificate and private key in PEM format."""
    os.makedirs(output_dir, exist_ok=True)
    cert_path = os.path.join(output_dir, "cert.pem")
    key_path = os.path.join(output_dir, "key.pem")

    # If already generated and valid, return existing paths
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return cert_path, key_path

    # Generate RSA Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Subject & Issuer Name
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Ghost-OS Hardware Intelligence"),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    # Build SANs
    san_entries: List[x509.GeneralName] = [
        x509.DNSName("localhost"),
        x509.DNSName("ghost-os.local"),
    ]
    for ip_str in get_local_ip_addresses():
        try:
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ip_str)))
        except Exception:
            pass

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=valid_days))
        .add_extension(
            x509.SubjectAlternativeName(san_entries),
            critical=False,
        )
        .sign(private_key, hashes.SHA256())
    )

    # Write Private Key
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    # Write Certificate
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_path, key_path
