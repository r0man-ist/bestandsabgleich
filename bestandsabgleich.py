import marimo

__generated_with = "0.21.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    from urllib.parse import urlencode, unquote
    import requests
    from lxml import etree
    import re

    return etree, io, mo, pd, requests, urlencode


@app.cell
def _(mo):
    mo.md("""
    # Bestandsabfrage
    Bestandsabfrage über die SRU-Schnittstelle ausgehend von Tabellenspalten (z.B. Signatur)
    """)
    return


@app.cell
def _(mo):
    upload = mo.ui.file(filetypes=[".csv"], kind="area", label="CSV-Datei laden")
    mo.vstack([mo.md("## CSV-Datei hochladen"), upload])
    return (upload,)


@app.cell
def _(io, mo, pd, upload):
    uploaded_file = upload.value[0]  # single-file upload
    df = pd.read_csv(
        io.BytesIO(uploaded_file.contents),
        sep=";",
        encoding="utf-8"  # or "latin1" if utf-8 fails
    )
    input_table = mo.ui.table(df)
    input_table
    return df, input_table


@app.cell
def _(mo):
    catalogue = mo.ui.dropdown(
        options=["k10plus", "stabikat", "VD17"]
    )
    catalogue

    mo.vstack([mo.md("Katalog (SRU) zum Abgleich wählen"), catalogue])
    return (catalogue,)


@app.cell
def _(df, mo):
    column_selector1 = mo.ui.dropdown(
        options=list(df.columns),
        label="Spalte wählen"
        )

    search_selector1 = mo.ui.dropdown(
        options={"Signatur (sgb)":"pica.sgb", "Titel (tit)":"pica.tit", "Jahr (jhr)": "pica.jah", "Autor:in (per)":"pica.per"},
        label="Suchschlüssel wählen"
    )

    boolean_operator = mo.ui.dropdown(
        options=["AND", "OR", "NOT"],
        value="AND"
    )

    column_selector2 = mo.ui.dropdown(
        options=list(df.columns),
        label="Spalte wählen"
        )

    search_selector2 = mo.ui.dropdown(
        options={"Signatur (sgb)":"pica.sgb", "Titel (tit)":"pica.tit", "Jahr (jhr)": "pica.jah", "Autor:in (per)":"pica.per"},
        label="Suchschlüssel wählen"
    )

    mo.vstack(
        [mo.md("""## Spalte(n) und Suchschlüssel wählen
    Wählen Sie die Spalte, deren Werte als Sucheingabe verwendet werden sollen sowie den Suchschlüssel"""),
         mo.hstack([column_selector1, search_selector1]),
         boolean_operator,
         mo.hstack([column_selector2, search_selector2])])
    return (
        boolean_operator,
        column_selector1,
        column_selector2,
        search_selector1,
        search_selector2,
    )


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="Abfrage starten!")
    return (run_button,)


@app.cell
def _(column_selector1, mo, run_button, search_selector1):
    mo.stop(not column_selector1.value and search_selector1.value)
    mo.vstack([mo.md("""## Zeilen in der Tabellenansicht auswählen und Abfrage starten"""),run_button])
    return


@app.cell
def _(pd):
    # helper functions to sanitise strings (mostly Signatur) 


    ## remove "/"
    def replace(value):
        value = value.replace("/", " ")
        return value


    def remove_ellipses(value):
        """
        Remove ellipses and square brackets as these seem to slow down the SRU-lookup significantly, probably due to server-     side fallback search (?)
        """
        value = value.replace("[...]", "")
        value = value.replace("[", "")
        value = value.replace("]", "")
        return value

    ## quote values
    def quote(value):
        """
        Quote a CQL term when it contains whitespace or CQL-reserved characters.
        CQL requires quotes for terms containing whitespace and several operators.
        """
        needs_quotes = any(ch.isspace() for ch in value) or any(ch in '<>=/()' for ch in value)
        return f'"{value}"' if needs_quotes else value

    def prepare_cql_string(value):
        if value is None or pd.isna(value):
            return ""

        value = remove_ellipses(value)
        value = replace(value)
        value = quote(value)

        return value

    return (prepare_cql_string,)


@app.cell
def _():
    # Constants
    # SRU base URLs
    SBB_SRU_BASE = "https://sru.k10plus.de/opac-de-1"
    k10plus_SRU_BASE = "https://sru.k10plus.de/opac-de-627"
    VD17_SRU_BASE = "https://sru.k10plus.de/vd17"

    # Default SRU parameters
    DEFAULT_RECORD_SCHEMA = "marcxml"

    # XML Namespaces
    NS = {
    "marc": "http://www.loc.gov/MARC21/slim",
    "zs": "http://www.loc.gov/zing/srw/",
    "ppxml": "http://www.oclcpica.org/xmlns/ppxml-1.0"
    }
    return (
        DEFAULT_RECORD_SCHEMA,
        NS,
        SBB_SRU_BASE,
        VD17_SRU_BASE,
        k10plus_SRU_BASE,
    )


@app.cell
def _(
    DEFAULT_RECORD_SCHEMA,
    SBB_SRU_BASE,
    VD17_SRU_BASE,
    catalogue,
    k10plus_SRU_BASE,
    requests,
    urlencode,
):
    def query_sru(query):
        if catalogue.value == "stabikat":
            base_url = SBB_SRU_BASE
        if catalogue.value == "k10plus":
             base_url = k10plus_SRU_BASE
        if catalogue.value == "VD17":    
             base_url = VD17_SRU_BASE

        #Escape some charaters in the query (but not in the index prefix)
        #pattern = re.compile(r'(?<!pica)\.|\(|\)|<|>|/')

        #query = pattern.sub(lambda m: "\\" + m.group(), query)

        # Add "x" in front of Index-term for stabikat
        if catalogue.value == "stabikat":
           query = query.replace("pica.", "pica.x")

        params = {
            'recordSchema': DEFAULT_RECORD_SCHEMA,
            'operation': 'searchRetrieve',
            'version': '1.1',
            'maximumRecords': '20',
            'query': query
        }

        query_string = urlencode(params, safe="+")
        print(query_string) # for debugging
        response = requests.get(f"{base_url}?{query_string}")
        response.raise_for_status()
        return response.text

    return (query_sru,)


@app.cell
def _(NS, etree):
    def parse_sru(xml_string):
        parser = etree.XMLParser(recover=True)

        if isinstance(xml_string, bytes):
            xml_string = xml_string.decode("utf-8", errors="replace")

        root = etree.fromstring(xml_string.encode("utf-8"), parser)

        number_of_records = int(
            root.findtext(".//zs:numberOfRecords", default="0", namespaces=NS) or 0
        )

        ppns = [
            elem.text
            for elem in root.findall('.//marc:controlfield[@tag="001"]', namespaces=NS)
            if elem.text is not None
        ]



        return number_of_records, ppns

    return (parse_sru,)


@app.cell
def _(
    boolean_operator,
    column_selector1,
    column_selector2,
    df,
    input_table,
    mo,
    parse_sru,
    prepare_cql_string,
    query_sru,
    run_button,
    search_selector1,
    search_selector2,
):
    mo.stop(not run_button.value)
    df_abgleich = df.copy()
    results = []

    selected_rows = df_abgleich.loc[input_table.value.index]

    def build_clause(search_key, raw_value):
        prepared = prepare_cql_string(raw_value)
        if prepared == "":
            return ""
        return f"{search_key}={prepared}"

    for idx, row in mo.status.progress_bar(
        selected_rows.iterrows(),
        title="Abgleich läuft",
        subtitle="API-Anfrage wird verarbeitet",
        total=len(selected_rows),
        show_eta=True,
        show_rate=True,
    ):
        clauses = []

        clause1 = build_clause(search_selector1.value, row[column_selector1.value])
        if clause1:
            clauses.append(clause1)

        if column_selector2.value and search_selector2.value:
            clause2 = build_clause(search_selector2.value, row[column_selector2.value])
            if clause2:
                clauses.append(clause2)

        if not clauses:
            results.append((idx, 0, []))
            continue

        if len(clauses) == 1:
            query = clauses[0]
        else:
            query = f" {boolean_operator.value} ".join(clauses)

        api_response = query_sru(query)
        nr_of_records, ppns = parse_sru(api_response)
        results.append((idx, nr_of_records, ppns))

    for idx, nr_of_records, ppns in results:
        df_abgleich.at[idx, "Anzahl_Treffer"] = nr_of_records
        df_abgleich.at[idx, "PPN_Liste"] = ", ".join(ppns)
    return (df_abgleich,)


@app.cell
def _(df_abgleich, mo, run_button):
    mo.stop(not run_button.value)
    table = mo.ui.table(df_abgleich)
    table
    return (table,)


@app.cell
def _(mo, table):
    mo.vstack([mo.md("## Tabellenzeilen inspizieren"),table.value])
    return


@app.cell
def _(mo, table):
    mo.vstack([mo.md("## Im stabikat nachschlagen:"),
    mo.vstack([
        mo.Html(f"<a href='https://stabikat.de/Search/Results?lookfor=id%3A{ppn.strip()}&type=AllFields' target='_blank' style='color: blue;'>{ppn.strip()}</a>")
        for _, row in table.value.iterrows()
        for ppn in row['PPN_Liste'].split(",")
    ])])
    return


@app.cell
def _():
    #editor = mo.ui.data_editor(df_abgleich)
    #mo.vstack([mo.md("## Tabelle bearbeiten"), editor])"""
    return


if __name__ == "__main__":
    app.run()
