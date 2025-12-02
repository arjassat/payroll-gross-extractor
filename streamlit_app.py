import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO

st.title("Employee Gross Remuneration Extractor")
st.write("Upload your PDF and extract Employee, Date, Gross Remuneration + Totals")

uploaded = st.file_uploader("Upload PDF", type=["pdf"])

# Regex patterns
name_pattern = re.compile(r"^[A-Z][a-zA-Z]+, [A-Za-z\s]+$")
date_pattern = re.compile(r"(\d{4}-\d{2}-\d{2})")
money_pattern = re.compile(r"R\s?([\d,]+\.\d{2})")

def extract_data(pdf_file):
    data = []
    current_employee = None

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for line in lines:

                # Detect employee name
                if name_pattern.match(line.strip()):
                    current_employee = line.strip()
                    continue

                # Extract rows containing dates
                date_match = date_pattern.search(line)
                if date_match:
                    date = date_match.group(1)

                    # Extract all R amounts
                    moneys = money_pattern.findall(line)

                    # Need at least 2 occurrences for Gross Remuneration
                    if len(moneys) >= 2:
                        gross = moneys[-2]  # second last R amount

                        data.append({
                            "Employee": current_employee,
                            "Date": date,
                            "Gross Remuneration": float(gross.replace(",", ""))
                        })

    return pd.DataFrame(data)

if uploaded:
    df = extract_data(uploaded)

    if df.empty:
        st.error("No transactions detected. Check PDF formatting.")
    else:
        # Calculate totals
        totals = df.groupby("Employee")["Gross Remuneration"].sum().reset_index()
        totals.rename(columns={"Gross Remuneration": "Total Gross"}, inplace=True)

        st.subheader("Extracted Data")
        st.dataframe(df)

        st.subheader("Employee Totals")
        st.dataframe(totals)

        # Create CSV for download
        output = BytesIO()
        df.to_csv(output, index=False)
        st.download_button(
            label="Download CSV",
            data=output.getvalue(),
            file_name="gross_remuneration.csv",
            mime="text/csv"
        )

        # Totals CSV
        output_totals = BytesIO()
        totals.to_csv(output_totals, index=False)
        st.download_button(
            label="Download Employee Totals CSV",
            data=output_totals.getvalue(),
            file_name="employee_totals.csv",
            mime="text/csv"
        )
