from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import os

os.makedirs("screenshots_industry", exist_ok=True)
opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--window-size=1920,1080')
d = webdriver.Chrome(options=opts)

try:
    # 1. Worklist with new sidebar dropdowns and quick filter buttons
    d.get('http://localhost:5173/#worklist')
    time.sleep(2)
    d.save_screenshot('screenshots_industry/1_worklist_overview.png')
    print("Saved 1_worklist_overview.png")

    # 2. Test quick filter: click 'High Risk' filter pill
    high_pills = d.find_elements(By.CSS_SELECTOR, ".quick-filter-btn.high")
    if high_pills:
        high_pills[0].click()
        time.sleep(1)
        d.save_screenshot('screenshots_industry/2_worklist_filtered_high_risk.png')
        print("Saved 2_worklist_filtered_high_risk.png")

    # 3. Open patient drawer on first high-risk encounter
    rows = d.find_elements(By.CSS_SELECTOR, "tr")
    for r in rows:
        if "ENC-" in r.text:
            r.click()
            break
    time.sleep(1)
    d.save_screenshot('screenshots_industry/3_encounter_drawer_chart.png')
    print("Saved 3_encounter_drawer_chart.png")

    # Close drawer
    close_btns = d.find_elements(By.CSS_SELECTOR, ".drawer-close-btn")
    if close_btns:
        close_btns[0].click()
        time.sleep(0.5)

    # 4. Bedside Calculator
    d.get('http://localhost:5173/#calculator')
    time.sleep(1.5)
    d.save_screenshot('screenshots_industry/4_calculator_view.png')
    print("Saved 4_calculator_view.png")

    # 5. Model Governance - Performance Tab (default)
    d.get('http://localhost:5173/#governance')
    time.sleep(1.5)
    d.save_screenshot('screenshots_industry/5_governance_performance.png')
    print("Saved 5_governance_performance.png")

    # 6. Model Governance - Click Demographic Fairness Tab
    gov_tabs = d.find_elements(By.CSS_SELECTOR, ".gov-tab-btn")
    for t in gov_tabs:
        if "Fairness" in t.text:
            t.click()
            break
    time.sleep(1)
    d.save_screenshot('screenshots_industry/6_governance_fairness.png')
    print("Saved 6_governance_fairness.png")

    # 7. Model Governance - Click Data Pipeline Tab
    for t in gov_tabs:
        if "Pipeline" in t.text:
            t.click()
            break
    time.sleep(1)
    d.save_screenshot('screenshots_industry/7_governance_pipeline.png')
    print("Saved 7_governance_pipeline.png")

finally:
    d.quit()
