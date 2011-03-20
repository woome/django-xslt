from lxml import etree
from StringIO import StringIO

# This is used as a parsed-XML cache
# We put all the content we parse here keyed by content
XMLCACHE={}

def assertXpath(xml, xpr, assertion_message="", namespaces=None, html=False):
    """Assert the Xpath 'xpr' evals against the 'xml' document.

    assertion_message can be specified as an alternative error message from a failure.
    namespaces can be specified as a list of namespace key:url pairs to be passed to XSLT
    html is boolean to specify whether to parse the document as HTML or not.
    """

    namespaces = {} if not namespaces else namespaces
    try:
        doc = XMLCACHE.get(xml)
        if not doc:
            parser = etree.HTMLParser() if html else etree.XMLParser()
            doc = etree.parse(StringIO(xml), parser)
            XMLCACHE[xml] = doc
    except Exception, e:
        raise e
    else:
        ret = doc.xpath(xpr, namespaces=namespaces) if namespaces else doc.xpath(xpr)
        if not ret:
            assertion_message = assertion_message \
                if assertion_message \
                else "{%s} did not evaluate with the specified document" % xpr
            raise AssertionError(assertion_message)

# End        
