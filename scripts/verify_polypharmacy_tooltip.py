import os
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

ARTIFACTS_DIR = r"C:\Users\vivek\.gemini\antigravity-ide\brain\59789402-409c-445e-b359-36125997a491"
SCREENSHOT_DIR = os.path.join(ARTIFACTS_DIR, "screenshots_polypharmacy")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

options = Options()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")

driver = webdriver.Chrome(options=options)
widths = [1920, 1440, 1024]
heights = [1080, 900, 768]
report = []

try:
    for mode in ["light", "dark"]:
        for w, h in zip(widths, heights):
            driver.set_window_size(w, h)
            driver.get("http://localhost:5173")
            time.sleep(1.5)

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

            # 1. Check for popups/toasts on page load
            toasts_on_load = driver.execute_script("""
                return document.querySelectorAll('[data-sonner-toast]').length;
            """)

            # 2. Check table legend
            legend_text = driver.execute_script("""
                const l = document.querySelector('.table-legend-bar');
                return l ? l.innerText.trim() : null;
            """)

            # 3. Test hover on Meds column header info icon
            info_icon = driver.find_element(By.CSS_SELECTOR, ".th-info-icon-btn")
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", info_icon)
            time.sleep(0.3)
            actions = ActionChains(driver)
            actions.move_to_element(info_icon).perform()
            time.sleep(0.5) # Wait > 300ms

            tooltip_count_hover_info = driver.execute_script("""
                return document.querySelectorAll('.clinical-shared-tooltip').length;
            """)
            tooltip_text_info = driver.execute_script("""
                const t = document.querySelector('.clinical-shared-tooltip-content');
                return t ? t.innerText.trim() : null;
            """)

            # Move away
            actions.move_by_offset(0, -50).perform()
            time.sleep(0.2)
            tooltip_count_after_leave = driver.execute_script("""
                return document.querySelectorAll('.clinical-shared-tooltip').length;
            """)

            # 4. Test hover on polypharmacy chip in first available row
            poly_chips = driver.find_elements(By.CSS_SELECTOR, ".polypharmacy-indicator")
            chip_hover_ok = False
            chip_tooltip_text = None
            if poly_chips:
                chip = poly_chips[0]
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chip)
                time.sleep(0.3)
                actions = ActionChains(driver)
                actions.move_to_element(chip).perform()
                time.sleep(0.5)
                chip_tooltip_count = driver.execute_script("""
                    return document.querySelectorAll('.clinical-shared-tooltip').length;
                """)
                chip_tooltip_text = driver.execute_script("""
                    const t = document.querySelector('.clinical-shared-tooltip-content');
                    return t ? t.innerText.trim() : null;
                """)
                chip_hover_ok = (chip_tooltip_count == 1)

                # Test Esc key hiding
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(0.2)
                esc_hidden = driver.execute_script("""
                    return document.querySelectorAll('.clinical-shared-tooltip').length;
                """) == 0
            else:
                esc_hidden = True

            # 5. Test row click (ensure nothing blocks clicks)
            first_row = driver.find_element(By.CSS_SELECTOR, ".clinical-data-table tbody tr:first-child")
            first_row.click()
            time.sleep(0.3)
            row_clicked = "row-focused" in first_row.get_attribute("class")

            # Check console errors
            logs = driver.get_log("browser")
            errors = [l for l in logs if l["level"] == "SEVERE"]

            # Save screenshot
            shot_file = f"tooltip_{mode}_{w}x{h}.png"
            driver.save_screenshot(os.path.join(SCREENSHOT_DIR, shot_file))

            res = {
                "mode": mode,
                "width": w,
                "height": h,
                "toastsOnLoad": toasts_on_load,
                "legendText": legend_text,
                "infoTooltipHover": tooltip_count_hover_info == 1,
                "infoTooltipText": tooltip_text_info,
                "infoTooltipHideOnLeave": tooltip_count_after_leave == 0,
                "chipHoverTooltip": chip_hover_ok,
                "chipTooltipText": chip_tooltip_text,
                "escHidesTooltip": esc_hidden,
                "rowClickable": row_clicked,
                "consoleErrors": len(errors)
            }
            report.append(res)
            print(f"[{mode.upper()} {w}x{h}] ToastsOnLoad: {toasts_on_load} | Legend: {legend_text is not None} | InfoTooltip: {tooltip_count_hover_info==1} | ChipTooltip: {chip_hover_ok} | EscHides: {esc_hidden} | RowClick: {row_clicked} | Errors: {len(errors)}")

    with open(os.path.join(ARTIFACTS_DIR, "polypharmacy_verification_report.json"), "w") as f:
        json.dump(report, f, indent=2)

finally:
    driver.quit()
