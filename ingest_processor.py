import os
import json
import pymongo
import fitz  
import time
import subprocess 
import sys 
import base64 

def get_text_from_file_chunk(file_path, start_page, end_page):
    """
    Extracts text from a specific page range of a PDF.
    """
    full_text = ""
    try:
        with fitz.open(file_path) as doc:
            if end_page > len(doc):
                end_page = len(doc)
            for page_num in range(start_page, end_page):
                page = doc.load_page(page_num)
                full_text += page.get_text()
        return full_text
    except Exception as e:
        print(f"Error reading PDF chunk {file_path} (Pages {start_page}-{end_page}): {e}")
        return None

def get_pdf_page_count(file_path):
    """Gets the total number of pages in a PDF."""
    try:
        with fitz.open(file_path) as doc:
            return len(doc)
    except Exception as e:
        print(f"Error opening PDF to get page count: {e}")
        return 0

def clean_ai_response(raw_text):
    """
    Cleans the AI's JSON response, removing markdown and whitespace.
    """
    print("  [Cleaner] Cleaning raw AI response...")
    try:
        start_index = raw_text.index('{')
        end_index = raw_text.rindex('}')
        json_string = raw_text[start_index:end_index+1]
        print("  [Cleaner] Response cleaned.")
        return json_string
    except ValueError:
        print("  [Cleaner] No JSON object found in response.")
        return raw_text

def call_ai_agent(text_input, mode):
    """
    Runs the ai_agent.py script, piping the text as a Base64 string.
    """
    process_args = [sys.executable, "ai_agent.py", mode]
    
    print(f"  [Processor] Converting text to Base64 and calling 'ai_agent.py' in '{mode}' mode...")
    
    try:
        text_bytes = text_input.encode('utf-8', errors='ignore')
        base64_bytes = base64.b64encode(text_bytes)
        base64_text_input = base64_bytes.decode('ascii')
        
        process = subprocess.Popen(
            process_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8' 
        )
        
        stdout_data, stderr_data = process.communicate(input=base64_text_input)
        
        if process.returncode != 0:
            print(f"  [AI Agent Error] Subprocess failed with code {process.returncode}")
            print(f"  [AI Agent Error] Stderr: {stderr_data}")
            return None
            
        if stderr_data:
             print(f"  [AI Agent Stderr]: {stderr_data.strip()}")

        return stdout_data
        
    except Exception as e:
        print(f"  [Processor Error] Failed to run subprocess: {e}")
        return None

def save_to_db(data_to_save, collection_name, document_id=None):
    """
    Saves or updates data in MongoDB. Imports pymongo locally.
    """
    import pymongo 
    
    db_client = None
    try:
        print("\nConnecting to MongoDB...")
        db_client = pymongo.MongoClient("mongodb://localhost:27018/", serverSelectionTimeoutMS=30000) 
        db_client.server_info()
        print("MongoDB connection successful.")
        db = db_client["bank_data"]
        
        safe_collection_name = collection_name.lower().replace(" ", "_").replace(".", "").replace("&", "and")
        bank_collection = db[safe_collection_name]
        
        if document_id:
            print(f"Updating document ID {document_id} in collection {safe_collection_name}...")
            bank_collection.update_one(
                {'_id': document_id},
                {'$set': {'data': data_to_save}}
            )
            print("Successfully updated document with detailed data.")
        else:
            print(f"Inserting new document into collection {safe_collection_name}...")
            insert_result = bank_collection.insert_one(data_to_save)
            print(f"Successfully inserted new document. ID: {insert_result.inserted_id}")
            if db_client: db_client.close()
            print("MongoDB connection closed.")
            return insert_result.inserted_id 

        if db_client: db_client.close()
        print("MongoDB connection closed.")
        return document_id

    except Exception as e:
        print(f"MongoDB connection/insertion failed: {e}")
        if db_client: db_client.close()
        return None


def process_file(file_path):
    print("--- Starting File Processing (Base64 Mode) ---")
    
    total_pages = get_pdf_page_count(file_path)
    if total_pages == 0: return False
    print(f"File has {total_pages} pages. Starting agent workflow...")

    CHUNK_SIZE = 3
    CHUNK_OVERLAP = 1
    API_COOLDOWN = 3
    
    print("\n--- STAGE 1: Finding Summary ---")
    found_chunk = None
    for i in range(0, total_pages, CHUNK_SIZE - CHUNK_OVERLAP):
        start_page = i
        end_page = i + CHUNK_SIZE
        print(f"  [Finder] Analyzing pages {start_page + 1}-{min(end_page, total_pages)}...")
        
        text_chunk = get_text_from_file_chunk(file_path, start_page, end_page)
        if not text_chunk: continue
            
        finder_response_raw = call_ai_agent(text_chunk, "find")
        if not finder_response_raw or finder_response_raw.strip().startswith('{"error"'):
            print(f"  [Finder] AI Agent returned an error: {finder_response_raw.strip()}")
            time.sleep(API_COOLDOWN)
            continue
            
        finder_response = finder_response_raw.strip().upper()
        print(f"  [Finder] Response: {finder_response}")
        if "YES" in finder_response:
            print(f"  [Finder] Found potential summary in pages {start_page + 1}-{min(end_page, total_pages)}.")
            found_chunk = text_chunk
            break 
        
        print(f"  [Cooldown] Waiting {API_COOLDOWN} seconds...")
        time.sleep(API_COOLDOWN)
    
    if not found_chunk:
        print("\nError: [Stage 1] Could not find summary. Aborting.")
        return False
        
    print("\n  [Extractor] Sending summary chunk to Extractor...")
    extractor_response_text = call_ai_agent(found_chunk, "extract")
    
    if not extractor_response_text or extractor_response_text.strip().startswith('{"error"}'):
        print(f"\nError: [Stage 1] Failed to extract summary: {extractor_response_text}")
        return False
        
    print(f"  [Extractor] AI Raw Response:\n{extractor_response_text}")
    
    base_document = None
    try:
        cleaned_json = clean_ai_response(extractor_response_text)
        base_document = json.loads(cleaned_json)
        print("Successfully parsed summary JSON.")
    except Exception as e:
        print(f"Error: [Stage 1] Failed to parse summary JSON: {e}")
        return False

    bank_name = base_document.get("bank_name")
    if not bank_name:
        print("Error: [Stage 1] Summary JSON has no 'bank_name'. Aborting.")
        return False
        
    new_document_id = save_to_db(base_document, bank_name, document_id=None)
    if not new_document_id:
        print("Error: [Stage 1] Failed to save base document to MongoDB. Aborting.")
        return False
        
    print("\n--- STAGE 2: Finding Full Balance Sheet ---")
    BALANCE_SHEET_CHUNK_SIZE = 10 
    found_balance_sheet_chunk = None

    for i in range(0, total_pages, BALANCE_SHEET_CHUNK_SIZE - CHUNK_OVERLAP):
        start_page = i
        end_page = i + BALANCE_SHEET_CHUNK_SIZE
        print(f"  [BS Finder] Analyzing pages {start_page + 1}-{min(end_page, total_pages)}...")
        
        text_chunk = get_text_from_file_chunk(file_path, start_page, end_page)
        if not text_chunk: continue
        
        finder_response_raw = call_ai_agent(text_chunk, "find_balance_sheet")
        if not finder_response_raw or finder_response_raw.strip().startswith('{"error"'):
            print(f"  [BS Finder] AI Agent returned an error: {finder_response_raw.strip()}")
            time.sleep(API_COOLDOWN)
            continue
            
        finder_response = finder_response_raw.strip().upper()
        print(f"  [BS Finder] Response: {finder_response}")
        if "YES" in finder_response:
            print(f"  [BS Finder] Found potential Balance Sheet in pages {start_page + 1}-{min(end_page, total_pages)}.")
            found_balance_sheet_chunk = text_chunk
            break 
        
        print(f"  [Cooldown] Waiting {API_COOLDOWN} seconds...")
        time.sleep(API_COOLDOWN)

    if not found_balance_sheet_chunk:
        print("\nWarning: [Stage 2] Could not find detailed Balance Sheet. Process finished with summary data only.")
        return True 

    print("\n  [BS Extractor] Sending balance sheet chunk to Extractor...")
    bs_extractor_response_text = call_ai_agent(found_balance_sheet_chunk, "extract_balance_sheet")

    if not bs_extractor_response_text or bs_extractor_response_text.strip().startswith('{"error"}'):
        print(f"\nError: [Stage 2] Failed to extract balance sheet: {bs_extractor_response_text}")
        return False

    print(f"  [BS Extractor] AI Raw Response:\n{bs_extractor_response_text}")

    try:
        cleaned_json = clean_ai_response(bs_extractor_response_text)
        detailed_data = json.loads(cleaned_json)
        print("Successfully parsed detailed balance sheet JSON.")
        
        save_to_db(detailed_data, bank_name, document_id=new_document_id)
        print("\n--- Process Finished Successfully (Two-Stage) ---")
        return True

    except Exception as e:
        print(f"Error: [Stage 2] Failed to parse or save detailed JSON: {e}")
        return False


if __name__ == "__main__":
    print("--- Running in Test Mode (Base64 Mode) ---")
    
    test_file = "uploads/download2.pdf"
    
    if os.path.exists(test_file):
        success = process_file(test_file)
        if success:
            print(f"\nTest finished successfully for {test_file}.")
        else:
            print(f"\nTest FAILED for {test_file}.")
    else:
        print(f"Test file not found: {test_file}")