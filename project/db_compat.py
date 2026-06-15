import operator


class _CanReturnColumnsFromInsert:
    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        if instance.connection.mysql_is_mariadb:
            return instance.connection.mysql_version >= (10, 5)
        return True


def allow_local_mariadb():
    """Allow XAMPP MariaDB 10.4 for local development with Django 6."""
    from django.db.backends.mysql.base import DatabaseWrapper
    from django.db.backends.mysql.features import DatabaseFeatures

    original = DatabaseWrapper.check_database_version_supported

    def check_database_version_supported(self):
        if self.mysql_is_mariadb and self.get_database_version() >= (10, 4):
            return
        return original(self)

    DatabaseWrapper.check_database_version_supported = (
        check_database_version_supported
    )

    DatabaseFeatures.can_return_columns_from_insert = (
        _CanReturnColumnsFromInsert()
    )
    DatabaseFeatures.can_return_rows_from_bulk_insert = property(
        operator.attrgetter("can_return_columns_from_insert")
    )
