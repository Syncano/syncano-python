import asyncore
import socket
import gevent.ssl
import ssl
import time
import json
import logging

from syncano.exceptions import AuthException, ConnectionLost
from syncano.callbacks import JsonCallback, ObjectCallback


HOST = 'api.syncano.com'
PORT = 8200

logger = logging.getLogger('syncano.client')


class SyncanoClient(asyncore.dispatcher):

    def __init__(self, instance, api_key, host=None, port=None, callback_handler=JsonCallback,
                 name="SYNCANO_CLIENT", *args, **kwargs):

        asyncore.dispatcher.__init__(self)
        self.callback = callback_handler(self, *args, **kwargs) if callback_handler else None
        self.instance = instance
        self.api_key = api_key
        self.name = name
        self.buffer = ''.encode('utf-8')
        self.results = []
        self.prepare_auth()
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host or HOST, port or PORT))
        self.authorized = None
        self.temp_received = ''

    def write_to_buffer(self, data):
        data = json.dumps(data) + '\n'
        self.buffer = self.buffer + data.encode('utf-8')

    def clean_buffer(self, offset):
        self.buffer = self.buffer[offset:]

    def prepare_auth(self):
        auth = dict(instance=self.instance, api_key=self.api_key)
        self.write_to_buffer(auth)

    def handle_connect(self):
        self.socket = gevent.ssl.wrap_socket(self.socket, do_handshake_on_connect=False)
        while True:
            try:
                self.socket.do_handshake()
            except ssl.SSLError as err:
                continue
            else:
                break

    def handle_close(self):
        self.close()

    def handle_read(self):
        last_received = self.recv(4048)
        received = '' + last_received
        while len(last_received) == 4048:
            last_received = self.recv(4048)
            received = received + last_received
        received = received.decode('utf-8')
        try:
            self.temp_received = self.temp_received + received
            received = json.loads(self.temp_received)
            self.temp_received = ''
        except ValueError:
            return

        logger.info(u'%s - received from server %s', self.name, received)
        if self.callback:
            res = self.callback.process_message(received)
            if res is not None:
                self.results.append(res)
        else:
            self.results.append(received)

    def writable(self):
        return self.buffer

    def readable(self):
        return True

    def handle_write(self):
        logger.info(u'%s - sent to server %s', self.name, self.buffer)
        sent = self.send(self.buffer)
        self.clean_buffer(sent)

    def handle_error(self):
        raise


class BaseMixin(object):

    @staticmethod
    def get_standard_params(method, message_id):
        attrs=dict(method=method, params=dict())
        if message_id:
            attrs['message_id'] = message_id
        return attrs

    def standard_method(self, method, message_id):
        attrs = self.get_standard_params(method, message_id)
        self.api_call(**attrs)

    def update_params(self, attrs, name, value):
        if value:
            attrs['params'][name] = value


class AdminMixin(BaseMixin):

    def admin_new(self, admin_email, role_id, message, message_id=None):
        attrs = self.get_standard_params('admin.new', message_id)
        attrs['params']['admin_email'] = admin_email
        attrs['params']['role_id'] = role_id
        attrs['params']['message'] = message
        self.api_call(**attrs)

    def admin_get(self, message_id=None):
        self.standard_method('admin.get', message_id)

    def admin_get_one(self, admin_id=None, admin_email=None, message_id=None):
        assert admin_id or admin_email, u"admin_id or admin_email_required"
        attrs = self.get_standard_params('admin.get_one', message_id)
        self.update_params(attrs, 'admin_id', admin_id)
        self.update_params(attrs, 'admin_email', admin_email)
        self.api_call(**attrs)

    def admin_update(self, admin_id=None, admin_email=None, role_id=None, message_id=None):
        assert admin_id or admin_email, u"admin_id or admin_email_required"
        assert role_id, u"admin_role required"
        attrs = self.get_standard_params('admin.update', message_id)
        self.update_params(attrs, 'admin_id', admin_id)
        self.update_params(attrs, 'admin_email', admin_email)
        self.update_params(attrs, 'role_id', role_id)
        self.api_call(**attrs)

    def admin_delete(self, admin_id=None, admin_email=None, message_id=None):
        assert admin_id or admin_email, u"admin_id or admin_email_required"
        attrs = self.get_standard_params('admin.delete', message_id)
        self.update_params(attrs, 'admin_id', admin_id)
        self.update_params(attrs, 'admin_email', admin_email)
        self.api_call(**attrs)


class ApikeyMixin(BaseMixin):

    def apikey_new(self, role_id, description, message_id=None):
        attrs = self.get_standard_params('apikey.new', message_id)
        attrs['params']['role_id'] = role_id
        attrs['params']['description'] = description
        self.api_call(**attrs)

    def apikey_get(self, message_id=None):
        self.standard_method('apikey.get', message_id)

    def apikey_get_one(self, api_client_id=None, message_id=None):
        attrs = self.get_standard_params('apikey.get_one', message_id)
        self.update_params(attrs, 'api_client_id', api_client_id)
        self.api_call(**attrs)

    def apikey_update_description(self, api_client_id=None, description=None, message_id=None):
        assert description is not None, "decription is required"
        attrs = self.get_standard_params('apikey.update_description', message_id)
        attrs['params']['description'] = description
        attrs['params']['api_client_id'] = api_client_id
        self.api_call(**attrs)

    def apikey_delete(self, api_client_id, message_id=None):
        attrs = self.get_standard_params('apikey.delete', message_id)
        attrs['params']['api_client_id'] = api_client_id
        self.api_call(**attrs)


class RoleMixin(BaseMixin):

    def role_get(self, message_id):
        self.standard_method('role.get', message_id)


class ConnectionMixin(BaseMixin):

    def connection_get(self, api_client_id=None, name=None, since_id=None, limit=None, message_id=None):
        attrs = self.get_standard_params('connection.get', message_id)
        self.update_params(attrs, 'api_client_id', api_client_id)
        self.update_params(attrs, 'name', name)
        self.update_params(attrs, 'since_id', since_id)
        self.update_params(attrs, 'limit', limit)
        self.api_call(**attrs)

    def connection_update(self, uuid, state=None, name=None, api_client_id=None, message_id=None):
        attrs = self.get_standard_params('connection.update', message_id)
        attrs['params']['uuid'] = uuid
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'name', name)
        self.update_params(attrs, 'api_client_id', api_client_id)
        self.api_call(**attrs)


class ProjectMixin(BaseMixin):

    def project_new(self, name, message_id=None):
        attrs = self.get_standard_params('project.new', message_id)
        attrs['params']['name'] = name
        self.api_call(**attrs)

    def project_get(self, message_id=None):
        self.standard_method('project.get', message_id)

    def project_get_one(self, project_id, message_id=None):
        attrs = self.get_standard_params('project.get_one', message_id)
        attrs['params']['project_id'] = project_id
        self.api_call(**attrs)

    def project_update(self, project_id, name, message_id=None):
        attrs = self.get_standard_params('project.update', message_id)
        attrs['params']['name'] = name
        attrs['params']['project_id'] = project_id
        self.api_call(**attrs)

    def project_delete(self, project_id, message_id=None):
        attrs = self.get_standard_params('project.delete', message_id)
        attrs['params']['project_id'] = project_id
        self.api_call(**attrs)


class CollectionMixin(BaseMixin):

    def collection_new(self, project_id, name, key, message_id=None):
        attrs = self.get_standard_params('collection.new', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['name'] = name
        attrs['params']['key'] = key
        self.api_call(**attrs)

    def collection_get(self, project_id, status='all', with_tags=None, message_id=None):
        attrs = self.get_standard_params('collection.get', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'status', status)
        self.update_params(attrs, 'with_tags', with_tags)
        self.api_call(**attrs)

    def collection_get_one(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.get_one', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def collection_activate(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.activate', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def collection_deactivate(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.deactivate', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def collection_update(self, project_id, collection_id, name=None, collection_key=None, message_id=None):
        attrs = self.get_standard_params('collection.update', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['collection_id'] = collection_id
        self.update_params(attrs, 'name', name)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def collection_delete(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.delete', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def collection_add_tag(self, project_id, collection_id=None, collection_key=None,
                           tags=[], weight=1, remove_other=False, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.add_tag', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'tags', tags)
        self.update_params(attrs, 'weight', weight)
        self.update_params(attrs, 'remove_other', remove_other)
        self.api_call(**attrs)

    def collection_delete_tag(self, project_id, collection_id=None, collection_key=None, tags=[], message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('collection.delete_tag', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'tags', tags)
        self.api_call(**attrs)


class FolderMixin(BaseMixin):

    def folder_new(self, project_id, name, collection_id=None, collection_key=None, source_id=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('folder.new', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['name'] = name
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'source_id', source_id)
        self.api_call(**attrs)

    def folder_get(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('folder.get', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def folder_get_one(self, project_id, folder_name, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('folder.get_one', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['folder_name'] = folder_name
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def folder_update(self, project_id, name, collection_id=None, collection_key=None,
                      new_name=None, source_id=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('folder.update', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['name'] = name
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'new_name', new_name)
        self.update_params(attrs, 'source_id', source_id)
        self.api_call(**attrs)

    def folder_delete(self, project_id, name, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('folder.delete', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['name'] = name
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)


class DataObjectMixin(BaseMixin):

    def data_new(self, project_id, collection_id=None, collection_key=None,
                 user_name=None, source_url=None, title=None, text=None, link=None, image=None,
                 image_url=None, folder=None, state='Pending', data_key=None,
                 parent_id=None, message_id=None, **kwargs):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.new', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'user_name', user_name)
        self.update_params(attrs, 'source_url', source_url)
        self.update_params(attrs, 'title', title)
        self.update_params(attrs, 'text', text)
        self.update_params(attrs, 'link', link)
        self.update_params(attrs, 'image', image)
        self.update_params(attrs, 'image_url', image_url)
        self.update_params(attrs, 'folder', folder)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'parent_id', parent_id)
        self.update_params(attrs, 'data_key', data_key)
        attrs['params'].update(kwargs)
        self.api_call(**attrs)

    def data_update(self, project_id, collection_id=None, collection_key=None, data_id=None, data_key=None,
                    update_method='replace', user_name=None, source_url=None, title=None, text=None,
                    link=None, image=None, image_url=None, folder=None, state=None, parent_id=None,
                    message_id=None, **kwargs):
        assert collection_id or collection_key, "collection_id or collection_key required"
        assert data_id or data_key, "data_id or data_key required"
        attrs = self.get_standard_params('data.update', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'data_id', data_id)
        self.update_params(attrs, 'data_key', data_key)
        self.update_params(attrs, 'update_method', update_method)
        self.update_params(attrs, 'user_name', user_name)
        self.update_params(attrs, 'source_url', source_url)
        self.update_params(attrs, 'title', title)
        self.update_params(attrs, 'text', text)
        self.update_params(attrs, 'link', link)
        self.update_params(attrs, 'image', image)
        self.update_params(attrs, 'image_url', image_url)
        self.update_params(attrs, 'folder', folder)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'parent_id', parent_id)
        attrs['params'].update(kwargs)
        self.api_call(**attrs)

    def data_get(self, project_id, collection_id=None, collection_key=None, state='All', folders=[], since_id=None,
                 max_id=None, since_time=None, limit=100, order='ASC', order_by='created_at', filter=None,
                 include_children=True, depth=None, children_limit=100, parent_ids=[], by_user=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.get', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'since_id', since_id)
        self.update_params(attrs, 'max_id', max_id)
        self.update_params(attrs, 'since_time', since_time)
        self.update_params(attrs, 'limit', limit)
        self.update_params(attrs, 'order', order)
        self.update_params(attrs, 'order_by', order_by)
        self.update_params(attrs, 'filter', filter)
        self.update_params(attrs, 'include_children', include_children)
        self.update_params(attrs, 'depth', depth)
        self.update_params(attrs, 'children_limit', children_limit)
        self.update_params(attrs, 'parent_ids', parent_ids)
        self.update_params(attrs, 'by_user', by_user)
        self.api_call(**attrs)

    def data_get_one(self, project_id, collection_id=None, collection_key=None, data_id=None,
                     data_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.get_one', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'data_id', data_id)
        self.update_params(attrs, 'data_key', data_key)
        self.api_call(**attrs)

    def data_move(self, project_id, collection_id=None, collection_key=None, data_ids=[], state='All', folders=[],
                  filter=None, by_user=None, limit=100, new_folder=None, new_state=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.move', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'data_ids', data_ids)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'filter', filter)
        self.update_params(attrs, 'by_user', by_user)
        self.update_params(attrs, 'limit', limit)
        self.update_params(attrs, 'new_folder', new_folder)
        self.update_params(attrs, 'new_state', new_state)
        self.api_call(**attrs)

    def data_copy(self, project_id, data_ids, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.copy', message_id)
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        attrs['params']['project_id'] = project_id
        attrs['params']['data_ids'] = data_ids
        self.api_call(**attrs)

    def data_add_parent(self, project_id, data_id, collection_id=None, collection_key=None,
                        parent_id=None, remove_other=False, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.add_parent', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['data_id'] = data_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'parent_id', parent_id)
        self.update_params(attrs, 'remove_other', remove_other)
        self.api_call(**attrs)

    def data_remove_parent(self, project_id, data_id, collection_id=None, collection_key=None,
                           parent_id=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.remove_parent', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['data_id'] = data_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'parent_id', parent_id)
        self.api_call(**attrs)

    def data_add_child(self, project_id, data_id, collection_id=None, collection_key=None,
                       child_id=None, remove_other=False, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.add_child', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['data_id'] = data_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'child_id', child_id)
        self.update_params(attrs, 'remove_other', remove_other)
        self.api_call(**attrs)

    def data_remove_child(self, project_id, data_id, collection_id=None, collection_key=None,
                          child_id=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.remove_child', message_id)
        attrs['params']['project_id'] = project_id
        attrs['params']['data_id'] = data_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'child_id', child_id)
        self.api_call(**attrs)

    def data_delete(self, project_id, collection_id=None, collection_key=None, data_ids=[],
                    state='All', folders=None, filter=None, by_user=None, limit=100, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.delete', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'data_ids', data_ids)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'filter', filter)
        self.update_params(attrs, 'by_user', by_user)
        self.update_params(attrs, 'limit', limit)
        self.api_call(**attrs)

    def data_count(self, project_id, collection_id=None, collection_key=None, state='All', folders=None,
                   filter=None, by_user=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('data.count', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'filter', filter)
        self.update_params(attrs, 'by_user', by_user)
        self.api_call(**attrs)


class UserMixin(BaseMixin):

    def user_new(self, user_name, nick=None, avatar=None, message_id=None):
        attrs = self.get_standard_params('user.new', message_id)
        attrs['params']['user_name'] = user_name
        self.update_params(attrs, 'nick', nick)
        self.update_params(attrs, 'avatar', avatar)
        self.api_call(**attrs)

    def user_get_all(self, since_id=None, limit=100, message_id=None):
        attrs = self.get_standard_params('user.get_all', message_id)
        self.update_params(attrs, 'since_id', since_id)
        self.update_params(attrs, 'limit', limit)
        self.api_call(**attrs)

    def user_get(self, project_id, collection_id=None, collection_key=None,
                 state='All', folders=None, filter=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('user.get', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'filter', filter)
        self.api_call(**attrs)

    def user_get_one(self, user_id=None, user_name=None, message_id=None):
        assert user_id or user_name, "user_id or user_name required"
        attrs = self.get_standard_params('user.get_one', message_id)
        self.update_params(attrs, 'user_id', user_id)
        self.update_params(attrs, 'user_name', user_name)
        self.api_call(**attrs)

    def user_update(self, user_id=None, user_name=None, nick=None, avatar=None, message_id=None):
        assert user_id or user_name, "user_id or user_name required"
        attrs = self.get_standard_params('user.update', message_id)
        self.update_params(attrs, 'user_id', user_id)
        self.update_params(attrs, 'user_name', user_name)
        self.update_params(attrs, 'nick', nick)
        self.update_params(attrs, 'avatar', avatar)
        self.api_call(**attrs)

    def user_count(self, project_id=None, collection_id=None, collection_key=None,
                   state='All', folders=None, filter=None, message_id=None):
        attrs = self.get_standard_params('user.count', message_id)
        self.update_params(attrs, 'project_id', project_id)
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.update_params(attrs, 'state', state)
        self.update_params(attrs, 'folders', folders)
        self.update_params(attrs, 'filter', filter)
        self.api_call(**attrs)

    def user_delete(self, user_id=None, user_name=None, message_id=None):
        assert user_id or user_name, "user_id or user_name required"
        attrs = self.get_standard_params('user.delete', message_id)
        self.update_params(attrs, 'user_id', user_id)
        self.update_params(attrs, 'user_name', user_name)
        self.api_call(**attrs)


class NotificationMixin(BaseMixin):

    def notification_send(self, uuid=None, api_client_id=None, message_id=None, **kwargs):
        attrs = self.get_standard_params('notification.send', message_id)
        self.update_params(attrs, 'uuid', uuid)
        self.update_params(attrs, 'api_client_id', api_client_id)
        attrs['params'].update(kwargs)
        self.api_call(**attrs)

    def notification_get_history(self, api_client_id=None, client_login=None, since_id=None,
                                 since_time=None, limit=100, order=None, message_id=None):
        attrs = self.get_standard_params('notification.get_history', message_id)
        self.update_params(attrs, 'api_client_id', api_client_id)
        self.update_params(attrs, 'client_login', client_login)
        self.update_params(attrs, 'since_id', since_id)
        self.update_params(attrs, 'since_time', since_time)
        self.update_params(attrs, 'limit', limit)
        self.update_params(attrs, 'order', order)
        self.api_call(**attrs)


class SubscriptionMixin(BaseMixin):

    def subscription_subscribe_project(self, project_id, message_id=None):
        attrs = self.get_standard_params('subscription.subscribe_project', message_id)
        attrs['params']['project_id'] = project_id
        self.api_call(**attrs)

    def subscription_unsubscribe_project(self, project_id, message_id=None):
        attrs = self.get_standard_params('subscription.unsubscribe_project', message_id)
        attrs['params']['project_id'] = project_id
        self.api_call(**attrs)

    def subscription_subscribe_collection(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('subscription.subscribe_collection', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def subscription_unsubscribe_collection(self, project_id, collection_id=None, collection_key=None, message_id=None):
        assert collection_id or collection_key, "collection_id or collection_key required"
        attrs = self.get_standard_params('subscription.unsubscribe_collection', message_id)
        attrs['params']['project_id'] = project_id
        self.update_params(attrs, 'collection_id', collection_id)
        self.update_params(attrs, 'collection_key', collection_key)
        self.api_call(**attrs)

    def subscription_get(self, api_client_id=None, client_login=None, message_id=None):
        attrs = self.get_standard_params('subscription.get', message_id)
        self.update_params(self, 'api_client_id', api_client_id)
        self.update_params(self, 'client_login', client_login)
        self.api_call(**attrs)


class SyncanoAsyncApi(AdminMixin, ApikeyMixin, RoleMixin, ProjectMixin, CollectionMixin, FolderMixin,
                      UserMixin, DataObjectMixin, NotificationMixin, SubscriptionMixin, ConnectionMixin):

    def __init__(self, instance, api_key, host=None, port=None, timeout=1, **kwargs):
        self.cli = SyncanoClient(instance, api_key, host=host, port=port, syncano=self, **kwargs)
        self.timeout = timeout
        self.cached_prefix = ''
        while self.cli.authorized is None:
            self.get_message(blocking=False)
            time.sleep(timeout)
        if not self.cli.authorized:
            raise AuthException

    def get_message(self, blocking=True, message_id=None):
        if message_id:
            for i, r in enumerate(self.cli.results):
                if r.get('message_id', None) == message_id:
                    return self.cli.results.pop(i)
        else:
            if self.cli.results:
                return self.cli.results.pop(0)
        while asyncore.socket_map:
            asyncore.loop(timeout=1, count=1)
            if message_id:
                for i, r in enumerate(self.cli.results):
                    if r.get('message_id', None) == message_id:
                        return self.cli.results.pop(i)
            else:
                if self.cli.results:
                    return self.cli.results.pop(0)
            if not blocking:
                return
        raise ConnectionLost

    def send_message(self, message):
        self.cli.write_to_buffer(message)

    def close(self):
        self.cli.handle_close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __getattribute__(self, item):
        for prefix in ['admin_', 'apikey_', 'role_', 'folder_', 'project_', 'collection_',
                       'data_', 'notification_', 'subscription_', 'user_', 'connection_']:
            if not item.startswith(prefix) and item.startswith(prefix[:-1]):
                self.cached_prefix = prefix
                return self
            elif item != 'cached_prefix':
                temp_prefix = self.cached_prefix
                self.cached_prefix = ''
                if temp_prefix:
                    return self.__getattribute__(temp_prefix + item)
        return super(SyncanoAsyncApi, self).__getattribute__(item)

    def api_call(self, **kwargs):
        data = {'type': 'call'}
        data.update(kwargs)
        self.send_message(data)


def format_result(f, instance, message_id, args, kwargs):
    r = instance.get_message(blocking=True, message_id=message_id)
    if isinstance(instance.cli.callback, ObjectCallback):

        fname = f.__name__
        if fname.startswith('collection_'):
            r.project_id = args[0]
        if fname.startswith('folder_') or fname.startswith('data_'):
            params_offset = 0
            if fname in ['folder_new', 'folder_update', 'folder_get_one', 'data_remove_child',
                         'data_remove_parent', 'data_add_child', 'data_add_parent', 'data_copy']:
                params_offset = 1
            r.project_id = args[0]
            if 'collection_id' in kwargs:
                r.collection_id = kwargs['collection_id']
            else:
                try:
                    r.collection_id = int(args[1 + params_offset])
                except (TypeError, IndexError):
                    r.collection_id = None
                    params_offset -= 1
            if 'collection_key' in kwargs:
                r.collection_key = kwargs['collection_key']
            elif len(args) > 2 + params_offset:
                r.collection_key = args[2 + params_offset]
            else:
                r.collection_key = None
    return r


def api_result_decorator(f, instance):
    def wrapper(*args, **kwargs):
        message_id = kwargs.pop('message_id', str(int(time.time()*10**4)))
        kwargs['message_id'] = message_id
        f(*args, **kwargs)
        return format_result(f, instance, message_id, args, kwargs)
    return wrapper


class SyncanoApi(SyncanoAsyncApi):

    def __getattribute__(self, item):
        for prefix in ['admin_', 'apikey_', 'role_', 'connection_', 'folder_', 'project_', 'collection_',
                       'data_', 'notification_', 'subscription_', 'user_']:
            if item.startswith(prefix):
                return api_result_decorator(super(SyncanoApi, self).__getattribute__(item), self)
        return super(SyncanoApi, self).__getattribute__(item)