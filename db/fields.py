from django.db import models


class EnumField(models.Field):
    """
    A field class that maps to MySQL's ENUM type.
    """
    def db_type(self, connection):
        return "enum({0})".format(','.join("'%s'" % v[0] for v in self.choices))
