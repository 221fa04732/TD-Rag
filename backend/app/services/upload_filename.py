"""Parse bulk figure upload filenames: `Figure 1.1 (Title of image).png` → figure_ref + title."""

import re


def parse_figure_upload_filename(stem: str) -> tuple[str, str]:
    """
    Expect the file **name** (without extension) to look like::

        Figure 1.1 (Title of the image)

    - Text before ``(`` → figure reference (as in the book).
    - Text inside the parentheses → image title.

    Raises ValueError with a short reason if the pattern does not match.
    """
    stem = (stem or "").strip()
    if not stem:
        raise ValueError("Empty filename.")

    m = re.match(r"^(.+?)\s*\((.+)\)\s*$", stem, re.DOTALL)
    if not m:
        raise ValueError(
            'Use: "Figure 1.1 (Your title here)" — figure label, then title in parentheses.'
        )

    figure_ref = m.group(1).strip()
    title = m.group(2).strip()
    if not figure_ref:
        raise ValueError("Figure label (before parentheses) is empty.")
    if not title:
        raise ValueError("Title inside parentheses is empty.")

    return figure_ref, title
