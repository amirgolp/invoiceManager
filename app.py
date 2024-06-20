import os
import cv2
import pytesseract
import re
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import plotly.express as px
from googletrans import Translator
from PIL import Image

# Set the TESSDATA_PREFIX environment variable
os.environ['TESSDATA_PREFIX'] = '/usr/share/tesseract-ocr/4.00/'  # Adjust the path as needed

# Configure Tesseract to use German language and set the path to the Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Adjust the path as needed
tesseract_config = r'--oem 3 --psm 6 -l deu'


def create_table_if_not_exists():
    conn = sqlite3.connect('expenditure.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY,
        date TEXT,
        product TEXT,
        price REAL
    )
    ''')
    conn.commit()
    conn.close()


def extract_text(image_path):
    # Load the image using OpenCV
    image = cv2.imread(image_path)
    # Convert the image to gray scale
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Use Tesseract to extract text
    extracted_text = pytesseract.image_to_string(gray_image, config=tesseract_config)
    return extracted_text


def extract_date(text):
    date_pattern = re.compile(r'\b(\d{2}\.\d{2}\.\d{4})\b')
    date_match = date_pattern.search(text)
    if date_match:
        return datetime.strptime(date_match.group(), '%d.%m.%Y').date()
    return None


def extract_products_and_prices(text):
    # Regular expression to match products and prices
    pattern = re.compile(r'([a-zA-ZäöüÄÖÜß\s]+)\s+(\d+,\d{2})')
    matches = pattern.findall(text)
    # Convert to dictionary with float prices
    products = {match[0].strip(): float(match[1].replace(',', '.')) for match in matches}
    return products


def translate_products(products):
    translator = Translator()
    translated_products = {}
    for product, price in products.items():
        translated = translator.translate(product, src='de', dest='en').text
        translated_products[translated] = price
    return translated_products


def save_to_database(date, products):
    conn = sqlite3.connect('expenditure.db')
    cursor = conn.cursor()
    for product, price in products.items():
        cursor.execute('INSERT INTO expenses (date, product, price) VALUES (?, ?, ?)', (date, product, price))
    conn.commit()
    conn.close()


def fetch_data():
    conn = sqlite3.connect('expenditure.db')
    cursor = conn.cursor()
    cursor.execute('SELECT date, SUM(price) as total FROM expenses GROUP BY date')
    data = cursor.fetchall()
    conn.close()
    return data


def plot_expenditure(data, months):
    df = pd.DataFrame(data, columns=['date', 'total'])
    df['date'] = pd.to_datetime(df['date'])
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30*months)
    filtered_df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
    fig = px.line(filtered_df, x='date', y='total', title=f'Expenditure for the past {months} months', labels={'total': 'Total Expenditure (€)', 'date': 'Date'})
    st.plotly_chart(fig)


# Create table if it does not exist
create_table_if_not_exists()

st.title('Receipt Scanner and Expenditure Tracker')

uploaded_file = st.file_uploader("Choose a receipt image...", type="jpeg")

if uploaded_file is not None:
    # Save the uploaded file temporarily
    temp_image_path = "temp_receipt.jpeg"
    with open(temp_image_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract text from image
    text = extract_text(temp_image_path)

    # Extract date from text
    date = extract_date(text)

    # Extract products and prices from text
    products = extract_products_and_prices(text)

    # Translate products to English
    translated_products = translate_products(products)

    # Save data to database
    if date and translated_products:
        save_to_database(date, translated_products)

    # Display the extracted information and image side by side
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"Date: {date}")
        st.write("Products and Prices:")
        st.write(translated_products)

    with col2:
        # Display the uploaded image
        image = Image.open(temp_image_path)
        st.image(image, caption='Uploaded Receipt', use_column_width=True)

    # Remove the temporary image file
    os.remove(temp_image_path)

# Fetch data and plot expenditure based on selected time frame
data = fetch_data()
st.write("Select the time frame for expenditure plot:")
if st.button('Past 1 month'):
    plot_expenditure(data, 1)
if st.button('Past 3 months'):
    plot_expenditure(data, 3)
if st.button('Past 6 months'):
    plot_expenditure(data, 6)
if st.button('Past 12 months'):
    plot_expenditure(data, 12)
