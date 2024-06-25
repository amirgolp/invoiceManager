import re

import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
from invoicer.db_connection import connect_to_db
from invoicer.data.model import Invoice, Item
from invoicer.data.config import load_config
from datetime import datetime

# Load application configuration
config = load_config('config.yaml')

# Configure Gemini API
genai.configure(api_key=config['gemini']['google_api_key'])

# Initialize Database connection (Singleton)
connect_to_db('config.yaml')


def get_gemini_response(prompt, image):
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([prompt, image[0]])
    print(response.text)
    return response.text


def save_uploaded_file(uploadedfile):
    temp_dir = "tempDir"
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    file_path = os.path.join(temp_dir, uploadedfile.name)
    with open(file_path, "wb") as f:
        f.write(uploadedfile.getbuffer())
    return file_path


def input_image_setup(uploaded_file):
    # Check if a file has been uploaded
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,  # Get the mime type of the uploaded file
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")


def parse_response(response_text):
    lines = response_text.strip().split('\n')
    items = []
    total_price = 0.0

    for line in lines:
        line = line.strip()
        if not line or line.startswith("The total price of the items is") or line.startswith("Total"):
            continue

        # Match the format with 'x quantity' or 'kg' in the quantity field
        match = re.match(r"^(.*) - (\d+\.?\d* .*) - (\d+\.\d{2}) EUR$", line)
        if match:
            name = match.group(1)
            quantity = match.group(2)
            total_item_price = float(match.group(3).replace(',', '.'))
        else:
            # Match the format without 'x quantity' or 'kg' in the quantity field
            match = re.match(r"^(.*) - (\d+\.\d{2}) EUR$", line)
            if match:
                name = match.group(1)
                quantity = "1"  # Default quantity to 1 if not specified
                total_item_price = float(match.group(2).replace(',', '.'))
            else:
                continue  # Skip lines that don't match any expected format

        items.append(Item(name=name, quantity=quantity, price=total_item_price))
        total_price += total_item_price

    return items, total_price


# Initialize our streamlit app
st.set_page_config(page_title="Gemini Image Demo")
st.header("Gemini Application")

uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
image = ""
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.", use_column_width=True)
    image_path = save_uploaded_file(uploaded_file)

submit = st.button("Extract the invoice data")

input_prompt = """
               You are an expert in understanding invoices.
               You will receive input images as invoices &
               you will have to find all items in the invoice. List them one per line, each
               line in this format: {name of the item} - {quantity} - {total price of the item}

               Make sure the summation of total prices matches the total price on the invoice.
               If the language is in German, translate the item names to English in response.
               """

# If ask button is clicked
if submit:
    image_data = input_image_setup(uploaded_file)
    response = get_gemini_response(input_prompt, image_data)
    st.subheader("The Response is")
    st.write(response)

    items, total_price = parse_response(response)
    st.write("Parsed Items:")
    for item in items:
        st.write(f"{item.name} - {item.quantity} - {item.price}")
    st.write(f"Total Price: {total_price}")

    invoice = Invoice(items=items, total_price=total_price, date=datetime.now())
    invoice.save()
    st.success("Invoice saved to MongoDB Atlas")

