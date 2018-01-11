
#
# Copyright 2018 University of Southern California
# Distributed under the Apache License, Version 2.0. See LICENSE for more info.
#

import web
from ermresolve.rest import urls

application = web.application(urls, globals()).wsgifunc()

