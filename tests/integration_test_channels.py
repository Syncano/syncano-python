import time
from threading import Thread

from syncano.models import Channel, ResponseTemplate
from tests.integration_test import InstanceMixin, IntegrationTest


class ChannelTest(InstanceMixin, IntegrationTest):

    template_content = 'Template content.'
    template_context = {'foo': 'bar'}
    response = None

    def test_template_poll(self):
        ResponseTemplate(
            name='test_template',
            content=self.template_content,
            content_type='text/plain',
            context=self.template_context
        ).save()
        c = Channel(name='test-channel', custom_publish=True).save()

        self.response = None

        def poll():
            def callback(data):
                self.response = data
            c.poll(callback=callback, timeout=40, template='test_template')

        t = Thread(target=poll)
        t.start()

        # wait for poll to start
        time.sleep(5)

        c.publish({})
        t.join(35)

        self.assertEqual(self.response, 'Template content.',
                         'Poll should return content appropriate for given template')
