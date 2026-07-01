from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TokenPolicy:
    access_token_expire_seconds: int
    refresh_token_expire_days: int
