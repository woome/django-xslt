# encoding=utf-8

"""Tests for xslt"""

import time
import re
from django.template import Context
from testhelp import assertXpath
from unittest import TestCase
from djangoxslt import xslt
import logging
logging.basicConfig()

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


from django.test.client import Client

class XSLTTest(TestCase):
    """Test the xslt system..
    """
    def setUp(self):
        self.client = Client()

    def test_simple_page(self):
        """Test that we can retrieve the simple page."""
        response = self.client.get("/testtransform/simplepage/")
        self.assertEquals(response.status_code, 200)
        # We should really assert some xpath things about it.
        
from djangoxslt.xslt import managers as xsltmanagers

def _qs_eval_helper(qs):
    """This is a useful little bit of code to eval the xml dom result.

    The qs MUST have the __xml__ method, ie: it must result from an
    .xml(...) somethere in the chain."""

    from lxml import etree
    data1 = qs.__xml__()
    strresult = etree.tostring(data1)
    # print strresult
    return strresult

class IterableTest(TestCase):
    def setUp(self):
        super(IterableTest, self).setUp()
        self.time = int(time.time() * 1000)

    def test_iterable_render(self):
        tmpl = BLANK % """
        <xsl:copy-of select="xdjango:foo%d()"/>
        """ % self.time
        transformer = xslt.Transformer(tmpl)
        
        dictlist = [
            {"a": 10, "b": 20, "c": 40},
            {"a": 11, "b": 21, "c": 41},
            {"a": 12, "b": 22, "c": 42},
            ]

        xmlobj = xsltmanagers.xmlifyiter(
            dictlist,
            "Simple",
            attriba="a",
            otherattrib="c"
            )

        # Use objects and NOT values
        context_key = 'foo%d' % self.time
        c = Context({ 
                context_key: xmlobj,
                })

        res = transformer(context=c)
        assertXpath(
            res, 
            '//simples/simple[@attriba="%s"]' % 10
            )

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

        # Use objects and NOT values
        qs = xsltmanagers.monkey_qs(
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

    def test_queryset_xmlify_user(self):
        """Tests that querysets can be rendered with the xmlify method.
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

        # Make a queryset
        qs = User.objects.filter(username="user%s" % self.time)

        # Make an xml object from it
        xml_list = xsltmanagers.xmlify(
            qs,
            first_name="first_name", 
            username="username"
            )

        context_key = 'foo%d' % self.time
        c = Context({ context_key: xml_list })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//users//user[@first_name="first%s"]' % self.time,
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
        qs = xsltmanagers.monkey_qs(
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


    def test_queryset_render_testmodel_no_kwargs(self):
        """Tests that querysets can be rendered without kwargs.

        Takes our own test model and xmlify it with no kwargs causing
        it's own __xml__ method to be used to render the XML.
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
            )

        xmlified = xsltmanagers.xmlify(xml, use_values=False)

        c = Context({ 'foo%d' % self.time: xmlified })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//xslttestmodels/xslttestmodel/name[text()="name%s"]' % self.time,
            )



    def test_queryset_render_persists(self):
        """Tests that queryset __xml__ method attachment works.

        The __xml__ method, attached by using the xml() method, should
        'stick' to a queryset through further child-querysets.
        """
        tmpl = BLANK % """
        <xsl:copy-of select="xdjango:foo%d()"/>
        """ % self.time
        transformer = xslt.Transformer(tmpl)
        
        from models import XSLTTestModel
        for i in range(1,20):
            testobject = XSLTTestModel(
                name = "name%s" % (int(self.time) * i),
                about = "about%s" % (int(self.time) * i),
                count = i
                )
            testobject.save()

        # Do the query - this qs should have an 'xml' method
        base_qs = XSLTTestModel.objects.filter(
            name="name%s" % self.time
            )

        # Make a first sub-qs to check the xml method is being cloned
        qs = base_qs.filter(count__lte=12)

        # Check it has the xml method
        self.assert_("xml" in qs.__dict__)

        # Call the 'xml' method to store the xml to be generated and return a new qs
        qs_from_xml = qs.xml(name="name",  about_text="about", count="count")

        # Check it has the __xml__ method
        self.assert_("__xml__" in qs_from_xml.__dict__)

        # Make another qs from the 'xml' decorated one
        selected = qs_from_xml.filter(count__lte=3)

        # Check the sub-queryset has the __xml__ method
        self.assert_("__xml__" in selected.__dict__)

        xml_result = _qs_eval_helper(selected)
        self.assert_(re.search(""" name="name%s"[ /]""" % self.time, xml_result))
        
        c = Context({ 'foo%d' % self.time: selected })
        res = transformer(context=c)
        assertXpath(
            res, 
            '//xslttestmodels/xslttestmodel[@name="name%s"]' % self.time,
            )
        assertXpath(
            res, 
            '//xslttestmodels/xslttestmodel[@about_text="about%s"]' % self.time,
            )

        ##### TODO!!!!
        ### need to assert we have the RIGHT number of xslttestmodel objects
        ### it should be 12 and not 3 because we do the .xml(...) before the lte=3
    


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
        assertXpath(
            res, 
            '//xhtml:a[@href="some-location/foo"]',
            namespaces={
                "xhtml": "http://www.w3.org/1999/xhtml",
                }
            )

    def test_nonroot_avt(self):
        tmpl = BLANK % """
        <a href="/{xdjango:foo%d()}/foo">!</a>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'some-location'})
        res = t(context=c)
        assertXpath(
            res, 
            '//xhtml:a[@href="/some-location/foo"]',
            namespaces={
                "xhtml": "http://www.w3.org/1999/xhtml",
                }
            )

    def test_nonroot_avt_method(self):
        tmpl = BLANK % """
        <a href="/{xdjango:foo%d.upper()}/foo">!</a>
        """ % self.time
        t = xslt.Transformer(tmpl)
        c = Context({'foo%d' % self.time: 'some-location'})
        res = t(context=c)
        assertXpath(
            res, 
            '//xhtml:a[@href="/SOME-LOCATION/foo"]',
            namespaces={
                "xhtml": "http://www.w3.org/1999/xhtml",
                }
            )

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
        c = Context({
                'foo%da' % self.time: 'some-location',
                'foo%db' % self.time: 'more'
                })
        res = t(context=c)
        assertXpath(
            res, 
            '//xhtml:a[@href="/some-location/more/foo"]',
            namespaces={
                "xhtml": "http://www.w3.org/1999/xhtml",
                }
            )

# End
