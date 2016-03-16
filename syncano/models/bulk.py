# -*- coding: utf-8 -*-
from abc import ABCMeta, abstractmethod

import six
from syncano.exceptions import SyncanoValidationError, SyncanoValueError


class BaseBulkCreate(six.with_metaclass(ABCMeta)):
    """
    Helper class for making bulk create;

    Usage:
        instances = ObjectBulkCreate(objects, manager).process()
    """
    MAX_BATCH_SIZE = 50

    @abstractmethod
    def __init__(self, objects, manager):
        self.objects = objects
        self.manager = manager
        self.response = None
        self.validated = False

    def validate(self):
        if len(self.objects) > self.MAX_BATCH_SIZE:
            raise SyncanoValueError('Only 50 objects can be created at once.')

    def make_batch_request(self):
        if not self.validated:
            raise SyncanoValueError('Bulk create not validated')
        self.response = self.manager.batch(*[o.save() for o in self.objects])

    def update_response(self, content_reponse):
        content_reponse.update(self.manager.properties)

    def process(self):
        self.validate()
        self.make_batch_request()
        return self.response


class ObjectBulkCreate(BaseBulkCreate):

    def __init__(self, objects, manager):
        super(ObjectBulkCreate, self).__init__(objects, manager)

    def validate(self):
        super(ObjectBulkCreate, self).validate()

        class_names = []
        instance_names = []
        # mark objects as lazy & make some check btw;
        for o in self.objects:
            class_names.append(o.class_name)
            instance_names.append(o.instance_name)
            o.mark_for_batch()

        if len(set(class_names)) != 1:
            raise SyncanoValidationError('Bulk create can handle only objects of the same type.')

        if len(set(instance_names)) != 1:
            raise SyncanoValidationError('Bulk create can handle only one instance.')
        self.validated = True

    def update_response(self, content_reponse):
        super(ObjectBulkCreate, self).update_response(content_reponse)
        content_reponse.update(
            {
                'class_name': self.objects[0].class_name,
                'instance_name': self.objects[0].instance_name
            }
        )


class ModelBulkCreate(BaseBulkCreate):

    def __init__(self, objects, manager):
        super(ModelBulkCreate, self).__init__(objects, manager)

    def validate(self):
        super(ModelBulkCreate, self).validate()

        class_names = []
        # mark objects as lazy & make some check btw;
        for o in self.objects:
            class_names.append(type(o))
            o.mark_for_batch()

        if len(set(class_names)) != 1:
            raise SyncanoValidationError('Bulk create can handle only objects of the same type.')

        self.validated = True
