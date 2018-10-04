
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

import urllib
import json

import web
from webauthn2.util import negotiated_content_type
from .config import get_service_config

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

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

class WebException (web.HTTPError):
    def __init__(self, status, data=u'', headers={}, desc=u'%s'):
        if isinstance(data, str):
            data = data.decode('utf8')
        if data is not None and desc is not None:
            data = ('%s\n%s\n' % (status, desc)) % data
            headers['Content-Type'] = 'text/plain'
        try:
            web.ctx.ermrest_request_trace(data)
        except:
            pass
        web.HTTPError.__init__(self, status, headers=headers, data=data if data is not None else '')

class BadRequest (WebException):
    def __init__(self, data=u'', headers={}):
        status = '400 Bad Request'
        desc = u'The request is malformed. %s'
        WebException.__init__(self, status, headers=headers, data=data, desc=desc)

class NotFound (WebException):
    def __init__(self, data=u'', headers={}):
        status = '404 Not Found'
        desc = u'The requested %s could not be found.'
        WebException.__init__(self, status, headers=headers, data=data, desc=desc)

class SeeOther (WebException):
    status = '303 See Other'
    def __init__(self, location, headers={'content-type': 'text/html'}):
        ctype = headers.get('content-type', 'text/html')
        headers['location'] = location
        if ctype == 'text/html':
            data = '<html><head><title>Redirect</title></head><body><a href="%(location)s">%(location)s</a></body></html>\n'
        elif ctype == 'text/uri-list':
            data = '%(location)s\n'
        else:
            raise NotImplementedError('See Other content-type %s' % ctype)
        data = data % headers
        WebException.__init__(self, self.status, headers=headers, data=data, desc=None)

class Resolver (object):
    """Implements ERMresolve REST API as a web.py request handler.

    """
    def GET(self, url_id_part):
        """Resolve url_id_part and redirect client to current GUI or data URL."""
        syntax_matched = False

        content_type = negotiated_content_type(
            ['text/csv', 'application/json', 'application/x-json-stream', 'text/html'],
            'application/json'
        )

        # search in order for syntax match
        for target in _config.targets:
            parts = target.match_parts(url_id_part)
            if parts:
                syntax_matched = True
                found = False

                # see if this target is the right one in ERMrest
                headers = {
                    "Accept": "application/json",
                    "Deriva-Client-Context": urllib.quote(
                        json.dumps(
                            {
                                "cid": "ermresolve",
                                "pid": web.ctx.env['UNIQUE_ID'],
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
                            if "deleted_at" in found:
                                # TODO: revisit if we get a Chaise tombstone app?
                                continue

                if found:
                    # build response for either resolution method
                    if content_type == 'text/html':
                        raise SeeOther(target.chaise_url_template % parts)
                    else:
                        raise SeeOther(target.ermrest_url_template % parts, {'content-type': 'text/uri-list'})

                #web.debug('ERMresolve %s did not produce a result' % ermrest_url)

        if syntax_matched:
            raise NotFound(web.ctx.env['REQUEST_URI'])
        else:
            raise BadRequest('Key "%s" is not a recognized ID format.' % url_id_part)

urls = ('/(.*)', Resolver)
