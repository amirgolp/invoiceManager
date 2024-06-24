import click
from datetime import datetime
from invoicer.db_connection import DatabaseConnection
from invoicer.data_model import insert_data, delete_data, update_data

# Database configuration
config = DatabaseConnection.load_config('config.yaml')

# Initialize Database connection
db = DatabaseConnection(config=config)
db.connect()


@click.group()
def cli():
    """CLI tool to manage grocery items in the database."""
    pass


@cli.group()
def admin():
    """Admin commands to manage grocery items."""
    pass


@admin.command()
@click.argument('item')
@click.argument('quantity', type=int)
@click.argument('price', type=float)
@click.argument('date', type=click.DateTime(formats=["%Y-%m-%d"]))
def add(item: str, quantity: int, price: float, date: datetime):
    """Add an item to the database."""
    insert_data(item, quantity, price, date.date())
    click.echo(f"Item '{item}' added successfully.")


@admin.command()
@click.argument('item')
@click.argument('quantity', type=int)
@click.argument('price', type=float)
@click.argument('date', type=click.DateTime(formats=["%Y-%m-%d"]))
def update(item: str, quantity: int, price: float, date: datetime):
    """Update an item in the database."""
    update_data(item, quantity, price, date.date())
    click.echo(f"Item '{item}' updated successfully.")


@admin.command()
@click.argument('item')
@click.argument('date', type=click.DateTime(formats=["%Y-%m-%d"]))
def delete(item: str, date: datetime):
    """Delete an item from the database."""
    delete_data(item, date.date())
    click.echo(f"Item '{item}' deleted successfully.")


if __name__ == '__main__':
    cli()
