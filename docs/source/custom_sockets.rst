.. _custom-sockets:

=========================
Custom Sockets in Syncano
=========================

``Syncano`` gives its users an ability to create Custom Sockets. What it means is that users can define 
a very specific endpoints in their Syncano application, and use them exactly like they would any other Syncano 
module (Classes, Scripts, etc), using standard API calls.
Currently, Custom Sockets allow only one dependency - Scripts. It means that under the hood,
each API call executes a Script, and result of this execution is returned as a result of the
API call.

Creating a custom socket
------------------------

To create a custom socket follow these steps::

    import syncano
    from syncano.models import CustomSocket, Endpoint, ScriptCall, ScriptDependency, RuntimeChoices
    from syncano.connection import Connection

    # 1. Initialize a custom socket.
    custom_socket = CustomSocket(name='my_custom_socket')  # this will create an object in place (do API call)

    # 2. Define endpoints.
    my_endpoint = Endpoint(name='my_endpoint')  # no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    # What happened here:
    # - We defined a new endpoint, that will be visible under `my_endpoint` name.
    # - You will be able to call this endpoint (execute attached `call`), 
    # by sending a reuqest, using any defined method to following API route:
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/my_endpoint/ 
    # - To get details on that endpoint, you need to send a GET request to following API route:
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/my_endpoint/
    #
    # Following example above - we defined two calls on our endpoint. 
    # First one means that using GET method will call the `custom_script` script,
    # and second one means that using POST method will call the `another_custom_script` script.
    # At the moment, only scripts are available as endpoint calls.
    #
    # As a general rule - to get endpoints details (but not call them), use following API route:
    # <host>://<api_version>/instances/<instance_name>/sockets/my_custom_socket/endpoints/<endpoint>/
    # and to run your endpoints (e.g. execute Script connected to them(, use following API route:
    # <host>://<api_version>/instances/<instance_name>/endpoints/sockets/<endpoint>/

    # 3. After creation of the endpoint, add it to your custom_socket.
    custom_socket.add_endpoint(my_endpoint)

    # 4. Define dependency.
    # 4.1 Using a new script - define a new source code.
    custom_socket.add_dependency(
        ScriptDependency(
            name='custom_script'
            script=Script(
                runtime_name=RuntimeChoices.PYTHON_V5_0,
                source='print("custom_script")'
            )
        )
    )
    # 4.2 Using an existing script.
    another_custom_script = Script.please.get(id=2)
    custom_socket.add_dependency(
        ScriptDependency(
            name='another_custom_script',
            script=another_custom_script
        )
    )

    # 4.3 Using an existing ScriptEndpoint.
    script_endpoint = ScriptEndpoint.please.get(name='script_endpoint_name')
    custom_socket.add_dependency(
        script_endpoint=script_endpoint
    )

    # 5. Publish custom_socket.
    custom_socket.publish()  # this will make an API call and create a script;

Sometimes, it's needed to set up the environment for the custom socket.
It's possible to check the custom socket status::

    # Reload will refresh object using Syncano API.
    custom_socket.reload()
    print(custom_socket.status)
    # and
    print(custom_socket.status_info)

Updating the custom socket
--------------------------

To update custom socket, use::

    custom_socket = CustomSocket.please.get(name='my_custom_socket')

    # to remove endpoint/dependency
    
    custom_socket.remove_endpoint(endpoint_name='my_endpoint')
    custom_socket.remove_dependency(dependency_name='custom_script')

    # or to add a new endpoint/dependency:

    custom_socket.add_endpoint(new_endpoint)  # see above code for endpoint examples;
    custom_socket.add_dependency(new_dependency)  # see above code for dependency examples;

    # save changes on Syncano
    
    custom_socket.update()


Running custom socket
-------------------------

To run a custom socket use::

    # this will run `my_endpoint` - and call `custom_script` (using GET method);
    result = custom_socket.run(method='GET', endpoint_name='my_endpoint')


Read all endpoints in a custom socket
-----------------------------------

To get the all defined endpoints in a custom socket run::

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

To get all endpoints that are defined in all custom sockets::

    socket_endpoint_list = SocketEndpoint.get_all_endpoints()

Above code will return a list with SocketEndpoint objects. To run an endpoint, 
choose one endpoint first, e.g.:

    endpoint = socket_endpoint_list[0]

and now run it::

    endpoint.run(method='GET')
    # or:
    endpoint.run(method='POST', data={'custom_data': 1})

Custom sockets endpoints
------------------------

Each custom socket requires a definition of at least one endpoint. This endpoint is defined by name and
a list of calls.  Each call is defined by its name and a list of methods. Name is used in identification for dependency, eg.
if it's equal to 'my_script' - the ScriptEndpoint with name 'my_script' will be used
(if it exists and Script source and passed runtime match) -- otherwise a new one will be created.
There's a special wildcard method: `methods=['*']` - it means that any request with
any method will be executed in this endpoint.

To add an endpoint to a chosen custom_socket use::

    my_endpoint = Endpoint(name='my_endpoint')  # no API call here
    my_endpoint.add_call(ScriptCall(name='custom_script'), methods=['GET'])
    my_endpoint.add_call(ScriptCall(name='another_custom_script'), methods=['POST'])

    custom_socket.add_endpoint(my_endpoint)

Custom socket dependency
------------------------

Each custom socket has a dependency -- meta information for an endpoint: which resource
should be used to return the API call results. These dependencies are bound to the endpoints call objects.
Currently the only supported dependency is a Script.

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

The creation of the socket can fail - this can happen, e.g. when an endpoint name is already taken by another
custom socket. To check the statuses use::

    print(custom_socket.status)
    print(custom_socket.status_info)

There is a possibility to re-check socket - this mean that if conditions are met - the socket endpoints and dependencies
will be checked - and if some of them are missing (e.g. some were deleted by mistake), they will be created again.
If the endpoints and dependencies do not meet the criteria - an error will be returned in the status field.

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

The disadvantage of this method is that internal structure of the JSON file must be known by developer.
