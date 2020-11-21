#! -*- coding: utf-8 -*-

# author: forcemain@163.com


from namekox_ldap.core.proxy import LdapProxy


class Ldap(object):
    def __init__(self, config):
        self.config = config
        self.proxy = LdapProxy(config)

    @classmethod
    def name(cls):
        return 'ldap'
