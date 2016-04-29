# -*- coding: utf-8 -*-
from syncano.models import Class
from tests.integration_test import InstanceMixin, IntegrationTest


class ResponseTemplateApiTest(InstanceMixin, IntegrationTest):

    @classmethod
    def setUpClass(cls):
        super(ResponseTemplateApiTest, cls).setUpClass()

        # prapare data
        cls.author = Class.please.create(name="author", schema=[
            {"name": "name", "type": "string", "filter_index": True},
            {"name": "birthday", "type": "integer"},
        ])

        cls.book = Class.please.create(name="book", schema=[
            {"name": "title", "type": "string", "filter_index": True},
            {"name": "authors", "type": "relation", "target": "author"},
        ])

        cls.prus = cls.author.objects.create(name='Bolesław Prus', birthday=1847)
        cls.lem = cls.author.objects.create(name='Stanisław Lem', birthday=1921)
        cls.coehlo = cls.author.objects.create(name='Paulo Coehlo', birthday=1947)

        cls.lalka = cls.book.objects.create(authors=[cls.prus.id], title='Lalka')
        cls.niezwyciezony = cls.book.objects.create(authors=[cls.lem.id], title='Niezwyciężony')
        cls.brida = cls.book.objects.create(authors=[cls.coehlo.id], title='Brida')

    def test_integers_list(self):
        authors_list_ids = [self.prus.id, self.coehlo.id]
        book = self.book.objects.create(authors=authors_list_ids, title='Strange title')
        self.assertItemsEqual(book.authors, authors_list_ids)

    def test_object_list(self):
        authors_list_ids = [self.prus.id, self.coehlo.id]
        book = self.book.objects.create(authors=authors_list_ids, title='Strange title')
        self.assertItemsEqual(book.authors, authors_list_ids)

    def test_object_assign(self):
        self.lalka.authors = [self.lem, self.coehlo]
        self.lalka.save()

        self.assertItemsEqual(self.lalka.authors, [self.lem.id, self.coehlo.id])

    def test_related_field_add(self):
        self.niezwyciezony.authors_set.add(self.coehlo)
        self.assertItemsEqual(self.niezwyciezony.authors, [self.lem.id, self.coehlo.id])

        self.niezwyciezony.authors_set.add(self.prus.id, self.coehlo.id)
        self.assertItemsEqual(self.niezwyciezony.authors, [self.lem.id, self.prus.id, self.coehlo.id])

    def test_related_field_remove(self):
        self.brida.authors_set.remove(self.coehlo)
        self.assertItemsEqual(self.brida.authors, None)

        self.niezwyciezony.authors_set.remove(self.prus, self.lem, self.coehlo)
        self.assertItemsEqual(self.niezwyciezony.authors, None)
