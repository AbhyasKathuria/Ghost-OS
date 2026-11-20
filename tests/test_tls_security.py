"""Tests for Ghost-OS TLS / HTTPS Security Certificate Generation."""

import os
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from ghost_core.security.tls import generate_self_signed_cert, get_local_ip_addresses


def test_tls_self_signed_cert_generation(tmp_path):
    """Verifies that pure Python TLS certificate generation produces valid x509 certificates."""
    cert_dir = str(tmp_path / "tls")
    cert_path, key_path = generate_self_signed_cert(output_dir=cert_dir, common_name="Ghost-OS Test Gateway")

    assert os.path.exists(cert_path)
    assert os.path.exists(key_path)

    # Read and parse cert
    with open(cert_path, "rb") as f:
        cert_data = f.read()
    cert = x509.load_pem_x509_certificate(cert_data)

    assert cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value == "Ghost-OS Test Gateway"

    # Verify SANs include localhost
    san_ext = cert.extensions.get_extension_for_oid(x509.oid.ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
    names = [str(n.value) for n in san_ext.value]
    assert "localhost" in names
    assert "127.0.0.1" in names

    # Verify idempotent re-call returns same paths
    c2, k2 = generate_self_signed_cert(output_dir=cert_dir)
    assert c2 == cert_path
    assert k2 == key_path
