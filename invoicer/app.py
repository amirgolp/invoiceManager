import re

import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
from invoicer.db_connection import connect_to_db
from invoicer.data.model import Invoice, Item
from invoicer.data.config import load_config
from datetime import datetime
import plotly.express as px
import pandas as pd
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        if not line or line.lower().startswith("total") or line.lower().startswith("the total price of the items is"):
            continue

        # Try to match the format "name - quantity - price"
        match = re.match(r"^(.*) - ([\d\.]+(?: kg)?) - ([\d\.]+(?: EUR)?)$", line)
        if match:
            name = match.group(1).strip()
            quantity = match.group(2).strip()
            price = match.group(3).strip()
            if ' EUR' in price:
                price = price.replace(' EUR', '')
            total_item_price = float(price.replace(',', '.'))
        else:
            # Try to match the format "name - price x quantity - total_price"
            match = re.match(r"^(.*) - ([\d\.]+(?: EUR)?) x ([\d\.]+) - ([\d\.]+(?: EUR)?)$", line)
            if match:
                name = match.group(1).strip()
                unit_price = match.group(2).strip()
                quantity = match.group(3).strip()
                total_item_price = match.group(4).strip()
                if ' EUR' in total_item_price:
                    total_item_price = total_item_price.replace(' EUR', '')
                total_item_price = float(total_item_price.replace(',', '.'))
            else:
                # Handle lines with format "name - quantity - price"
                parts = line.split(' - ')
                if len(parts) == 3:
                    name = parts[0].strip()
                    quantity = parts[1].strip()
                    total_item_price = parts[2].strip()
                    if ' EUR' in total_item_price:
                        total_item_price = total_item_price.replace(' EUR', '')
                    total_item_price = float(total_item_price.replace(',', '.'))
                else:
                    # Handle unexpected formats by skipping
                    continue

        items.append(Item(name=name, quantity=quantity, price=total_item_price))
        total_price += total_item_price

    return items, total_price


def save_to_mongodb():
    print("Save to MongoDB function called")
    if st.session_state.processed_items is not None and st.session_state.processed_total_price is not None:
        print(f"Processed items: {st.session_state.processed_items}")
        print(f"Total price: {st.session_state.processed_total_price}")
        try:
            invoice = Invoice(
                items=st.session_state.processed_items,
                total_price=st.session_state.processed_total_price,
                date=datetime.now()
            )
            print(f"Invoice created: {invoice.to_json()}")
            invoice.save()
            print("Invoice saved successfully")
            st.success("Invoice saved to MongoDB Atlas")
            # Clear the processed data
            st.session_state.processed_items = None
            st.session_state.processed_total_price = None
        except Exception as e:
            print(f"Error saving to MongoDB: {str(e)}")
            st.error(f"Failed to save to MongoDB: {str(e)}")
    else:
        print("No processed data available")
        st.warning("No processed data available. Please extract invoice data first.")


def query_invoices(start_date, end_date):
    invoices = Invoice.objects(date__gte=start_date, date__lte=end_date)
    return [{"date": inv.date.date(), "total_price": inv.total_price} for inv in invoices]


def add_new_invoice():
    st.subheader("Add New Invoice")

    if 'item_count' not in st.session_state:
        st.session_state.item_count = 1

    with st.form("new_invoice_form2"):
        date = st.date_input("Invoice Date", datetime.now())
        time = st.time_input("Invoice Time", datetime.now().time())

        total_price = st.number_input("Total Price", min_value=0.0, step=0.01)

        # Dynamic form for adding items
        items = []
        for i in range(st.session_state.item_count):
            col1, col2, col3 = st.columns(3)
            with col1:
                name = st.text_input(f"Item {i + 1} Name", key=f"name_{i}")
            with col2:
                quantity = st.number_input(f"Item {i + 1} Quantity", min_value=0, step=1, key=f"quantity_{i}")
            with col3:
                price = st.number_input(f"Item {i + 1} Price", min_value=0.0, step=0.01, key=f"price_{i}")

            if name and quantity > 0 and price > 0:
                items.append(Item(name=name, quantity=quantity, price=price))

        add_item = st.form_submit_button("Add a New Item")
        if add_item:
            st.session_state.item_count += 1
            st.experimental_rerun()

        submitted = st.form_submit_button("Add Invoice")
        if submitted:
            new_invoice = Invoice(date=date, items=items, total_price=total_price)
            new_invoice.save()
            st.success("New invoice added successfully!")
            st.session_state.item_count = 1  # Reset item count after successful submission


def edit_delete_invoice():
    st.subheader("Edit/Delete Invoice")
    invoices = Invoice.objects.order_by('-date')
    selected_invoice = st.selectbox("Select an invoice", options=invoices,
                                    format_func=lambda x: f"{x.date} - Total: {x.total_price}")

    if selected_invoice:
        with st.form("edit_invoice_form"):
            date = st.date_input("Invoice Date", selected_invoice.date)
            total_price = st.number_input("Total Price", min_value=0.0, step=0.01, value=selected_invoice.total_price)

            items = []
            for i, item in enumerate(selected_invoice.items):
                col1, col2, col3 = st.columns(3)
                with col1:
                    name = st.text_input(f"Item {i + 1} Name", value=item.name, key=f"edit_name_{i}")
                with col2:
                    quantity = st.number_input(f"Item {i + 1} Quantity", min_value=0, step=1, value=item.quantity,
                                               key=f"edit_quantity_{i}")
                with col3:
                    price = st.number_input(f"Item {i + 1} Price", min_value=0.0, step=0.01, value=item.price,
                                            key=f"edit_price_{i}")

                if name and quantity > 0 and price > 0:
                    items.append(Item(name=name, quantity=quantity, price=price))

            col1, col2 = st.columns(2)
            with col1:
                update = st.form_submit_button("Update Invoice")
            with col2:
                delete = st.form_submit_button("Delete Invoice")

            if update:
                selected_invoice.date = date
                selected_invoice.items = items
                selected_invoice.total_price = total_price
                selected_invoice.save()
                st.success("Invoice updated successfully!")

            if delete:
                selected_invoice.delete()
                st.success("Invoice deleted successfully!")
                st.experimental_rerun()


# Initialize our streamlit app
st.set_page_config(page_title="Gemini Image Demo")
st.header("Gemini Application")

if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
if 'processed_items' not in st.session_state:
    st.session_state.processed_items = None
if 'processed_total_price' not in st.session_state:
    st.session_state.processed_total_price = None

# Call the add_new_invoice function in the Streamlit app
add_new_invoice()

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

# If ask button is clicked
if submit and st.session_state.uploaded_file is not None:
    image_data = input_image_setup(st.session_state.uploaded_file)
    response = get_gemini_response(input_prompt, image_data)
    st.subheader("The Response is")
    st.write(response)

    items, total_price = parse_response(response)
    st.write("Parsed Items:")
    for item in items:
        st.write(f"{item.name} - {item.quantity} - {item.price}")
    st.write(f"Total Price: {total_price}")

    # Store the processed data in session state
    st.session_state.processed_items = items
    st.session_state.processed_total_price = total_price

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Reprocess Image"):
            st.experimental_rerun()
    with col2:
        st.button("Save to MongoDB", on_click=save_to_mongodb)


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

# Main app layout
st.title("Invoice Manager")

col1, col2 = st.columns(2)
with col1:
    if st.button("Add New Invoice"):
        st.session_state.show_add_dialog = True

with col2:
    if st.button("Edit/Delete Invoice"):
        st.session_state.show_edit_dialog = True

if 'show_add_dialog' not in st.session_state:
    st.session_state.show_add_dialog = False

if 'show_edit_dialog' not in st.session_state:
    st.session_state.show_edit_dialog = False

# if st.session_state.show_edit_dialog:
#     edit_delete_invoice()
