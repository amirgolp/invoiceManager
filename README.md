# Invoicer

Invoicer is a Python package for managing grocery invoices. It provides tools to extract data from invoices, store them in a MongoDB database, and interact with the data using a command-line interface (CLI) and a Streamlit web application.

## Features

- Extract data from invoice images using Gemini Pro API.
- Store and manage grocery items in a MongoDB database.
- Command-line interface for adding, updating, and deleting items.
- Streamlit application for uploading invoices and viewing/managing data.

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/yourusername/invoicer.git
    cd invoicer
    ```

2. Create and activate a virtual environment (optional but recommended):

    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. Install the package in editable mode:

    ```sh
    pip install -e .
    ```

4. Create a `config.yaml` file in the root of your project directory with your MongoDB configuration:

    ```yaml
    database:
      db_name: "invoiceDB"
      username: "your_username"
      password: "your_password"
      host: "your_cluster_url"
    ```

    Replace the placeholders with your actual MongoDB Atlas credentials.

## Usage

### Command-Line Interface (CLI)

The CLI allows you to manage grocery items in the database. Use the following commands:

- **Add an item:**

    ```sh
    invoicer admin add ITEM_NAME QUANTITY PRICE DATE
    ```

    Example:

    ```sh
    invoicer admin add "Apple" 10 0.99 2023-01-01
    ```

- **Update an item:**

    ```sh
    invoicer admin update ITEM_NAME QUANTITY PRICE DATE
    ```

    Example:

    ```sh
    invoicer admin update "Apple" 15 0.89 2023-01-01
    ```

- **Delete an item:**

    ```sh
    invoicer admin delete ITEM_NAME DATE
    ```

    Example:

    ```sh
    invoicer admin delete "Apple" 2023-01-01
    ```

### Streamlit Application

The Streamlit application provides a web interface for interacting with the invoice data.

1. Run the Streamlit app:

    ```sh
    streamlit run invoicer/streamlit_app.py
    ```

2. Open the provided URL in your web browser.

3. Upload invoice images, view extracted data, and manage items directly from the web interface.

## Dependencies

The project requires the following Python packages:

- `click`
- `mongoengine`
- `streamlit`
- `pandas`
- `pillow`
- `requests`
- `pydantic`

These dependencies are specified in the `pyproject.toml` file and will be installed automatically when you install the package.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Contact

For questions or suggestions, please contact [Amir Golparvar](mailto:amir.golparvar@physik.hu-berlin.de).
