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
if 'processed_items' not in st.session_state:
    st.session_state.processed_items = None
if 'processed_total_price' not in st.session_state:
    st.session_state.processed_total_price = None

# Main app layout
st.title("Invoice Manager")

# Sidebar with options
st.sidebar.header("Invoice Options")
option = st.sidebar.radio("Select an option",
                          ["None", "Add New Invoice", "Edit/Delete Invoice", "Parse Invoice from Image"])

st.sidebar.header("Analysis")
show_graphs = st.sidebar.checkbox("Show Expenditure Analysis", False)

if option == "Add New Invoice":
    add_new_invoice()

elif option == "Edit/Delete Invoice":
    edit_delete_invoice()

elif option == "Parse Invoice from Image":
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    if uploaded_file is not None:
        st.session_state.uploaded_file = uploaded_file

    if st.session_state.uploaded_file is not None:
        image = Image.open(st.session_state.uploaded_file)
        st.image(image, caption="Uploaded Image.", use_column_width=True)
        image_path = save_uploaded_file(st.session_state.uploaded_file)

    submit = st.button("Extract the invoice data")

    input_prompt = """
                   You are an expert in understanding invoices.
                   You will receive input images as invoices &
                   you will have to find all items in the invoice. 
                   If the language is in German, translate the item names to English before putting them in the 
                   following format. If the names are abbreviated, try to get the full English names.
                   for example, "Gurken" should be written as "cucumber". When extracting the quantity,
                   if you find the unit of "kilograms" or "kg", just extract the value, and if you
                   find a "multiplier" sign or "cross" sign, the ignore the individual unit price and
                   extract the total number or total weight as for the quantity. 
                   List them one per line, each
                   line in this format: {name of the item} - {quantity} - {total price of the item}

                   Do NOT write the total/sum amount.
                   """

    if submit and st.session_state.uploaded_file is not None:
        image_data = input_image_setup(st.session_state.uploaded_file)
        response = get_gemini_response(gemini_model, input_prompt, image_data)
        st.subheader("The Response is")
        st.write(response)

        items, total_price = parse_response(response)
        st.write("Parsed Items:")
        for item in items:
            st.write(f"{item.name} - {item.quantity} - {item.price}")
        st.write(f"Total Price: {total_price}")

        st.session_state.processed_items = items
        st.session_state.processed_total_price = total_price

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Reprocess Image"):
                st.experimental_rerun()
        with col2:
            st.button("Save to MongoDB", on_click=save_to_mongodb)

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
