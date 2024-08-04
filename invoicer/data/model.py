import dateutil
from mongoengine import (Document, StringField, FloatField, DateTimeField, ListField, EmbeddedDocument,
                         EmbeddedDocumentField)


class Item(EmbeddedDocument):
    Name = StringField()
    Unit_Price_EUR = FloatField()
    Total_Price_EUR = FloatField()
    Quantity = FloatField()
    Product_Name_German = StringField()
    Product_Name_English = StringField()


class Invoice(Document):
    Items = ListField(EmbeddedDocumentField(Item))
    Issuer = StringField()
    Issuer_Address = StringField()
    Issuer_Phone = StringField()
    Invoice_Number = FloatField()
    Date_Issued = DateTimeField()
    Time_Issued = StringField()
    Total_Invoice_Expense_EUR = FloatField()
