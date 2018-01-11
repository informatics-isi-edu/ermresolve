
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
from ermrest.exception.rest import *
from .config import get_service_config

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

_session = requests.session()
_retries = Retry(
    connect=5,
    read=5,
    backoff_factor=1.0,
    status_forcelist=[500, 502, 503, 504]
)
_session.mount('https://localhost', HTTPAdapter(max_retries=_retries))

class Resolver (object):
    """Implements ERMresolve REST API as a web.py request handler.

    """
    config = get_service_config()
    
    def GET(self, url_id_part):
        """Resolve url_id_part and redirect client to current GUI or data URL."""
        syntax_matched = False

        # search in order for syntax match
        for target in self.config.targets:
            parts = target.match_parts(url_id_part)
            if parts:
                syntax_matched = True

                # see if this target is the right one in ERMrest
                ermrest_path = (target.ermrest_url_template % parts)
                resp = _session.get(
                    'https://localhost' + ermrest_path,
                    headers={"Accept": "application/json"}
                )
                if resp.status == 200:
                    rows = resp.json()
                    resp.close()
                    if rows:
                        assert len(rows) == 1, "resolution should never find multiple rows"
                        # TODO: handle content negotiation for GUI
                        raise web.seeother(ermrest_path)

        if syntax_matched:
            raise NotFound(url_id_part)
        else:
            raise BadRequest('Key "%s" is not a recognized ID format.' % url_id_part)

urls = ('.*', Resolver)
