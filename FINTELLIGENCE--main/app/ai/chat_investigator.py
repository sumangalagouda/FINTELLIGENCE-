import spacy
from app.ai.ollama_client import call_ollama
from app.models.transaction import Transaction

# Load NLP model safely
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def ask_investigator(question: str, case_id: str, conversation_history: list = None) -> dict:
    # 1. Use spaCy NER to extract account numbers / names
    doc = nlp(question)
    extracted_entities = [ent.text for ent in doc.ents if ent.label_ in ['PERSON', 'ORG', 'MONEY', 'CARDINAL']]
    
    # Simple regex fallback for account like extraction
    import re
    accounts = re.findall(r'[A-Z]+_ACC\d+', question)
    
    keywords = set(extracted_entities + accounts)
    
    # 2. Fetch relevant transactions (basic keyword search)
    query = Transaction.query.filter_by(case_id=case_id, is_failed=False).order_by(Transaction.date)
    
    # If the user asks about specific threshold
    amounts = re.findall(r'\b\d{4,}\b', question) # looking for >1000 amounts roughly
    
    transactions = query.all()
    
    # Filter locally to avoid complex DB queries for this simplified version
    relevant_txns = []
    for t in transactions:
        text_to_search = f"{t.sender_account} {t.receiver_account} {t.description} {t.amount}".lower()
        question_lower = question.lower()
        
        # Heuristics:
        # If question has specific account, filter
        is_relevant = False
        
        if any(acc.lower() in text_to_search for acc in accounts):
            is_relevant = True
        elif any(k.lower() in text_to_search for k in keywords):
            is_relevant = True
        elif 'top' in question_lower or 'most' in question_lower:
            # just include all to let Groq aggregate, but cap at 100
            is_relevant = True
        elif 'suspicious' in question_lower and getattr(t, 'is_flagged', False):
            is_relevant = True
        elif not keywords and not accounts:
            # If no specific target, include all
            is_relevant = True
            
        if is_relevant:
            relevant_txns.append(t)
            
    # Cap to avoid token limits
    relevant_txns = relevant_txns[-100:] # last 100 relevant
    
    # 3. Build context string
    context_lines = []
    txn_ids = []
    for t in relevant_txns:
        context_lines.append(f"Txn {t.id}: {t.date} | ₹{t.amount} | {t.type} | From: {t.sender_account} To: {t.receiver_account} | Desc: {t.description}")
        txn_ids.append(t.id)
        
    context_str = "\n".join(context_lines)
    if not context_str:
        context_str = "No specific transactions found matching the query context."

    system_prompt = (
        "You are a senior financial fraud investigator with 20 years of experience in AML "
        "and forensic accounting in India. You analyze bank statement transaction data "
        "provided to you. Answer investigator questions precisely and concisely. "
        "Always cite specific transaction IDs and amounts when making claims. "
        "Format all amounts in Indian Rupees with ₹ symbol and use Indian number formatting "
        "(lakhs, crores). Be direct. Do not add disclaimers."
    )
    
    user_prompt = (
        f"Context Transactions:\n{context_str}\n\n"
        f"Investigator Question: {question}"
    )
    
    # 4. Send to Groq
    try:
        answer = call_ollama(system_prompt, user_prompt, max_tokens=1500)
    except RuntimeError as err:
        answer = str(err)
    except Exception:
        answer = "AI analysis is currently unavailable. Please try again later."
    
    # 5. Return response
    confidence = "high"
    if "I don't have enough information" in answer or not relevant_txns:
        confidence = "low"
        
    return {
        "answer": answer,
        "transactions_referenced": txn_ids,
        "confidence": confidence
    }
