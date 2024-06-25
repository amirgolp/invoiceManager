# Invoicer

Invoicer is a Python package for managing grocery invoices. It provides tools to extract data from invoices using the Gemini Pro API, store them in a MongoDB database, and interact with the data using a command-line interface (CLI) and a Streamlit web application.

## Features

- Extract data from invoice images using Gemini Pro API.
- Store and manage invoice data in a MongoDB database.
- Command-line interface for processing invoices and generating reports.
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

3. Install the package:

    ```sh
    pip install -e .
    ```

4. Create a `config.yaml` file in the root of your project directory with your MongoDB and Gemini API configurations:

    ```yaml
    gemini:
      google_api_key: "YOUR_GOOGLE_API_KEY"
    database:
      uri: "YOUR_MONGODB_CONNECTION_STRING"
      database: "Your database name"
    ```

    Replace the placeholders with your actual credentials.

## Usage

### Command-Line Interface (CLI)

The CLI allows you to process invoices and generate reports. Use the following commands:

- **Process an invoice:**

    ```sh
    invoicer process-invoice /path/to/invoice/image.jpg
    ```

    This command will extract data from the invoice image and save it to the database.

- **Generate a report:**

    ```sh
    invoicer generate-report --start-date 2024-01-01 --end-date 2024-12-31
    ```

    This command will generate a report of invoices within the specified date range.

### Streamlit Application

The Streamlit application provides a web interface for interacting with the invoice data.

1. Run the Streamlit app:

    ```sh
    streamlit run invoicer/app.py
    ```
   
    or via the cli:

    ```sh
    invoicer run-app
    ```

Make sure you're in the root directory of the project when running this command.

2. Open the provided URL in your web browser.

3. Upload invoice images, view extracted data, and manage items directly from the web interface.

## Dependencies

The project dependencies are managed through the `pyproject.toml` file and will be installed automatically when you install the package.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## Contact

For questions or suggestions, please contact [Amir Golparvar](mailto:amir.golparvar@physik.hu-berlin.de).