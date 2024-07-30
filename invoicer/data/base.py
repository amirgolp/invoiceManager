import re
import os
from datetime import datetime
import google.generativeai as genai
from invoicer.data.model import Invoice, Item
import logging
import streamlit as st

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_gemini_response(gemini_model, prompt, image):
    model = genai.GenerativeModel(gemini_model)
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
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        image_parts = [
            {
                "mime_type": uploaded_file.type,
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

        match = re.match(r"^(.*) - ([\d\.]+(?: kg)?) - ([\d\.]+(?: EUR)?)$", line)
        if match:
            name = match.group(1).strip()
            quantity = match.group(2).strip()
            price = match.group(3).strip()
            if ' EUR' in price:
                price = price.replace(' EUR', '')
            total_item_price = float(price.replace(',', '.'))
        else:
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
                parts = line.split(' - ')
                if len(parts) == 3:
                    name = parts[0].strip()
                    quantity = parts[1].strip()
                    total_item_price = parts[2].strip()
                    if ' EUR' in total_item_price:
                        total_item_price = total_item_price.replace(' EUR', '')
                    total_item_price = float(total_item_price.replace(',', '.'))
                else:
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
            new_invoice = Invoice(date=datetime.combine(date, time), items=items, total_price=total_price)
            new_invoice.save()
            st.success("New invoice added successfully!")
            st.session_state.item_count = 1


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

            update = st.form_submit_button("Update Invoice")
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
