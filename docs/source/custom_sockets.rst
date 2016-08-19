.. _custom-sockets:

=========================
Custom Sockets in Syncano
=========================

``Syncano`` gives its users the ability to create Custom Sockets. What this means is that users can define very specific
endpoints in their Syncano application, and use them exactly like they would any other Syncano 
module (Classes, Scripts, etc), using standard API calls.
Currently, Custom Sockets allow only one dependency - Scripts. Under the hood,
each API call executes a Script, and the result of this execution is returned as a result of the
API call.

Creating a custom Socket
------------------------

To create a custom Socket follow these steps::

    import syncano
    from syncano.models import CustomSocket, Endpoint, ScriptCall, ScriptDependency, RuntimeChoices
    from syncano.connection import Connection

    # 1. Initialize a custom Socket.
    custom_socket = CustomSocket(name='my_custom_socket')  # this will create an object in place (do API call)

    # 2. Define endpoints.
    my_endpoint = Endpoint(name='my_endpoint')  # no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    # What happened here:
    # - We defined a new endpoint that will be visible under the name `my_endpoint`
    # - You will be able to call this endpoint (execute attached `call`), 
    # by sending a request, using any defined method to the following API route:
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/my_endpoint/ 
    # - To get details for that endpoint, you need to send a GET request to following API route:
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/my_endpoint/
    #
    # Following the example above - we defined two calls on our endpoint with the `add_call` method
    # The first one means that using a GET method will call the `custom_script` Script,
    # and second one means that using a POST method will call the `another_custom_script` Script.
    # At the moment, only Scripts are available as endpoint calls.
    #
    # As a general rule - to get endpoint details (but not call them), use following API route:
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/<endpoint>/
    # and to run your endpoints (e.g. execute Script connected to them), use following API route:
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/<endpoint>/

    # 3. After creation of the endpoint, add it to your custom_socket.
    custom_socket.add_endpoint(my_endpoint)

    # 4. Define dependency.
    # 4.1 Using a new Script - define a new source code.
    custom_socket.add_dependency(
        ScriptDependency(
            Script(
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            ),
            name='custom_script'
        )
    )
    # 4.2 Using an existing Script.
    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            another_custom_script,
            name='another_custom_script',
        )
    )

    # 4.3 Using an existing ScriptEndpoint.
    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint
    )

    # 5. Install custom_socket.
    custom_socket.install()  # this will make an API call and create a script;

It may take some time to set up the Socket, so you can check the status.
It's possible to check the custom Socket status::

    # Reload will refresh object using Syncano API.
    custom_socket.reload()
    print(custom_socket.status)
    # and
    print(custom_socket.status_info)

Updating the custom Socket
--------------------------

To update custom Socket, use::

    custom_socket = CustomSocket.please.get(name='my_custom_socket')

    # to remove endpoint/dependency
    
    custom_socket.remove_endpoint(endpoint_name='my_endpoint')
    custom_socket.remove_dependency(dependency_name='custom_script')

    # or to add a new endpoint/dependency:

    custom_socket.add_endpoint(new_endpoint)  # see above code for endpoint examples;
    custom_socket.add_dependency(new_dependency)  # see above code for dependency examples;

    # save changes on Syncano
    
    custom_socket.update()


Running custom Socket
-------------------------

To run a custom Socket use::

    # this will run `my_endpoint` - and call `custom_script` using GET method;
    result = custom_socket.run(method='GET', endpoint_name='my_endpoint')


Read all endpoints in a custom Socket
-----------------------------------

To get the all defined endpoints in a custom Socket run::

    endpoints = custom_socket.get_endpoints()

    for endpoint in endpoints:
        print(endpoint.name)
        print(endpoint.calls)

To run a particular endpoint::

    endpoint.run(method='GET')
    # or:
    endpoint.run(method='POST', data={'name': 'test_name'})

Data will be passed to the API call in the request body.

Read all endpoints
------------------

To get all endpoints that are defined in all custom Sockets::

    socket_endpoint_list = SocketEndpoint.get_all_endpoints()

Above code will return a list with SocketEndpoint objects. To run an endpoint, 
choose one endpoint first, e.g.:

    endpoint = socket_endpoint_list[0]

and now run it::

    endpoint.run(method='GET')
    # or:
    endpoint.run(method='POST', data={'custom_data': 1})

Custom Sockets endpoints
------------------------

Each custom socket requires defining at least one endpoint. This endpoint is defined by name and
a list of calls. Each call is defined by its name and a list of methods. `name` is used as an
identification for the dependency, eg. if `name` is equal to 'my_script' - the ScriptEndpoint with name 'my_script'
will be used (if it exists and Script source and passed runtime match) -- otherwise a new one will be created.
There's a special wildcard method: `methods=['*']` - this allows you to execute the provided custom Socket
with any request method (GET, POST, PATCH, etc.).

To add an endpoint to a chosen custom_socket use::

    my_endpoint = Endpoint(name='my_endpoint')  # no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    custom_socket.add_endpoint(my_endpoint)

Custom Socket dependency
------------------------

Each custom socket has a dependency -- meta information for an endpoint: which resource
should be used to return the API call results. These dependencies are bound to the endpoints call object.
Currently the only supported dependency is a Script.

**Using new Script**

::

    custom_socket.add_dependency(
        ScriptDependency(
            Script(
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            ),
            name='custom_script'
        )
    )


**Using defined Script**

::

    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            another_custom_script,
            name='another_custom_script'
        )
    )

**Using defined Script endpoint**

::

    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint
    )

You can overwrite the Script name in the following way::

    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint,
        name='custom_name'
    )

Custom Socket recheck
---------------------

The creation of a Socket can fail - this can happen, for example, when an endpoint name is already taken by another
custom Socket. To check the creation status use::

    print(custom_socket.status)
    print(custom_socket.status_info)

You can also re-check a Socket. This mean that all dependencies will be checked - if some of them are missing
(e.g. some were deleted by mistake), they will be created again. If the endpoints and dependencies do not meet
the criteria - an error will be returned in the status field.

Custom Socket - raw format
--------------------------

If you prefer raw JSON format for creating Sockets, the Python library allows you to do so::::

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

The disadvantage of this method is that the internal structure of the JSON file must be known by the developer.
