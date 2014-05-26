# coding=utf8

from setuptools import setup

setup(name='syncano',
      version='0.6.2',
      description='Python Library for syncano.com api',
      author=u'Piotr Czesław Kalmus',
      author_email='piotr.kalmus@syncano.com',
      url='http://syncano.com',
      packages=['syncano',],
      classifiers=['Development Status :: 4 - Beta',
                   'License :: OSI Approved :: MIT License',
                   'Programming Language :: Python',
                   'Programming Language :: Python :: 2.7',
                   'Programming Language :: Python :: 3.3'],
      install_requires=['gevent==1.0.1']
    )

