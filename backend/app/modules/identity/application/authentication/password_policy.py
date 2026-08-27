from dataclasses import dataclass


class PasswordPolicyViolation(ValueError):
    """Raised when a new password does not satisfy the Core password policy."""


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Canonical validation policy for every Core password-setting flow."""

    min_length: int = 12
    max_length: int = 255

    def validate(self, password: str) -> None:
        length = len(password)
        if length < self.min_length:
            raise PasswordPolicyViolation(
                f"Password must be at least {self.min_length} characters long"
            )
        if length > self.max_length:
            raise PasswordPolicyViolation(
                f"Password must be at most {self.max_length} characters long"
            )


DEFAULT_PASSWORD_POLICY = PasswordPolicy()
