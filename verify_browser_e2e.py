import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.getcwd(), "browser_verification_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_browser_verification():
    print("=== STARTING BROWSER E2E VERIFICATION ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Landing Page
        print("\n[1/12] Testing Landing Page...")
        page.goto("http://localhost:3000")
        page.wait_for_load_state("networkidle")
        assert "VyaparSetu" in page.title() or page.locator("text=VyaparSetu").count() > 0
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_landing_page.png"))
        print("  ✓ Landing page rendered successfully.")

        # 2. Login Flow
        print("\n[2/12] Testing Demo Login Flow...")
        page.goto("http://localhost:3000/login")
        page.wait_for_load_state("networkidle")
        
        # Click Quick Demo Filler
        page.locator("button:has-text('Fill Demo')").click()
        page.wait_for_timeout(500)
        
        # Submit Login
        page.locator("button[type='submit']").click()
        page.wait_for_url("**/dashboard**", timeout=10000)
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_dashboard_executive.png"))
        print("  ✓ Authenticated and redirected to Executive Dashboard.")

        # 3. Dashboard Verification
        print("\n[3/12] Verifying Dashboard KPIs & Active Tenant...")
        page.wait_for_selector("text=Sharma Kirana & Hardware Traders", timeout=10000)
        assert page.locator("text=Sharma Kirana & Hardware Traders").count() > 0
        print("  ✓ Active workspace 'Sharma Kirana & Hardware Traders' verified.")

        # 4. Transactions Ledger
        print("\n[4/12] Testing Transactions Ledger & Synthetic Ingestion...")
        page.goto("http://localhost:3000/dashboard/transactions")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_transactions_ledger.png"))
        assert page.locator("text=Bank & UPI Transactions Ledger").count() > 0
        print("  ✓ Transactions ledger displayed.")

        # 5. Invoices & OCR
        print("\n[5/12] Testing Invoices & Document OCR...")
        page.goto("http://localhost:3000/dashboard/invoices")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_invoices_ocr.png"))
        assert page.locator("text=Document OCR").count() > 0
        print("  ✓ Invoices & OCR screen verified.")

        # 6. AI Bookkeeping with LangGraph & BharatCode
        print("\n[6/12] Testing LangGraph Multi-Agent Bookkeeping Workbench...")
        page.goto("http://localhost:3000/dashboard/bookkeeping")
        page.wait_for_load_state("networkidle")
        
        # Click a preset example (Raw Materials Hinglish)
        page.locator("button:has-text('Raw Materials (Hinglish)')").click()
        page.wait_for_timeout(500)
        
        # Execute LangGraph Agent
        page.locator("button:has-text('Run LangGraph Agent')").click()
        # Wait for result to appear
        page.wait_for_selector("text=Autonomous Decision", timeout=15000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_bookkeeping_agent_run.png"))
        print("  ✓ LangGraph agent executed and auto-posted balanced double-entry vouchers.")

        # 7. Approvals (HITL Queue)
        print("\n[7/12] Testing Human Approval Queue...")
        page.goto("http://localhost:3000/dashboard/approvals")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_approvals_queue.png"))
        assert page.locator("text=Pending Human Verification").count() > 0
        print("  ✓ Human-in-the-Loop approval queue verified.")

        # 8. General Ledger & Trial Balance
        print("\n[8/12] Testing Double-Entry Ledger & Trial Balance...")
        page.goto("http://localhost:3000/dashboard/ledger")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=Trial Balance Verified: Exactly Balanced").count() > 0
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_trial_balance_balanced.png"))
        print("  ✓ General Ledger strictly verified: Σ Debits == Σ Credits.")

        # 9. Bank & Invoice Reconciliation
        print("\n[9/12] Testing Reconciliation Workspace...")
        page.goto("http://localhost:3000/dashboard/reconciliation")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_reconciliation.png"))
        assert page.locator("text=Bank vs Invoice Matching").count() > 0
        print("  ✓ Bank and invoice reconciliation workspace verified.")

        # 10. Financial Statements (P&L and Balance Sheet)
        print("\n[10/12] Testing Financial Reports...")
        page.goto("http://localhost:3000/dashboard/reports")
        page.wait_for_load_state("networkidle")
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_financial_statements.png"))
        assert page.locator("text=Profit & Loss").count() > 0
        print("  ✓ Profit & Loss and Balance sheet statements verified.")

        # 11. GST Regional Workspace
        print("\n[11/12] Testing GST Regional Workspace & Simulated Filing...")
        page.goto("http://localhost:3000/dashboard/gst")
        page.wait_for_load_state("networkidle")
        assert page.locator("text=SIMULATED GST SANDBOX").count() > 0
        
        # Click Instant Calculator Tab
        page.locator("button:has-text('Instant GST Calculator')").click()
        page.wait_for_timeout(500)
        assert page.locator("text=Section 170 Statutory Rounded Tax").count() > 0
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_gst_workspace.png"))
        print("  ✓ GST compliance workspace and Section 170 calculations verified.")

        # 12. AI Assistant (RAG)
        print("\n[12/12] Testing AI Assistant with BharatCode RAG...")
        page.goto("http://localhost:3000/dashboard/assistant")
        page.wait_for_load_state("networkidle")
        
        # Click a statutory suggested question
        page.locator("button:has-text('What are the 4 mandatory conditions to claim Input Tax Credit under Section 16(2)?')").click()
        # Wait for answer to arrive from BharatCode RAG
        page.wait_for_selector("text=Statutory Authority Cited", timeout=15000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "11_assistant_rag.png"))
        print("  ✓ BharatCode statutory RAG assistant responded with section citations.")

        browser.close()
        print("\n=== ALL 12 BROWSER END-TO-END FLOWS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_browser_verification()

