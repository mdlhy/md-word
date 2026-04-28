import re

from .models import MathSpan


def _is_likely_currency(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return False
    return bool(re.match(r'^\d[\d,.\s]*[a-zA-Z]?$', stripped))


def _is_likely_math(content: str) -> bool:
    stripped = content.strip()
    if not stripped:
        return False
    if re.search(r'[\^_{}\\]', stripped):
        return True
    if re.search(r'[+\-=<>|/]', stripped) and not re.search(r'[a-zA-Z]{3,}', stripped):
        return True
    if not re.search(r'[a-zA-Z]{3,}', stripped) and len(stripped) < 30:
        return True
    return False


def parse_math_spans(text: str) -> list[MathSpan]:
    spans: list[MathSpan] = []
    i = 0
    n = len(text)

    in_math = False
    math_start = 0
    math_content: list[str] = []
    math_delimiter = ''

    while i < n:
        ch = text[i]

        if not in_math:
            if ch == '\\' and i + 1 < n:
                next_ch = text[i + 1]
                if next_ch == '(':
                    math_start = i
                    math_delimiter = 'paren'
                    math_content = []
                    in_math = True
                    i += 2
                    continue
                elif next_ch == '[':
                    math_start = i
                    math_delimiter = 'bracket'
                    math_content = []
                    in_math = True
                    i += 2
                    continue
                elif next_ch == '$':
                    i += 2
                    continue
                else:
                    i += 1
                    continue
            elif ch == '$':
                if i + 1 < n and text[i + 1] == '$':
                    math_start = i
                    math_delimiter = 'double_dollar'
                    math_content = []
                    in_math = True
                    i += 2
                    continue
                else:
                    math_start = i
                    math_delimiter = 'dollar'
                    math_content = []
                    in_math = True
                    i += 1
                    continue
            else:
                i += 1
                continue

        else:
            if ch == '\\' and i + 1 < n:
                next_ch = text[i + 1]

                if next_ch == '\\':
                    math_content.append(text[i:i + 2])
                    i += 2
                    continue

                if math_delimiter == 'paren' and next_ch == ')':
                    content = ''.join(math_content)
                    if content.strip():
                        spans.append(MathSpan(
                            start=math_start,
                            end=i + 2,
                            content=content,
                            display=False,
                            delimiter_type='paren',
                        ))
                    in_math = False
                    i += 2
                    continue

                if math_delimiter == 'bracket' and next_ch == ']':
                    content = ''.join(math_content)
                    if content.strip():
                        spans.append(MathSpan(
                            start=math_start,
                            end=i + 2,
                            content=content,
                            display=True,
                            delimiter_type='bracket',
                        ))
                    in_math = False
                    i += 2
                    continue

                if math_delimiter in ('dollar', 'double_dollar') and next_ch == '$':
                    math_content.append(text[i:i + 2])
                    i += 2
                    continue

                math_content.append(text[i:i + 2])
                i += 2
                continue

            elif ch == '$':
                if math_delimiter == 'dollar':
                    content = ''.join(math_content)
                    if content.strip() and _is_likely_math(content) and not _is_likely_currency(content):
                        spans.append(MathSpan(
                            start=math_start,
                            end=i + 1,
                            content=content,
                            display=False,
                            delimiter_type='dollar',
                        ))
                        in_math = False
                        i += 1
                    elif _is_likely_currency(content):
                        in_math = False
                        i += 1
                    else:
                        in_math = False
                    continue

                elif math_delimiter == 'double_dollar':
                    if i + 1 < n and text[i + 1] == '$':
                        content = ''.join(math_content)
                        if content.strip():
                            spans.append(MathSpan(
                                start=math_start,
                                end=i + 2,
                                content=content,
                                display=True,
                                delimiter_type='double_dollar',
                            ))
                        in_math = False
                        i += 2
                        continue
                    else:
                        math_content.append(ch)
                        i += 1
                        continue

                else:
                    math_content.append(ch)
                    i += 1
                    continue

            else:
                math_content.append(ch)
                i += 1
                continue

    return spans
