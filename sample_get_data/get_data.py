
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

import pandas as pd
import subprocess
import sys
import time 
import json
import socket
import shutil
import random
import numpy as np
from tempfile import mkstemp
from shutil import move, copymode
import os
from os import fdopen, remove
from distutils.dir_util import copy_tree
import glob 
import threading

HOW_MANY_PAPERS_TO_GET = 4 # np.inf

def isConnected():
    try:
        # connect to the host -- tells us if the host is actually reachable
        sock = socket.create_connection(("www.google.com", 80))
        if sock is not None:
            # print('Closing socket')
            sock.close
        return True
    except OSError:
        pass
    return False

def setup():

    settings = {
        "recentDestinations": [{
                "id": "Save as PDF",
                "origin": "local",
                "account": "",
            }],
            "selectedDestinationId": "Save as PDF",
            "version": 2
        }
    prefs = {'printing.print_preview_sticky_settings.appState': json.dumps(settings)}

    path_to_chromedriver = '/usr/local/bin/chromedriver'  # change path as needed
    chrome_options = Options()
    # chrome_options.add_argument('--headless')
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--window-size=2000,2000") # helps with the random crashes of chrome via selenium
    # chrome_options.add_argument("--start-maximized");
    # chrome_options.add_argument("download.default_directory=notices/")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36")
    chrome_options.add_argument('--kiosk-logging.infoing')
    
    browser = webdriver.Chrome(options=chrome_options)
    return browser




if __name__ == "__main__":

    # storage setup 
    all_data = []

    # get browser
    browser = setup()
    browser.implicitly_wait(10)

    ## get PETS data as tester 
    # 1. get dblp paper links 
    # 2. visit those links and grab info
    # 3. store results in format that CART accepts

    for i in range(2023,2024):
        print("scraping year:", str(i))

        ############################################################ step1 get the URLs
        year_string = str(i)
        pets_url = "https://dblp.org/db/journals/popets/popets" + year_string + ".html"
        conference_url = pets_url
        print("scraping conference:", conference_url)

        while not isConnected():
            print("--sleeping to wait for internet--")
            time.sleep(5)
        browser.get(conference_url)
        # time.sleep(random.randint(10,25))
        all_links = browser.find_elements_by_css_selector("nav.publ ul li div > a") 
        paper_links = []

        for link in all_links:
            # link_html = link.get_attribute("outerHTML")
            # print(link)
            this_link = link.get_attribute('href')
            # print(this_link)
            if 'https://doi.org/' in this_link:
                paper_links.append(this_link)
        # print(paper_links)
        print("how many papers did we find:", len(paper_links))
        print("\ntotal papers:", len(paper_links))

        ############################################################ step2 get paper abstracts and titles
        paper_counter = 0
        time.sleep(random.randint(3,25))
        for paper_url in paper_links:
            while not isConnected():
                print("--sleeping to wait for internet--")
                time.sleep(5)
            browser.get(paper_url)
            
            if "?" in browser.current_url:
                browser.get(browser.current_url + "&tab_body=abstract") 
            else:
                browser.get(browser.current_url + "?tab_body=abstract") 
            time.sleep(2)

            try:
                # articleTitle = browser.find_element_by_css_selector(self.title_selector).text
                articleTitle = browser.find_element(By.XPATH, '/html/body/div/div[2]/h2').get_attribute('innerHTML')
            except: 
                articleTitle = ""

            try:    
                # abstract = browser.find_element_by_css_selector(self.abstract_selector).text
                abstract = browser.find_element(By.XPATH, '/html/body/div/div[2]/p[4]').get_attribute('innerHTML')
                if "Download PDF" in abstract:
                    abstract = browser.find_element(By.XPATH, '/html/body/div/div[2]/p[5]').get_attribute('innerHTML')
            except:
                abstract = ""

            print(str(paper_counter)+ " --- " + "Title: " + articleTitle + "\nAbstract: " + abstract + "\nURL:" + paper_url)
            
            all_data.append([paper_url, articleTitle, abstract])
            paper_counter += 1
            if paper_counter > 4:
                break

        browser.quit()

        ############################################################ step2 get paper abstracts and titles
        ## at this stage you can drop duplicate papers with different URLs but same title (fuzzy matching)
        all_papers = pd.DataFrame(all_data, columns=['url', 'title', 'abstract'])
        # get the path to save these abstracts
        output_path='../abstracts/-sample_from_scrape/SAMPLE_PETS_at_' + str(time.ctime()) + '/'
        os.mkdir(output_path)

        # save each paper in the right format
        paper_unique_id_counter = 1
        for index,row in all_papers.iterrows():
            unique_id = paper_unique_id_counter
            review_count = 0
            this_url = row['url'] 
            this_title = row['title']
            this_abstract = row['abstract'] + '------endofabstract------' + str(unique_id)
            user = 'none'
            vote = 'none'
            in_progress = 'no'
            row_to_add = [unique_id, review_count, this_url, this_title, this_abstract, user, vote, in_progress, str(time.time())]
            temp = pd.DataFrame([row_to_add], columns=['unique_id', 'review_count', 'url', 'title', 'abstract', 'user', 'vote', 'in_progress', 'time'])
            temp.to_csv(output_path + str(paper_unique_id_counter) + '.csv', mode='w+', header=True, index=False)
            paper_unique_id_counter += 1
        sys.exit()

 