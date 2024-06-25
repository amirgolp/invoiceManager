from mongoengine import (Document, StringField, FloatField, DateTimeField, ListField, EmbeddedDocument,
                         EmbeddedDocumentField)


class Item(EmbeddedDocument):
    name = StringField(required=True)
    quantity = StringField(required=True)
    price = FloatField(required=True)


class Invoice(Document):
    items = ListField(EmbeddedDocumentField(Item), required=True)
    total_price = FloatField(required=True)
    date = DateTimeField(required=True)
