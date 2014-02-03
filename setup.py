import ultrasoap

from setuptools import setup

setup(
    version=ultrasoap.__version__,
    url=ultrasoap.__url__,
    packages=['ultrasoap'],
    install_requires=[
        'demands >= 1.0.5, < 2.0.0',
        'flake8 < 3.0.0',
        'mock < 2.0.0',
        'nose < 2.0.0',
        'suds == 0.4',
        'unittest2 < 1.0.0',
    ]
)
