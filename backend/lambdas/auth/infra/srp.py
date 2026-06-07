from __future__ import annotations

"""Pure Python Cognito SRP helper."""

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime

_N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
    "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
    "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
    "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
    "43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
_N = int(_N_HEX, 16)
_G = 2
_INFO_BITS = b"Caldera Derived Key"
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex_hash(hex_string: str) -> str:
    return _hash_sha256(bytes.fromhex(hex_string))


def _pad_hex(value: int | str) -> str:
    hex_value = value if isinstance(value, str) else f"{value:x}"
    if len(hex_value) % 2 == 1:
        hex_value = "0" + hex_value
    elif hex_value[0] in "89ABCDEFabcdef":
        hex_value = "00" + hex_value
    return hex_value


def _hkdf(ikm: bytes, salt: bytes) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, _INFO_BITS + b"\x01", hashlib.sha256).digest()[:16]


def _timestamp() -> str:
    now = datetime.now(UTC)
    return (
        f"{_WEEKDAYS[now.weekday()]} {_MONTHS[now.month - 1]} {now.day} "
        f"{now:%H:%M:%S} UTC {now.year}"
    )


class CognitoSrpSession:
    def __init__(self, *, user_pool_id: str, username: str, password: str) -> None:
        self.user_pool_id = user_pool_id
        self.username = username
        self.password = password
        self._a = secrets.randbits(1024)
        self._big_a = pow(_G, self._a, _N)
        if self._big_a % _N == 0:
            raise RuntimeError("SRP_A inválido")
        self._k = int(_hex_hash(_pad_hex(_N) + _pad_hex(_G)), 16)

    @property
    def srp_a(self) -> str:
        return f"{self._big_a:x}"

    def challenge_responses(self, challenge: dict[str, str]) -> dict[str, str]:
        user_id = challenge["USER_ID_FOR_SRP"]
        salt = int(challenge["SALT"], 16)
        big_b = int(challenge["SRP_B"], 16)
        secret_block = base64.b64decode(challenge["SECRET_BLOCK"])

        if big_b % _N == 0:
            raise RuntimeError("SRP_B inválido")

        u_value = int(_hex_hash(_pad_hex(self._big_a) + _pad_hex(big_b)), 16)
        if u_value == 0:
            raise RuntimeError("SRP_U inválido")

        pool_name = self.user_pool_id.split("_", 1)[1]
        user_password_hash = _hash_sha256(f"{pool_name}{user_id}:{self.password}".encode())
        x_value = int(_hex_hash(_pad_hex(salt) + user_password_hash), 16)
        s_value = pow(big_b - self._k * pow(_G, x_value, _N), self._a + u_value * x_value, _N)
        key = _hkdf(bytes.fromhex(_pad_hex(s_value)), bytes.fromhex(_pad_hex(u_value)))

        timestamp = _timestamp()
        signature = base64.b64encode(
            hmac.new(
                key,
                (pool_name + user_id).encode("utf-8") + secret_block + timestamp.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        return {
            "USERNAME": user_id,
            "PASSWORD_CLAIM_SECRET_BLOCK": challenge["SECRET_BLOCK"],
            "PASSWORD_CLAIM_SIGNATURE": signature,
            "TIMESTAMP": timestamp,
        }
