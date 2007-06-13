# browsershots.org - Test your web design in different browsers
# Copyright (C) 2007 Johann C. Rocholl <johann@browsershots.org>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston,
# MA 02111-1307, USA.

"""
Browsershots front page.
"""

__revision__ = "$Rev$"
__date__ = "$Date$"
__author__ = "$Author$"

from django.http import HttpResponseRedirect
from django import newforms as forms
from django.shortcuts import render_to_response
from django.utils.text import capfirst
from shotserver04.websites import extract_domain
from shotserver04.platforms.models import Platform
from shotserver04.browsers.models import BrowserGroup, Browser
from shotserver04.websites.models import Domain, Website
from shotserver04.requests.models import RequestGroup, Request
from datetime import datetime, timedelta


class URLForm(forms.Form):
    """
    URL input form.
    """
    url = forms.URLField(max_length=400)


class OptionsForm(forms.Form):
    """
    Request options input form.
    """
    screen_size = forms.ChoiceField(
        label=capfirst(_("screen size")),
        initial='any', choices=(
        ('any', capfirst(_("don't care"))),
        (640, "640x480"),
        (800, "800x600"),
        (1024, "1024x768"),
        (1280, "1280x1024"),
        (1600, "1600x1200"),
        ))
    color_depth = forms.ChoiceField(
        label=capfirst(_("color depth")),
        initial='any', choices=(
        ('any', capfirst(_("don't care"))),
        (4, capfirst(_("%(bits)d bits (%(colors)d colors)")) %
         {'bits': 4, 'colors': 2 ** 4}),
        (8, capfirst(_("%(bits)d bits (%(colors)d colors)")) %
         {'bits': 8, 'colors': 2 ** 8}),
        (16, capfirst(_("16 bits (high color)"))),
        (24, capfirst(_("24 bits (true color)"))),
        ))
    javascript = forms.ChoiceField(
        label=capfirst(_("Javascript")),
        initial='any', choices=(
        ('any', capfirst(_("don't care"))),
        ('no', capfirst(_("disabled"))),
        ('yes', capfirst(_("enabled"))),
        ))
    java = forms.ChoiceField(
        label=capfirst(_("Java")),
        initial='any', choices=(
        ('any', capfirst(_("don't care"))),
        ('no', capfirst(_("disabled"))),
        ('yes', capfirst(_("enabled"))),
        ))
    flash = forms.ChoiceField(
        label=capfirst(_("Flash")),
        initial='any', choices=(
        ('any', capfirst(_("don't care"))),
        ('no', capfirst(_("disabled"))),
        ('yes', capfirst(_("enabled"))),
        (5, capfirst(_("version %(version)d")) % {'version': 5}),
        (5, capfirst(_("version %(version)d")) % {'version': 6}),
        (5, capfirst(_("version %(version)d")) % {'version': 7}),
        (5, capfirst(_("version %(version)d")) % {'version': 8}),
        (5, capfirst(_("version %(version)d")) % {'version': 9}),
        ))
    maximum_wait = forms.ChoiceField(
        label=capfirst(_("maximum wait")),
        initial=30, choices=(
        (15, capfirst(_("15 minutes"))),
        (30, capfirst(_("30 minutes"))),
        (60, capfirst(_("1 hour"))),
        (120, capfirst(_("%(hours)d hours")) % {'hours': 2}),
        (240, capfirst(_("%(hours)d hours")) % {'hours': 4}),
        ))


class BrowserForm(forms.BaseForm):
    """
    Browser chooser form for one platform.
    """

    errors = {}
    base_fields = forms.forms.SortedDictFromList()

    def __init__(self, platform, data=None):
        forms.BaseForm.__init__(self, data)
        self.platform = platform
        self.parts = 1
        platform_browsers = Browser.objects.filter(
            factory__operating_system__platform=platform,
            disabled=False)
        active_browsers = platform_browsers.extra(
            where=['"browsers_browser__factory"."last_poll"' +
                   ' > NOW() - %s::interval'], params=['0:10'])
        field_dict = {}
        for browser in active_browsers:
            label = browser.browser_group.name
            if browser.major is not None:
                label += ' ' + str(browser.major)
                if browser.minor is not None:
                    label += '.' + str(browser.minor)
            name = '_'.join((
                platform.name.lower().replace(' ', '-'),
                browser.browser_group.name.lower().replace(' ', '-'),
                str(browser.major),
                str(browser.minor),
                ))
            if name in field_dict:
                continue
            initial = data is None or (name in data and 'on' in data[name])
            field = forms.BooleanField(
                label=label, initial=initial, required=False)
            field_dict[name] = field
        field_names = field_dict.keys()
        field_names.sort()
        for name in field_names:
            self.fields[name] = field_dict[name]

    def __unicode__(self):
        fields = list(self.fields)
        fields_per_part = (len(fields) + self.parts - 1) / self.parts
        output = []
        for part in range(self.parts):
            output.append('<div style="width:12em;float:left">')
            for index in range(fields_per_part):
                if not fields:
                    break
                field = fields.pop(0)
                output.append(unicode(self[field]) +
                    ' <label for="id_%s">%s</label><br />' % (
                    field, self[field].label))
            output.append('</div>')
        return u'\n'.join(output)


def start(request):
    """
    Front page with URL input, browser chooser, and options.
    """
    post = request.POST or None
    url_form = URLForm(post)
    options_form = OptionsForm(post)
    valid_post = url_form.is_valid() and options_form.is_valid()
    browser_forms = []
    no_active_factories = True
    for platform in Platform.objects.all():
        browser_form = BrowserForm(platform, post)
        if browser_form.is_bound:
            browser_form.full_clean()
        browser_forms.append(browser_form)
        valid_post = valid_post and browser_form.is_valid()
        no_active_factories = no_active_factories and not browser_form.fields
    if valid_post:
        # Submit URL
        url = url_form.cleaned_data['url']
        if url.count('/') == 2:
            url += '/' # Slash after domain name
        domain, created = Domain.objects.get_or_create(
            name=extract_domain(url, remove_www=True))
        website, created = Website.objects.get_or_create(
            url=url, domain=domain)
        # Calculate expiration timeout
        minutes = int(options_form.cleaned_data['maximum_wait'])
        timeout = timedelta(0, minutes * 60, 0)
        expire = datetime.now() + timeout
        # Submit request group
        request_group = RequestGroup.objects.create(
            website=website,
            width=try_int(options_form.cleaned_data['screen_size']),
            bits_per_pixel=try_int(options_form.cleaned_data['color_depth']),
            javascript=options_form.cleaned_data['javascript'],
            java=options_form.cleaned_data['java'],
            flash=options_form.cleaned_data['flash'],
            expire=expire,
            )
        for browser_form in browser_forms:
            create_platform_requests(
                request_group, browser_form.platform, browser_form)
        # return render_to_response('debug.html', locals())
        return HttpResponseRedirect(website.get_absolute_url())
    else:
        # Show HTML form
        return render_to_response('start.html', locals())


def create_platform_requests(request_group, platform, browser_form):
    platform_lower = platform.name.lower().replace(' ', '-')
    result = []
    for name in browser_form.fields:
        if not browser_form.cleaned_data[name]:
            continue # Browser not selected
        first_part, browser_name, major, minor = name.split('_')
        if first_part != platform_lower:
            continue # Different platform
        browser_group = BrowserGroup.objects.get(
            name__iexact=browser_name.replace('-', ' '))
        result.append(Request.objects.create(
            request_group=request_group,
            platform=platform,
            browser_group=browser_group,
            major=try_int(major),
            minor=try_int(minor),
            ))
    return result


def try_int(value):
    if value.isdigit():
        return int(value)
