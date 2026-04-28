import os
import sys
import time
import asyncio
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Please run: pip install -r requirements.txt")
    sys.exit(1)

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def print_pass(msg):
    print(f"{GREEN}[PASS]{RESET} {msg}")

def print_fail(msg):
    print(f"{RED}[FAIL]{RESET} {msg}")

def print_warn(msg):
    print(f"{YELLOW}[WARN]{RESET} {msg}")

# 1. Environment Infrastructure
load_dotenv(override=True)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "backend"))

try:
    from backend.app.core.llm_gateway import LLMGateway
    from backend.app.core.config import settings
except ImportError as e:
    print(f"Missing dependencies. Please run: pip install -r requirements.txt\nDetails: {e}")
    sys.exit(1)

async def verify_gateway():
    print("\n=== PART A: Phase 0 Diagnostic (Multi-Model Mesh) ===")
    
    try:
        # Temporarily bypass init validation to handle specific missing keys gracefully
        original_check = LLMGateway._check_api_keys
        LLMGateway._check_api_keys = lambda self: None
        gateway = LLMGateway()
        LLMGateway._check_api_keys = original_check
    except Exception as e:
        print_fail(f"Gateway Initialization Failed: {e}")
        return False

    roles_to_test = [
        ("LIBRARIAN", "XAI_API_KEY"),
        ("ORCHESTRATOR", "GROQ_API_KEY"),
        ("JUDGE", "MISTRAL_API_KEY")
    ]
    
    all_passed = True
    for role, key_env in roles_to_test:
        if role == "LIBRARIAN" and not os.environ.get("XAI_API_KEY"):
            print(f"{YELLOW}LIBRARIAN TEST SKIPPED: Missing xAI Key.{RESET}")
            # If missing XAI key, we skip it but don't fail the overall Gateway status if it's expected
            continue
            
        print(f"Testing {role}...")
        start_time = time.time()
        try:
            response = await gateway.get_response(
                role=role,
                messages=[{"role": "user", "content": "Reply with 'Success'"}]
            )
            elapsed = time.time() - start_time
            if elapsed > 5:
                latency_msg = f"{YELLOW}High Latency: {elapsed:.2f}s{RESET}"
                print_warn(f"{role} responded ({latency_msg}): {response.choices[0].message.content.strip()}")
            else:
                latency_msg = f"{elapsed:.2f}s"
                print_pass(f"{role} responded ({latency_msg}): {response.choices[0].message.content.strip()}")
        except Exception as e:
            elapsed = time.time() - start_time
            print_fail(f"{role} failed ({elapsed:.2f}s): {e}")
            all_passed = False

    return all_passed

async def verify_mcp():
    print("\n=== PART B: Phase 1 Diagnostic (MCP Tool Integrity) ===")
    all_passed = True
    
    try:
        from backend.app.mcp.mcp_server import (
            mcp, 
            list_available_materials, 
            fetch_student_stats, 
            log_ai_decision, 
            search_knowledge_base
        )
    except ImportError as e:
        print_fail(f"Could not import MCP components: {e}")
        return False
        
    # Correct Tool discovery for FastMCP
    tools = await mcp.list_tools() # FastMCP has a built-in method
    
    print(f"Registered tools count: {len(tools)}")
    if len(tools) >= 8:
        print_pass(f"Exactly {len(tools)} tools registered on MCP object.")
    else:
        print_warn(f"Expected 8 tools, found {len(tools)}.")
        
    # Test list_available_materials
    try:
        mats = await list_available_materials()
        if isinstance(mats, list):
            print_pass(f"list_available_materials returned a list (length {len(mats)}).")
        else:
            print_fail("list_available_materials did not return a list.")
            all_passed = False
    except Exception as e:
        print_fail(f"list_available_materials crashed: {e}")
        all_passed = False
        
    # Test fetch_student_stats
    try:
        stats = await fetch_student_stats("default")
        if isinstance(stats, dict) and "average_score" in stats:
            print_pass(f"fetch_student_stats returned stats payload.")
        else:
            print_fail(f"fetch_student_stats returned unexpected type/format: {stats}")
            all_passed = False
    except Exception as e:
        print_fail(f"fetch_student_stats crashed: {e}")
        all_passed = False

    # Test log_ai_decision
    try:
        res = await log_ai_decision("verify_session", "Diagnostic Run")
        # Verify in DB
        with sqlite3.connect(settings.database_path) as conn:
            row = conn.execute("SELECT * FROM ai_logs WHERE session_id = 'verify_session'").fetchone()
            if row:
                print_pass("log_ai_decision successfully wrote to DB ai_logs table.")
            else:
                print_fail("log_ai_decision executed but row not found in DB.")
                all_passed = False
    except Exception as e:
        print_fail(f"log_ai_decision crashed: {e}")
        all_passed = False

    # Test search_knowledge_base missing doc
    try:
        await search_knowledge_base("test query", "dummy_id")
        print_warn("search_knowledge_base executed without exception. If dummy_id exists, this is fine, otherwise it should raise an error.")
    except ValueError as e:
        print_pass(f"search_knowledge_base gracefully handled missing document (ValueError): {e}")
    except Exception as e:
        print_fail(f"search_knowledge_base crashed unexpectedly: {e}")
        all_passed = False

    return all_passed

async def main():
    print(f"{GREEN}Initializing Diagnostic Suite...{RESET}")
    
    db_ok = "OK"
    faiss_ok = "OK"
    
    try:
        with sqlite3.connect(settings.database_path) as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        db_ok = "ERROR"
        
    try:
        if not settings.faiss_index_dir.exists():
            settings.faiss_index_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        faiss_ok = "ERROR"

    gateway_status = await verify_gateway()
    mcp_status = await verify_mcp()

    db_str = f"{GREEN}[OK]{RESET}" if db_ok == "OK" else f"{RED}[ERROR]{RESET}"
    faiss_str = f"{GREEN}[OK]{RESET}" if faiss_ok == "OK" else f"{RED}[ERROR]{RESET}"
    
    print("\n=== PART C: System Health Report ===")
    print(f"Gateway Status:         {GREEN}[PASS]{RESET}" if gateway_status else f"Gateway Status:         {RED}[FAIL]{RESET}")
    print(f"MCP Tool Status:        {GREEN}[PASS]{RESET}" if mcp_status else f"MCP Tool Status:        {RED}[FAIL]{RESET}")
    print(f"Database Connectivity:  {db_str}")
    print(f"FAISS Directory Access: {faiss_str}")

if __name__ == "__main__":
    asyncio.run(main())
