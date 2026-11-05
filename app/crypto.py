"""Encryption helpers for private-context code generation responses."""
from __future__ import annotations

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key


def encrypt_payload(plaintext: str, recipient_public_key: str, key_id: str) -> dict[str, str]:
    """Encrypt a payload using a Fernet data key wrapped by recipient RSA public key."""
    try:
        public_key = load_pem_public_key(recipient_public_key.encode("utf-8"))
    except Exception as exc:
        raise ValueError("Invalid recipient_public_key. Expected PEM-encoded key.") from exc

    data_key = Fernet.generate_key()
    encrypted_text = Fernet(data_key).encrypt(plaintext.encode("utf-8"))
    wrapped_key = public_key.encrypt(
        data_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

    return {
        "ciphertext": base64.b64encode(encrypted_text).decode("ascii"),
        "wrapped_key": base64.b64encode(wrapped_key).decode("ascii"),
        "encryption_alg": "fernet+rsa-oaep-sha256",
        "key_id": key_id,
    }
