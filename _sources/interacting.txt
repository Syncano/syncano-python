.. _interacting:

========================
Interacting with Syncano
========================

This tutorial will walk you through our ORM syntax and how to use it to make proper API calls.


Creating a Connection
---------------------

In each example I'll be assuming that you have configured connection to `syncano`::

    >>> import syncano
    >>> connection = syncano.connect(email='YOUR_EMAIL', password='YOUR_PASSWORD')


Accessing models
----------------

All models are defined in :mod:`syncano.models.base` but ``syncano`` simplifies access to them
by attaching all of them directly to ``connection``. Thus::

    from syncano.models.base import Instance

and::

    Instance = connection.Instance

are equivalent.

Creating objects
----------------

A model class represents a single ``Syncano API`` endpoint,
and an instance of that class represents a particular record in this endpoint.

To create an object, instantiate it using **keyword arguments** to the model class,
then call :meth:`~syncano.models.base.Model.save` to save it to the ``Syncano API``.

Here’s an example::

    >>> instance = Instance(name='test-one', description='')
    >>> instance.save()

This performs a **POST** request to ``Syncano API`` behind the scenes.
Syncano doesn’t hit the API until you explicitly call :meth:`~syncano.models.base.Model.save`.

.. note::
    To create and save **an object** in a single step, use the :meth:`~syncano.models.manager.Manager.create` method.
    To create and save **multiple objects** in a single step, use the :meth:`~syncano.models.manager.Manager.bulk_create` method.


Saving changes to objects
-------------------------

To save changes to an object that’s already in the ``Syncano API``, use :meth:`~syncano.models.base.Model.save`.
Regarding our **instance** from previous example,
this example changes its description and updates its record in the ``Syncano API``::

>>> instance.description = 'new description'
>>> instance.save()

This performs a **PUT** request to ``Syncano API`` behind the scenes.
Syncano doesn’t hit the API until you explicitly call :meth:`~syncano.models.base.Model.save`.

.. note::
    To change and save **an object** in a single step, use the :meth:`~syncano.models.manager.Manager.update` method.


Retrieving objects
------------------

To retrieve objects from ``Syncano API``, construct a query via a :class:`~syncano.models.manager.Manager` on your model class.

Each model has only one :class:`~syncano.models.manager.Manager`, and it’s called **please** by default.
Access it directly via the model class, like so::

    >>> Instance.please
    [<Instance: test>, <Instance: test-two>, '...(remaining elements truncated)...']
    >>> i = Instance(name='Foo', description='Bar')
    >>> i.please
    Traceback:
    ...
    AttributeError: Manager isn't accessible via Instance instances.

.. note::
    **Managers** are accessible only via model classes, rather than from model instances,
    to enforce a separation between “table-level” operations and “record-level” operations.


Retrieving all objects
----------------------

The simplest way to retrieve objects from a ``Syncano API`` is to get all of them.
To do this, use the :meth:`~syncano.models.manager.Manager.all` or :meth:`~syncano.models.manager.Manager.list`
method on a :class:`~syncano.models.manager.Manager`::

>>> Instance.please
>>> Instance.please.all()
>>> Instance.please.list()

This performs a **GET** request to ``Syncano API`` list endpoint behind the scenes.

.. note::
    :meth:`~syncano.models.manager.Manager.all` removes any limits from query and loads all
    possible objects from API, while the :meth:`~syncano.models.manager.Manager.list` method
    just executes current query.

Manager is lazy
---------------

:class:`~syncano.models.manager.Manager` is lazy – the act of creating a **Manager** doesn’t involve any API activity.
You can stack Manager methods all day long, and Syncano won’t actually run the API call until the **Manager** is evaluated.
Take a look at this example::

>>> query = Class.please.list('test-instance')
>>> query = query.limit(10)
>>> print(query)

Though this looks like two API calls, in fact it hits API only once, at the last line (``print(query)``).
In general, the results of a :class:`~syncano.models.manager.Manager` aren’t fetched from API until you “ask” for them.


Retrieving a single object
--------------------------

If you know there is only one object that matches your API call,
you can use the :meth:`~syncano.models.manager.Manager.get` method on a :class:`~syncano.models.manager.Manager`
which returns the object directly::

>>> instance = Instance.please.get('instance-name')

This performs a **GET** request to ``Syncano API`` details endpoint behind the scenes.

If there are no results that match the API call, :meth:`~syncano.models.manager.Manager.get`
will raise a :class:`~syncano.exceptions.SyncanoDoesNotExist` exception.
This exception is an attribute of the model class that the API call is being performed on - so in the code above,
if there is no **Instance** object with a name equal "instance-name", Syncano will raise **Instance.DoesNotExist**.

.. note::
    To have more RESTful like method names there is :meth:`~syncano.models.manager.Manager.detail`
    alias for :meth:`~syncano.models.manager.Manager.get` method.


Removing a single object
------------------------

The delete method, conveniently, is named :meth:`~syncano.models.base.Model.delete`.
This method immediately deletes the object and has no return value.
Example::

>>> instance = Instance.please.get('test-one')
>>> instance.delete()

This performs a **DELETE** request to ``Syncano API`` details endpoint behind the scenes.


Limiting returned objects
-------------------------

Use a subset of Python’s array-slicing syntax to limit your
:class:`~syncano.models.manager.Manager` to a certain number of results.

For example, this returns the first 5 objects::

>>> Instance.please[:5]

This returns the sixth through tenth objects::

>>> Instance.please[5:10]

Negative indexing (i.e. **Instance.please.all()[-1]**) is not supported.

.. note::
    If you don't want to use array-slicing syntax there
    is a special manager method  called :meth:`~syncano.models.manager.Manager.limit`.


.. warning::
    Python’s array-slicing syntax is a expensive operation in context of API calls so using
    :meth:`~syncano.models.manager.Manager.limit` is a recommended way.


Lookups that span relationships
-------------------------------

``Syncano API`` has nested architecture so in some cases there will be a need to provide
a few additional arguments to resolve endpoint URL.

For example :class:`~syncano.models.base.ApiKey` is related to :class:`~syncano.models.base.Instance` and
its URL patter looks like this::

/v1/instances/{instance_name}/api_keys/{id}

This example will not work::

    >>> ApiKey.please.list()
    Traceback:
    ...
    SyncanoValueError: Request property "instance_name" is required.

So how to fix that? We need to provide ``instance_name`` as an argument
to :meth:`~syncano.models.manager.Manager.list` method::

    >>> ApiKey.please.list(instance_name='test-one')
    [<ApiKey 1>...]
    >>> ApiKey.please.list('test-one')
    [<ApiKey 1>...]

This performs a **GET** request to ``/v1/instances/test-one/api_keys/``.

.. note::
    Additional request properties are resolved in order as they occurred in URL pattern.
    So if you have pattern like this ``/v1/{a}/{b}/{c}/`` :meth:`~syncano.models.manager.Manager.list`
    method can be invoked like any other Python function i.e ``list('a', 'b', 'c')`` or ``list('a', c='c', b='b')``.


Backward relations
------------------

For example :class:`~syncano.models.base.Instance` has related :class:`~syncano.models.base.ApiKey` model so
all :class:`~syncano.models.base.Instance` objects will have backward relation to list of :class:`~syncano.models.base.ApiKey`'s::

    >>> instance = Instance.please.get('test-one')
    >>> instance.api_keys.list()
    [<ApiKey 1>...]
    >>> instance.api_keys.get(1)
    <ApiKey 1>

.. note::
    **Related** objects do not require additional request properties passed to
    :meth:`~syncano.models.manager.Manager.list` method.

Falling back to raw JSON
------------------------

If you find yourself needing to work on raw JSON data instead of Python objects just use
:meth:`~syncano.models.manager.Manager.raw` method::

    >>> Instance.please.list()
    [<Instance: test>, <Instance: test-two>, '...(remaining elements truncated)...']

    >>> Instance.please.list().raw()
    [{u'name': u'test-one'...} ...]

    >>> Instance.please.list().limit(1).raw()
    [{u'name': u'test-one'...}]

    >>> Instance.please.raw().get('test-one')
    {u'name': u'test-one'...}



Environmental variables
-----------------------

Some settings can be overwritten via environmental variables e.g:

.. code-block:: bash

    $ export SYNCANO_LOGLEVEL=DEBUG
    $ export SYNCANO_APIROOT='https://127.0.0.1/'
    $ export SYNCANO_EMAIL=admin@syncano.com
    $ export SYNCANO_PASSWORD=dummy
    $ export SYNCANO_APIKEY=dummy123
    $ export SYNCANO_INSTANCE=test

.. warning::
    **DEBUG** loglevel will **disbale** SSL cert check.
