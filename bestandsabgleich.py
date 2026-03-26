import marimo

__generated_with = "0.16.4"
app = marimo.App(width="medium")


@app.cell
def _():
    # Todos
    # - Option to choose csv delimiter?
    # - Option to choose api endpoint (k10plus, etc.) -- also needs to update index keys (xsgb > sgb)
    # - click trough PPN catalogue
    # - field to save abgleich_df as csv
    return


@app.cell
def _():
    import marimo as mo
    import pandas as pd
    import io
    from urllib.parse import urlencode, unquote
    import requests
    from lxml import etree
    import re
    return etree, io, mo, pd, re, requests, urlencode


@app.cell
def _(mo):
    mo.md(
        """
    # Bestandsabfrage
    Bestandsabfrage über die SRU-Schnittstelle ausgehend von Tabellenspalten (z.B. Signatur)
    """
    )
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
def _(df, mo):
    column_selector = mo.ui.dropdown(
        options=list(df.columns),
        label="Spalte wählen"
        )

    search_selector = mo.ui.dropdown(
        options={"Signatur (sgb)":"pica.xsgb", "Titel (tit)":"pica.xtit"},
        label="Suchschlüssel wählen"
    )

    mo.vstack([mo.md("""## Spalte und Suchschlüssel wähle
    Wählen Sie die Spalte, deren Werte als Sucheingabe verwendet werden sollen sowie den Suchschlüssel"""),mo.hstack([column_selector, search_selector])])
    return column_selector, search_selector


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="Abfrage starten!")
    return (run_button,)


@app.cell
def _(column_selector, mo, run_button, search_selector):
    mo.stop(not column_selector.value and search_selector.value)
    mo.vstack([mo.md("""## Zeilen in der Tabellenansicht auswählen und Abfrage starten"""),run_button])
    return


@app.cell
def _():
    # helper functions to sanitise strings (mostly Signatur) 


    ## remove "/"
    def replace(value):
        value = value.replace("/", " ")
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
        if value is None:
            return value

        value = replace(value)
        value = quote(value)

        return value
    return (prepare_cql_string,)


@app.cell
def _():
    # Constants
    # SRU base URLs
    SBB_SRU_BASE = "https://sru.k10plus.de/opac-de-1"


    # Default SRU parameters
    DEFAULT_RECORD_SCHEMA = "marcxml"

    # XML Namespaces
    NS = {
    "marc": "http://www.loc.gov/MARC21/slim",
    "zs": "http://www.loc.gov/zing/srw/",
    "ppxml": "http://www.oclcpica.org/xmlns/ppxml-1.0"
    }
    return DEFAULT_RECORD_SCHEMA, NS, SBB_SRU_BASE


@app.cell
def _(DEFAULT_RECORD_SCHEMA, SBB_SRU_BASE, re, requests, urlencode):
    def query_sru(query):
        base_url = SBB_SRU_BASE
        params = {
            'recordSchema': DEFAULT_RECORD_SCHEMA,
            'operation': 'searchRetrieve',
            'version': '1.1',
            'maximumRecords': '5',
            'query': query
        }
        #Escape some charaters in the query (but not in the index prefix)
        pattern = re.compile(r'(?<!pica)\.|\(|\)|<|>|/')

        query = pattern.sub(lambda m: "\\" + m.group(), query)


        query_string = urlencode(params, safe="+")
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
    column_selector,
    df,
    input_table,
    mo,
    parse_sru,
    prepare_cql_string,
    query_sru,
    run_button,
    search_selector,
):
    mo.stop(not run_button.value)
    df_abgleich = df.copy()  # full df
    results = []

    series = df_abgleich.loc[input_table.value.index, column_selector.value]  # only selected rows

    for idx, raw_value in mo.status.progress_bar(
        series.items(),
        title="Abgleich läuft",
        subtitle="API-Anfrage wird verarbeitet",
        total=len(series),
        show_eta=True,
        show_rate=True,
    ):
        prepared_value = prepare_cql_string(raw_value)
        query = f"{search_selector.value}={prepared_value}"
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
