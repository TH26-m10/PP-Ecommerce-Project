# import pymysql  # noqa: E402
# pymysql.install_as_MySQLdb()  # noqa: E402
from django.core.wsgi import get_wsgi_application
import os
from project.db_compat import allow_local_mariadb

"""
WSGI config for project project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

allow_local_mariadb()

application = get_wsgi_application()
