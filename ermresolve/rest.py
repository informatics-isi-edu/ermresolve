
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

import web
from webauthn2.util import negotiated_content_type
from ermrest.exception.rest import *
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

                # see if this target is the right one in ERMrest
                ermrest_url = (target.ermrest_url_template % parts)
                with _session.get(
                        ermrest_url,
                        headers={"Accept": "application/json"}
                ) as resp:
                    rows = None
                    if resp.status_code == 200:
                        rows = resp.json()
                        if rows:
                            assert len(rows) == 1, "resolution should never find multiple rows"
                            if content_type == 'text/html':
                                raise web.seeother(target.chaise_url_template % parts)
                            else:
                                raise web.seeother(ermrest_url)

                    web.debug('ERMresolve %s did not produce a result' % ermrest_url)

        if syntax_matched:
            raise NotFound(web.ctx.env['REQUEST_URI'])
        else:
            raise BadRequest('Key "%s" is not a recognized ID format.' % url_id_part)

urls = ('/(.*)', Resolver)
