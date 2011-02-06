"""Models for XSLT.

These are purely for testing the XSLT code.
"""

from django.db import models
from managers import RenderingManager

# A test manager
class XSLTTestManager(RenderingManager):
    pass

# A test model
class XSLTTestModel(models.Model):
    name = models.CharField(max_length=50)
    about = models.TextField()
    count = models.IntegerField()

    # Setup the manager to be a rendering manager
    objects = XSLTTestManager()

# End
