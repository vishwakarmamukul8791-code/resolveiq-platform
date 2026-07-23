import re


def clean_text(text: str) -> str:

    text = _fix_encoding_artifacts(text)
    text = _normalize_whitespace(text)

    return text


def _normalize_whitespace(text: str) -> str:

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _fix_encoding_artifacts(text: str) -> str:

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\ufb01": "fi",
        "\ufb02": "fl",
    }

    for bad, good in replacements.items():
        text = text.replace(bad, good)

    return text