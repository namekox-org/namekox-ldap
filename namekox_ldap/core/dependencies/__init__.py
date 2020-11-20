#! -*- coding: utf-8 -*-

# author: forcemain@163.com


import ldap3
import socket
import itertools


from ldap3.core.exceptions import LDAPException
from namekox_ldap.constants import LDAP_CONFIG_KEY
from namekox_core.core.service.dependency import Dependency
from namekox_ldap.constants import DEFAULT_LDAP_CONNECT_TIMEOUT
from namekox_core.core.friendly import AsLazyProperty, auto_sleep_retry, ignore_exception


class LdapHelper(Dependency):
    def __init__(self, dbname, servers=None, retries=2, base_dn='', base_dc='', usrname='', usrpass='', options=None):
        self.dbname = dbname
        self._instance = None
        self.retries = retries
        self.base_dn = base_dn
        self.base_dc = base_dc
        self.usrname = usrname
        self.usrpass = usrpass
        self.servers = servers or []
        self.options = options or {}
        self._instance_excinfo = None
        self.servers_generator = None
        super(LdapHelper, self).__init__()

    @AsLazyProperty
    def uris(self):
        return self.container.config.get(LDAP_CONFIG_KEY, {})

    def setup(self):
        config = self.uris[self.dbname]
        self.options.update(config.get('options', {}))
        self.servers = self.servers or config.get('servers', [])
        self.servers_generator = itertools.cycle(self.servers)
        self.base_dn = self.base_dn or config.get('base_dn', '')
        self.base_dc = self.base_dc or config.get('base_dc', '')
        self.usrname = self.usrname or config.get('usrname', '')
        self.usrpass = self.usrpass or config.get('usrpass', '')

    @staticmethod
    def _raise(exc_info):
        raise exc_info[1]

    def connect(self, usrname, usrpass, base_dc, **options):
        config = self.servers_generator.next()
        config.setdefault('connect_timeout', DEFAULT_LDAP_CONNECT_TIMEOUT)
        server = ldap3.Server(**config)
        server_user = '{0}\\{1}'.format(base_dc, usrname)
        if 'auto_bind' not in options:
            options.update({'auto_bind': True})
        if 'authentication' not in options:
            options.update({'authentication': ldap3.NTLM})
        return ldap3.Connection(server, user=server_user, password=usrpass, **options)

    def acquire(self):
        def check_available():
            self._instance_excinfo = None
            self._instance.extend.standard.who_am_i()

        def start_reconnect(exc_info):
            connection = self.connect(self.usrname, self.usrpass, self.base_dc, **self.options)
            self._instance = connection

        def reset_reconnect(exc_info):
            self._instance = None
            self._instance_excinfo = exc_info

        expect_exception = (AttributeError, LDAPException, socket.error)
        start_reconnect = ignore_exception(start_reconnect, reset_reconnect)
        auto_sleep_retry(check_available, start_reconnect, expect_exception, max_retries=self.retries, time_sleep=0.001)
        self._instance_excinfo and self._raise(self._instance_excinfo)
        return self._instance
