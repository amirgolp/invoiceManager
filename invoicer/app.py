import json
from datetime import datetime

import streamlit as st
from PIL import Image
import google.generativeai as genai

from invoicer.data.model import Invoice
from invoicer.db_connection import connect_to_db
from invoicer.data.config import load_config
import plotly.express as px
import pandas as pd
import logging
from data.base import (get_gemini_response, save_uploaded_file, input_image_setup, parse_response,
                       save_to_mongodb, query_invoices, add_new_invoice, edit_delete_invoice)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load application configuration
config = load_config('config.yaml')

# Configure Gemini API
genai.configure(api_key=config['gemini']['google_api_key'])
gemini_model = config['gemini']['gemini_model']

# Initialize Database connection (Singleton)
connect_to_db('config.yaml')

# Initialize session state variables
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'response_dict' not in st.session_state:
    st.session_state.response_dict = None
if 'processed_items' not in st.session_state:
    st.session_state.processed_items = None
if 'invoice_metadata' not in st.session_state:
    st.session_state.invoice_metadata = None

# Main app layout
st.title("Invoice Manager")

# Sidebar with options
st.sidebar.header("Invoice Options")
option = st.sidebar.radio("Select an option",
                          [
                              "None",
                              "Automatically Add New Invoice",
                              "Manually Add New Invoice",
                              "Edit/Delete Previous Invoice"
                           ])

st.sidebar.header("Analysis")
show_graphs = st.sidebar.checkbox("Show Expenditure Analysis", False)

if option == "Manually Add New Invoice":
    add_new_invoice()

elif option == "Edit/Delete Invoice":
    edit_delete_invoice()

elif option == "Automatically Add New Invoice":
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file

    if st.session_state.uploaded_file is not None:
        image = Image.open(st.session_state.uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
        image_path = save_uploaded_file(st.session_state.uploaded_file)

    submit = st.button("Extract the invoice data")

    input_prompt = """
    Extract the following values in JSON format: Items (each item should be a nested dictionary with keys: Name, 
    Quantity, Unit Price (EUR), Total Price (EUR), Product Name (German), Product Name (English)), Issuer, 
    Issuer Address, Issuer Phone, Invoice Number, Date Issued, Time Issued.

    Ensure the output JSON structure matches this example:
    {
        "Items": [
            {
                "Name": "Lindt Excell.85%",
                "Quantity": 1,
                "Unit Price (EUR)": 2.69,
                "Total Price (EUR)": 2.69,
                "Product Name (German)": "Lindt Excell.85%",
                "Product Name (English)": "Lindt Excellence 85%"
            }
        ],
        "Issuer": "EDEKA Christ",
        "Issuer Address": "Hildburghauser Str. 52, 12279 Berlin",
        "Issuer Phone": "030-710 99 49-0",
        "Invoice Number": "3793",
        "Date Issued": "05.07.2024",
        "Time Issued": "20:37:58",
        "Total Invoice Expense (EUR)": 17.2
    }
    """

    if submit and st.session_state.uploaded_file is not None:
        image_data = input_image_setup(st.session_state.uploaded_file)
        try:
            response = get_gemini_response(gemini_model, input_prompt, image_data)
            st.subheader("The Response is")

            if not response:
                st.error("Received empty response from the API.")
            else:
                response = response.replace('```', '').replace('\n', '').replace('json', '')

                response_dict = json.loads(response)
                if response_dict['Date Issued'] is None:
                    response_dict['Date Issued'] = datetime.now().date()
                    response_dict['Time Issued'] = datetime.now().time().isoformat()

                st.session_state.response_dict = response_dict.copy()

                items = response_dict.pop("Items", [])
                items_df = pd.DataFrame(items)

                invoice_metadata = pd.DataFrame([response_dict])

                st.subheader("Extracted Items")
                st.dataframe(items_df)

                st.subheader("Invoice Metadata")
                st.dataframe(invoice_metadata)

            st.session_state.processed_items = items
            st.session_state.invoice_metadata = invoice_metadata

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Reprocess Image"):
                    st.experimental_rerun()
            with col2:
                st.button("Save to MongoDB", on_click=save_to_mongodb)
        except json.JSONDecodeError as e:
            st.error(f"JSON decode error: {e}")
        except Exception as e:
            st.error(f"An error occurred: {e}")

if show_graphs:
    st.header("Expenditure Analysis")
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")

    if st.button("Generate Report"):
        invoices = query_invoices(start_date, end_date)

        if not invoices:
            st.warning("No invoices found for the selected date range.")
        else:
            df = pd.DataFrame(invoices)

            total_expenditure = df['total_price'].sum()

            st.subheader(f"Total Expenditure from {start_date} to {end_date}")
            st.write(f"Total Expenditure: {total_expenditure:.2f} EUR")

            # Prepare data for pie chart
            item_summary = {}
            for invoice in Invoice.objects(date__gte=start_date, date__lte=end_date):
                for item in invoice.items:
                    if item.name in item_summary:
                        item_summary[item.name] += item.price
                    else:
                        item_summary[item.name] = item.price

            # Pie chart for expenditure distribution
            item_names = list(item_summary.keys())
            item_prices = list(item_summary.values())

            fig_pie = px.pie(values=item_prices, names=item_names, title="Expenditure Distribution")
            st.plotly_chart(fig_pie)

            # Line chart for total expenses over time
            df = df.sort_values('date')
            fig_line = px.line(df, x='date', y='total_price', title='Total Expenses Over Time')
            st.plotly_chart(fig_line)
