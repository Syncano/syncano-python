# -*- coding: utf-8 -*-


class RenameMixin(object):

    def rename(self, new_name):
        """
        A method for changing the name of the object; Corresponds to the Mixin in CORE;

        :param new_name: the new name for the object;
        :return: a populated object;
        """
        rename_path = self.links.rename
        data = {'new_name': new_name}
        connection = self._get_connection()
        response = connection.request('POST', rename_path, data=data)
        self.to_python(response)
        return self
