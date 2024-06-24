import streamlit as st
import pandas as pd
from datetime import datetime
from PIL import Image
import requests
from invoicer.db_connection import DatabaseConnection, DatabaseConfig
from invoicer.data_model import get_data, insert_data, delete_data, manually_add_item

# Database configuration
config = DatabaseConfig(
    db_name='invoiceDB',
    username='your_username',
    password='your_password',
    host='your_cluster_url'
)

# Initialize Database connection
db = DatabaseConnection(config=config)
db.connect()


# Gemini Pro API for text extraction
def extract_text_from_image_with_gemini(image, gemini_pro_access_token):
    url = "https://api.gemini-pro.com/ocr"
    headers = {
        "Authorization": f"Bearer {gemini_pro_access_token}"
    }
    files = {'file': image}
    response = requests.post(url, headers=headers, files=files)
    text = response.json().get('text', '')
    return text


def extract_data_from_text(text):
    # Mock function to simulate data extraction from text
    # Replace with your actual logic
    lines = text.strip().split('\n')
    data = []
    for line in lines:
        if line:
            parts = line.split(',')
            if len(parts) == 3:
                item, quantity, price = parts
                data.append((item.strip(), int(quantity.strip()), float(price.strip())))
    return data


# Streamlit interface
st.title("Invoice Data Extraction")


# Function to display data
def display_data():
    data = get_data()
    df = pd.DataFrame(data)
    if not df.empty:
        st.dataframe(df)
    else:
        st.write("No data available.")


# Upload and process invoice
uploaded_file = st.file_uploader("Choose an invoice image...", type=["jpg", "jpeg", "png"])
invoice_date = st.date_input("Invoice Date", datetime.now())

if uploaded_file is not None:
    gemini_pro_access_token = st.text_input("Enter Gemini Pro Access Token", type="password")
    if gemini_pro_access_token:
        text = extract_text_from_image_with_gemini(uploaded_file, gemini_pro_access_token)
        extracted_data = extract_data_from_text(text)
        st.write("Extracted Data:")
        for item, quantity, price in extracted_data:
            st.write(f"Item: {item}, Quantity: {quantity}, Price: {price}")
            insert_data(item, quantity, price, invoice_date)

st.write("Stored Data in Database:")
display_data()

# Manual entry form
st.write("Manually Add/Update/Delete Item")
manual_item = st.text_input("Item Name")
manual_quantity = st.number_input("Quantity", min_value=0, value=0)
manual_price = st.number_input("Price", min_value=0.0, value=0.0)
manual_date = st.date_input("Date", datetime.now())

if st.button("Add/Update Item"):
    manually_add_item(manual_item, manual_quantity, manual_price, manual_date)
    st.write("Item added/updated.")
    display_data()

if st.button("Delete Item"):
    delete_data(manual_item, manual_date)
    st.write("Item deleted.")
    display_data()
