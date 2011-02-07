<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet  version="1.0" 
    extension-element-prefixes="xdjango error"
    exclude-result-prefixes="xdjango"
    xmlns="http://www.w3.org/1999/xhtml"
    xmlns:error="http://djangoproject.com/template/error"
    xmlns:xdjango="http://djangoproject.com/template/xslt"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:import href="_common.xslt"/>

    <!-- All top level pages need this -->
    <xsl:template match="/">
        <xsl:call-template name="common_mainpage"/>
    </xsl:template>

    <!-- This is how we provide in-woome frame content -->
    <xsl:template match="/" mode="body">
        <h1>This is a test error page</h1>

        <div id="error"><xsl:value-of select="$wierderror"/></div>
    </xsl:template>

    <xsl:template name="greybox">
    </xsl:template>

</xsl:stylesheet>
