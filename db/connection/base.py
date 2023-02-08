import logging


from django.db import IntegrityError
from django.db.backends.mysql import base

logger = logging.getLogger('db_connection')


def check_mysql_gone_away(db_wrapper):
    def decorate(f):
        def wrapper(self, query, args=None):
            try:
                return f(self, query, args)
            except Exception as e:
                if (
                        'MySQL server has gone away' in str(e) or
                        'Lost connection to MySQL server during query' in str(e)
                ):
                    logger.warning("MySQL client error. Rerunning query: %s", query)
                    db_wrapper.connection.close()
                    db_wrapper.connect()
                    self.cursor = db_wrapper.connection.cursor()
                    return f(self, query, args)
                # Map some error codes to IntegrityError, since they seem to be
                # misclassified and Django would prefer the more logical place.
                if e.args[0] in self.codes_for_integrityerror:
                    raise IntegrityError(*tuple(e.args))
                raise

        return wrapper

    return decorate


class DatabaseWrapper(base.DatabaseWrapper):

    def create_cursor(self, name=None):
        class CursorWrapper(base.CursorWrapper):

            @check_mysql_gone_away(self)
            def execute(self, query, args=None):
                return self.cursor.execute(query, args)

            @check_mysql_gone_away(self)
            def executemany(self, query, args):
                return self.cursor.executemany(query, args)

        cursor = self.connection.cursor()
        return CursorWrapper(cursor)
