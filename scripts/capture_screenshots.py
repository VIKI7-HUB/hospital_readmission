import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

def capture(prefix="before"):
    os.makedirs("screenshots", exist_ok=True)
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1920,1080")
    d = webdriver.Chrome(options=opts)
    try:
        d.get("http://localhost:5173")
        time.sleep(2)
        d.save_screenshot(f"screenshots/{prefix}_worklist.png")
        print(f"Saved screenshots/{prefix}_worklist.png")

        # Calculator
        btn_calc = d.find_element(By.CSS_SELECTOR, "button[title='Risk calculator']")
        btn_calc.click()
        time.sleep(1)
        d.save_screenshot(f"screenshots/{prefix}_calculator.png")
        print(f"Saved screenshots/{prefix}_calculator.png")

        # Governance
        btn_gov = d.find_element(By.CSS_SELECTOR, "button[title='Model governance']")
        btn_gov.click()
        time.sleep(1)
        d.save_screenshot(f"screenshots/{prefix}_governance.png")
        print(f"Saved screenshots/{prefix}_governance.png")
    finally:
        d.quit()

if __name__ == "__main__":
    import sys
    prefix = sys.argv[1] if len(sys.argv) > 1 else "before"
    capture(prefix)
