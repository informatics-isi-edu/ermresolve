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
3. ERMresolve can hide the catalog identifier if configured to work
   on a default catalog.

NOTE: ERMresolve **does not** provide stable identifiers if the
underlying ERMrest catalog content does not provide any stable
identifying attributes. The best practice when using ERMresolve is
to use RID values of entities. Alternate configuration allows some
ERMresolve instances to also resolve legacy identifiers.

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
    `https://foo.example.com/id/1-X140`.
   - An HTTP GET operation is performed on the ERMresolve URL.
   - ERMresolve determines a current mapping and issues an appropriate
    HTTP redirect response.
   - The secondary data consumer attempts to retrieve the actual data.

The final redirected URL may be content-negotiated:

1. For clients requesting HTML, a Chaise GUI application URL is
   supplied, e.g. `https://example.com/chaise/#1/Schema:Table/RID=1-X140`.
   - Or a Chaise resolver error app? TBD.
2. For clients requesting JSON or CSV data, a raw ERMrest data URL is
   supplied, e.g. `https://example.com/ermrest/catalog/1/Schema:Table/RID=1-X140`.
   - Or a raw HTTP error response? TBD.

### Multi-tenancy

For projects wishing to service a number of catalogs out of a single
resolver using a single CURIE prefix, we recommend prefixing the local
key portion of the CURIE with a catalog identifier as a path
element. e.g.:

1. A researcher creates an entity in a table in catalog `7` with RID
   value `1-X140` and wishes to use `FOO` as the CURIE prefix for all
   catalogs on this host.
2. The *citation* CURIE is `FOO:7/1-X140`.
3. The `FOO` prefix represents the multi-tenant ERMresolve instance
   `https://foo.example.com/id/`
4. The citation CURIE is mapped to `https://foo.example.com/7/1-X140`.

Alternatively, a community could also establish a separate
catalog-specific CURIE prefix to avoid embedding a catalog identifier
in each CURIE:

1. A researcher creates an entity in a table in catalog `7` with RID
   value `1-X140` and wishes to use `SUBFOO` as the CURIE prefix for 
   this specific catalog.
2. The *citation* CURIE is `SUBFOO:1-X140`.
3. The `SUBFOO` prefix represents the catalog sub-space of the
   ERMresolve instance `https://foo.example.com/id/7/`.
4. This citation CURIE is mapped to `https://foo.example.com/7/1-X140`.

With an appropriate configuration, ERMresolve will recognize the `7`
in the URL as a catalog identifier and attempt resolution of the
`1-X140` key in the given catalog.

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
   - This is *optional* for customizing behavior. In the absence of a
     configuration file, the service will use a default configuration
     suitable for many multi-tenant scenarios.
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
- `"catalog"`: The default catalog to consult.
- `"credential_file"`: The deriva-py formatted credential file needed
  to make authenticated requests to the configured ERMrest
  `"server_url"` (optional, defaults to anonymous requests). Such
  authentication is useful to enable resolution in a catalog which is
  normally hidden from anonymous users, or to allow legacy resolution
  on tables where rows are not visible to anonymous users.
- `"targets"`: An array of configuration objects, each with named
  fields (optional, defaults to `[{}]`):
   - `patterns`: one or more Python regular expressions with named
      groups for `KEY` and optionally `SNAP` and/or `CAT`
      - the `KEY` group MUST be present and matching the row key material
      - the `SNAP` group SHOULD be present if and only if it matches
        catalog snapshot identifier
	  - the `CAT` group SHOULD be present if and only it matches an
        embedded catalog identifier
   - `server_url`: the target base server URL (optional, defaults to
     global setting)
   - `catalog`: the target catalog identifier (optional)
   - `schema`: legacy target schema name (optional)
   - `table`: legacy target table name (optional)
   - `column`: legacy target column name (optional)

#### Default server URL

If `server_url` is absent in the target, the service-wide setting is
is chosen, and that in turn has a default defined in case it is not
present in the top-level configuration document.

#### Default configuration

The service includes many default configuration choices. In the
complete absence of a configuration file, these choices combine to
provide a usable default behavior for many deployments. In general, a
field can be omitted from the configuration file to select default
behaviors. Thus, the following configuration documents are all
equivalent.

The simplest, empty document:

    {}

That is the same as this, filling all the absent top-level fields with
their implicit defaults:

    {
	  "server_url": "http://myserver.example.com",
	  "catalog": null,
	  "credential_file": null,
	  "targets": [{}]
	}

The preceding uses an empty target `{}` which can be further expanded
to show the default patterns:

    {
	  "server_url": "http://myserver.example.com",
	  "catalog": null,
	  "credential_file": null,
	  "targets": [
	    {
		  "patterns": [
            "^(?P<KEY>[-0-9A-Za-z]+)$",
            "^(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$"
            "^(?P<CAT>[^/@]+)/(?P<KEY>[-0-9A-Za-z]+)$",
            "^(?P<CAT>[^/@]+)/)(?P<KEY>[-0-9A-Za-z]+)@(?P<SNAP>[-0-9A-Za-z]+)$"
		  ]
		}
	  ]
	}

This target uses the [new resolution method](#new-resolution-method)
to efficiently resolve RIDs across all tables in the catalog, which
will be configured by the `CAT` group in the last two patterns to
recognize resolution URLs with embedded catalog identifiers.

#### Catalog selection

The configured catalog for a matching target is chosen in the
following order (first applicable source wins):

1. The `CAT` group in the match supplies a catalog identifier from the
   ERMresolve URL.
2. The `catalog` field of the target supplies a non-null value.
3. The service-wide `catalog` field supplies a non-null value.
4. The target is considered *incomplete* and is skipped.

#### Multiple targets and default target

When the `targets` list includes multiple target configuration
objects, the targets represented by the configuration are
searched in list order.

Subsequent targets are searched only if the previous targets do not
have a matching pattern or yield an inconclusive resolution, i.e. no
match when probing that target in ERMrest.

The default `targets` list or `[{}]` enables the new resolution
method, taking into consideration any default `server_url` and
`catalog` settings in the service-wide
configuration. See [default configuration](#default-configuration)
for the equivalent fully concrete configuration content, which
includes the default patterns.

#### New resolution method

When the `schema`, `table`, and `column` fields are all absent or set
to `null`, ERMresolve is configured to use the new `/entity_rid/` API
of the configured ERMrest catalog. This method generates GET requests
on the following forms of ERMrest URL:

1. Versioned entity_rid:
   `/ermrest/catalog/1@2P4-RJ1W-WGHG/entity_rid/1-X140`
2. Unversioned entity_rid:
   `/ermrest/catalog/1/entity_rid/1-X140`

ERMresolve understands the special JSON response format of this API
and interprets them appropriately.

#### Legacy resolution method

When the `schema`, `table`, and `column` fields are present with
non-null values, ERMresolve is configured to use the `/entity/` API
of the configured ERMrest catalog. This method generates GET requests
on the following forms of ERMrest URL:

1. Versioned entity:
   `/ermrest/catalog/1@2P4-RJ1W-WGHG/entity/Schema:Table/RID=1-X140`
2. Unversioned entity:
   `/ermrest/catalog/1/entity/Schema:Table/RID=1-X140`

A non-empty result set is interpreted as successful resolution of
the entity in the target table.

A partial legacy configuration target is considered invalid and the
service will abort with diagnostics in the HTTPD error log.

#### Default patterns

If `patterns` is absent in the target object, a default pattern list
is configured. See [default configuration](#default-configuration)
for the concrete details. This default set of patterns can match:
- RIDs in a default catalog (if configured):
   - Unversioned RIDs such as `1-X140`
   - Versioned RIDs such as `1-X140@2P4-RJ1W-WGHG`
- RIDs in a specific catalog:
   - Unversioned RIDs such as `7/1-X140`
   - Versioned RIDs such as `7/1-X140@2P4-RJ1W-WGHG`

These defaults SHOULD be overridden with the `patterns` configuration
field if it is not desirable to support versioned RIDs or embedded
catalog identifiers.

### Example ERMresolve Configuration

This example JSON content demonstrates a resolver that can search for
any RID in the default catalog, search for RIDs in designated
catalogs, and attempt a fallback resolution for a legacy identifier:

    {
      "server_url": "http://myserver.example.com",
      "catalog": 1,
      "targets": [
        { },
		{
		  "schema": "legacy_schema",
		  "table": "legacy_table",
		  "column": "legacy_id"
		}
      ]
    }

The first, empty target `{ }` tells ERMresolve to first try the new
resolution method using the default catalog `1` (unless the `CAT` group
provides a different catalog identifier). The second target configures
a custom search on a legacy table.

### Example WSGI Configuration

    WSGIPythonOptimize 1
    WSGIDaemonProcess ermresolve processes=4 threads=4 user=ermresolve maximum-requests=2000
    WSGIScriptAlias /project1 /usr/lib/python2.7/site-packages/ermresolve/ermresolve.wsgi
    
    WSGISocketPrefix /var/run/wsgi/wsgi
    
    <Location /id>
       Satisfy any
       Allow from all
       WSGIProcessGroup ermresolve
    </Location>

For complex deployments, more than one `Location` may be
configured. Using different `WSGIProcessGroup` and `WSGIDaemonProcess`
stanzas, separate daemon accounts with separate configuration files
can be used for each ERMresolve instance at a separate URL location
prefix.

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
