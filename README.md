# Generative AI Financial Data Agent

A comprehensive automated system designed to ingest financial documents (such as Annual Reports or Bank Statements), extract key financial metrics using Generative AI, and store structured data in a MongoDB database. The project features a Flask-based web interface for file management and data review.

## Features

* **PDF Ingestion**: Automatically parses text from PDF documents using `PyMuPDF`.
* **AI-Powered Extraction**: Utilizes OpenRouter (DeepSeek model) to intelligently locate and extract:
    * **Financial Summaries**: Key metrics like Net Profit, Deposits, and Advances.
    * **Balance Sheets**: Detailed breakdown of Assets, Liabilities, and Equity.
* **Two-Stage Processing**: Implements a "Finder" agent to locate relevant pages and an "Extractor" agent to parse data into strict JSON schemas.
* **Database Integration**: Stores extracted financial data in **MongoDB** for persistent record-keeping.
* **Web Interface**: A user-friendly Dashboard built with **Flask** to upload files and review extracted data.
* **Authentication**: Secure login system to protect data views.

## Tech Stack

* **Language**: Python 3.x
* **Web Framework**: Flask (with Flask-Login)
* **Database**: MongoDB
* **AI/LLM**: OpenAI Client (via OpenRouter targeting `deepseek-r1t2-chimera`)
* **PDF Processing**: PyMuPDF (fitz)

## Installation

1.  **Clone the repository**
    ```bash
    git clone <repository-url>
    cd Generative_AI_Financial_Data_Agent
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up MongoDB**
    Ensure you have MongoDB installed. This project is configured to look for MongoDB on port **<Your port>**.
    ```bash
    # Example command to start mongo on the specific port
    mongod --port <your port>
    ```

4.  **Environment Configuration**
    Create a `.env` file in the root directory and add your OpenRouter API key:
    ```env
    OPENROUTER_API_KEY=your_api_key_here
    ```

## Usage

### 1. Run the Application
Start the Flask server:
```bash
python app.py
```
You should see output indicating the server is running on [http://127.0.0.1:5000](http://127.0.0.1:5000).

### 2. Access the Web Interface

* **Upload**: Select a PDF financial report and click "Upload". The system will process it in the background.
* **Login**: To view extracted data, navigate to the Login page.
    * Default Username: `admin`
    * Default Password: `password123` (Note: These credentials are hardcoded in `app.py` for demonstration purposes).
* **Review**: Once logged in, you can see a JSON-formatted breakdown of the data extracted from your uploaded documents.

## Project Structure

* **app.py**: The main Flask application entry point. Handles routing, authentication, and file uploads.
* **ingest_processor.py**: The core logic engine. It handles PDF chunking, calls the AI agent, and manages MongoDB operations.
* **ai_agent.py**: A CLI script (called by the processor) that interfaces with the AI API to perform specific tasks (Find/Extract).
* **test_*.py**: Utility scripts to verify your environment:
    * **test_api.py**: Checks connectivity to OpenRouter.
    * **test_db.py**: Checks connectivity to MongoDB (Port 27018).
    * **test_imports.py**: Verifies all Python dependencies are installed.

## Testing

To ensure your environment is set up correctly before running the main app, you can run the provided test scripts:
```bash
# Test API Connection
python test_api.py

# Test Database Connection
python test_db.py
```

## License

This project is licensed under the Apache License 2.0. See the LICENSE file for details.
