from setuptools import setup, find_packages
from syncano import __version__


def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='syncano',
    version=__version__,
    description='Python Library for syncano.com api',
    long_description=readme(),
    author='Daniel Kopka',
    author_email='daniel.kopka@syncano.com',
    url='http://syncano.com',
    packages=find_packages(),
    test_suite='tests',
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
    ],
    install_requires=[
        'requests==2.5.1',
        'six==1.9.0',
    ],
    tests_require=[
        'mock>=1.0.1',
        'coverage>=3.7.1',
    ],
)
