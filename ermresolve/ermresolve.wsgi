
#
# Copyright 2018-2023 University of Southern California
# Distributed under the Apache License, Version 2.0. See LICENSE for more info.
#

import os
from ermresolve.rest import app
from werkzeug.middleware.proxy_fix import ProxyFix

if os.environ.get("DERIVA_WSGI_RPROXY", "").lower() in {"1", "true", "yes"}:
    application = ProxyFix(app, x_for=1, x_proto=1, x_host=1)
else:
    application = app
