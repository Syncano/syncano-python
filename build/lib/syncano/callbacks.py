import logging
import sys

if sys.version_info[0] >= 3:
    unicode_types = (str,)
else:
    unicode_types = (str, unicode)

from syncano.exceptions import ApiException

logger = logging.getLogger('syncano.callbacks')


class JsonCallback(object):

    def __init__(self, owner, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
        self.owner = owner

    def process_message(self, received):
        ignored = getattr(self, 'ignored_types', [])
        message_type = received.get('type', 'error')
        if not self.owner.authorized and message_type == 'error':
            message_type='auth'
        if message_type in ('new', 'change', 'delete', 'message') :
            res = self.process_notification(received)
        else:
            res = getattr(self, 'process_' + message_type)(received)
        if message_type in ignored:
            return
        return res

    def process_ping(self, received):
        self.owner.last_ping = received['timestamp']
        return received

    def process_auth(self, received):
        result = received['result']
        self.owner.authorized = result == 'OK'
        if self.owner.authorized:
            self.owner.uuid = received['uuid']
        return received

    def process_callresponse(self, received):
        if received['result'] == 'OK':
            return received
        self.process_error(received['data'])

    @staticmethod
    def process_error(received):
        raise ApiException(received['error'])

    @staticmethod
    def process_notification(received):
        return received


class BaseResultObject(object):

    TAG = None

    def __init__(self, syncano_connection, result_object_dict, message_id=None):
            self.conn = syncano_connection
            self.message_id = message_id
            for key in result_object_dict:
                if isinstance(result_object_dict[key], dict):
                    setattr(self, key, BaseResultObject(None, result_object_dict[key]))
                elif isinstance(result_object_dict[key], list):
                    r = result_object_dict[key]
                    temp = [BaseResultObject(None, x) if isinstance(x, dict) else x for x in r]
                    setattr(self, key, temp)
                else:
                    setattr(self, key, result_object_dict[key])

    def update_attrs(self, **kwargs):
        for k in kwargs:
            if kwargs[k]:
                if isinstance(kwargs[k], dict):
                    setattr(self, k, BaseResultObject(None, kwargs[k]))
                else:
                    setattr(self, k, kwargs[k])

    def get(self, key, default=None):
        return getattr(self, key, default)


def check_attributes_decorator(*fields_list):
    def decorator(f):

        def format_field(obj):
            if isinstance(obj, list):
                return ' or '.join(obj)
            return obj

        def wrapper(self, *args, **kwargs):
            failed = []
            for field in fields_list:
                if isinstance(field, list):
                    if not any([getattr(self, x, 0) for x in field]):
                        failed.append(field)
                else:
                    if not getattr(self, field, 0):
                        failed.append(field)
            if failed:
                assert False, """Some attributes: {0!s} are missing use synchronized mode(SyncanoApi)
                or use update_args to add missing attributes""".format(', '.join(map(format_field, failed)))
            return f(self, *args, **kwargs)
        return wrapper
    return decorator


class AdminObject(BaseResultObject):

    TAG = 'admin'

    def delete(self):
        self.conn.admin.delete(admin_id=self.id)

    def update(self, role_id):
        self.conn.admin.update(admin_id=self.id, role_id=role_id)
        self.update_attrs(role_id=role_id)


class ApikeyObject(BaseResultObject):

    TAG = 'apikey'

    def delete(self):
        self.conn.apikey.delete(self.id)

    def update_description(self, description):
        self.conn.apikey.update_description(self.id, description=description)
        self.desription = description

class RoleObject(BaseResultObject):

    TAG = 'role'

class ProjectObject(BaseResultObject):

    TAG = 'project'

    def delete(self):
        self.conn.project.delete(self.id)

    def update(self, name):
        self.conn.project.update(self.id, name)
        self.name = name


class ConnectionObject(BaseResultObject):

    TAG = 'connection'

    def update(self, state=None, name=None):
        self.conn.connection.update(self.uuid, api_client_id=self.api_client_id, state=state, name=name)
        self.update_attrs(state=state, name=name)


class CollectionObject(BaseResultObject):

    TAG = 'collection'

    @check_attributes_decorator('project_id', 'id')
    def activate(self):
        self.conn.collection.activate(self.project_id, self.id)

    @check_attributes_decorator('project_id', 'id')
    def deactivate(self):
        self.conn.collection.deactivate(self.project_id, self.id)

    @check_attributes_decorator('project_id', 'id')
    def update(self, name=None, collection_key=None):
        self.conn.collection_update(self.project_id, collection_id=self.id,
                                    collection_key=collection_key, name=name)
        self.update_attrs(name=name, key=collection_key)

    @check_attributes_decorator('project_id', 'id')
    def delete(self):
        self.conn.collection.delete(self.project_id, self.id)

    @check_attributes_decorator('project_id', 'id')
    def add_tag(self, tags, weight=1, remove_other=False):
        if isinstance(tags, unicode_types):
            tags = [tags]
        self.conn.collection.add_tag(self.project_id, collection_id=self.id,
                                     tags=tags, weight=weight, remove_other=remove_other)
        new_tags = {t: weight for t in tags}
        if remove_other:
            self.tags = BaseResultObject(None, new_tags)
        else:
            self.tags.update_attrs(**new_tags)

    @check_attributes_decorator('project_id', 'id')
    def delete_tag(self, tags):
        if isinstance(tags, unicode_types):
            tags = [tags]
        self.conn.collection.delete_tag(self.project_id, self.id, tags=tags)
        for t in tags:
            delattr(self.tags, t)


class FolderObject(BaseResultObject):

    TAG = 'folder'

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'name')
    def update(self, new_name, source_id=None):
        self.conn.folder.update(self.project_id, collection_id=self.collection_id,
                                collection_key=self.collection_key,
                                name=self.name, new_name=new_name, source_id=source_id)
        self.update_attrs(name=new_name, source_id=source_id)

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'name')
    def delete(self):
        self.conn.folder.delete(self.project_id, collection_id=self.collection_id,
                                collection_key=self.collection_key, name=self.name)


class DataObject(BaseResultObject):

    TAG = 'data'

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'id')
    def delete(self):
        self.conn.data.delete(self.project_id, collection_id=self.collection_id, collection_key=self.collection_key,
                              data_ids=[self.id])

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'id')
    def remove_parent(self, parent_id=None):
        self.conn.data.remove_parent(self.project_id, self.id, collection_id=self.collection_id,
                                     collection_key=self.collection_key, parent_id=parent_id)

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'id')
    def add_parent(self, parent_id, remove_other=False):
        self.conn.data.add_parent(self.project_id, self.id, collection_id=self.collection_id,
                                  collection_key=self.collection_key, parent_id=parent_id, remove_other=remove_other)

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'id')
    def move(self, new_folder=None, new_state=None):
        self.conn.data.move(self.project_id, collection_id=self.collection_id, collection_key=self.collection_key,
                            data_ids=[self.id], new_folder=new_folder, new_state=new_state)

    @check_attributes_decorator('project_id', ['collection_id', 'collection_key'], 'id')
    def update(self, update_method='replace', user_name=None, source_url=None, title=None,
               text=None, link=None, image=None, image_url=None, folder=None, state=None, parent_id=None):
        res = self.conn.data.update(self.project_id, collection_id=self.collection_id, update_method=update_method,
                                    collection_key=self.collection_key, data_id=self.id,
                                    data_key=getattr(self, 'key', None), user_name=user_name, source_url=source_url,
                                    title=title, text=text, link=link, image=image, image_url=image_url,
                                    folder=folder, state=state, parent_id=parent_id)
        self.__init__(self.conn, res.__dict__)


class UserObject(BaseResultObject):

    TAG = 'user'

    def update(self, user_name=None, nick=None, avatar=None):
        self.conn.user.update(user_id=self.id, user_name=user_name, nick=nick, avatar=avatar)
        self.update_attrs(user_name=user_name, nick=nick, avatar=avatar)

    def delete(self):
        self.conn.user_delete(self.id)


class SubscriptionObject(BaseResultObject):

    TAG = 'subscription'

    def unsubscribe_project(self):
        if self.type == 'Project':
            self.conn.subscription.unsubscribe_project(self.id)

    def unsubscribe_collection(self, project_id):
        if self.type == 'Collection':
            self.conn.subscription.unsubscribe_collection(project_id, self.id)


class ObjectIterResult(object):

    def __init__(self, items, message_id=None):
        self.items = items
        self.message_id = message_id

    def get(self, key, default):
        return getattr(self, key, default)

    def set_if_not_exist(self, obj, key):
        obj_iter_value = getattr(self, key, None)
        if not getattr(obj, key, False):
            setattr(obj, key, obj_iter_value)

    def __iter__(self):
        for i in self.items:
            for k in ('project_id', 'collection_id', 'collection_key'):
                self.set_if_not_exist(i, k)
            yield i

    def __len__(self):
        return len(self.items)

    def __getitem__(self, index):
        return self.items[index]


class ObjectCallback(JsonCallback):

    @staticmethod
    def match_result_to_class(result):
        for clss in [AdminObject, ProjectObject, CollectionObject, FolderObject, ApikeyObject,
                     DataObject, UserObject, SubscriptionObject, RoleObject, ConnectionObject]:
            if clss.TAG in result['data']:
                return clss
        else:
            return BaseResultObject

    def process_callresponse(self, received):
        if received['result'] == 'OK':
            message_id = received.get('message_id', None)
            cls = self.match_result_to_class(received)
            if cls.TAG:
                result = received['data'][cls.TAG]
                if isinstance(result, list):
                    return ObjectIterResult([cls(self.syncano, r, message_id) for r in result], message_id)
                else:
                    return cls(self.syncano, result, message_id)
            else:
                return cls(self.syncano, received['data'], message_id)
        else:
            return super(ObjectCallback, self).process_callresponse(received)


