.. _getting-started:

============================
Getting Started with Syncano
============================

This tutorial will walk you through installing and configuring ``syncano``, as
well how to use it to make API calls.

This tutorial assumes you are familiar with Python & that you have registered
for an `Syncano`_ account.

.. _`Syncano`: http://www.syncano.com/


Installing Syncano
------------------

You can use ``pip`` to install the latest released version of ``syncano``::

    pip install syncano

If you want to install ``syncano`` from source::

    git clone git@github.com:Syncano/syncano-python.git
    cd syncano-python
    python setup.py install


Using Virtual Environments
--------------------------

Another common way to install ``syncano`` is to use a ``virtualenv``, which
provides isolated environments. First, install the ``virtualenv`` Python
package::

    pip install virtualenv

Next, create a virtual environment by using the ``virtualenv`` command and
specifying where you want the virtualenv to be created (you can specify
any directory you like, though this example allows for compatibility with
``virtualenvwrapper``)::

    mkdir ~/.virtualenvs
    virtualenv ~/.virtualenvs/syncano

You can now activate the virtual environment::

    source ~/.virtualenvs/syncano/bin/activate

Now, any usage of ``python`` or ``pip`` (within the current shell) will default
to the new, isolated version within your virtualenv.

You can now install ``syncano`` into this virtual environment::

    pip install syncano

When you are done using ``syncano``, you can deactivate your virtual environment::

    deactivate

If you are creating a lot of virtual environments, `virtualenvwrapper`_
is an excellent tool that lets you easily manage your virtual environments.

.. _`virtualenvwrapper`: http://virtualenvwrapper.readthedocs.org/en/latest/


Making Connections
------------------

``syncano`` provides a number of convenience functions to simplify connecting to our services::

    >>> import syncano
    >>> connection = syncano.connect(email='YOUR_EMAIL', password='YOUR_PASSWORD')

If you want to connect directly to chosen instance you can use :func:`~syncano.connect_instance` function::

    >>> import syncano
    >>> connection = syncano.connect_insatnce('insatnce_name', email='YOUR_EMAIL', password='YOUR_PASSWORD')

If you have obtained your ``Account Key`` from the website you can omit ``email`` & ``password`` and pass ``Account Key`` directly to connection:

    >>> import syncano
    >>> connection = syncano.connect(api_key='YOUR_API_KEY')
    >>> connection = syncano.connect_insatnce('insatnce_name', api_key='YOUR_API_KEY')


Troubleshooting Connections
---------------------------
When calling the various queries, you might run into an error like this:

    >>> import syncano
    >>> connection = syncano.connect(api_key='abcd')
    >>> list(connection.instances)
    Traceback (most recent call last):
      ...
        raise SSLError(e, request=request)
    requests.exceptions.SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed (_ssl.c:581)

This is because your endpoint has invalid SSL certificate.
If you want to skip SSL verification you need to create a new connection like this::

    >>> import syncano
    >>> connection = syncano.connect(api_key='abcd', verify_ssl=False)
    >>> list(connection.instances)
    [<Instance: syncano>]

Interacting with Syncano
------------------------

The following code demonstrates how to create a new :class:`~syncano.models.base.Instance`
and add a :class:`~syncano.models.base.ApiKey` to it::

    >>> import syncano
    >>> connection = syncano.connect(api_key='abcd')
    >>> instance = connection.instances.create(name='dummy_test', description='test')
    >>> instance
    <Instance: dummy_test>

    >>> api_key = instance.api_keys.create()
    >>> ApiKey: 47>
    <ApiKey: 47>
    >>> api_key.api_key
    u'aad17f86d41483db7088ad2549ccb87902d60e45'

Each model has a different set of fields and commands. For more informations check :ref:`available models <models>`.

Next Steps
----------

If you'd like more information on interacting with Syncano, check out the :ref:`interacting tutorial<interacting>` or if you
want to know what kind of models are avalable check out the :ref:`available models <models>` list.



