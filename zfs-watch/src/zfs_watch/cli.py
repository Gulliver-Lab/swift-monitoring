import dataclasses
import subprocess


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


def main() -> None:
    print("track expired")
