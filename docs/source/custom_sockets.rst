.. _custom-sockets:

=========================
Custom Sockets in Syncano
=========================

``Syncano`` provides possibility of creating the custom sockets. It means that there's a possibility
to define a very specific endpoints in syncano application and use them as normal api calls.
Currently custom sockets allow only one dependency - script. This mean that on the backend side
each time the api is called - the script is executed and result from this script is returned as a result of the
api call.

Creating a custom socket
------------------------

There are two methods of creating the custom socket. First: use the helpers objects defined in Python Libray.
Second: use the raw format - this is described below.

To create a custom socket follow the steps::

    import syncano
    from syncano.models import CustomSocket, Endpoint, ScriptCall, ScriptDependency, RuntimeChoices
    from syncano.connection import Connection

    custom_socket = CustomSocket(name='my_custom_socket')  # this will create an object in place (do api call)

    # define endpoints
    my_endpoint = Endpoint(name='my_endpoint')  # again - no api call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    # explanation for the above lines:
    # The endpoint will be seen under `my_endpoint` name:
    # On this syncano api endpoint the above endpoint will be called (after custom socket creation)
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/my_endpoint/
    # On this syncano api endpoint the details of the defined endpoint will be returned
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/my_endpoint/
    # For the above endpoint - the two calls are defined, one uses GET method - the custom_script will be executed
    # there, second uses the POST method and then the another_custom_script will be called;
    # Currently only script are available for calls;

    # After the creation of the endpoint, add them to custom_socket:
    custom_socket.add_endpoint(my_endpoint)

    # define dependency now;
    # using a new script - defining new source code;
    custom_socket.add_dependency(
        ScriptDependency(
            Script(
                label='custom_script',
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            )
        )
    )
    # using a existing script:
    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            another_custom_script
        )
    )

    # now it is time to publish custom_socket;
    custom_socket.publish()  # this will do an api call and will create script;

Some time is needed to setup the environment for this custom socket.
There is possibility to check the custom socket status::

    print(custom_socket.status)
    # and
    print(custom_socket.status_info)

    # to reload object (read it again from syncano api) use:
    custom_socket.reload()



Updating the custom socket
--------------------------

To update custom socket, use::

    custom_socket = CustomSocket.please.get(name='my_custom_socket')

    custom_socket.remove_endpoint(endpoint_name='my_endpoint')
    custom_socket.remove_dependency(dependency_name='custom_script')

    # or add new:

    custom_socket.add_endpoint(new_endpoint)  # see above code for endpoint examples;
    custom_socket.add_dependency(new_dependency)  # see above code for dependency examples;

    custom_socket.update()


Running the custom socket
-------------------------

To run custom socket use::

    # this will run the my_endpoint - and call the custom_script (method is GET);
    result = custom_socket.run(method='GET', endpoint_name='my_endpoint')


Read all endpoints
------------------

To get the all defined endpoints in custom socket run::

    endpoints = custom_socket.get_endpoints()

    for endpoint in endpoints:
        print(endpoint.name)
        print(endpoint.calls)

To run particular endpoint::

    endpoint.run(method='GET')
    # or:
    endpoint.run(method='POST', data={'name': 'test_name'})

The data will be passed to the api call in the request body.

Custom sockets endpoints
------------------------

Each custom socket is created from at least one endpoint. The endpoint is characterized by name and
defined calls. Calls is characterized by name and methods. The name is a identification for dependency, eg.
if it's equal to 'my_script' - the Script with label 'my_script' will be used (if exist and the source match),
or new one will be created.
There's a special wildcard method: `methods=['*']` - this mean that any request with
any method will be executed in this endpoint.

To add endpoint to the custom_socket use::

    my_endpoint = Endpoint(name='my_endpoint')  # again - no api call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    custom_socket.add_endpoint(my_endpoint)

Custom socket dependency
------------------------

Each custom socket has dependency - this is a meta information for endpoint: which resource
should be used to return the api call results. The dependencies are bind to the endpoints call objects.
Currently supported dependency in only script.

**Using new script**

::

    custom_socket.add_dependency(
        ScriptDependency(
            Script(
                label='custom_script',
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            )
        )
    )


**Using defined script**

::

    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            another_custom_script
        )
    )


Custom socket recheck
---------------------

The creation of the socket can fail - this happen, eg. when endpoint name is already taken by another
custom socket. To check the statuses use::

    print(custom_socket.status)
    print(custom_socket.status_info)

There is a possibility to re-check socket - this mean that if conditions are met - the socket will be
`created` again and available to use - if not the error will be returned in status field.

Custom socket - raw format
--------------------------

There is a possibility to create a custom socket from the raw JSON format::

    CustomSocket.please.create(
        name='my_custom_socket_3',
        endpoints={
            "my_endpoint_3": {
                "calls":
                    [
                        {"type": "script", "name": "my_script_3", "methods": ["POST"]}
                    ]
                }
            },
        dependencies=[
            {
                "type": "script",
                "runtime_name": "python_library_v5.0",
                "name": "my_script_3",
                "source": "print(3)"
            }
        ]
    )

The disadvantage of this method is that - the JSON internal structure must be known by developer.
