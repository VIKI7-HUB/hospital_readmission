from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

os.makedirs("screenshots_refined", exist_ok=True)
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--window-size=1920,1080')
d = webdriver.Chrome(options=opts)

try:
    # 1. Worklist in Dark Mode
    d.get('http://localhost:5173/#worklist')
    time.sleep(2)
    d.save_screenshot('screenshots_refined/worklist_dark.png')
    print("Saved worklist_dark.png")

    # 2. Drawer Open in Dark Mode
    rows = d.find_elements(By.CSS_SELECTOR, "tr")
    for r in rows:
        if "ENC-" in r.text:
            r.click()
            break
    time.sleep(1)
    d.save_screenshot('screenshots_refined/drawer_dark.png')
    print("Saved drawer_dark.png")

    # Close drawer by pressing Escape or clicking close button
    close_btns = d.find_elements(By.CSS_SELECTOR, ".drawer-close-btn")
    if close_btns:
        close_btns[0].click()
        time.sleep(0.5)

    # 3. Worklist in Light Mode
    theme_btns = d.find_elements(By.CSS_SELECTOR, "button[title*='Switch to' i]")
    if theme_btns:
        theme_btns[0].click()
        time.sleep(1)
        d.save_screenshot('screenshots_refined/worklist_light.png')
        print("Saved worklist_light.png")
        # switch back to dark mode
        theme_btns[0].click()
        time.sleep(0.5)

    # 4. Calculator Initial State
    d.get('http://localhost:5173/#calculator')
    time.sleep(1.5)
    d.save_screenshot('screenshots_refined/calculator_initial.png')
    print("Saved calculator_initial.png")

    # 5. Calculator After Calculating
    calc_btns = d.find_elements(By.CSS_SELECTOR, ".primary-calc-btn")
    if calc_btns:
        calc_btns[0].click()
        time.sleep(2)
        d.save_screenshot('screenshots_refined/calculator_calculated.png')
        print("Saved calculator_calculated.png")

    # 6. Governance Page
    d.get('http://localhost:5173/#governance')
    time.sleep(1.5)
    d.save_screenshot('screenshots_refined/governance_dark.png')
    print("Saved governance_dark.png")

finally:
    d.quit()
