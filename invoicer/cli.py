import click
from invoicer.db_connection import connect_to_db
from invoicer.data.model import Invoice
from invoicer.data.config import load_config
import requests


@click.group()
def cli():
    pass


@cli.command()
@click.argument('image_path')
def process_invoice(image_path):
    connect_to_db()
    config = load_config()
    api_key = config['google']['gemini_api_key']

    # Use Google Gemini API to parse the image
    parsed_data = parse_invoice(image_path, api_key)

    # Save parsed data to MongoDB
    invoice = Invoice(**parsed_data)
    invoice.save()
    click.echo("Invoice saved to MongoDB Atlas")


def parse_invoice(image_path, api_key):
    # Simulating the Google Gemini API call
    url = f"https://gemini.googleapis.com/v1/invoices:parse?key={api_key}"
    with open(image_path, 'rb') as image_file:
        response = requests.post(url, files={"file": image_file})

    # Simulating a response
    response_data = response.json()
    parsed_data = {
        "invoice_number": response_data["invoiceNumber"],
        "vendor_name": response_data["vendorName"],
        "total_amount": response_data["totalAmount"],
        "date": response_data["date"]
    }
    return parsed_data


if __name__ == "__main__":
    cli()
