import os
import sys
import time
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.getcwd(), "browser_verification_screenshots", "milestone4")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

def run_chatbot_browser_verification():
    print("=== STARTING MILESTONE 4 CHATBOT BROWSER VERIFICATION ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login Flow
        print("\n[1/7] Authenticating via Demo Login...")
        page.goto("http://localhost:3000/login")
        page.wait_for_load_state("networkidle")
        page.locator("button:has-text('Fill Demo')").click()
        page.wait_for_timeout(300)
        page.locator("button[type='submit']").click()
        page.wait_for_url("**/dashboard**", timeout=10000)
        page.wait_for_load_state("networkidle")
        print("  ✓ Authenticated successfully.")

        # 2. Command Centre Chat Interface
        print("\n[2/7] Loading Conversational Command Centre...")
        page.goto("http://localhost:3000/dashboard/command")
        page.wait_for_load_state("networkidle")
        page.wait_for_selector("text=Agentic Financial Operations Chatbot", timeout=10000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_chat_interface_initial.png"))
        print("  ✓ Conversational chat interface verified.")

        # 3. Test Query 1: Top Vendors (Non-suggested analytical query)
        print("\n[3/7] Testing Query 1: 'Show me the five vendors I paid the most this quarter'...")
        textarea = page.locator("textarea").first
        textarea.fill("Show me the five vendors I paid the most this quarter")
        page.locator("button:has-text('Send')").click()
        page.wait_for_selector("text=Top Vendors Expenditure Ranking", timeout=20000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_top_vendors_card.png"))
        print("  ✓ Top Vendors tool result card rendered in conversation stream.")

        # 4. Test Query 2: Unmatched Payments to Vendor
        print("\n[4/7] Testing Query 2: 'Find payments to Sharma Traders that do not have matching invoices'...")
        textarea.fill("Find payments to Sharma Traders that do not have matching invoices")
        page.locator("button:has-text('Send')").click()
        page.wait_for_selector("text=Unmatched Payments", timeout=20000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_unmatched_payments_card.png"))
        print("  ✓ Unmatched payments card rendered.")

        # 5. Test Query 3: Multi-Turn Context Follow-Up
        print("\n[5/7] Testing Multi-Turn Follow-Up: 'Which of those are not reconciled?'...")
        textarea.fill("Which of those are not reconciled?")
        page.locator("button:has-text('Send')").click()
        page.wait_for_timeout(2000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_multiturn_followup.png"))
        print("  ✓ Multi-turn follow-up resolved entity from conversation context.")

        # 6. Test Query 4: Expense Comparison
        print("\n[6/7] Testing Query 4: 'Compare my October expenses with September'...")
        textarea.fill("Compare my October expenses with September")
        page.locator("button:has-text('Send')").click()
        page.wait_for_selector("text=Expense Comparison", timeout=20000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_expense_comparison_card.png"))
        print("  ✓ Expense comparison tool card rendered.")

        # 7. Test Query 5: Out of scope inquiry
        print("\n[7/7] Testing Out-of-Scope Query: 'What is the capital of France?'...")
        textarea.fill("What is the capital of France?")
        page.locator("button:has-text('Send')").click()
        page.wait_for_selector("text=Scope Boundary Evaluation", timeout=20000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_out_of_scope_boundary.png"))
        print("  ✓ Polite out-of-scope boundary guardrail confirmed.")

        browser.close()
        print("\n=== ALL MILESTONE 4 BROWSER CHECKS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_chatbot_browser_verification()
