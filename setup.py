#from setuptools import setup
#from setuptools import find_packages
from setuptools import setup

classifiers = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Utilities',
    'Topic :: Communications :: Email',
]

# Depends: 
# django
setup(
    name = "django-xslt",
    version = "0.1",
    description = "an XSLT template system for Django",
    long_description = """A replacment for Django's template system based on XSLT.""",
    license = "BSD",
    author = "Nic Ferrier",
    author_email = "nic@woome.com",
    url = "http://github.com/woome/xslt",
    download_url="http://github.com/woome/xslt/downloads",
    platforms = ["unix"],
    packages = ["django.contrib.xslt"],
    package_dir = {"":"src"},
    test_suite = "django.contrib.xslt",
# Not sure we need a script, it would be nice to ship a django command line xsltproc?
#    scripts=['src/md'],   
    classifiers =  classifiers
    )