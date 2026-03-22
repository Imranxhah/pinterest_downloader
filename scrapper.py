import time
import csv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.keys import Keys # NEW IMPORT FOR PRESSING ENTER

# 1. Setup
driver = webdriver.Chrome()
wait = WebDriverWait(driver, 10)
unique_image_urls = set()
TARGET_COUNT = 2000
SEARCH_TERM = "Apple Plant" # Change this to search for whatever you want!

try:
    # 2. Login Sequence
    print("Navigating to login...")
    driver.get("https://www.pinterest.com/login/")

    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="emailInputField"]')))
    email_input.send_keys("YOUR_EMAIL") # DO NOT PUSH SECRETS TO GITHUB

    password_input = driver.find_element(By.CSS_SELECTOR, '[data-test-id="passwordInputField"]')
    password_input.send_keys("YOUR_PASSWORD") 

    login_button = driver.find_element(By.CSS_SELECTOR, '[data-test-id="registerFormSubmitButton"] button')
    login_button.click()

    # Wait for the home feed to load completely
    print("Waiting for home feed to load...")
    time.sleep(8) 

    # 3. Perform the Search
    print(f"Searching for '{SEARCH_TERM}'...")
    
    # Find the search box
    search_box = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-test-id="search-box-input"]')))
    
    # Type the search term
    search_box.send_keys(SEARCH_TERM)
    
    # Press "Enter"
    search_box.send_keys(Keys.RETURN)
    
    # Wait for the search results page to load
    print("Waiting for search results...")
    time.sleep(5)

    # 4. Scrape Loop (Unchanged)
    print(f"Scraping started. Target: {TARGET_COUNT} images...")
    
    while len(unique_image_urls) < TARGET_COUNT:
        
        images = driver.find_elements(By.CSS_SELECTOR, '[data-test-id="pinrep-image"] img')
        
        for img in images:
            try:
                url = img.get_attribute('src')
                if url:
                    unique_image_urls.add(url)
                
                if len(unique_image_urls) >= TARGET_COUNT:
                    break
                    
            except StaleElementReferenceException:
                continue
                
        print(f"Collected {len(unique_image_urls)}/{TARGET_COUNT} unique URLs...")
        
        if len(unique_image_urls) >= TARGET_COUNT:
            break
        
        driver.execute_script("window.scrollBy(0, 800);")
        time.sleep(1.5)

    print("Target reached!")

    # 5. Save to CSV
    csv_filename = f"pinterest_{SEARCH_TERM.replace(' ', '_').lower()}.csv"
    print(f"Saving data to {csv_filename}...")
    
    with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(["Image URL"])
        
        for url in list(unique_image_urls)[:TARGET_COUNT]:
            writer.writerow([url])
            
    print("Save complete.")

except Exception as e:
    print(f"An unexpected error occurred: {e}")

finally:
    driver.quit()