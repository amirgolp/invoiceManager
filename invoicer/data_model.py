import mongoengine as me
from datetime import date
from typing import List
from pydantic import BaseModel, Field, ValidationError, field_validator


class GroceryItemModel(BaseModel):
    item: str = Field(..., min_length=1)
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0.0)
    date: date

    @field_validator('date')
    def date_cannot_be_in_future(cls, value):
        if value > date.today():
            raise ValueError("Date cannot be in the future.")
        return value


class GroceryItem(me.Document):
    item = me.StringField(required=True)
    quantity = me.IntField(required=True)
    price = me.FloatField(required=True)
    date = me.DateField(required=True)


def insert_data(item: str, quantity: int, price: float, date: date):
    try:
        data = GroceryItemModel(item=item, quantity=quantity, price=price, date=date)
        grocery_item = GroceryItem(**data.dict())
        grocery_item.save()
    except ValidationError as e:
        print(f"Validation error: {e}")


def update_data(item: str, quantity: int, price: float, date: date):
    try:
        data = GroceryItemModel(item=item, quantity=quantity, price=price, date=date)
        GroceryItem.objects(item=data.item, date=data.date).update_one(set__quantity=data.quantity, set__price=data.price, upsert=True)
    except ValidationError as e:
        print(f"Validation error: {e}")


def delete_data(item: str, date: date):
    GroceryItem.objects(item=item, date=date).delete()


def get_data() -> List[GroceryItem]:
    return list(GroceryItem.objects)


def manually_add_item(item: str, quantity: int, price: float, date: date):
    insert_data(item, quantity, price, date)
