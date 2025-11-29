# """
# NLP Service using Gemini API for transaction extraction
# """
# import os
# from typing import Optional
# from pydantic import BaseModel
# import google.genai as gai

# # Configure Gemini API
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-api-key-here")
# client = gai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# class TransactionIntent(BaseModel):
#     amount: float
#     category: str
#     type: str  # 'deposit' or 'withdrawal'
#     merchant: Optional[str] = None
#     confidence: float

# class NLPService:
#     def __init__(self):
#         # Initialize Gemini model
#         self.model = gai.GenerativeModel('gemini-1.5-flash')
        
#         # Define the function schema for transaction extraction
#         self.transaction_tool = {
#             "function_declarations": [
#                 {
#                     "name": "record_transaction",
#                     "description": "Record a financial transaction (income or expense) from user's natural language description",
#                     "parameters": {
#                         "type": "object",
#                         "properties": {
#                             "amount": {
#                                 "type": "number",
#                                 "description": "The monetary amount of the transaction in Rupees"
#                             },
#                             "category": {
#                                 "type": "string",
#                                 "description": "Category of the transaction. Examples: food, groceries, travel, rent, bills, entertainment, salary, freelance, etc."
#                             },
#                             "transaction_type": {
#                                 "type": "string",
#                                 "enum": ["deposit", "withdrawal"],
#                                 "description": "Type of transaction. 'deposit' for income/credit, 'withdrawal' for expense/debit"
#                             },
#                             "merchant": {
#                                 "type": "string",
#                                 "description": "Name of merchant or source (e.g. Swiggy, Ola, Salary). Optional."
#                             }
#                         },
#                         "required": ["amount", "category", "transaction_type"]
#                     }
#                 }
#             ]
#         }
    
#     def extract_transaction_details(self, text: str) -> Optional[TransactionIntent]:
#         """
#         Extract transaction details from natural language using Gemini API
#         """
#         try:
#             # Create a chat with the model using function calling
#             chat = self.model.start_chat()
            
#             # System instructions embedded in the prompt
#             prompt = f"""You are a financial assistant helping users record transactions.
            
# User's message: "{text}"

# Analyze this message and extract the transaction details. Determine:
# 1. The amount in Rupees (Rs or ₹)
# 2. The category (food, groceries, travel, bills, rent, entertainment, salary, etc.)
# 3. Whether it's income (deposit) or expense (withdrawal)
# 4. Any merchant/source name if mentioned

# If the user mentions spending, paying, bought, or similar words → it's a 'withdrawal'
# If the user mentions received, got, income, salary, earned → it's a 'deposit'

# Call the record_transaction function with the extracted details."""

#             response = chat.send_message(
#                 prompt,
#                 tools=[self.transaction_tool]
#             )
            
#             # Check if model wants to call the function
#             if response.candidates[0].content.parts[0].function_call:
#                 function_call = response.candidates[0].content.parts[0].function_call
                
#                 # Extract the arguments
#                 args = dict(function_call.args)
                
#                 return TransactionIntent(
#                     amount=float(args.get('amount', 0)),
#                     category=args.get('category', 'uncategorized'),
#                     type=args.get('transaction_type', 'withdrawal'),
#                     merchant=args.get('merchant'),
#                     confidence=0.95  # Gemini confidence is high
#                 )
#             else:
#                 # Model couldn't extract transaction details
#                 return None
                
#         except Exception as e:
#             print(f"Gemini API error: {e}")
#             # Fallback to simple regex if API fails
#             return self._regex_fallback(text)
    
#     def _regex_fallback(self, text: str) -> Optional[TransactionIntent]:
#         """Fallback regex parser if Gemini API fails"""
#         import re
        
#         text = text.lower().strip()
#         amount_match = re.search(r'(?:rs\.?|₹)?\s*(\d+(?:\.\d{2})?)\s*(?:rs\.?|₹)?', text)
        
#         if not amount_match:
#             return None
        
#         amount = float(amount_match.group(1))
#         income_keywords = ['received', 'got', 'income', 'salary', 'credit', 'deposit']
#         is_income = any(word in text for word in income_keywords)
        
#         return TransactionIntent(
#             amount=amount,
#             category="uncategorized",
#             type="deposit" if is_income else "withdrawal",
#             merchant=None,
#             confidence=0.6
#         )

# nlp_service = NLPService()

import os
from typing import Optional
from pydantic import BaseModel
import google.genai as genai
from google.genai import types

# Configure Gemini API
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

class TransactionIntent(BaseModel):
    amount: float
    category: str
    type: str  # 'deposit' or 'withdrawal'
    merchant: Optional[str] = None
    confidence: float

class NLPService:
    def __init__(self):
        # Define the function declaration for transaction extraction
        self.record_transaction_func = types.FunctionDeclaration(
            name="record_transaction",
            description="Record a financial transaction (income or expense) from user's natural language description",
            parameters={
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "The monetary amount of the transaction in Rupees"
                    },
                    "category": {
                        "type": "string",
                        "description": "Category of the transaction. Examples: food, groceries, travel, rent, bills, entertainment, salary, freelance, etc."
                    },
                    "transaction_type": {
                        "type": "string",
                        "enum": ["deposit", "withdrawal"],
                        "description": "Type of transaction. 'deposit' for income/credit, 'withdrawal' for expense/debit"
                    },
                    "merchant": {
                        "type": "string",
                        "description": "Name of merchant or source (e.g. Swiggy, Ola, Salary). Optional."
                    }
                },
                "required": ["amount", "category", "transaction_type"]
            }
        )
        
        # Create tool with function declaration
        self.transaction_tool = types.Tool(
            function_declarations=[self.record_transaction_func]
        )
    
    def extract_transaction_details(self, text: str) -> Optional[TransactionIntent]:
        """
        Extract transaction details from natural language using Gemini API
        """
        try:
            # System instruction
            system_instruction = """You are a financial assistant helping users record transactions.
Analyze user messages and extract transaction details using the record_transaction function.

Rules:
- If user mentions spending, paying, bought, purchased → it's a 'withdrawal'
- If user mentions received, got, income, salary, earned, credited → it's a 'deposit'
- Extract amount in Rupees (handle Rs, ₹, rupees variations)
- Identify category from context (food, groceries, travel, bills, etc.)
- Extract merchant name if mentioned"""

            # Create prompt
            prompt = f"User message: {text}\n\nExtract the transaction details and call the record_transaction function."
            
            # Generate content with function calling
            response = client.models.generate_content(
                model='gemini-2.0-flash-exp',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    tools=[self.transaction_tool],
                    temperature=0.1
                )
            )
            
            # Check if function was called
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        
                        # Extract arguments
                        args = function_call.args
                        if args:
                            return TransactionIntent(
                                amount=float(args.get('amount', 0)),
                                category=args.get('category', 'uncategorized'),
                                type=args.get('transaction_type', 'withdrawal'),
                                merchant=args.get('merchant'),
                                confidence=0.95
                            )
            
            # Model didn't call function
            return None
                
        except Exception as e:
            print(f"Gemini API error: {e}")
            # Fallback to regex
            return self._regex_fallback(text)
    
    def _regex_fallback(self, text: str) -> Optional[TransactionIntent]:
        """Fallback regex parser if Gemini API fails"""
        import re
        
        text = text.lower().strip()
        amount_match = re.search(r'(?:rs\.?|₹)?\s*(\d+(?:\.\d{2})?)\s*(?:rs\.?|₹)?', text)
        
        if not amount_match:
            return None
        
        amount = float(amount_match.group(1))
        income_keywords = ['received', 'got', 'income', 'salary', 'credit', 'deposit']
        is_income = any(word in text for word in income_keywords)
        
        return TransactionIntent(
            amount=amount,
            category="uncategorized",
            type="deposit" if is_income else "withdrawal",
            merchant=None,
            confidence=0.6
        )

nlp_service = NLPService()
