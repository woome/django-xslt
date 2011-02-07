# Model Managers.

from django.db import models
from django.template import Template
from django.template import Context
import types

class XPathRenderer(object):
    """This is an interface for objects that have __xml__"""
    def __xml__(self, *args):
        return ""

def xmlify(qs, use_values=True, **kwargs):
    """XML serializer for queryset qs using the template described in kwargs.

    This operates a little like django values (indeed it uses django
    values if use_values is True) but allows you to specify the
    resulting XML name.

    Taking an input like this:

       xmlify(qs, **{
          "xml_field_name": "django_queryset__model__accessor",
          "other_xml_field": "django_queryset__deep__reference__field",
          "xml_field": "django_queryset__model__field|upper",
          })

    we get the output:

     [ "xml_field_name='value from django_queryset.model.accessor row 1'
         other_xml_field='value from django_queryset.deep.reference.field row 1'
         xml_field='value to caps from django_queryset.model.field row 1'",

       "xml_field_name='value from django_queryset.model.accessor row 2'
         other_xml_field='value from django_queryset.deep.reference.field row 2'
         xml_field='value to caps from django_queryset.model.field row 2'",
       .
       .
       .
       ]

    Any valid django template may be used on the django field name.

    If use_values is False then a vanilla queryset is used.
    """

    template_list = [(name, Template('{{%s}}' % value)) \
                         for name,value in kwargs.iteritems()]
    django_fields = [template.split("|")[0].split(".")[0] for template in kwargs.values()]

    # Do the query that gets the data to XML
    # Ordinarily we use 'values' but we can use an ordniary query if necessary
    rows = []
    text_fields = []
    if use_values:
        rows = qs.values(*django_fields)
    else:
        for row in qs:
            row_result = {}
            for field in django_fields:
                value = getattr(row, field)
                row_result[field] = value() if isinstance(value, types.MethodType) else value
                if getattr(value, 'is_text', False):
                    text_fields.append(field)
            rows += [row_result]

    # Make a nice list of template outputed rows
    from lxml import etree
    xmlname = qs.model.__name__
    xmlroot = etree.Element("%ss" % xmlname.lower())
    #import pdb
    #pdb.set_trace()
    for record in rows:
        c = Context()
        c.update(record)
        child = etree.SubElement(xmlroot, xmlname.lower())
        for name,template in template_list:
            if name in text_fields:
                elem = etree.SubElement(child, name)
                elem.text = template.render(c)
            else:
                child.attrib[name] = template.render(c)

    class XML(XPathRenderer):
        def __xml__(self, *args):
            return xmlroot
                
    return XML()


from django.db.models.query import QuerySet
class XmlQuerySet(QuerySet):
    """A queryset that does xmlifying"""
    def xml(self, **kwargs):
        return xmlify(self, use_values=getattr(self, "use_values", True), **kwargs)

def monkey_qs(qs, use_values=True):
    """Decorate a queryset with an 'xml' method.

    The 'xml' method returns __xml__ supporting objects.
    __xml__ renders the queryset into the xml specified by the xml
    method.

    For example:

       c = Context({
          "smiths": Profile.objects.filter(
                         user__last_name="smith"
                        ).xml(
                         first_name="user__first_name",
                         username="user__username"
                        )
         })
       t = xslt.Transformer(template)
       t(context=c)

    Results in the xml:

       <profiles>
         <profile first_name="..." username="..."/>
         ...
       </profiles>
    
    being available to the xslt with a call like:

       xdjango:smiths()
    """
    # We use a func here instead of a lambda purely for debuggability
    def adapt(**args):
        data = xmlify(qs, use_values=use_values, **args)
        return data
    capturedclone = qs._clone
    def xmlclone(selfarg, *args, **kwargs):
        newclone = capturedclone(*args, **kwargs)
        newclone.__dict__["xml"] = adapt
        newclone.__dict__["use_values"] = use_values
        newclone.__dict__["_clone"] = types.MethodType(xmlclone, selfarg, selfarg.__class__)
        return newclone
    return xmlclone(qs)


class RenderingManager(models.Manager):
    """Use monkey_qs to decorate the queryset.

    This makes querysets that use values calls by default. To get a
    queryset that will render without using values create the manager
    with:

      use_values=False
    """
    def __init__(self, use_values=True):
        models.Manager.__init__(self)
        self.use_values = use_values

    def get_query_set(self):
        qs = super(RenderingManager, self).get_query_set()
        return monkey_qs(qs)

# End
