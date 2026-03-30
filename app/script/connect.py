import os

from trino.dbapi import connect


class Connect:

    def __init__(self,
                 host: str = None,
                 port: int = None,
                 catalog: str = "lakehouse",
                 schema: str = "default",
                 username: str = "trino"):
        self.host = host or os.environ.get("TRINO_HOST", "trino")
        self.port = port or int(os.environ.get("TRINO_PORT", "8080"))
        self.catalog = catalog
        self.schema = schema
        self.username = username
        self._connect = self.connect()

    def connect(self):
        return connect(
            host=self.host,
            port=self.port,
            catalog=self.catalog,
            schema=self.schema,
            user=self.username,
        )

    def get_fetchone(self, query: str, params=None):
        cursor = self._connect.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        cursor.close()
        if result is not None:
            return result[0]
        else:
            return None

    def execute(self, query: str):
        cursor = self._connect.cursor()
        cursor.execute(query)
        return cursor

    def fetchall(self, query: str):
        return self.execute(query).fetchall()

    def fetchone(self, query: str):
        return self.execute(query).fetchone()

    def close(self):
        self._connect.close()
