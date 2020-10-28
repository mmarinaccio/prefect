from prefect import Task
from prefect.utilities.tasks import defaults_from_attrs

import pymysql.cursors
import logging
from typing import Any, Callable, Union


class MySQLExecute(Task):
    """
    Task for executing a query against a MySQL database.

    Args:
        - db_name (str): name of MySQL database
        - user (str): user name used to authenticate
        - password (str): password used to authenticate
        - host (str): database host address
        - port (int, optional): port used to connect to MySQL database, defaults to 3307
            if not provided
        - query (str, optional): query to execute against database
        - commit (bool, optional): set to True to commit transaction, defaults to false
        - charset (str, optional): charset you want to use (defaults to utf8mb4)
        - **kwargs (Any, optional): additional keyword arguments to pass to the
            Task constructor
    """

    def __init__(
        self,
        db_name: str,
        user: str,
        password: str,
        host: str,
        port: int = 3306,
        query: str = None,
        commit: bool = False,
        charset: str = "utf8mb4",
        **kwargs: Any,
    ):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.query = query
        self.commit = commit
        self.charset = charset
        super().__init__(**kwargs)

    @defaults_from_attrs("query", "commit", "charset")
    def run(self, query: str, commit: bool = False, charset: str = "utf8mb4") -> int:
        """
        Task run method. Executes a query against MySQL database.

        Args:
            - query (str, optional): query to execute against database
            - commit (bool, optional): set to True to commit transaction, defaults to False
            - charset (str, optional): charset of the query, defaults to "utf8mb4"

        Returns:
            - executed (int): number of affected rows

        Raises:
            - pymysql.MySQLError
        """
        if not query:
            raise ValueError("A query string must be provided")

        conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            db=self.db_name,
            charset=self.charset,
            port=self.port,
        )

        try:
            with conn.cursor() as cursor:
                executed = cursor.execute(query)
                if commit:
                    conn.commit()

            conn.close()
            logging.debug("Execute Results: %s", executed)
            return executed

        except (Exception, pymysql.MySQLError) as e:
            conn.close()
            logging.debug("Execute Error: %s", e)
            raise e


class MySQLFetch(Task):
    """
    Task for fetching results of query from MySQL database.

    Args:
        - db_name (str): name of MySQL database
        - user (str): user name used to authenticate
        - password (str): password used to authenticate
        - host (str): database host address
        - port (int, optional): port used to connect to MySQL database, defaults to 3307 if not
            provided
        - fetch (str, optional): one of "one" "many" or "all", used to determine how many
            results to fetch from executed query
        - fetch_count (int, optional): if fetch = 'many', determines the number of results to
            fetch, defaults to 10
        - query (str, optional): query to execute against database
        - commit (bool, optional): set to True to commit transaction, defaults to false
        - charset (str, optional): charset of the query, defaults to "utf8mb4"
        - cursor_type (Union[str, Callable], optional): The cursor type to use.
            Can be `'cursor'` (the default), `'dictcursor'`, or a full cursor class.
        - **kwargs (Any, optional): additional keyword arguments to pass to the
            Task constructor
    """

    def __init__(
        self,
        db_name: str,
        user: str,
        password: str,
        host: str,
        port: int = 3306,
        fetch: str = "one",
        fetch_count: int = 10,
        query: str = None,
        commit: bool = False,
        charset: str = "utf8mb4",
        cursor_type: Union[str, Callable] = "cursor",
        **kwargs: Any,
    ):
        self.db_name = db_name
        self.user = user
        self.password = password
        self.host = host
        self.port = port
        self.fetch = fetch
        self.fetch_count = fetch_count
        self.query = query
        self.commit = commit
        self.charset = charset
        self.cursor_type = cursor_type
        super().__init__(**kwargs)

    @defaults_from_attrs(
        "fetch", "fetch_count", "query", "commit", "charset", "cursor_type"
    )
    def run(
        self,
        query: str,
        fetch: str = "one",
        fetch_count: int = 10,
        commit: bool = False,
        charset: str = "utf8mb4",
        cursor_type: Union[str, Callable] = "cursor",
    ) -> Any:
        """
        Task run method. Executes a query against MySQL database and fetches results.

        Args:
            - fetch (str, optional): one of "one" "many" or "all", used to determine how many
                results to fetch from executed query
            - fetch_count (int, optional): if fetch = 'many', determines the number of results
                to fetch, defaults to 10
            - query (str, optional): query to execute against database
            - commit (bool, optional): set to True to commit transaction, defaults to false
            - charset (str, optional): charset of the query, defaults to "utf8mb4"
            - cursor_type (Union[str, Callable], optional): The cursor type to use.
                Can be `'cursor'` (the default), `'dictcursor'`, or a full cursor class.

        Returns:
            - results (tuple or list of tuples): records from provided query

        Raises:
            - pymysql.MySQLError
        """
        if not query:
            raise ValueError("A query string must be provided")

        if fetch not in {"one", "many", "all"}:
            raise ValueError(
                "The 'fetch' parameter must be one of the following - ('one', 'many', 'all')"
            )

        cursor_types = {
            "cursor": pymysql.cursors.Cursor,
            "dictcursor": pymysql.cursors.DictCursor,
        }

        if callable(cursor_type):
            cursor_class = cursor_type
        else:
            cursor_class = cursor_types.get(cursor_type.lower())

        if cursor_class is None or cursor_class not in cursor_types.values():
            raise TypeError(
                f"'cursor_type' should be one of ('cursor', 'dictcursor') or the callable equivalent, got {cursor_type}"
            )

        conn = pymysql.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            db=self.db_name,
            charset=self.charset,
            port=self.port,
            cursorclass=cursor_class,
        )

        try:
            with conn.cursor() as cursor:
                cursor.execute(query)

                # override mypy inferred type since we redefine with incompatible types
                results: Any

                if fetch == "all":
                    results = cursor.fetchall()
                elif fetch == "many":
                    results = cursor.fetchmany(fetch_count)
                else:
                    results = cursor.fetchone()

                if commit:
                    conn.commit()

            conn.close()
            logging.debug("Fetch Results: %s", results)
            return results

        except (Exception, pymysql.MySQLError) as e:
            conn.close()
            logging.debug("Fetch Error: %s", e)
            raise e
