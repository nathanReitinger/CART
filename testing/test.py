
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

import subprocess
import sys
import time 
import json
import socket
import shutil
from tempfile import mkstemp
from shutil import move, copymode
import os
from os import fdopen, remove
from distutils.dir_util import copy_tree
import glob 
import threading
import random 

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
    chrome_options.add_argument('--headless')
    chrome_options.add_experimental_option('prefs', prefs)
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument("--window-size=2000,2000") # helps with the random crashes of chrome via selenium
    # chrome_options.add_argument("--start-maximized");
    # chrome_options.add_argument("download.default_directory=notices/")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36")
    chrome_options.add_argument('--kiosk-logging.infoing')
    # chrome_options.add_argument("user-data-dir=/nfshomes/nlr/bndb/scrape/tmp/" + str(time.time()))
    
    # test

    browser = webdriver.Chrome(options=chrome_options)
    return browser

def replace(file_path, pattern, subst):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    #Copy the file permissions from the old file to the new file
    copymode(file_path, abs_path)
    #Remove original file
    remove(file_path)
    #Move new file
    move(abs_path, file_path)

def clear_out_files():
    os.chdir('../')
    print("[ ] clear_out_files")

    # clear out testing folder 
    files = glob.glob('abstracts/*.csv')
    for f in files:
        print('removing! --> ', f)
        os.remove(f)
        time.sleep(.2)
    files = glob.glob('abstracts/*.txt')
    for f in files:
        print('removing! --> ', f)
        os.remove(f)
    files = glob.glob('abstracts/*.lock')
    for f in files:
        print('removing! --> ',f)
        os.remove(f)
    try:
        os.remove('abstracts/coders.txt')
    except:
        print("no coders.txt") 
    try:
        os.remove('abstracts/confetti.txt')
    except:
        print("no confetti.txt")
    try:
        os.remove('abstracts/ngrok_auth.txt')
    except:
        print("no ngrok_auth.txt") 
    try:
        os.remove('abstracts/ngrok_domain.txt')
    except:
        print("no ngrok_domain.txt")
    try:
        os.remove('abstracts/num_reviews_per_abstract.txt')
    except:
        print("no num_reviews_per_abstract.txt") 
    print("[+] clear_out_files")
    os.chdir('testing')
    return

def teardown():
    print("[ ] teardown")

    # clear out testing folder 
    files = glob.glob('abstracts/-testing/*')
    for f in files:
        print(f)
        os.remove(f)
    try:
        os.remove("cart_testing.py")
    except:
        print("no 'cart_testing.py' exists")
    print("[+] teardown")
    return


def test_vote(examples_to_use, number_to_vote):

    try:
        print("[ ] setup")

        # we are in testing folder, go back one step 
        os.chdir('..')

        # clear out testing folder 
        files = glob.glob('abstracts/-testing/*')
        for f in files:
            print(f)
            os.remove(f)
        
        # check that we have some files in the testing cateogry (copy over from -example_data_small)
        print('[ ] grabbing files')
        files_to_copy = glob.glob('abstracts/' + examples_to_use + '/*')
        for f in files_to_copy:
            print(f)
            shutil.copy(f, "abstracts/")
        print('[+] done grabbing files')

        # copy the file for testing
        print('[ ] moving files into the right location for CART') 
        shutil.copyfile("cart.py", "cart_testing.py")
        file_path = 'cart_testing.py'
        pattern1 = 'PATH_TO_ABSTRACTS = "abstracts/*.csv"'
        pattern2 = 'DEFAULT_PATH = "abstracts/"'
        subst1 = 'PATH_TO_ABSTRACTS = "abstracts/-testing/*.csv"'
        subst2 = 'DEFAULT_PATH = "abstracts/-testing/"'
        replace(file_path,pattern1,subst1)
        time.sleep(10)
        replace(file_path,pattern2,subst2)
        time.sleep(10)
        print('[+] done moving files into the right location for CART') 

        print("[+] setup")
      
        print("[ ] load up CART")

        # start up CART, hide output 
        subprocess.Popen(['stty', '-tostop'])
        proc = subprocess.Popen(["python3","cart_testing.py","-c", "user1", "-c", "user2", "-p", "8083", "-r", "2"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        time.sleep(10)
        print("[+] load up CART DONE")

        print("[ ] selenium setup")
        # get browser
        browser = setup()
        browser.implicitly_wait(10)
        # check if internet (not necessary for localhost)
        while not isConnected():
            print("--sleeping to wait for internet--")
            time.sleep(5)
        # get homepage
        print("[+] selenium setup DONE")

        print("[ ] login")
        browser.get('http://127.0.0.1:8083/')
        time.sleep(15)
        

        ## check that you can vote on all abstracts in small example and then be done 
        # get first user 
        select = Select(browser.find_element('xpath', '/html/body/main/article/div/div/div/div/div/form/select'))
        # select by value 
        select.select_by_value('user1')
        time.sleep(10)
        actions = ActionChains(browser)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(3) 
        print("[+] login DONE")

        print("[ ] cast vote for all examples")
        # for each of the 5 abstracts, vote yes
        for i in range(number_to_vote):
            if random.randint(0,10) >= 5:
                print(i, "[yes] vote cast")
                ActionChains(browser).send_keys("y").perform()
            else:
                print(i, "[no] vote cast")
                ActionChains(browser).send_keys("n").perform()
            time.sleep(1)  
        print("[+] cast vote of yes on all abstracts in the small examples DONE")
        # check that printed to screen is the done statement

        print("[ ] check successful vote casting")
        is_done_statement = int(browser.find_element(By.ID, 'ticker').get_attribute("data-value"))
        print("[x] check successful vote casting")

        browser.quit()
        print("[ ] teardown starting")
        teardown()
        print("[x] teardown completed")
        # we are in testing folder, go back one step 
        os.chdir(os.getcwd() + '/testing')

        if number_to_vote == is_done_statement:
            return ('test_vote: success')
        else:
            return ('test_vote: fail')
        

    except Exception as e:
        print("error on test, FAIL\n", e)
        # browser.quit()
        teardown()
        # we are in testing folder, go back one step 
        os.chdir(os.getcwd() + '/testing')
        sys.exit()

if __name__ == "__main__":
    print(
"""\n\n
# TESTING IS FOR DEVELOPERS ONLY, USE AT YOUR OWN RISK 
#
#
# ,-. ,-. ,-. |- 
# |   ,-| |   |  
# `-' `-^ '   `' 
#
#
# TESTING IS FOR DEVELOPERS ONLY, USE AT YOUR OWN RISK 
\n\n"""
    )

    check_with_user = input("--------------------------------------------\nTesting uses 'clear_out_files()' which \nremoves all files in the 'abstracts/*.*'\nfolder. Ensure you have safely copied \nany work!\n--------------------------------------------\n\n\n\tEnter 'yes' to continue: ")
    if check_with_user == 'yes':
        clear_out_files()
        test_vote_small_results = test_vote(examples_to_use='-example_data_small', number_to_vote=5)
        # test_vote_big_results = test_vote(examples_to_use='-example_data_big', number_to_vote=50)
        clear_out_files()
        print("small example set vote testing---", test_vote_small_results)
        # print("big example set vote testing---", test_vote_big_results)

   
