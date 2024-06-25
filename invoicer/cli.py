import base64

import click
from datetime import datetime
from invoicer.db_connection import connect_to_db
from invoicer.data.model import Invoice, Item
from invoicer.data.config import load_config
import requests
import json


@click.group()
def cli():
    """Invoice processing and management CLI tool."""
    pass


@cli.command()
@click.argument('image_path', type=click.Path(exists=True))
@click.option('--config', default='config.yaml', help='Path to configuration file')
def process_invoice(image_path, config):
    """Process an invoice image and save it to the database."""
    connect_to_db(config)
    config_data = load_config(config)
    api_key = config_data['gemini']['google_api_key']

    click.echo(f"Processing invoice: {image_path}")
    parsed_data = parse_invoice(image_path, api_key)

    invoice = Invoice(
        items=[Item(**item) for item in parsed_data['items']],
        total_price=parsed_data['total_price'],
        date=datetime.now()
    )
    invoice.save()
    click.echo("Invoice saved to MongoDB Atlas")


@cli.command()
@click.option('--start-date', type=click.DateTime(), help='Start date for report (YYYY-MM-DD)')
@click.option('--end-date', type=click.DateTime(), help='End date for report (YYYY-MM-DD)')
@click.option('--config', default='config.yaml', help='Path to configuration file')
def generate_report(start_date, end_date, config):
    """Generate a report of invoices within a date range."""
    connect_to_db(config)
    invoices = Invoice.objects(date__gte=start_date, date__lte=end_date)

    total_expenditure = sum(invoice.total_price for invoice in invoices)
    click.echo(f"Total Expenditure from {start_date} to {end_date}: {total_expenditure:.2f} EUR")

    item_summary = {}
    for invoice in invoices:
        for item in invoice.items:
            if item.name in item_summary:
                item_summary[item.name] += item.price
            else:
                item_summary[item.name] = item.price

    click.echo("\nExpenditure by Item:")
    for item, price in item_summary.items():
        click.echo(f"{item}: {price:.2f} EUR")


def parse_invoice(image_path, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}"

    with open(image_path, 'rb') as image_file:
        image_data = image_file.read()

    payload = {
        "contents": [{
            "parts": [
                {
                    "text": "Extract the items, quantities, and prices from this invoice image. Format the response as a JSON object with 'items' as a list of objects containing 'name', 'quantity', and 'price', and a 'total_price' field."},
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": base64.b64encode(image_data).decode('utf-8')
                    }
                }
            ]
        }]
    }

    response = requests.post(url, json=payload)
    response_data = response.json()

    # Extract the generated text from the response
    generated_text = response_data['candidates'][0]['content']['parts'][0]['text']

    # Parse the generated text as JSON
    parsed_data = json.loads(generated_text)

    return parsed_data


if __name__ == "__main__":
    cli()
