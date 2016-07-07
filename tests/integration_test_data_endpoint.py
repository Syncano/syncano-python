# -*- coding: utf-8 -*-
import re

from syncano.models import Class, DataEndpoint, Object, ResponseTemplate
from tests.integration_test import InstanceMixin, IntegrationTest


class DataEndpointTest(InstanceMixin, IntegrationTest):

    schema = [
        {
            'name': 'title',
            'type': 'string',
            'order_index': True,
            'filter_index': True

        }
    ]

    template_content = '''
        {% if action == 'list' %}
            {% set objects = response.objects %}
        {% elif action == 'retrieve' %}
            {% set objects = [response] %}
        {% else %}
            {% set objects = [] %}
        {% endif %}
        {% if objects %}
            <table{% if table_classes %} class="{{ table_classes }}"{% endif %}>

            <tr{% if tr_header_classes %} class="{{ tr_header_classes }}"{% endif %}>
                {% for key in objects[0] if key not in fields_to_skip %}
                    <th{% if th_header_classes %} class="{{ th_header_classes }}"{% endif %}>{{ key }}</th>
                {% endfor %}
            </tr>
            {% for object in objects %}
                <tr{% if tr_row_classes %} class="{{ tr_row_classes }}"{% endif %}>
                {% for key, value in object.iteritems() if key not in fields_to_skip %}
                    <td{% if td_row_classes %} class="{{ td_row_classes }}"{% endif %}>{{ value }}</td>
                {% endfor %}
                </tr>
            {% endfor %}
            </table>
        {% endif %}
    '''

    template_context = {
        "tr_header_classes": "",
        "th_header_classes": "",
        "tr_row_classes": "",
        "table_classes": "",
        "td_row_classes": "",
        "fields_to_skip": [
            "id",
            "channel",
            "channel_room",
            "group",
            "links",
            "group_permissions",
            "owner_permissions",
            "other_permissions",
            "owner",
            "revision",
            "updated_at",
            "created_at"
        ]
    }

    def test_template_response(self):
        Class(name='test_class', schema=self.schema).save()
        Object(class_name='test_class', title='test_title').save()
        template = ResponseTemplate(
            name='test_template',
            content=self.template_content,
            content_type='text/html',
            context=self.template_context
        ).save()
        data_endpoint = DataEndpoint(name='test_endpoint', class_name='test_class').save()

        response = list(data_endpoint.get(response_template=template))
        self.assertEqual(len(response), 1, 'Data endpoint should return 1 element if queried with response_template.')
        data = re.sub('[\s+]', '', response[0])
        self.assertEqual(data, '<table><tr><th>title</th></tr><tr><td>test_title</td></tr></table>')
