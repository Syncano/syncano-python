============
syncano
============


:Author: Piotr Kalmus

About
=====

Library for syncano.com api


Dependencies
============

gevent==1.0.1

Installation
============

::

  pip install syncano --pre

Examples
========


Creating, Modifing, Listing, Deleting Projects
----------------------------------------------

::

  with  SyncanoApi(instance_name, apikey) as syncano:

    project = syncano.project_new('test', message_id=1)
    project_id = project['data']['project']['id']
    syncano.project_update(project_id, 'test_2', message_id=2)
    print(syncano.project_get(message_id=3))
    syncano.project_delete(project_id)


or

::

   with  SyncanoApi(instance_name, apikey) as syncano:

    project = syncano.project.new('test', message_id=1)
    project_id = project['data']['project']['id']
    syncano.project.update(project_id, 'test_2', message_id=2)
    print(syncano.project.get(message_id=3))
    syncano.project.delete(project_id)



Subscribe and listen to notifications, and pings
------------------------------------------------

::

  with  SyncanoAsyncApi(instance_name, apikey) as syncano:
      syncano.subscription_subscribe_project(your_project_id)
      while True:
          message =  syncano.get_message(blocking=False)
          if message:
              print ('message', message)


Creating message callback, that is printing all messages from server
--------------------------------------------------------------------

::

    class PrintCallback(callbacks.JsonCallback):

        def process_message(self, received):
            print (received)

    with  SyncanoAsyncApi(instance_name, apikey, callback_handler=PrintCallback) as syncano:
      pass




Using ObjectCallback to get "object like" response with methods
---------------------------------------------------------------

::

    with SyncanoApi(instance_name, apikey, callback_handler=callbacks.ObjectCallback) as syncano:
        project = syncano.project.new(name)
        project.update(new_name)
        project.delete()



