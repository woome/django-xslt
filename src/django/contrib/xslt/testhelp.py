from lxml import etree
from StringIO import StringIO
import pdb

# This is used as a parsed-XML cache
# We put all the content we parse here keyed by content
XMLCACHE={}

def assertXpath(xml, xpr, assertion_message="", html=False):
    """Assert the Xpath 'xpr' evals against the 'xml' document"""

    try:
        doc = XMLCACHE.get(xml)
        if not doc:
            parser = etree.HTMLParser() if html else etree.XMLParser()
            doc = etree.parse(StringIO(xml), parser)
            XMLCACHE[xml] = doc
    except Exception, e:
        raise e
    else:
        ret = doc.xpath(xpr)
        if not ret:
            assertion_message = assertion_message \
                if assertion_message \
                else "{%s} did not evaluate with the specified document" % xpr
            raise AssertionError(assertion_message)

# End        
