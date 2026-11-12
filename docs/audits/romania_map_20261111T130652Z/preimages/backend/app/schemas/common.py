from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

# Deliberately simple syntactic check: police units run internal mail domains (e.g. *.local)
# that strict validators reject, and deliverability is irrelevant (invites are handed over).
Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, to_lower=True, max_length=320, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    ),
]
