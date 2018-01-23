# ERMresolve

[ERMresolve](http://github.com/informatics-isi-edu/ermresolve) is a
trivial identifier resolver and redirect service to help cite entities
in an [ERMrest](http://github.com/informatics-isi-edu/ermrest)
catalog.

## Purpose of ERMresolve

The sole purpose of ERMresolve is to provide an easily managed URL
space to use in support of data citation. It is designed to complement
the use of [CURIEs a.k.a. Compact URIs](http://www.w3.org/TR/curie) to form
short, permanent, and resolvable identifiers. Typical use would be to
associate a CURIE prefix with an ERMresolve deployment, such that a
CURIE resolver could translate the CURIE into a valid ERMresolve HTTP
URL and then fetch that resource to obtain cited data from ERMrest.

ERMrest exposes a structured resource space consisting of multiple
tables with keyed rows. ERMresolve provides a level of indirection
compared to the ERMrest, providing more stable citation in the face of
evolving ERMrest catalog models:

1. ERMresolve provides a flat URL space lacking model element names
   such as schema, table, or column name which might change over time.
2. ERMresolve can fuse multiple tables into its identifier space,
   shielding citations from changes in ERM granularity where tables
   have been merged or split over time.

NOTE: ERMresolve **does not** provide stable identifiers if the
underlying ERMrest catalog content does not provide any stable
identifying attributes. A best practice when using ERMresolve would be
to expose immutable row identifiers such as the `RID` column.

## Using ERMresolve

Assuming an ERMrest catalog and companion ERMresolve service is
already configured and operational, there are three kinds of user
experience related to citable data:

1. A researcher creates an entity (row in a table) in ERMrest and it
   is given one or more stable identifying attributes.
2. A primary data consumer makes use of the entity data and obtains a
   *citation* which references the entity as a CURIE such as
   `FOO:1-X140`.
   - The practical processes to accomplish this are TBD.
3. A secondary data consumer encounters the citation and wishes to
   review the same data.
   - The CURIE is mapped to an ERMresolve URL such as
    `https://example.com/foo/1-X140`.
   - An HTTP GET operation is performed on the ERMresolve URL.
   - ERMresolve determines a current mapping and issues an appropriate
    HTTP redirect response.
   - The secondary data consumer attempts to retrieve the actual data.

The final redirected URL may be content-negotiated:

1. For clients requesting HTML, a Chaise GUI application URL is
   supplied, e.g. `https://example.com/chaise/#1/Schema:Table/RID=1-X140`.
2. For clients requesting JSON or CSV data, a raw ERMrest data URL is
   supplied, e.g. `https://example.com/ermrest/catalog/1/Schema:Table/RID=1-X140`.

## Deploying ERMresolve

Given an existing server with operational ERMrest service endpoint, an
administrator may deploy ERMresolve as another sibling service on the
same webserver. ERMresolve by default contacts its companion ERMrest
service via the local host's fully-qualified domain name.

### Prerequisites

The essential ERMrest prerequisite also satisfies most of the other
third-party prerequisites since they share common implementation
techniques.

- ermrest (and functioning at `/ermrest/` path on server)
- webauthn2
- Apache HTTPD
- mod_wsgi
- web.py lightweight web framework
- Chaise web UI at `/chaise/` path on server

### Planning the Deployment

The administrator SHOULD make several decisions in advance:

- Choose which catalog(s) and table(s) have data to be cited.
- Ensure that all target tables have coordinated/disjoint key material.
- Choose an appropriate CURIE prefix for citations.
- Choose a URL path prefix for the resolver, which MAY match the
  chosen CURIE prefix.

These choices will be encoded in the deployed configuration. Once
users are allowed to start forming citations, a site operator SHOULD
NOT make changes which would break existing citations. However, they
MAY make changes which expand the set of citable content or which
serve to enhance the stability of reference for existing citations.

### Software Installation

These steps assume that prerequisites are already met, e.g. by
following the more complex ERMrest installation procedure.

1. Download ERMresolve.
   ```
   # git clone https://github.com/informatics-isi-edu/ermresolve.git ermresolve
   ```
2. From the source directory, run the installation script.
   ```
   # cd ermresolve
   # pip install .
   ```

### Service Deployment and Configuration

1. Create `ermresolve` daemon user to run the web service.
   ```
   # useradd --create-home --system ermresolve
   # chmod og+rx ~ermresolve
   ```
2. Configure `~/ermresolve.json` in daemon home directory, readable by Apache HTTPD.
   - See [example ERMresolve configuration](#example-ermresolve-configuration)
3. Configure `mod_wsgi` to run ERMresolve.
   - See [example WSGI configuration](#example-wsgi-configuration)
4. Restart HTTPD to activate configuration.
   ```
   # service httpd restart
   ```

### Working with SE-Linux

The following is an example set of commands to allow ERMresolve to
read its configuration data and talk to ERMrest on a Fedora
installation.  On other distributions, the appropriate path and
SE-Linux contexts might vary slightly:

    setsebool -P httpd_can_network_connect on
    setsebool -P httpd_execmem on
    semanage fcontext --add --type httpd_sys_content_t "/home/ermresolve(/ermresolve_config.json)?"
    restorecon -rv /home/ermresolve

NOTE: for those uncomfortable with enabling `httpd_execmem`, the
alternative is to only use plain `http://` URLs in the configured
targets. Unfortunately, the Python `requests` library seems to require
`httpd_execmem` when using HTTPS protocol to talk to ERMrest.

If you enable authenticated requests, the named `"credential_file"` in
the configuration must also be readable by the service, e.g. by adding
another related policy:

    semanage fcontext --add --type httpd_sys_content_t "/home/secrets/ermresolve(/ermresolve_cred.json)?"
    restorecon -rv /home/secrets/ermresolve

### Configuration Language

The configuration file has a top-level object with several fields:

- `"server_url"`: The base server URL to use when talking to ERMrest
  (optional, defaults to `http://fqdn` for the local host's
  fully-qualified domain name).
- `"credential_file"`: The deriva-py formatted credential file needed
  to make authenticated requests to the configured ERMrest
  `"server_url"` (optional, defaults to anonymous requests).
- `"targets"`: An array of configuration objects, each with named
  fields:
   - `patterns`: one or more Python regular expressions with named
      groups for `KEY` and optionally `SNAP`
      - the `KEY` group MUST be present and matching the row key material
      - the `SNAP` group SHOULD be present if and only if it matches
        catalog snapshot identifier
   - `server_url`: the target base server URL (optional, defaults to
     global setting)
   - `catalog`: the target catalog identifier
   - `schema`: the target schema name
   - `table`: the target table name
   - `column`: the target column name

ERMresolve will produce one of two ERMrest URL formats to attempt to
resolve a matching identifier, e.g.:

1. Versioned entity:
   `/ermrest/catalog/1@2P4-RJ1W-WGHG/entity/Schema:Table/RID=1-X140`
2. Unversioned entity:
   `/ermrest/catalog/1/entity/Schema:Table/RID=1-X140`

The first configuration block with a matching pattern **and** a
non-empty entity query result will be considered the proper resolution
for the identifier.

#### Syntactic Sugars

For brevity of configuration, a variety of pluralized target names can
optionally imply a family of related configuration objects in a more
terse configuration syntax. This is helpful when searching large
numbers of tables in a complex catalog model.

- `catalog_schema_table_columns`: a list of `[catalog, schema, table,
  column]` quadruples
- `schema_table_columns`: a list of `[schema, table, column]` triples
- `schema_tables`: a list of `[schema, table]` schema-table name pairs
- `table_columns`: a list of `[table, column]` table-column name pairs
- `tables`: a list of table names (in the single schema)

This table summarizes the source of each configuration value when
mixing notations:

| Sugar format                   | Pattern    | Server URL   | Catalog   | Schema   | Table   | Column   |
|--------------------------------|------------|--------------|-----------|----------|---------|----------|
| no sugar                       | `patterns` | `server_url` | `catalog` | `schema` | `table` | `column` |
| `tables`                       | `patterns` | `server_url` | `catalog` | `schema` | list element | `column` |
| `table_columns`                | `patterns` | `server_url` | `catalog` | `schema` | 2-tuple | 2-tuple  |
| `schema_tables`                | `patterns` | `server_url` | `catalog` | 2-tuple  | 2-tuple | `column` |
| `schema_table_columns`         | `patterns` | `server_url` | `catalog` | 3-tuple  | 3-tuple | 3-tuple  |
| `catalog_schema_table_columns` | `patterns` | `server_url` | 4-tuple   | 4-tuple  | 4-tuple | 4-tuple  |

If multiple notations are combined, they are implicitly ordered as per
this table. The ERMresolve service does not attempt to preserve or
intepret the JSON document order of fields within the configuration object.

Each case above is only activated if **all** sources in that sugar
format are properly configured. However, if `patterns` is absent in
the target object, a default pattern list is configured:

    [
      "^(?P<KEY>[-0-9A-Za-z]+)$",
      "^(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$"
    ]
	
Similarly, if `server_url` is absent in the target, the service-wide
setting is is chosen, and that in turn has a default defined in case
it is not present in the top-level configuration document.

The default set of patterns can match an unversioned RID such as
`1-X140` or a versioned RID such as `1-X140@2P4-RJ1W-WGHG`.  When a
deployment cannot or should not resolve versioned identifiers, the
`patterns` list SHOULD be overridden to eliminate the default pattern
that matches the `SNAP` group. Resolvers MAY also be configured to
match other legacy identifier types other than the ERMrest RID column
syntax.

### Example ERMresolve Configuration

This example JSON content demonstrates a resolver that can search two
named tables and find entities cited by their immutable `RID` key:

    {
      "server_url": "http://example.com",
      "targets": [
        {
          "catalog": 1,
          "column": "RID",
          "schema": "My Schema",
          "tables": [
            "table 1",
            "table 2"
          ]
        }
      ]
    }

### Example WSGI Configuration

    WSGIPythonOptimize 1
    WSGIDaemonProcess ermresolve processes=4 threads=4 user=ermresolve maximum-requests=2000
    WSGIScriptAlias /project1 /usr/lib/python2.7/site-packages/ermresolve/ermresolve.wsgi
    
    WSGISocketPrefix /var/run/wsgi/wsgi
    
    <Location /project1>
       Satisfy any
       Allow from all
       WSGIProcessGroup ermresolve
    </Location>

## Help and Contact

Please direct questions and comments to
the
[project issue tracker](https://github.com/informatics-isi-edu/ermresolve/issues) at
GitHub.

## License

ERMresolve is made available as open source under the Apache License,
Version 2.0. Please see the [LICENSE file](LICENSE) for more
information.

## About Us

ERMresolve is developed in
the
[Informatics group](http://www.isi.edu/research_groups/informatics/home) at
the [USC Information Sciences Institute](http://www.isi.edu).
