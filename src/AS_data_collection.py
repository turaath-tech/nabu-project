#!/usr/bin/env python
# coding: utf-8

## Athar Sale
## available in English and Arabic: https://atharsale.com/

## This code collects data from the following categories:
    # 'Jewelry and Accessories'
    # 'Books and Manuscripts'
    # 'Old Paintings and Handicrafts'
    # 'Old Coins and Stamps'
    # 'Miscellaneous'
    # 'Antiques' (subcategory of 'Antique Furniture and Household Antiques')

## ⚠️ Disclaimer on Data Use
# This tool is provided under the MIT License. While the code is freely available for use, modification, and distribution, users are solely responsible for how they apply it and any outputs it generates.
# Some output data may contain information that could be sensitive or identifying. Users must ensure that any collection, processing, analysis, or dissemination of such data complies with applicable laws, regulations, and ethical standards, including those relating to privacy, data protection, and cultural heritage.
# The availability of this code does not grant permission to use data in ways that may be harmful, unlawful, or unethical. Responsibility for the use of this tool and its outputs rests entirely with the user.
# More information on the NABU project can be found at www.turaath.tech/nabu-project and www.github.com/turaath-tech/nabu-project

import pandas as pd
import time, os, fnmatch, shutil
from datetime import datetime
import json
import hashlib
import re
import glob
from tqdm import tqdm
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException, WebDriverException

FILENAME = "AS_output.json"
URL = 'https://atharsale.com/en'
ARABIC_NUMBERS = {'٠': '0',
                  '١': '1',
                  '٢': '2',
                  '٣': '3',
                  '٤': '4',
                  '٥': '5',
                  '٦': '6',
                  '٧': '7',
                  '٨': '8',
                  '٩': '9'}
CONVERT_ARABIC_NUMBERS = str.maketrans(ARABIC_NUMBERS) # convert Arabic numbers to Arabic numerals if needed (used for phone numbers)
AUCTION_CATEGORIES = [f'{URL}/%D9%85%D8%AC%D9%88%D9%87%D8%B1%D8%A7%D8%AA-%D9%88--%D8%A7%D9%83%D8%B3%D8%B3%D9%88%D8%A7%D8%B1%D8%A7%D8%AA',
                      f'{URL}/%D9%83%D8%AA%D8%A8-%D9%88-%D9%85%D8%AE%D8%B7%D9%88%D8%B7%D8%A7%D8%AA',
                      f'{URL}/%D9%84%D9%88%D8%AD%D8%A7%D8%AA-%D9%88-%D8%A3%D8%B9%D9%85%D8%A7%D9%84-%D9%8A%D8%AF%D9%88%D9%8A%D8%A9-%D9%82%D8%AF%D9%8A%D9%85%D8%A9',
                      f'{URL}/%D8%B9%D9%85%D9%84%D8%A7%D8%AA-%D9%88-%D8%B7%D9%88%D8%A7%D8%A8%D8%B9-%D9%82%D8%AF%D9%8A%D9%85%D8%A9',
                      f'{URL}/%D9%85%D8%AA%D9%81%D8%B1%D9%82%D8%A7%D8%AA',
                      f'{URL}/%D8%A7%D8%AB%D8%A7%D8%AB-%D9%88-%D8%AA%D8%AD%D9%81-%D9%85%D9%86%D8%B2%D9%84%D9%8A%D8%A9-%D9%82%D8%AF%D9%8A%D9%85%D8%A9/%D8%AA%D8%AD%D9%81']
OBJ_CATEGORIES = ['Jewelry and Accessories', 'Books and Manuscripts', 'Old Paintings and Handicrafts', 'Old Coins and Stamps', 'Miscellaneous', 'Antiques']

## DEFINE FUNCTIONS

def log_status(status, l = None):
    '''
    Updates AS_status.txt with what the tool is currently handling

    Args
    ---
    :param status, str message to be written to the status.txt

    :return nothing, update status.txt
    '''
    t = time.localtime()
    time_and_date = time.strftime('%b-%d-%Y_%H-%M-%S', t)
    with open("AS_status.txt", "a") as file:
        file.write(f"{time_and_date}: {status}\n")
    if type(l) == list:
        for element in l:
            with open("AS_status.txt", "a") as file:
                file.write(f"{element}\n")

def generate_id(prefix, input_str):
    '''
    Generates unique IDs for each object based on a hash of the object's permanent url

    Args
    ---
    :param prefix, str that indicates the datasource, to be appended to the beginning of the ID
    :param input_str, string from which hash is generated

    :return formatted ID
    '''
    h = hashlib.new('sha256')
    h.update(input_str.encode())
    hx = h.hexdigest()
    return f"{prefix}_{str(int(hx, base=16))[:15]}"

def clean_text(s):
    '''
    Remove extra spaces and HTML tags from string

    Args
    ---
    :param s, string to be cleaned

    :return string with unnecessary spaces removed
    '''
    regex_match = '<[^<>]*>'
    clean_string = re.sub(regex_match, '', s)
    return ' '.join(clean_string.split())
    
def collect_metadata(data_dict):
    '''
    Collect listing publication and modification dates from the page metadata and add them to object data dictionary

    Args
    ---
    :param data_dict, dictionary of data to which metadata should be added

    :return data_dict with metadata
    '''
    meta_tags = driver.find_elements(By.TAG_NAME, 'meta')
    for tag in meta_tags:
        prop = tag.get_attribute('property')
        if prop == 'article:published_time':
            data_dict['publication_date'] = tag.get_attribute('content')
        elif prop == 'article:modified_time':
            data_dict['modification_date'] = tag.get_attribute('content')
    return data_dict

def chromeinit():
    '''
    Initialise chrome driver to be used by Selenium

    :returns initialised driver
    '''
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')

    chromedriver_autoinstaller.install()

    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(10)
    driver.implicitly_wait(10)
    return driver

def robust_get(url, max_attempts=3):
    '''
    Use chromedriver to get url, try multiple times if there is a TimeoutException

    Args
    ---
    :param url, url to be retrieved by driver

    '''
    for attempt in range(1, max_attempts + 1):
        try:
            time.sleep(2)
            driver.get(url)
            return True
        except TimeoutException:
            pass
    return False

def collect_data(driver, url, problem_pages):
    '''
    Collect data from online listing

    Args
    ---
    :param driver, chromedriver to be used
    :param url, page to be parsed
    :param problem_pages, list of urls with persistent timeout errors to be tried again later

    :return dictionary of object data
    '''
    if not robust_get(url):
        problem_pages.append(url)
        data_dict = {}
    else:
        try:
            title = driver.find_element(By.CLASS_NAME, 'product-title').text
            seller_name = driver.find_element(By.CLASS_NAME, 'product-details-user').find_element(By.TAG_NAME, 'a').text
            seller_url = driver.find_element(By.CLASS_NAME, 'product-details-user').find_element(By.TAG_NAME, 'a').get_attribute('href')
            price = driver.find_element(By.XPATH, '//*[@id="product_details_price_container"]').text
            description = driver.find_element(By.XPATH, '//*[@id="collapse_description_content"]/div[1]').text
            obj_category = driver.find_element(By.XPATH, '//*[@id="wrapper"]/div/div/div[1]/nav/ol/li[2]/a').text
            
            data_dict = {'listing_identifier': generate_id("AS", url),
                         'title': title,
                         'description': description,
                         'obj_category': obj_category,
                         'price': clean_text(price),
                         'seller_name': seller_name,
                         'seller_url': seller_url,
                         'listing_url': url,
                         'site_name': 'اثار'}
            
            # go to Additional Information page and collect data from table: seller country, seller phone number, and evaluation certificate
            additional_information_tab = driver.find_element(By.XPATH, '/html/body/div[5]/div/div/div[2]/div[2]/div/div/ul/li[2]/a')
            driver.execute_script("arguments[0].click();", additional_information_tab)
            driver.implicitly_wait(1)
            table = driver.find_elements(By.TAG_NAME, 'tbody')
            if len(table) > 0:
                table_rows = table[-1].find_elements(By.TAG_NAME, 'tr')
                for i in range(len(table_rows)):
                    x_path = '//*[@id="collapse_additional_information_content"]/table/tbody/'
                    key = driver.find_element(By.XPATH, f'{x_path}tr[{i+1}]/td[1]').get_attribute("innerText")
                    val = driver.find_element(By.XPATH, f'{x_path}tr[{i+1}]/td[2]').get_attribute("innerText")
                    if key == 'Advertiser Country':
                        data_dict['seller_country'] = val
                    elif key == 'Contact number':
                        data_dict['seller_phone_number'] = "".join(filter(str.isdigit, val.translate(CONVERT_ARABIC_NUMBERS)))
                    elif key == 'Is there an evaluation certificate for the piece':
                        data_dict['evaluation_certificate'] = False if val == 'No' else True
                    else:
                        data_dict[key] = val
            else:
                pass

            data_dict = collect_metadata(data_dict)
        
        except NoSuchElementException:
            print(f"NoSuchElementException error encountered with {url}")
            problem_pages.append(url)
            data_dict = {}
    return data_dict, problem_pages

def save_data(data_dict):
    '''
    Dumps object dictionaries to a JSON file

    Args
    ---
    :param data_dict, dictionary of object data to be dumped to JSON
    '''
    if glob.glob(FILENAME):
        with open(FILENAME, 'r', encoding="utf8") as data:
            objs = json.load(data)
            objs.append(data_dict)
        with open(FILENAME, "w", encoding='utf8') as file:
            json.dump(objs, file, ensure_ascii=False)
    else:
        with open(FILENAME, "w", encoding='utf8') as file:
            json.dump([data_dict], file, ensure_ascii=False)

## RUN THE DATA COLLECTION

log_status(f"collecting URLs for all available objects")

# takes about five minutes to collect all object URLs
object_urls = []
driver = chromeinit()

for cat in tqdm(AUCTION_CATEGORIES):
    i = 1
    while True:
        count = len(object_urls)
        url = f'{cat}?page={i}'
        robust_get(url)
        objects = driver.find_elements(By.XPATH, '//*[@id="productListResultContainer"]/div/div/div[2]/h3/a')
        if len(objects) == 0:
            objects = driver.find_elements(By.XPATH, '//*[@id="productListResultContainer"]/div/div/div[1]/div[2]/a')
        for obj in objects:
            if obj.get_attribute('href') not in object_urls:
                object_urls.append(obj.get_attribute('href'))
        new_count = len(object_urls)
        
        # break if there are no new results; we try at least the first five pages anyway because some categories have the most popular objects listed in other categories so they will already be in the list of URLs
        if count == new_count and i > 5:
            break
        else:
            i = i + 1
    log_status(f"finished collecting URLs for objects in the {OBJ_CATEGORIES[AUCTION_CATEGORIES.index(cat)]} category")

# write checkpoint file of URLs
with open("AS_listing_urls.json", "w", encoding='utf8') as file:
    json.dump(object_urls, file, ensure_ascii=False)

log_status(f"starting scraping")

problem_pages = []

for url in tqdm(object_urls):
    try:
        data_dict, problem_pages = collect_data(driver, url, problem_pages)
        if len(data_dict.keys()) > 0:
            save_data(data_dict)
            time.sleep(1)
    except:
        problem_pages.append(url)

error_pages = []
for url in tqdm(problem_pages):
    data_dict, error_pages = collect_data(driver, url, error_pages)
    if len(data_dict.keys()) > 0:
        save_data(data_dict)
        time.sleep(1)

if len(error_pages) > 0:
    log_status("couldn't collect data from the following URLs due to persistent errors:", error_pages)

log_status(f'finished scraping; final data available at {FILENAME}')
driver.quit()
