
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

import os
import json
import re
import urllib

def urlquote(s, safe=''):
    return urllib.quote(s)

class ResolverTarget (object):
    def __init__(self, patterns, catalog, schema, table, column):
        """Construct target given 5-tuple of target configuration."""
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

        self.catalog = validate('catalog', catalog, [int])
        self.schema = validate('schema', schema)
        self.table = validate('table', table)
        self.column = validate('column', column)

    def __str__(self):
        return "ResolverTarget(%s, %s, %s, %s, %s)" % self.astuple()

    def astuple(self):
        return (
            [ p.pattern for p in self.patterns ],
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
                return {
                    "catalog": "%s%s" % (
                        self.catalog,
                        ('@' + g['SNAP']) if "SNAP" in g else ''
                    ),
                    "schema": urlquote(self.schema),
                    "table": urlquote(self.table),
                    "column": urlquote(self.column),
                    "key": g["KEY"]
                }

    ermrest_url_template = "/ermrest/catalog/%(catalog)s/entity/%(schema)s:%(table)s/%(column)s=%(key)s"
    chaise_url_template = "/chaise/record/#%(catalog)s/%(schema)s:%(table)s/%(column)s=%(key)s"

    @classmethod
    def from_config_element(cls, element):
        """Construct iterable set of targets from config document element."""
        patterns = element.get(
            'patterns',
            [
                '^(?P<KEY>[-0-9A-Za-z]+)$',
                '^(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$',
            ]
        )

        def validate_list(name, n):
            l = element[name]
            if type(l) is not list:
                raise TypeError('Target set "%s" must be a list, not %s.' % (name, type(l)))
            for item in l:
                if type(item) is not list:
                    raise TypeError('Target set "%s" member must be a list, not %s.' % (name, type(item)))
                if len(item) != n:
                    raise ValueError('Target set "%s" member %s must have length %d, not %d.' % (name, n, len(item)))
                yield item

        # conditionally expand the different syntactic sugar permutations
        # these must be done in a specific order to meet the documented behavior
        if 'catalog' in element:
            catalog = element['catalog']

            if 'schema' in element:
                schema = element['schema']

                if 'column' in element:
                    column = element['column']

                    if 'table' in element:
                        # this is the "no sugar" scenario
                        table = element['table']
                        yield cls(patterns, catalog, schema, table, column)

                    if 'tables' in element:
                        for table in element['tables']:
                            yield cls(patterns, catalog, schema, table, column)

                if 'table_columns' in element:
                    for table, column in validate_list('table_columns', 2):
                        yield cls(patterns, catalog, schema, table, column)

            if 'schema_tables' in element:
                column = element.get('column')
                for schema, table in validate_list('schema_tables', 2):
                    yield cls(patterns, catalog, schema, table, column)

            if 'schema_table_columns' in element:
                for schema, table, column in validate_list('schema_table_columns', 3):
                    yield cls(patterns, catalog, schema, table, column)

        if 'catalog_schema_table_columns' in element:
            for catalog, schema, table, column in validate_list('catalog_schema_table_columns', 4):
                yield cls(patterns, catalog, schema, table, column)

class ResolverConfig (object):
    def __init__(self, doc):
        self.targets = []
        if type(doc) is not list:
            raise TypeError('ERMresolve configuration MUST be a list of target definitions.')
        for element in doc:
            self.targets.extend(ResolverTarget.from_config_element(element))

def get_service_config(configfile=None):
    """Construct ERMresolve configuration objects from JSON configuration file."""
    if configfile is None:
        configfile = '%s/ermresolve_config.json' % os.environ.get('HOME', './')
    with open(configfile) as f:
        return ResolverConfig(json.load(f))
