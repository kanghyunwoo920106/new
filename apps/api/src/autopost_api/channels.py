"""Publish destinations. site is the own blog; blogger uses the official write API.

Tistory stays in the allowlist so old jobs fail with a clear message.
Its official write API ended in February 2024 and cannot be turned on.
"""

ALLOWED_CHANNELS = ("site", "tistory", "blogger")
