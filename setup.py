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

from setuptools import setup

setup(
    name='ermresolve',
    description='ERM citation resolver for ERMrest',
    version='20230926.0',
    zip_safe=False, # we need to unpack for mod_wsgi to find ermrest.wsgi 
    packages=[
        'ermresolve',
    ],
    package_data={
        'ermresolve': ['*.wsgi']
    },
    scripts=[
    ],
    requires=['flask', 'ermrest'],
    maintainer_email='support@misd.isi.edu',
    license='Apache License, Version 2.0',
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ])
