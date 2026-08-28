import datetime
import os

import pytest

from conftest import write_config

cryptography = pytest.importorskip('cryptography')


def _make_cert(path, cn, sans, days=63):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
               .public_key(key.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=days)))
    if sans:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(s) for s in sans]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    with open(path, 'wb') as fh:
        fh.write(cert.public_bytes(serialization.Encoding.PEM))
    return path


def _load(tmp_path, cn, sans):
    import core.certs as certs_mod
    crt = _make_cert(str(tmp_path / 'shop.crt'), cn, sans)
    write_config(
        "tls:\n"
        "  certificates:\n"
        f"    - certFile: {crt}\n"
        f"      keyFile: {crt}\n"
    )
    return [c for c in certs_mod._certs_from_tls_configs() if c.get('resolver') == 'file']


def test_file_provider_cert_reports_its_domains(client, tmp_path):
    found = _load(tmp_path, 'shop.example.com', ['shop.example.com', 'www.shop.example.com'])
    assert found, 'file-provider certificate was not listed at all'
    c = found[0]
    assert c['main'] == 'shop.example.com', c
    assert c['sans'] == ['shop.example.com', 'www.shop.example.com'], c
    assert c['not_after'], 'expiry missing'
    assert os.path.basename(c['certFile']) == 'shop.crt'


def test_cert_without_sans_falls_back_to_common_name(client, tmp_path):
    found = _load(tmp_path, 'legacy.example.com', [])
    assert found
    assert found[0]['main'] == 'legacy.example.com', found[0]
    assert found[0]['sans'] == []
