import sys
import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import time


FINDER_PROMPT = """
You are a data-processing agent. You will be given a long string of
Base64 encoded text.
Your task is to:
1.  First, Base64-decode this string back into plain UTF-8 text.
2.  Second, analyze that decoded text. Does it contain a high-level,
    summary financial table? This table is usually labeled "Overview",
    "Financial Highlights", or "Performance".
3.  Do NOT say YES to the main, multi-page "Consolidated Balance Sheet".
    Only say YES to the high-level summary.
4.  Respond with only the word "YES" or "NO".
"""

EXTRACTOR_PROMPT = """
You are a data-processing agent. You will be given a long string of
Base64 encoded text.
Your task is to:
1.  First, Base64-decode this string back into plain UTF-8 text, replacing
    any invalid characters.
2.  Second, find the key financial information in that decoded text.
3.  Third, respond with ONLY a single, valid JSON object using this
    exact schema:
{
  "bank_name": "string (e.g., HDFC Bank)",
  "report_year": "string (e.g., 2024-25)",
  "schema_type": "annual_report_summary",
  "data": {
    "balance_sheet_size_cr": "integer",
    "profit_after_tax_cr": "integer",
    "deposits_cr": "integer",
    "advances_cr": "integer",
    "return_on_equity_percent": "float",
    "dividend_per_share_inr": "float"
  }
}
If a value is not found, use null.
Find the *latest* year's data.
"""

FINDER_BALANCE_SHEET_PROMPT = """
You are a financial analyst. You will be given a long string of
Base64 encoded text.
Your task is to:
1.  First, Base64-decode this string back into plain UTF-8 text.
2.  Second, analyze that decoded text. Does this text contain the *start*
    of the main, multi-page "CONSOLIDATED BALANCE SHEET"?
3.  This page will have headers like "ASSETS", "LIABILITIES",
    "Shareholder's Equity", "Cash and cash equivalents", "Loans", etc.
4.  Respond with only the word "YES" or "NO".
"""

EXTRACTOR_BALANCE_SHEET_PROMPT = """
You are an expert financial data extraction agent. You will be given a
long string of Base64 encoded text.
Your task is to:
1.  First, Base64-decode this string back into plain UTF-8 text, replacing
    any invalid characters.
2.  Second, find the key financial information in that decoded text, which
    is from a "Consolidated Balance Sheet".
3.  Third, respond with ONLY a single, valid JSON object using this
    exact schema. Be extremely detailed.

{
  "total_assets": "integer",
  "total_liabilities": "integer",
  "total_shareholders_equity": "integer",
  "asset_breakdown": {
    "cash_and_cash_equivalents": "integer",
    "loans_receivable": "integer",
    "investments": "integer",
    "property_plant_equipment": "integer",
    "other_assets": "integer"
  },
  "liability_breakdown": {
    "deposits": "integer",
    "borrowings": "integer",
    "other_liabilities": "integer"
  },
  "equity_breakdown": {
    "equity_share_capital": "integer",
    "reserves_and_surplus": "integer",
    "other_equity": "integer"
  }
}

If a value is not found, use null.
Find the numbers for the *latest* year (e.g., 2025 or 2024).
Extract all monetary values as simple integers.
"""



def get_ai_response(client, headers, text, prompt_type):
    
    if prompt_type == "find": system_prompt = FINDER_PROMPT
    elif prompt_type == "extract": system_prompt = EXTRACTOR_PROMPT
    elif prompt_type == "find_balance_sheet": system_prompt = FINDER_BALANCE_SHEET_PROMPT
    elif prompt_type == "extract_balance_sheet": system_prompt = EXTRACTOR_BALANCE_SHEET_PROMPT
    else: return '{"error": "Invalid prompt type"}'

    MAX_RETRIES = 3
    for attempt in range(MAX_RETRIES):
        try:
            completion = client.chat.completions.create(
                extra_headers=headers,
                model="tngtech/deepseek-r1t2-chimera:free",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text} 
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"  [AI Agent] Call failed (Attempt {attempt + 1}/{MAX_RETRIES}): {e}", file=sys.stderr)
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
            else:
                return f'{{"error": "AI API call failed", "details": "{str(e)}"}}'

def main():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print('{"error": "OPENROUTER_API_KEY not found"}')
        return

    headers_to_send = {
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "AI Bank Ingestion"
    }

    try:
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    except Exception as e:
        print(f'{{"error": "Failed to create AI client", "details": "{str(e)}"}}')
        return

    try:
        mode = sys.argv[1] 
    except IndexError:
        print('{"error": "No mode provided"}')
        return

    base64_input = sys.stdin.read()
    if not base64_input:
        print('{"error": "No Base64 text provided via stdin"}')
        return
        
    response = get_ai_response(client, headers_to_send, base64_input, mode)
    
    print(response)

if __name__ == "__main__":
    main()