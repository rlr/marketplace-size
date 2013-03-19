#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import datetime
import pickle
import re
import time

import webapp2
from google.appengine.api import memcache, urlfetch
from webapp2_extras import jinja2

from models.entry import Entry

asset_url_pattern = re.compile(r'(src|href)="(.*)"')

urls = {'dev': 'https://support-dev.allizom.org',
        'prod': 'https://support.mozilla.org'}


class BaseHandler(webapp2.RequestHandler):
    @webapp2.cached_property
    def jinja2(self):
        return jinja2.get_jinja2(app=self.app)

    def render_template(self, template, **context):
        rv = self.jinja2.render_template(template, **context)
        self.response.write(rv)


def get_recent_data(domain):
    key = '%s:recent' % domain
    data = memcache.get(key)
    if data is not None:
        return pickle.loads(data)
    else:
        # ~Two weeks of data.
        data = list(Entry.all().filter('domain =', urls[domain])
                               .order('-time')
                               .run(limit=600))
        memcache.add(key, pickle.dumps(data), time=1800)
        return data


class MainHandler(BaseHandler):
    def get(self):
        domain = self.request.get('server', 'dev')
        if domain not in urls:
            return

        ctx = {'entries': reversed(get_recent_data(domain))}
        self.render_template("homepage.html", **ctx)

    def head(self):
        return self.get()


class CheckHandler(webapp2.RequestHandler):

    def _test_url(self, url):
        self.response.write('%s<br>' % url)
        resp = urlfetch.fetch('%s/media/revision.txt' % url)
        assert resp.status_code == 200
        rev = resp.content.strip()

        resp = urlfetch.fetch('%s?mobile=true' % url)
        if resp.status_code != 200:
            return

        size = len(resp.content)
        asset_size = 0
        css_size = 0
        js_size = 0

        for asset in (m.group(2) for m in
                      asset_url_pattern.finditer(resp.content)):

            # Handle relative URLs
            if '://' not in asset:
                asset = url + asset

            if ('.js?' in asset or '.css' in asset or
                asset.endswith('.js')):

                self.response.write('%s<br>' % asset)
                try:
                    data = urlfetch.fetch(asset).content
                except Exception:
                    continue
                if data:
                    data_len = len(data)
                    if '.js?' in asset:
                        js_size += data_len
                    elif '.css' in asset:
                        css_size += data_len
                    asset_size += data_len

        entry = Entry(time=datetime.datetime.now(), size=size,
                      domain=url, with_assets=size + asset_size,
                      commit=rev, size_css=css_size, size_js=js_size)
        entry.put()
        self.response.write('Size: %d<br>' % size)
        self.response.write('Assets Size: %d ' % asset_size)
        self.response.write('(CSS: %d, JS: %d)<br>' % (css_size, js_size))

    def get(self):
        now = time.time()
        last_test = memcache.get('last_cron')
        if last_test is not None and now - int(last_test) < 60 * 15:
            self.response.write('Last cron was too recent.')
            return

        memcache.add('last_cron', now)

        for url in urls.values():
            self._test_url(url)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/tasks/check', CheckHandler),
], debug=True)
