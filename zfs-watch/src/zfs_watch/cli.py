import dataclasses
import re
import ssl
import subprocess

from ldap3 import ANONYMOUS, Connection, Server, Tls

from .config import LDAP_BASE, LDAP_HOST, LDAP_PORT


@dataclasses.dataclass
class User:
    uid: int
    name: str | None
    used: str
    pi: str | None


def get_expired_users() -> list[User]:
    # TODO: change the call to zfs userspace gulliver/home
    result = subprocess.run(
        ["cat", "/home/francois/tmp/zfs.txt"], stdout=subprocess.PIPE
    ).stdout.decode("utf-8")

    users = []
    for line in result.splitlines()[1:]:
        _, _, uid, used, _, _, _ = line.split()
        # Only keep the ones where the "name" is the uid
        # These are the expired accounts
        if uid.isdigit():
            users.append(User(int(uid), None, used, None))

    return users


def update_with_name_and_pi(users: list[User]) -> None:
    # Disable certificate verification (mirrors LDAPTLS_REQCERT=never)
    tls = Tls(validate=ssl.CERT_NONE)
    server = Server(LDAP_HOST, port=LDAP_PORT, use_ssl=True, tls=tls)

    ldap_filter = (
        "(&(objectClass=frESPCIperson)(ou=gulliver)(|"
        + "".join([f"(uidNumber={user.uid})" for user in users])
        + "))"
    )

    ldap_attributes = ["uid", "cn", "manager", "uidNumber"]

    with Connection(server, authentication=ANONYMOUS, auto_bind=True) as conn:
        conn.search(
            search_base=LDAP_BASE,
            search_filter=ldap_filter,
            attributes=ldap_attributes,
        )

    if len(conn.entries) != len(users):
        raise RuntimeError("Did not find everyone!")

    for user, entry in zip(
        sorted(users, key=lambda x: x.uid),
        sorted(conn.entries, key=lambda x: x.uidNumber.value),
    ):
        if user.uid != entry.uidNumber.value:
            raise RuntimeError("Error in matching")

        user.name = entry.cn.value
        pi = re.match(r"uid=([^,]+)", entry.manager.value, re.IGNORECASE)
        user.pi = pi.group(1) if pi else ""


def main() -> None:
    print("track expired")
