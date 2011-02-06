# encoding=utf-8

"""Tests for xslt"""

import time
from django.template import Context
from testhelp import assertXpath
from unittest import TestCase
import mock
import xslt

BLANK = """<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet  version="1.0" 
                 xmlns="http://www.w3.org/1999/xhtml"
                 xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                 xmlns:xdjango="http://djangoproject.com/template/xslt"
                 extension-element-prefixes="xdjango"
                 exclude-result-prefixes="xdjango">
    <xsl:output omit-xml-declaration="yes"/>
    <xsl:template match="/">
%s
    </xsl:template>
</xsl:stylesheet>
"""

class DjangoContextFuncTest(TestCase):
    def setUp(self):
        super(DjangoContextFuncTest, self).setUp()
        self.func = xslt.DjangoContextFunc("testfunc")
        c = Context({'testfunc': 'a value'})
        xslt.djangothread.context = c

    def test_parse_str(self):
        result = self.func.parse("<tag>no</tag>")

    def test_parse_unicode(self):
        result = self.func.parse(u"<tag>sí</tag>")

    def test_parsehtml_str(self):
        result = self.func.parsehtml("<a>no</a>")

    def test_parsehtml_unicode(self):
        result = self.func.parsehtml(u"<a>sí</a>")

    def test_call_str(self):
        result = self.func("testval")
        assert result == "a value"

    def test_call_unicode(self):
        c = Context({'testfunc': u'☃☃☃☃☃'})
        xslt.djangothread.context = c
        result = self.func(u"téstv☃al")
        assert result == u'☃☃☃☃☃'

    def tearDown(self):
        xslt.djangothread.context = None


class XSLT(TestCase):
    """Test the xslt system..
    """

    def test_simple_page(self):
        """Test that we can retrieve the simple page."""
        response = self.client.get("/testtransform/simplepage/")
        self.assertEquals(response.status_code, 200)
        print response.content

    def test_woome_page(self):
        """Test that we can retrieve a WooMe page.

        This tests that imports of WooMe's existing XSLTs work."""

        response = self.client.get("/testtransform/woomepage/")
        self.assertEquals(response.status_code, 200)

        tester = self.make_and_get_person('xsl1')
        self.client.login(username=tester.user.username)
        response = self.client.get("/testtransform/woomepage/")
        print response.content

        self.assertEquals(response.status_code, 200)
        assertXpath(
            response.content,
            "//div[@id='test__username']/text()='%s'" % tester.user.username,
            )

import xslt.managers

class QSRenderTestCase(TestCase):
    def setUp(self):
        super(QSRenderTestCase, self).setUp()
        self.time = int(time.time() * 1000)

    def test_queryset_render_non_values(self):
        """Tests that querysets can be rendered without using 'values'.

        Takes a django User object and monkey_qs's it then test the
        xml is returned correctly when we use a dynamic method and
        therefore specify no to 'use_values'
        """
        tmpl = BLANK % """
        <xsl:copy-of select="xdjango:foo%d()"/>
        """ % self.time
        transformer = xslt.Transformer(tmpl)
        
        from django.contrib.auth.models import User
        user = User(
            username="user%s" % self.time,
            password="password%s" % self.time,
            first_name="first%s" % self.time,
            last_name="last%s" % self.time
            )
        user.save()
        qs = xslt.managers.monkey_qs(
            User.objects.filter(username="user%s" % self.time),
            use_values=False
            )

        context_key = 'foo%d' % self.time
        xml = qs.xml(full_name="get_full_name", username="username")
        c = Context({ context_key: xml })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//users/user[@full_name="first%s last%s"]' % (self.time, self.time)
            )


    def test_queryset_render_user(self):
        """Tests that querysets can be rendered.

        Takes a django User object and monkey_qs's it then test the
        xml is returned correctly.
        """
        tmpl = BLANK % """
        <xsl:copy-of select="xdjango:foo%d()"/>
        """ % self.time
        transformer = xslt.Transformer(tmpl)
        
        from django.contrib.auth.models import User
        user = User(
            username="user%s" % self.time,
            password="password%s" % self.time,
            first_name="first%s" % self.time
            )
        user.save()
        qs = xslt.managers.monkey_qs(
            User.objects.filter(username="user%s" % self.time)
            )

        context_key = 'foo%d' % self.time
        xml = qs.xml(first_name="first_name", username="username")
        c = Context({ context_key: xml })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//users/user[@first_name="first%s"]' % self.time,
            )

    def test_queryset_render_testmodel(self):
        """Tests that querysets can be rendered.

        Takes our own test model and uses the model's built in manager
        which monkey patches all querysets coming out of it.
        """
        tmpl = BLANK % """
        <xsl:copy-of select="xdjango:foo%d()"/>
        """ % self.time
        transformer = xslt.Transformer(tmpl)
        
        from models import XSLTTestModel
        testobject = XSLTTestModel(
            name = "name%s" % self.time,
            about = "about%s" % self.time,
            count = 10
            )
        testobject.save()

        # Do the query and pull back the xml
        xml = XSLTTestModel.objects.filter(
            name="name%s" % self.time
            ).xml(
            name="name", 
            about_text="about", 
            count="count"
            )
        c = Context({ 'foo%d' % self.time: xml })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//xslttestmodels/xslttestmodel[@name="name%s"]' % self.time,
            )
        assertXpath(
            res, 
            '//xslttestmodels/xslttestmodel[@about_text="about%s"]' % self.time,
            )


class AVTTestCase(TestCase):
    def setUp(self):
        super(AVTTestCase, self).setUp()
        self.time = int(time.time() * 1000)

    def test_variable_usage(self):
        tmpl = BLANK % """
        <xsl:variable name="test" select="xdjango:foo%d()"/>
        <xsl:value-of select="$test"/>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'hello world'})
        assert t(context=c) == 'hello world\n'

    def test_simple(self):
        tmpl = BLANK % """
        <xsl:value-of select="xdjango:foo%d()"/>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'hello world'})
        assert t(context=c) == 'hello world\n'

    def test_rooted_avt(self):
        tmpl = BLANK % """
        <a href="{xdjango:foo%d()}/foo">!</a>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'some-location'})
        res = t(context=c)
        assertXpath(res, '//a[@href="some-location/foo"]')

    def test_nonroot_avt(self):
        tmpl = BLANK % """
        <a href="/{xdjango:foo%d()}/foo">!</a>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'some-location'})
        res = t(context=c)
        assertXpath(res, '//a[@href="/some-location/foo"]')

    def test_nonroot_avt_method(self):
        tmpl = BLANK % """
        <a href="/{xdjango:foo%d.upper()}/foo">!</a>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'some-location'})
        res = t(context=c)
        assertXpath(res, '//a[@href="/SOME-LOCATION/foo"]')

    def test_method(self):
        tmpl = BLANK % """
        <xsl:value-of select="xdjango:foo%d.upper()"/>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'hello world'})
        assert t(context=c) == 'HELLO WORLD\n'

    def test_multiple_avt(self):
        tmpl = BLANK % """
        <a href="/{xdjango:foo%da()}/{xdjango:foo%db()}/foo">!</a>
        """ % (self.time, self.time)
        t = xslt.Transformer(tmpl)
        c = Context({'foo%da' % self.time: 'some-location',
            'foo%db' % self.time: 'more'})
        res = t(context=c)
        assertXpath(res, '//a[@href="/some-location/more/foo"]')

# End