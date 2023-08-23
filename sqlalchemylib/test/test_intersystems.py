#!/usr/bin/env python3
from sqlalchemylib.sqlalchemylib.connection import Connection
import urllib.parse

SERVER = "127.0.0.1"
PORT = "40034"
NAMESPACE = "dhc-app"
USER = "dhview"
PASSWORD = "fsnh&&123"

params=urllib.parse.quote_plus(f"DRIVER={{Intersystems}};SERVER={SERVER};PORT={PORT};DATABASE={NAMESPACE};UID={USER};PWD={PASSWORD};AutoTranslate=yes")

#conn = Connection('intersystems+pyodbc:///?odbc_connect={}'.format(params))
conn = Connection(f'intersystems+pyodbc://{USER}:{urllib.parse.quote(PASSWORD)}@{SERVER}/{NAMESPACE}?port={PORT}&driver=Intersystems&odbc_autotranslate=Yes')

print(list(conn.iterResult("select code, convert(varchar(5), iname) as iname from dbo.BT_Specimen")))