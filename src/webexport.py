"""Export Excel en mémoire (bytes) pour st.download_button."""
from __future__ import annotations

import io
import pandas as pd

NAVY = "#14375A"


def build_excel(sheets: dict[str, pd.DataFrame]) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter",
                        engine_kwargs={"options": {"in_memory": True}}) as writer:
        wb = writer.book
        hdr = wb.add_format({"bold": True, "bg_color": NAVY, "font_color": "white",
                             "border": 1})
        for name, df in sheets.items():
            sheet = (name or "Feuille")[:31]
            out = df.copy()
            out.to_excel(writer, sheet_name=sheet)
            ws = writer.sheets[sheet]
            for j, col in enumerate([out.index.name or ""] + list(out.columns)):
                ws.write(0, j, str(col), hdr)
            ws.set_column(0, len(out.columns), 16)
            ws.freeze_panes(1, 1)
    return buf.getvalue()
