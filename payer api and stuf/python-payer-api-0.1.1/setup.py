from distutils.core import setup
import os

VERSION = __import__("payer_api").VERSION

CLASSIFIERS = [
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Topic :: Software Development',
]

install_requires = [
    'lxml>=3.0',
]


def read_md(path):
    long_desc = ""
    if os.path.exists(path):
        try:
            from pypandoc import convert
            long_desc = convert(path, 'rst')
        except:
            try:
                long_desc = open(path, 'r').read()
            except:
                pass
    return long_desc

long_desc = read_md("README.md")

setup(
    name="python-payer-api",
    description="Python package for interacting with the Payer payments API\
        (http://www.payer.se).",
    long_description=long_desc,
    version=VERSION,
    author="Simon Fransson",
    author_email="simon@dessibelle.se",
    url="https://github.com/dessibelle/python-payer-api",
    download_url="https://github.com/dessibelle/python-payer-api/"
        "archive/%s.tar.gz" % VERSION,
    packages=['payer_api', 'payer_api.tests'],
    install_requires=install_requires,
    classifiers=CLASSIFIERS,
    license="MIT",
)
