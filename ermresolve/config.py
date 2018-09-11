
# 
# Copyright 2018 University of Southern California
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#    http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import platform
import os
import json
import re
import urllib

def urlquote(s, safe=''):
    return urllib.quote(s)

class ResolverTarget (object):
    def __init__(self, patterns, server_url, catalog, schema, table, column):
        """Construct target given 5-tuple of target configuration."""
        if type(server_url) not in [str, unicode]:
            raise TypeError('ERMresolve target "server_url" field MUST be a string.')

        self.server_url = server_url

        if type(patterns) is not list:
            raise TypeError('ERMresolve target "patterns" field MUST be a list.')
        
        def compile(s):
            if type(s) not in [str, unicode]:
                raise TypeError('Each ERMresolve target pattern MUST be a string.')
            try:
                return re.compile(s)
            except Exception as e:
                raise ValueError('Error interpreting "%s" as a regular expression: %s.' % (s, e))

        self.patterns = [ compile(s) for s in patterns ]

        def validate(name, s, extra_types=[]):
            if type(s) not in [str, unicode] + extra_types:
                raise TypeError('Target "%s" type %s not supported.' % (name, type(s)))
            return s

        self.catalog = validate('catalog', catalog, [int, type(None)])
        self.schema = validate('schema', schema, [type(None)])
        self.table = validate('table', table, [type(None)])
        self.column = validate('column', column, [type(None)])
        self.legacy = self.schema is not None and self.table is not None and self.column is not None

    def __str__(self):
        return "ResolverTarget(%s, %s, %s, %s, %s, %s)" % self.astuple()

    def astuple(self):
        return (
            [ p.pattern for p in self.patterns ],
            self.server_url,
            self.catalog,
            self.schema,
            self.table,
            self.column
        )

    def match_parts(self, url_id_part):
        """Return a dictionary of named parts if we have a match, else None.

           A resulting dictionary can be interpolated into either URL
           template: self.ermrest_url_template or self.chaise_url_template

        """
        for pattern in self.patterns:
            m = re.match(pattern, url_id_part)
            if m:
                g = m.groupdict()
                if g.get("CAT", self.catalog) is None:
                    # don't allow a match if target catalog is not determined
                    return
                return {
                    "server_url": self.server_url,
                    "catalog": "%s%s" % (
                        g.get("CAT", self.catalog),
                        ('@' + g['SNAP']) if "SNAP" in g else ''
                    ),
                    "schema": urlquote(self.schema) if self.schema is not None else None,
                    "table": urlquote(self.table) if self.table is not None else None,
                    "column": urlquote(self.column) if self.column is not None else None,
                    "key": g["KEY"],
                }

    ermrest_resolve_template = "%(server_url)s/ermrest/catalog/%(catalog)s/entity_rid/%(key)s"
    ermrest_url_template = "%(server_url)s/ermrest/catalog/%(catalog)s/entity/%(schema)s:%(table)s/%(column)s=%(key)s?limit=2"
    chaise_url_template = "%(server_url)s/chaise/record/#%(catalog)s/%(schema)s:%(table)s/%(column)s=%(key)s"

    @classmethod
    def from_config_element(cls, element, server_url, catalog):
        """Construct iterable set of targets from config document element."""
        patterns = element.get(
            'patterns',
            [
                '^(?P<KEY>[-0-9A-Za-z]+)$',
                '^(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$',
                '^(?P<CAT>[^/@]+)/(?P<KEY>[-0-9A-Za-z]+)$',
                '^(?P<CAT>[^/@]+)/(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$',
            ]
        )
        server_url = element.get('server_url', server_url)
        catalog = element.get('catalog', catalog)
        schema = element.get('schema')
        table = element.get('table')
        column = element.get('column')

        yield cls(patterns, server_url, catalog, schema, table, column)

class ResolverConfig (object):
    def __init__(self, doc):
        self.targets = []
        if type(doc) is not dict:
            raise TypeError('ERMresolve configuration MUST be an object.')
        self.server_url = doc.get('server_url', 'http://' + platform.node())
        self.credential_file = doc.get('credential_file')
        self.catalog = doc.get('catalog')
        targets_doc = doc.get('targets', [{}])
        if type(targets_doc) is not list:
            raise TypeError('ERMresolve "targets" MUST be a list of target definitions.')
        for element in targets_doc:
            self.targets.extend(ResolverTarget.from_config_element(element, self.server_url, self.catalog))

def get_service_config(configfile=None):
    """Construct ERMresolve configuration objects from JSON configuration file."""
    if configfile is None:
        configfile = '%s/ermresolve_config.json' % os.environ.get('HOME', './')
    with open(configfile) as f:
        return ResolverConfig(json.load(f))
