import cv2
import pytesseract
import re
import sqlite3
from datetime import datetime
import pandas as pd
import streamlit as st
import plotly.express as px

# Configure Tesseract to use German language
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Adjust the path as needed
tesseract_config = r'--oem 3 --psm 6 -l deu'

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

def save_to_database(date, products):
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

def plot_expenditure(data):
    df = pd.DataFrame(data, columns=['date', 'total'])
    df['date'] = pd.to_datetime(df['date'])
    fig = px.line(df, x='date', y='total', title='Daily Expenditure', labels={'total': 'Total Expenditure (€)', 'date': 'Date'})
    st.plotly_chart(fig)

st.title('Receipt Scanner and Expenditure Tracker')

uploaded_file = st.file_uploader("Choose a receipt image...", type="jpeg")

if uploaded_file is not None:
    # Save the uploaded file temporarily
    with open("temp_receipt.jpeg", "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Extract text from image
    text = extract_text("temp_receipt.jpeg")

    # Extract date from text
    date = extract_date(text)

    # Extract products and prices from text
    products = extract_products_and_prices(text)

    # Save data to database
    if date and products:
        save_to_database(date, products)

    # Display extracted information
    st.write(f"Date: {date}")
    st.write("Products and Prices:")
    st.write(products)

# Fetch data and plot expenditure
data = fetch_data()
plot_expenditure(data)
