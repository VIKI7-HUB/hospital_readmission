from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--window-size=1920,1080')
d = webdriver.Chrome(options=opts)
try:
    d.get('http://localhost:5173')
    time.sleep(2)
    b = d.find_element(By.XPATH, "//button[contains(@title, 'light mode')]")
    b.click()
    time.sleep(1)
    d.save_screenshot('screenshots/light_mode_worklist.png')
    print('Saved light_mode_worklist.png')
finally:
    d.quit()
