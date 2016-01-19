# -*- coding: utf-8 -*-
from syncano.exceptions import SyncanoRequestError
from syncano.models import ResponseTemplate
from tests.integration_test import InstanceMixin, IntegrationTest


class ManagerBatchTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ManagerBatchTest, cls).setUpClass()
        cls.to_delete = cls.instance.templates.create(name='to_delete', content="<br/>",
                                                      content_type='text/html', context={'one': 1})
        cls.for_update = cls.instance.templates.create(name='to_update', content="<br/>",
                                                       content_type='text/html', context={'one': 1})

    def test_retrieve_api(self):
        template = ResponseTemplate.please.get('to_update')
        self.assertTrue(isinstance(template, ResponseTemplate))
        self.assertTrue(ResponseTemplate.name)
        self.assertTrue(ResponseTemplate.content)
        self.assertTrue(ResponseTemplate.content_type)
        self.assertTrue(ResponseTemplate.context)

    def test_create_api(self):
        template = ResponseTemplate.please.create(name='just_created', content='<div></div>', content_type='text/html',
                                                  context={'two': 2})
        self.assertTrue(isinstance(template, ResponseTemplate))

    def test_delete_api(self):
        ResponseTemplate.please.get('to_delete').delete()
        with self.assertRaises(SyncanoRequestError):
            ResponseTemplate.please.get('to_delete')

    def test_update_api(self):
        self.for_update.content = "<div>Hello!</div>"
        self.for_update.save()

        template = ResponseTemplate.please.get(name='to_udpate')
        self.assertEqual(template.content, "<div>Hello!</div>")

    def test_render_api(self):
        render_template = self.instance.templates.create(name='to_update',
                                                         content="{% for o in objects}<li>o</li>{% endfor %}",
                                                         content_type='text/html', context={'objects': [1, 2]})

        rendered = render_template.render()
        self.assertEqual(rendered, '<li>1</li><li>2</li>')

        rendered = render_template.render(context={'objects': [3]})
        self.assertEqual(rendered, '<li>3</li>')
