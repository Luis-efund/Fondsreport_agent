
import streamlit as st
import pandas as pd
import pdfplumber
import re

st.set_page_config(page_title="Fondsreport Debug VWG Fix", layout="wide")
st.title("🛠 Fondsreport Agent – Debug-Version (VWG Fix)")

uploaded_files = st.file_uploader("Lade die 4 PDFs in dieser Reihenfolge hoch:\n1. Fondsvolumen\n2. Zuflüsse nach Kategorien\n3. Zuflüsse nach Zielgruppen\n4. Verwaltungsgesellschaften",
                                  type="pdf", accept_multiple_files=True)

@st.cache_data
def extract_text(pdf_file):
    with pdfplumber.open(pdf_file) as pdf:
        return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

def parse_fondsvolumen(text):
    pattern = r"(?P<Kategorie>[A-Za-z\s\-]+)\s+(?P<Janner>[\d\.,]+)\s+(?P<Prozent>\d{1,2},\d{2})%"
    matches = re.findall(pattern, text)
    rows = []
    for match in matches:
        rows.append({
            "Kategorie": match[0].strip(),
            "Volumen_Janner": float(match[1].replace(".", "").replace(",", ".")),
            "Anteil_%": float(match[2].replace(",", "."))
        })
    return pd.DataFrame(rows)

def parse_nettomittel(text):
    lines = text.split("\n")
    rows = []
    for line in lines:
        if any(char.isdigit() for char in line) and "," in line:
            parts = re.findall(r"-?[\d\.]+,[\d]+", line)
            if len(parts) >= 3:
                try:
                    rows.append([float(p.replace(".", "").replace(",", ".")) for p in parts[:4]])
                except:
                    pass
    return pd.DataFrame(rows, columns=["Gruppe 1", "Gruppe 2", "Gruppe 3", "Gesamt"])

def parse_vwg_table(text):
    lines = text.split("\n")
    data = []
    current_name = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.search(r"[A-Za-z].*\d+,\d{2}", line):
            parts = re.findall(r"^(.*?)(\d{1,3}(?:\.\d{3})*,\d{2})", line)
            if parts:
                name = parts[0][0].strip()
                val = parts[0][1].replace(".", "").replace(",", ".")
                try:
                    data.append((name, float(val)))
                except:
                    pass
            else:
                current_name = line
        elif current_name and re.match(r"^\d{1,3}(?:\.\d{3})*,\d{2}", line):
            val = line.replace(".", "").replace(",", ".")
            try:
                data.append((current_name, float(val)))
            except:
                pass
            current_name = None
    return pd.DataFrame(data, columns=["Gesellschaft", "Volumen_Mio_EUR"])

if uploaded_files and len(uploaded_files) == 4:
    texts = [extract_text(f) for f in uploaded_files]

    st.header("🔍 Einzelprüfung aller PDFs")

    labels = [
        "📁 Fondsvolumen (PDF 1)",
        "📁 Zuflüsse nach Kategorien (PDF 2)",
        "📁 Zuflüsse nach Zielgruppen (PDF 3)",
        "📁 Verwaltungsgesellschaften (PDF 4)"
    ]
    parsers = [
        parse_fondsvolumen,
        parse_nettomittel,
        parse_nettomittel,
        parse_vwg_table
    ]

    for i, (label, parser) in enumerate(zip(labels, parsers)):
        st.subheader(label)
        st.text(f"Dateiname: {uploaded_files[i].name}")
        try:
            df = parser(texts[i])
            if df.empty:
                st.error("❌ Tabelle konnte NICHT erkannt werden.")
            else:
                st.success(f"✅ Tabelle erkannt ({len(df)} Zeilen)")
                st.dataframe(df.head())
        except Exception as e:
            st.error(f"❌ Fehler beim Parsen: {str(e)}")
else:
    st.info("Bitte lade genau 4 PDF-Dateien hoch.")
