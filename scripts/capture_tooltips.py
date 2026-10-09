import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

options = Options()
options.add_argument('--headless=new')
options.add_argument('--window-size=1440,900')
driver = webdriver.Chrome(options=options)
try:
    driver.get('http://localhost:5173')
    time.sleep(1.5)

    # Screenshot of legend & table
    driver.save_screenshot(r'C:\Users\vivek\.gemini\antigravity-ide\brain\59789402-409c-445e-b359-36125997a491\screenshots_polypharmacy\legend_view_light.png')

    # Hover info icon
    info_icon = driver.find_element(By.CSS_SELECTOR, '.th-info-icon-btn')
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", info_icon)
    time.sleep(0.3)
    actions = ActionChains(driver)
    actions.move_to_element(info_icon).perform()
    time.sleep(0.5)
    driver.save_screenshot(r'C:\Users\vivek\.gemini\antigravity-ide\brain\59789402-409c-445e-b359-36125997a491\screenshots_polypharmacy\hover_info_tooltip.png')

    # Dark mode hover polypharmacy chip
    driver.execute_script("document.documentElement.setAttribute('data-theme', 'dark');")
    time.sleep(0.3)
    poly_chip = driver.find_element(By.CSS_SELECTOR, '.polypharmacy-indicator')
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", poly_chip)
    time.sleep(0.3)
    actions = ActionChains(driver)
    actions.move_to_element(poly_chip).perform()
    time.sleep(0.5)
    driver.save_screenshot(r'C:\Users\vivek\.gemini\antigravity-ide\brain\59789402-409c-445e-b359-36125997a491\screenshots_polypharmacy\hover_chip_dark.png')

    print('Detailed screenshots saved successfully')
finally:
    driver.quit()
