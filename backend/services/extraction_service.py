import pandas as pd
import pdfplumber


def extract_text(file_path: str):
    """
    Returns a list of segments. Each segment is one addressable
    location inside the source document (one PDF page, one CSV row,
    or the whole file for plain text):

        {
            "text": str,
            "page_number": int or None,   # used later to jump to a PDF page
            "source_location": str        # human-readable label, e.g. "Page 3"
        }
    """

    if file_path.lower().endswith(".pdf"):
        return _extract_from_pdf(file_path)

    elif file_path.lower().endswith(".csv"):
        return _extract_from_csv(file_path)

    else:
        return _extract_from_txt(file_path)


def _extract_from_pdf(file_path: str):

    segments = []

    with pdfplumber.open(file_path) as pdf:

        for page_index, page in enumerate(pdf.pages, start=1):

            page_text = page.extract_text(x_tolerance=1)

            if page_text:
                segments.append({
                    "text": page_text,
                    "page_number": page_index,
                    "source_location": f"Page {page_index}"
                })

    return segments


def _extract_from_csv(file_path: str):

    df = pd.read_csv(file_path)

    segments = []

    for row_index, row in df.iterrows():

        row_sentence = ", ".join(
            f"{column}: {row[column]}" for column in df.columns
        )

        row_number = row_index + 1

        segments.append({
            "text": row_sentence,
            "page_number": None,
            "source_location": f"Row {row_number}"
        })

    return segments


def _extract_from_txt(file_path: str):

    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return [{
        "text": text,
        "page_number": None,
        "source_location": "Full Document"
    }]