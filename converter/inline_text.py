from __future__ import annotations

from collections.abc import Iterable

from converter.md_parser import Token


def tokens_to_plain_text(tokens: Iterable[Token]) -> str:
    return "".join(token_to_plain_text(token) for token in tokens)


def token_to_plain_text(token: Token) -> str:
    if token.content:
        return token.content

    if token.type == "image":
        return token.attrs.get("alt", "") or token.content

    if token.children:
        return tokens_to_plain_text(token.children)

    return ""
