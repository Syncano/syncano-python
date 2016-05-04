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
        self.assertListEqual(sorted(book.authors), sorted(authors_list_ids))

    def test_object_list(self):
        authors_list_ids = [self.prus.id, self.coehlo.id]
        book = self.book.objects.create(authors=authors_list_ids, title='Strange title')
        self.assertListEqual(sorted(book.authors), sorted(authors_list_ids))

    def test_object_assign(self):
        self.lalka.authors = [self.lem, self.coehlo]
        self.lalka.save()

        self.assertListEqual(sorted(self.lalka.authors), sorted([self.lem.id, self.coehlo.id]))

    def test_related_field_add(self):
        self.niezwyciezony.authors_set.add(self.coehlo)
        self.assertListEqual(sorted(self.niezwyciezony.authors), sorted([self.lem.id, self.coehlo.id]))

        self.niezwyciezony.authors_set.add(self.prus.id, self.coehlo.id)
        self.assertListEqual(sorted(self.niezwyciezony.authors), sorted([self.lem.id, self.prus.id, self.coehlo.id]))

    def test_related_field_remove(self):
        self.brida.authors_set.remove(self.coehlo)
        self.assertEqual(self.brida.authors, None)

        self.niezwyciezony.authors_set.remove(self.prus, self.lem, self.coehlo)
        self.assertEqual(self.niezwyciezony.authors, None)

    def test_related_field_lookup_contains(self):
        filtered_books = self.book.objects.list().filter(author__contains=[self.prus])

        self.assertEqual(len(filtered_books), 1)

        for book in filtered_books:
            self.assertEqual(book.title, self.lalka.title)

    def test_related_field_lookup_contains_fail(self):
        filtered_books = self.book.objects.list().filter(author__contains=[self.prus, self.lem])
        self.assertEqual(len(filtered_books), 0)

    def test_related_field_lookup_is(self):
        filtered_books = self.book.objects.list().filter(author__name__startswith='Stan')

        self.assertEqual(len(filtered_books), 1)
        for book in filtered_books:
            self.assertEqual(book.title, self.niezwyciezony.title)
