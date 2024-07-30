from dotenv import load_dotenv
import streamlit as st
import os
from PIL import Image
import google.generativeai as genai
import json
import pandas as pd

# Load environment variables from .env
load_dotenv()

# Configure the Google API
api_key = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=api_key)
gemini_model = os.getenv("GEMINI_MODEL")

# Function to load OpenAI model and get response
def get_gemini_response(input_text, image, prompt):
    model = genai.GenerativeModel(gemini_model)
    response = model.generate_content([input_text, image[0], prompt])
    return response.text

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

# Initialize Streamlit app
st.set_page_config(page_title="Gemini Image Demo")

st.header("Gemini Application")
input_text = st.text_input("Input Prompt: ", key="input")
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
image = ""
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.", use_column_width=True)

submit = st.button("Tell me about the image")

input_prompt = """
Extract the following values in JSON format: Items (each item should be a nested dictionary with keys: item_name, Quantity, Unit Price (EUR), Total Price (EUR), Product Name (German), Product Name (English)), Issuer, Issuer Address, Issuer Phone, Invoice Number, Date Issued, Time Issued.

Ensure the output JSON structure matches this example:
{
    "Items": [
        {
            "item_name": "Lindt Excell.85%",
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

# If submit button is clicked
if submit:
    try:
        image_data = input_image_setup(uploaded_file)
        response = get_gemini_response(input_text, image_data, input_prompt)

        # Print the raw response for debugging
        st.write("Raw API response:", response)

        # Check if the response is empty
        if not response:
            st.error("Received empty response from the API.")
        else:
            response = response.replace('```', '').replace('\n', '').replace('json', '')

            response_dict = json.loads(response)

            items = response_dict.pop("Items", [])
            items_df = pd.DataFrame(items)

            other_details_df = pd.DataFrame([response_dict])

            st.subheader("Extracted Items")
            st.dataframe(items_df)

            st.subheader("Other Invoice Details")
            st.dataframe(other_details_df)
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error: {e}")
    except Exception as e:
        st.error(f"An error occurred: {e}")
