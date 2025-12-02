import streamlit as st
import pdfplumber
import pandas as pd

st.set_page_config(page_title="Payroll → CSV", layout="centered")
st.title("🛡️ Armour Me Payroll → CSV Extractor")
st.write("Upload the Armour Me (Pty) Ltd transaction history PDF → get clean CSV with Gross Remuneration + totals per employee.")

uploaded_file = st.file_uploader("Upload PDF", type="pdf", label_visibility="collapsed")

if uploaded_file:
    records = []

    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if len(table) < 3:  # need header + at least 1 data row
                    continue

                # Create DataFrame
                header = [cell.strip() if cell else "" for cell in table[0]]
                df = pd.DataFrame(table[1:], columns=header)

                if "Date" not in df.columns:
                    continue

                # Find the Gross Remuneration column (the second/last one, the simple one)
                gross_cols = [c for c in df.columns if "Gross Remuneration" in c]
                if not gross_cols:
                    gross_cols = [c for c in df.columns if "Gross" in c]  # fallback
                gross_col = gross_cols[-1]  # always the last one in your PDFs

                # === Extract employee name (band just above the table) ===
                band = 80  # points — works perfectly captures the name in your file
                table_top_y = table.bbox[3]  # y1 = top coordinate
                crop_box = (0, table_top_y, page.width, table_top_y + band)
                cropped = page.crop(crop_box)
                text_above = cropped.extract_text()

                if text_above:
                    lines = [line.strip() for line in text_above.split("\n") if line.strip()]
                    employee_name = "Unknown"
                    for line in reversed(lines):  # last non-empty line is almost always the name
                        if "," in line and len(line.split()) <= 5 and not any(word.lower() in line.lower() for word in ["date", "basic", "tax", "uif", "sdl", "loan", "page", "armour", "transaction", "period", "number"]):
                            employee_name = line
                            break
                else:
                    employee_name = "Unknown"

                # Extract rows
                for _, row in df.iterrows():
                    date = row["Date"]
                    if not str(date).strip().startswith("20"):
                        continue  # skip header/footer rows

                    gross_str = str(row[gross_col]).replace("R", "").replace(" ", "").replace(",", "").strip()
                    if not gross_str or gross_str == "-":
                        continue

                    gross = float(gross_str)

                    records.append({
                        "Employee": employee_name,
                        "Date": date.strip(),
                        "Gross Remuneration": gross
                    })

    if records:
        df = pd.DataFrame(records)

        # Sort by employee name then date
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.sort_values(["Employee", "Date"])

        # Build final list with Total row after each employee
        final_records = []
        for employee, group in df.groupby("Employee", sort=False):
            for _, r in group.iterrows():
                final_records.append({
                    "Employee": r["Employee"],
                    "Date": r["Date"].strftime("%Y-%m-%d") if pd.notna(r["Date"]) else r["Date"],
                    "Gross Remuneration": f"R {r['Gross Remuneration']:,.2f}"
                })
            total = group["Gross Remuneration"].sum()
            final_records.append({
                "Employee": employee,
                "Date": "Total",
                "Gross Remuneration": f"R {total:,.2f}"
            })

        final_df = pd.DataFrame(final_records)

        st.success(f"Extracted {len(df)} rows from {len(df['Employee'].unique())} employees")
        st.dataframe(final_df, use_container_width=True, hide_index=True)

        csv = final_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="📄 Download CSV",
            data=csv,
            file_name="armour_me_gross_remuneration.csv",
            mime="text/csv"
        )
    else:
        st.error("No data found — check if the PDF is the correct format.")
else:
    st.info("Upload your Armour Me payroll report PDF above ↑")

st.markdown("---")
st.markdown("100% free · GitHub + Streamlit · no limits · made for your exact PDF format")
