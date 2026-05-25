import time
import csv
import threading
import os
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

AUTO_SCROLL_ENABLED = True

def input_listener():
    global AUTO_SCROLL_ENABLED
    while True:
        input() # Wait for Enter
        AUTO_SCROLL_ENABLED = not AUTO_SCROLL_ENABLED
        status = "RESUMED" if AUTO_SCROLL_ENABLED else "PAUSED"
        print(f"\n[!] AUTO-SCROLL {status}. (Press Enter to toggle again)")

# Start background listener
listener_thread = threading.Thread(target=input_listener, daemon=True)
listener_thread.start()

# Filename for saving
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "CSV_DATA")
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

csv_filename = os.path.join(OUTPUT_DIR, f"pinterest_{SEARCH_TERM.replace(' ', '_').lower()}.csv")

# Pre-load existing URLs to avoid duplicates across runs
if os.path.exists(csv_filename):
    try:
        with open(csv_filename, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # skip header
            for row in reader:
                if row:
                    unique_image_urls.add(row[0])
        print(f"Loaded {len(unique_image_urls)} existing URLs from {csv_filename} (skipping duplicates).")
    except Exception as e:
        print(f"Warning: could not read existing CSV — {e}")

try:
    # 2. Login Sequence
    print("Navigating to login...")
    driver.get("https://www.pinterest.com/login/")

    email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test-id="emailInputField"]')))
    email_input.send_keys("YOUR_EMAIL") # DO NOT PUSH SECRETS TO GITHUB

    password_input = driver.find_element(By.CSS_SELECTOR, '[data-test-id="passwordInputField"]')
    password_input.send_keys("YOUR_PASSWORD") 

    login_button = wait.until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, '[data-test-id="registerFormSubmitButton"] button')
        )
    )
    driver.execute_script("arguments[0].click();", login_button)

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
                if url and "/videos/" not in url:
                    unique_image_urls.add(url)
                
                if len(unique_image_urls) >= TARGET_COUNT:
                    break
                    
            except StaleElementReferenceException:
                continue
                
        print(f"Collected {len(unique_image_urls)}/{TARGET_COUNT} unique URLs...")
        
        if len(unique_image_urls) >= TARGET_COUNT:
            break
        
        if AUTO_SCROLL_ENABLED:
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(1.5)
        else:
            time.sleep(0.5)

    print("Target reached!")

    # 5. Save to CSV
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