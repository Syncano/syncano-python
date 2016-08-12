.. _custom-sockets:

=========================
Custom Sockets in Syncano
=========================

``Syncano`` provides possibility of creating custom sockets. It means that there's a possibility
to define a very specific endpoints in syncano application and use them as normal API calls.
Currently custom sockets allow only one dependency - script. This mean that on the backend side
each time the API is called - the script is executed and result from this script is returned as a result of the
API call.

Creating a custom socket
------------------------

To create a custom socket follow these steps::

    import syncano
    from syncano.models import CustomSocket, Endpoint, ScriptCall, ScriptDependency, RuntimeChoices
    from syncano.connection import Connection

    # 1. Initialize the custom socket.
    custom_socket = CustomSocket(name='my_custom_socket')  # this will create an object in place (do API call)

    # 2. Define endpoints.
    my_endpoint = Endpoint(name='my_endpoint')  # again - no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    # explanation for the above lines:
    # The endpoint will be seen under `my_endpoint` name:
    # On this syncano API endpoint the above endpoint will be called (after custom socket creation)
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/my_endpoint/
    # On this syncano API endpoint the details of the defined endpoint will be returned
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/my_endpoint/
    # For the above endpoint - the two calls are defined, one uses GET method - the custom_script will be executed
    # there, second uses the POST method and then the another_custom_script will be called;
    # Currently only script are available for calls;

    # 3. After the creation of the endpoint, add them to custom_socket.
    custom_socket.add_endpoint(my_endpoint)

    # 4. Define dependency now.
    # 4.1 using a new script - defining new source code.
    custom_socket.add_dependency(
        ScriptDependency(
            name='custom_script'
            script=Script(
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            )
        )
    )
    # 4.2 using an existing script.
    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            name='another_custom_script',
            script=another_custom_script
        )
    )

    # 4.3 using an existing ScriptEndpoint.
    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint=script_endpoint
    )

    # 5. Publish custom_socket.
    custom_socket.publish()  # this will do an API call and will create script;

Some time is needed to setup the environment for this custom socket.
There is possibility to check the custom socket status::

    # Reload will refresh object using syncano API.
    custom_socket.reload()
    print(custom_socket.status)
    # and
    print(custom_socket.status_info)

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


Read all endpoints in custom socket
-----------------------------------

To get the all defined endpoints in custom socket run::

    endpoints = custom_socket.get_endpoints()

    for endpoint in endpoints:
        print(endpoint.name)
        print(endpoint.calls)

To run a particular endpoint::

    endpoint.run(method='GET')
    # or:
    endpoint.run(method='POST', data={'name': 'test_name'})

The data will be passed to the API call in the request body.

Read all endpoints
------------------

To get all endpoints that are defined in all custom sockets::

    socket_endpoint_list = SocketEndpoint.get_all_endpoints()

Above code will return a list with SocketEndpoint objects. To run such endpoint, use::

    socket_endpoint_list.run(method='GET')
    # or:
    socket_endpoint_list.run(method='POST', data={'custom_data': 1})

Custom sockets endpoints
------------------------

Each custom socket requires to define at least one endpoint. The endpoint is defined by name and
a list of calls.  Each call is defined by a name and a list of methods. The name is a identification for dependency, eg.
if it's equal to 'my_script' - the ScriptEndpoint with name 'my_script' will be used
(if it exists and Script source and runtime matches) or a new one will be created.
There's a special wildcard method: `methods=['*']` - this mean that any request with
any method will be executed in this endpoint.

To add an endpoint to the custom_socket use::

    my_endpoint = Endpoint(name='my_endpoint')  # again - no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    custom_socket.add_endpoint(my_endpoint)

Custom socket dependency
------------------------

Each custom socket has dependency - this is a meta information for endpoint: which resource
should be used to return the API call results. The dependencies are bind to the endpoints call objects.
Currently the only supported dependency is script.

**Using new script**

::

    custom_socket.add_dependency(
        ScriptDependency(
            name='custom_script'
            script=Script(
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
            name='another_custom_script',
            script=another_custom_script
        )
    )

**Using defined script endpoint**

::

    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint=script_endpoint
    )

Custom socket recheck
---------------------

The creation of the socket can fail - this happen, eg. when endpoint name is already taken by another
custom socket. To check the statuses use::

    print(custom_socket.status)
    print(custom_socket.status_info)

There is a possibility to re-check socket - this mean that if conditions are met - the socket endpoints and dependencies
will be checked - and if some of them are missing (eg. mistake deletion), they will be created again.
If the endpoints and dependencies do not met the criteria - the error will be returned in the status field.

Custom socket - raw format
--------------------------

If you prefer raw JSON format for creating sockets, you can resort to use it in python library as well::::

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
