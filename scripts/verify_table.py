import json
import os
import time

from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

ARTIFACTS_DIR = r"C:\Users\vivek\.gemini\antigravity-ide\brain\59789402-409c-445e-b359-36125997a491"
SCREENSHOT_DIR = os.path.join(ARTIFACTS_DIR, "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)

widths = [1920, 1440, 1280, 1024, 768]
heights = [1080, 900, 800, 768, 1024]
results = []

try:
    driver.get("http://localhost:5173")
    time.sleep(2)

    # Wait for the table to appear
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".clinical-data-table tbody tr"))
    )

    for mode in ["light", "dark"]:
        # Set theme
        driver.execute_script(f"""
            if ('{mode}' === 'dark') {{
                document.documentElement.setAttribute('data-theme', 'dark');
                localStorage.setItem('clinicalai-theme', 'dark');
            }} else {{
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('clinicalai-theme', 'light');
            }}
        """)
        time.sleep(0.5)

        for w, h in zip(widths, heights):
            driver.set_window_size(w, h)
            time.sleep(0.8)

            # Check page-level horizontal scroll
            has_page_hscroll = driver.execute_script(
                "return document.documentElement.scrollWidth > document.documentElement.clientWidth;"
            )

            # Check table container scroll
            container_info = driver.execute_script("""
                const c = document.querySelector('.data-table-container');
                if (!c) return null;
                return {
                    scrollWidth: c.scrollWidth,
                    clientWidth: c.clientWidth,
                    hasScroll: c.scrollWidth > c.clientWidth
                };
            """)

            # Check overlap between care flags and risk column across all rendered rows
            overlap_check = driver.execute_script("""
                const rows = document.querySelectorAll('.clinical-data-table tbody tr');
                const checks = [];
                for (let i = 0; i < Math.min(rows.length, 10); i++) {
                    const row = rows[i];
                    const flagsCell = row.querySelector('.col-flags');
                    const riskCell = row.querySelector('.col-risk');
                    if (!flagsCell || !riskCell) continue;
                    
                    const flagsRect = flagsCell.getBoundingClientRect();
                    const riskRect = riskCell.getBoundingClientRect();

                    const pills = Array.from(flagsCell.querySelectorAll('.care-flag-pill, .flag-overflow-chip'));
                    let maxPillRight = flagsRect.left;
                    for (const p of pills) {
                        const pr = p.getBoundingClientRect();
                        if (pr.right > maxPillRight) maxPillRight = pr.right;
                    }

                    const pct = riskCell.querySelector('.risk-pct-large');
                    const badge = riskCell.querySelector('.risk-badge-pill');
                    const bar = riskCell.querySelector('.risk-mini-bar-track');

                    checks.push({
                        row: i,
                        flagsRight: flagsRect.right,
                        riskLeft: riskRect.left,
                        maxPillRight: maxPillRight,
                        flagsOverlapRisk: maxPillRight > riskRect.left,
                        hasDividerGap: (riskRect.left - flagsRect.right) >= 0,
                        pctLeft: pct ? pct.getBoundingClientRect().left : null,
                        badgeRight: badge ? badge.getBoundingClientRect().right : null,
                        barLeft: bar ? bar.getBoundingClientRect().left : null,
                        barWidth: bar ? bar.getBoundingClientRect().width : null,
                        riskCellWidth: riskRect.width
                    });
                }
                return checks;
            """)

            # Check console errors
            logs = driver.get_log("browser")
            errors = [log for log in logs if log["level"] == "SEVERE"]

            # Save screenshot
            shot_name = f"table_{mode}_{w}x{h}.png"
            shot_path = os.path.join(SCREENSHOT_DIR, shot_name)
            driver.save_screenshot(shot_path)

            try:
                table_card = driver.find_element(By.CSS_SELECTOR, '.table-section-card')
                card_shot_name = f"card_{mode}_{w}x{h}.png"
                table_card.screenshot(os.path.join(SCREENSHOT_DIR, card_shot_name))
            except WebDriverException:
                pass

            any_overlap = any(c["flagsOverlapRisk"] for c in overlap_check)

            res = {
                "mode": mode,
                "width": w,
                "height": h,
                "pageHScroll": has_page_hscroll,
                "containerScroll": container_info,
                "overlapsFound": any_overlap,
                "sampleRow": overlap_check[0] if overlap_check else None,
                "errorsCount": len(errors),
                "screenshot": shot_name
            }
            results.append(res)
            print(f"[{mode.upper()} {w}x{h}] Overlap: {any_overlap} | Page H-Scroll: {has_page_hscroll} | Container scroll: {container_info['hasScroll']} | Severe errors: {len(errors)}")

    # Test hover and focus highlight
    print("Testing row hover and focus highlight...")
    driver.set_window_size(1440, 900)
    time.sleep(0.5)
    first_row = driver.find_element(By.CSS_SELECTOR, ".clinical-data-table tbody tr:first-child")
    first_row.click()
    time.sleep(0.3)
    has_focused = "row-focused" in first_row.get_attribute("class")
    print(f"Row click sets row-focused: {has_focused}")

    shot_focused = os.path.join(SCREENSHOT_DIR, "table_row_focused_dark.png")
    driver.save_screenshot(shot_focused)

    with open(os.path.join(ARTIFACTS_DIR, "table_verification_results.json"), "w") as f:
        json.dump(results, f, indent=2)

finally:
    driver.quit()
