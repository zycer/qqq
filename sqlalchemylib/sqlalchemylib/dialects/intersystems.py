from sqlalchemy.dialects.mssql.pyodbc import MSDialect_pyodbc
import platform


class IntersystemsDialect(MSDialect_pyodbc):

    name = 'intersystems'

    default_schema_name = "SQLUser"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _get_default_schema_name(self, connection):
        return self.default_schema_name
    
    def on_connect(self):
        super_ = super(IntersystemsDialect, self).on_connect()
        import pyodbc

        def on_connect(conn):
            if super_ is not None:
                super_(conn)
            # 仅在mac下修复问题, linux下不存在此问题
            if platform.system() == 'Darwin':
                conn.setdecoding(pyodbc.SQL_CHAR, encoding="utf-8")
                conn.setdecoding(pyodbc.SQL_WCHAR, encoding="utf-8")

        return on_connect
    
    @classmethod
    def register(cls):
        from sqlalchemy.dialects import registry
        registry.register("intersystems.pyodbc", "sqlalchemylib.dialects.intersystems", "IntersystemsDialect")