import dataclasses


@dataclasses.dataclass
class User:
    uid: int
    name: str | None
    used: str
    pi: str | None


def get_expired_users() -> list[User]:
    pass


def main() -> None:
    print("track expired")
