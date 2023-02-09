
# 
# Copyright 2018-2023 University of Southern California
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

import urllib
import json
from collections import OrderedDict
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import werkzeug.exceptions
import flask
import flask.views

from webauthn2.util import deriva_debug, RestException

from .config import get_service_config

_config = get_service_config()

_session = requests.session()
_retries = Retry(
    connect=5,
    read=5,
    backoff_factor=1.0,
    status_forcelist=[500, 502, 503, 504]
)

_session.mount('http://', HTTPAdapter(max_retries=_retries))
_session.mount('https://', HTTPAdapter(max_retries=_retries))

if _config.credential_file is not None:
    with open(_config.credential_file, 'rb') as credential_file:
        _credentials = json.load(credential_file)
else:
    _credentials = {}

def target_server(target):
    if target.server_url.startswith('https://'):
        return target.server_url[len('https://'):]
    elif target.server_url.startswith('http://'):
        return target.server_url[len('http://'):]
    else:
        raise NotImplementedError("unsupported server_url %s" % target.server_url)

class ErmresolvException (RestException):
    def __init__(self, message=None, headers={}):
        if message is None:
            message = self.description
        else:
            message = '%s Detail: %s' % (self.description, message)
        super(ErmresolvException, self).__init__(message, headers=headers)

class NotFound (ErmresolvException):
    code = 404
    description = 'Resource not found.'

class BadRequest (ErmresolvException):
    code = 400
    description = 'Request malformed.'

class SeeOther (ErmresolvException):
    code = 303
    description = 'See Other'
    title = 'Redirect'

    # the ancestor RestException class handled content-negotiation
    # but we want different options for the redirect responses...
    response_templates = OrderedDict([
        ("text/html", '<html><head><title>%(title)s</title><body><a href="%(message)s">%(message)s</a></body></html>'),
        ("text/plain", 'See Other: %(message)s'),
        ("text/uri-list", '%(message)s'),
    ])

    def __init__(self, location, headers={}):
        headers = dict(headers)
        headers['location'] = location
        super(SeeOther, self).__init__(location, headers=headers)
        # set just the location URL as the whole message
        # otherwise we get extra text formatting from the ancestor classes
        self.description = location

app = flask.Flask('ermresolv')

@app.errorhandler(Exception)
def error_handler(ev):
    if isinstance(ev, (RestException, werkzeug.exceptions.HTTPException)):
        # TODO: add logging here if desired?
        pass
    else:
        et, ev2, tb = sys.exc_info()
        deriva_debug('Got unhandled exception in ermresolv: %s\n' % (ev,))
        deriva_debug(''.join(traceback.format_exception(et, ev2, tb)))

    # TODO: investigate and rewrite any unhandled exceptions
    # otherwise flask will turn them into 500 Internal Server Error
    return ev

class Resolver (flask.views.MethodView):
    """Implements ERMresolve REST API request handler.

    """
    def get(self, url_id_part):
        """Resolve url_id_part and redirect client to current GUI or data URL."""
        syntax_matched = False

        # search in order for syntax match
        for target in _config.targets:
            parts = target.match_parts(url_id_part)
            if parts:
                syntax_matched = True
                found = False

                # see if this target is the right one in ERMrest
                headers = {
                    "Accept": "application/json",
                    "Deriva-Client-Context": urllib.parse.quote(
                        json.dumps(
                            {
                                "cid": "ermresolve",
                                "pid": flask.request.environ['UNIQUE_ID'],
                            },
                            separators=(',', ':')
                        ),
                        safe='",:{}'
                    )
                }
                cookie = _credentials.get(target_server(target), {}).get('cookie', None)
                if cookie is not None:
                    headers['Cookie'] = cookie

                if target.legacy:
                    # legacy search of specific table via ermrest entity API
                    ermrest_url = (target.ermrest_url_template % parts)
                    with _session.get(ermrest_url, headers=headers) as resp:
                        if resp.status_code == 200:
                            found = resp.json()
                            assert len(found) in [0, 1], "resolution should never find multiple rows"
                else:
                    # new resolution method via ermrest entity_rid API
                    resolve_url = (target.ermrest_resolve_template % parts)
                    with _session.get(resolve_url, headers=headers) as resp:
                        if resp.status_code == 200:
                            found = resp.json()
                            parts.update({
                                "schema": found["schema_name"],
                                "table": found["table_name"],
                                "column": "RID",
                                "key": found["RID"], # handle possible RID normalization!
                            })
                            if "last_visible_snaptime" in found:
                                # TODO: revisit if we get a Chaise tombstone app?
                                parts["catalog"] = "%s@%s" % (
                                    parts["catalog_bare"],
                                    found["last_visible_snaptime"],
                                )

                if found:
                    # build response for either resolution method
                    raise SeeOther(target.chaise_url_template % parts)

                #deriva_debug('ERMresolve %s did not produce a result' % ermrest_url)

        if syntax_matched:
            raise NotFound(flask.request.environ['REQUEST_URI'])
        else:
            raise BadRequest('Key "%s" is not a recognized ID format.' % url_id_part)

        # always raise an exception above, never return a normal flask response!

# setup flask route
urls = ('/(.*)', Resolver)
_Resolver_view = app.route(
    '/<path:url_id_part>'
)(Resolver.as_view('Resolver'))
