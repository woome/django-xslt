<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet  version="1.0" 
    extension-element-prefixes="xdjango"
    exclude-result-prefixes="xdjango fb"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:xdjango="http://djangoproject.com/template/xslt"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:output 
        method="xml" 
        indent="yes" 
        omit-xml-declaration="yes"
        doctype-system="http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"
        doctype-public="-//W3C//DTD XHTML 1.0 Transitional//EN" />

    <!-- 
         Stuff to do with this test page 

         - add some django context calls to pull out some data
    -->
    <xsl:template match="/">
        <html>
            <head>
                <title>WooMe Test</title>
            </head>
            <body>
                <h1>This is a test page</h1>
            </body>
        </html>
    </xsl:template>

</xsl:stylesheet>
