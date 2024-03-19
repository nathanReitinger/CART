##################
# ,-. ,-. ,-. |- #
# |   ,-| |   |  #
# `-' `-^ '   `' #
##################
# Culling        #
# Abstracts for  #
# Relevancy in   #
# Teams          #
#################$

from flask import Flask  # main load
from flask import (
    jsonify,
    render_template,
    request,
    redirect,
    session,
    url_for,
)  # getting right abstract, and updating right abstract
from flask_session import Session  # cookie and other local info storage
from tempfile import mkdtemp  # related to error on flask session and permissions
from filelock import Timeout, FileLock  # https://py-filelock.readthedocs.io/en/latest/
import glob, os  # handling all abstract files as pandas df, and file actions with os
import json, signal # handling shutdown
import pandas as pd  # for csv rows per grader
import numpy as np  # data analysis
import random  # for shufflingcron list of abstracts on each run
import sys  # debugging
import time  # time functions for keeping track of edits
import moment  # time functions for keeping track of edits
from pathlib import Path  # helper for reading files
from datetime import (
    datetime,
)  # we want to have historical perspective for user who wants to edit
from multiprocessing import Pool  # speedup on processing
import argparse  # initial setup
from ngrok_flask_cart import run_with_ngrok # https://pypi.org/project/ngrok-flask-cart/

PATH_TO_ABSTRACTS = "abstracts/*.csv"
DEFAULT_PATH = "abstracts/"
DEBUG = False


############################################# ------------------------------------file structure
# 1,                                          number of this abstract (unique)
# 0,                                          number of reviews so far on this abstract
# <abstract text>------endofabstract------1,  abstract text plus frontEnd flag for unique ID and end of abstract
# none,                                       the user who reviwed the abstract
# none,                                       user's vote (relevant, or not relevant)
# no,                                         was the abstract picked up for review already
# 1690286841.3695428                          timestamp (time.time() as unix)
############################################# ------------------------------------file structure

# visualizations
import json
import plotly
import plotly.express as px

######## globals
colnames = [
    "unique_id",
    "review_count",
    "url",
    "title",
    "abstract",
    "user",
    "vote",
    "in_progress",
    "time",
]
default_path = DEFAULT_PATH
timeout_for_locks = 1
CODERS = DEFAULT_PATH + "coders.txt"
is_onboarding = [""]  # list of usernames in onboarding
onBoarding_number = (
    0  # how many abstracts are included in the onboarding process (default 0)
)
PATH_num_reviews_per_abstract = (
    DEFAULT_PATH + "num_reviews_per_abstract.txt"
)  # how many reviewers should vote on each abstract
PATH_ngrok_authtoken = (
    DEFAULT_PATH + "ngrok_auth.txt"
)  # https://dashboard.ngrok.com/get-started/your-authtoken
PATH_ngrok_domain = (
    DEFAULT_PATH + "ngrok_domain.txt"
)  # https://dashboard.ngrok.com/get-started/your-authtoken

PATH_confetti_rollover = (
    DEFAULT_PATH + "confetti.txt"
)  # reward gamified
HTTP_VARIANT = "http"
######## globals


######## helpers
def reader(filename):
    return pd.read_csv(filename)

def shutdown_server():
    ## this throws error because there is no return, but ends the session
    os.kill(os.getpid(), signal.SIGINT)
######## helpers



app = Flask(__name__)
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = 'filesystem'
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config[
    "SESSION_COOKIE_SAMESITE"
] = "Lax"  # firefox complains about this and will boot sessions on https
app.secret_key = "*KRUD?zrAJ|jX=L]]y=[T)P@]<UEe'"

Session(app)

def start_lock(file_path):

    if DEBUG:
        print("[-] starting lock process now")
    to_ret = {}
    file_path = file_path
    lock_path = file_path + ".lock"
    lock = FileLock(lock_path, timeout=timeout_for_locks)
    try:
        with lock.acquire():
            temp_df = pd.read_csv(file_path, names=colnames, header=None)
            last_row = temp_df.iloc[-1]

            # get some useful things to return
            to_ret["unique_id"] = last_row["unique_id"]
            to_ret["review_count"] = last_row["review_count"]
            to_ret["abstract"] = last_row["abstract"]
            to_ret["title"] = last_row["title"]
            to_ret["url"] = last_row["url"]
            to_ret["user"] = last_row["user"]
            to_ret["vote"] = last_row["vote"]
            to_ret["time"] = last_row["time"]

            # if someone else has already viewed this file, then make a new row
            # if no one has viewed this file, then it has no user
            if last_row["user"] != "none":
                # append rather than update
                new_row = [
                    to_ret["unique_id"],
                    to_ret["review_count"],
                    to_ret["url"],
                    to_ret["title"],
                    to_ret["abstract"],
                    session["name"],
                    "none",
                    "yes",
                    str(time.time()),
                ]
                temp_df.loc[len(temp_df.index)] = new_row
            else:
                # update as "in progress"
                last_row["in_progress"] = "yes"
                last_row["user"] = session["name"]
                last_row["time"] = str(time.time())

            to_ret["success"] = True
            to_ret["lock"] = lock
            if DEBUG:
                print("-------------------------")
            if DEBUG:
                print(temp_df.head(50))
            temp_df.to_csv(file_path, index=False, header=False)
            if DEBUG:
                print(temp_df.head(50))
            if DEBUG:
                print("-------------------------")
            if DEBUG:
                print("[+] successful lock process, returning now")
    except Timeout:
        if DEBUG:
            print(
                "[---] Another instance of this application currently holds the lock."
            )
        to_ret["success"] = False
        to_ret["lock"] = None
    return to_ret


###
# we will get the <n review abstracts here, using locks to prevent overlap
###
@app.route("/")
def index():

    # check if we have a username yet, else go back to username selection page
    try:
        print(session["name"])
    except:
        return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))
    if session["name"] == None or session["name"] == " ":
        return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))

    # check that user has abstracts in the folder
    how_many_papers = len(glob.glob(PATH_TO_ABSTRACTS))
    if DEBUG: print("how many papers am i seeing", len(glob.glob(PATH_TO_ABSTRACTS)))
    if how_many_papers == 0:
        if DEBUG: print("error, need to exit, user hasn't provided any papers")
        return render_template(
            "start.html", value="⚠️⚠️⚠️ no papers found in <code>abstracts/</code> folder ⚠️⚠️⚠️ <br/> Please add a few <code>.csv</code> files and then try again!"
        )


    # instantiate
    all_files = []
    this_abstract = "DONE WITH ALL ABSTRACTS :)"
    this_url = ""
    this_title = ""
    this_unique_id = "pending"
    i_have_it = False
    user_has_pending_review = False
    quick_save = False
    all_done_flag = False

    if DEBUG:
        print("----> getting all files")
    for file in glob.glob(PATH_TO_ABSTRACTS):

        # weed out none.csv which crops up when errors are made on live edits to system
        is_real = False
        try:
            head, tail = os.path.split(file)
            num = int(tail.split(".csv")[0])
            if "None" in tail:
                is_real = False
            else:
                is_real = True
        except:
            print("error on this file", file)

        if is_real:
            if session["name"] in is_onboarding:
                head, tail = os.path.split(file)
                num = int(tail.split(".csv")[0])
                if num <= onBoarding_number:
                    all_files.append(file)
            else:
                head, tail = os.path.split(file)
                num = int(tail.split(".csv")[0])
                if num > onBoarding_number:
                    all_files.append(file)
    # important so that you don't get all from one conference, but also means that liklihood of matches is low at first
    random.shuffle(all_files)

    if session["name"] in is_onboarding:
        reviews_per_abstract = onBoarding_number
    else:
        reviews_per_abstract = int(
            Path(PATH_num_reviews_per_abstract).read_text().strip()
        )

    if DEBUG:
        print("is there an open session -----------> ", session["incomplete_review"])
    # get pending review, user can't move on until they mark it!
    if session["incomplete_review"] == "need full review":

        # check if storage picked up the last abstract, if so, then start there, else do a full sweep just in case
        # os.path.isfile(DEFAULT_PATH + session['name'])
        local_storage_path = DEFAULT_PATH + session["name"] + ".txt"
        progress_file = Path(local_storage_path)
        if progress_file.is_file():
            if DEBUG: print("localstorage savepath active! save time!!")
            with open(local_storage_path) as f:
                current_info = f.readlines()
                current_abstract = current_info[0].strip("\n")
                current_user_counter = current_info[1].strip("\n")
                if current_abstract != "---all done---":
                    path_to_this_abstract = DEFAULT_PATH + current_abstract + ".csv"
                    temp_df = pd.read_csv(
                        path_to_this_abstract, names=colnames, header=None
                    )
                    only_row = temp_df.iloc[-1]
                    user_has_pending_review = True
                    this_abstract_id = current_abstract
                    this_abstract = only_row["abstract"]
                    this_title = only_row["title"]
                    this_url = only_row["url"]
                    quick_save = True
                    user_has_pending_review = True
                    session["user_counter"] = current_user_counter
                else:
                    session["user_counter"] = current_user_counter
                    all_done_flag = True

        else:
            if DEBUG:
                print("first time logging in, do full sweep")
            # set counters
            coding_mapping = {
                "no, not relevant": 0,
                "yes, is relevant": 1,
                "not_a_paper": np.nan,
            }
            all_dfs = []
            for file in glob.glob(PATH_TO_ABSTRACTS):
                # if os.path.isfile(file + ".lock"):
                all_dfs.append(pd.read_csv(file))
            df = pd.concat(all_dfs)
            if DEBUG:
                print(df.head())
            user_list = []
            seen_it = []
            for index, row in df.iterrows():
                if (
                    row["user"] != "none"
                    and row["user"] == session["name"]
                    and row["in_progress"] != "yes"
                ):
                    user_pair = str(row["unique_id"]) + "---" + row["user"]
                    if user_pair not in seen_it:
                        user_list.append([row["user"], row["unique_id"]])
                    seen_it.append(user_pair)
            session["user_counter"] = len(user_list)

            for f in all_files:
                if os.path.isfile(f + ".lock"):
                    temp_df = pd.read_csv(
                        f, names=colnames, header=None
                    )  # bottleneck here
                    all_users_who_touched = temp_df["user"].unique()
                    if session["name"] in all_users_who_touched:
                        for i, r in temp_df[::-1].iterrows():
                            if (
                                r["user"] == session["name"]
                                and r["in_progress"] == "yes"
                            ):
                                if DEBUG:
                                    print("pending review exists")
                                user_has_pending_review = True
                                this_abstract = str(r["abstract"])
                                this_title = str(r["title"])
                                this_url = str(r["url"])
                                this_unique_id = str(r["unique_id"])
                                session["incomplete_review"] = this_unique_id
                                session["abstract"] = this_abstract
                                session["title"] = this_title
                                session["url"] = this_url
                                break
                # else:
                #     print("no one has reviewed this yet, how could it be open!")
    elif session["incomplete_review"] == "none":
        if DEBUG:
            print("NO OPEN REVIEW, GET ONE NOW")
    else:
        if quick_save == False:
            if DEBUG:
                print("pending review exists")
            user_has_pending_review = True
            this_abstract_id = session["incomplete_review"]
            this_abstract = session["abstract"]
            this_title = session["title"]
            this_url = session["url"]

    # if no pending reviews, get a new review that has less than 2 people who reviewed it and this user hasn't reviewed it
    if user_has_pending_review == False and all_done_flag == False:
        if DEBUG:
            print(
                "----> finding an abstract with <",
                str(reviews_per_abstract),
                " reviews",
            )
        for f in all_files:
            if i_have_it == False:
                temp_df = pd.read_csv(f, names=colnames, header=None)
                last_row = temp_df.iloc[-1]

                # and last_row['in_progress'] != 'yes'

                current_review_count = int(last_row["review_count"])
                current_id = int(last_row["unique_id"])

                ### this is a random abstract, can this user review it
                # - less than 2 total reviews
                # - this user has not already looked at it
                # - there is a decision on it

                if (
                    current_review_count < reviews_per_abstract
                    and session["name"] not in temp_df["user"].unique()
                    and "not_a_paper" not in temp_df["vote"].unique()
                    and last_row["in_progress"] != "yes"
                ):
                    if DEBUG:
                        print("----> found potential abstract, checking locks")
                    ret = start_lock(f)
                    if ret["success"] == True:
                        if DEBUG:
                            print(ret)
                        this_success = ret["success"]
                        this_lock = ret["lock"]
                        this_unique_id = ret["unique_id"]
                        this_eview_count = ret["review_count"]
                        this_abstract = str(ret["abstract"])
                        this_title = str(ret["title"])
                        this_url = str(ret["url"])
                        this_user = ret["user"]
                        this_vote = ret["vote"]
                        this_time = ret["time"]
                        parsed_time = float(this_time)
                        parsed_time = moment.unix(parsed_time)
                        if DEBUG:
                            try:
                                print(parsed_time.format("YYYY-M-D h:m A"))
                            except:
                                print("maybe error in computer interpreting 'A'")
                                print(parsed_time.format("YYYY-M-D H:m"))
                        if DEBUG:
                            print("----> !! success, serving abstract now")

                        print(this_unique_id)
                        print(type(this_unique_id))

                        # log the open review
                        session["incomplete_review"] = this_unique_id
                        session["abstract"] = this_abstract
                        session["title"] = this_title
                        session["url"] = this_url

                        # store local progress here
                        local_updater = open(
                            DEFAULT_PATH + session["name"] + ".txt", "w+"
                        )
                        local_updater.write(str(this_unique_id) + "\n")
                        local_updater.write(str(session["user_counter"]) + "\n")
                        local_updater.close()

                        i_have_it = True
                    else:
                        if DEBUG:
                            print("lock already in use, keep looking")
                        # continue
    # time.sleep(3)
    if DEBUG:
        print("DONE DONE")
    coders_left_todo = ''
    if this_abstract == "DONE WITH ALL ABSTRACTS :)":
        local_updater = open(DEFAULT_PATH + session["name"] + ".txt", "w+")
        local_updater.write("---all done---" + "\n")
        local_updater.write(str(session["user_counter"]) + "\n")
        local_updater.close()

        # check if others are done 
        provided_coders = [line.rstrip() for line in open(CODERS)]
        coders_left_todo = ''
        for coder in provided_coders:
            try:
                to_read = DEFAULT_PATH + coder + ".txt"
                f = open(to_read, "r")
                lines = f.readlines()[0]
                if '---all done---' not in lines:
                    coders_left_todo += coder + " one or more open reviews<br/>"
                    if DEBUG:
                        print(coder + " one open review<br/>")
                else:
                    coders_left_todo += coder + " IS DONE!!!<br/>"
                    if DEBUG:
                        print(coder + " IS DONE!!!<br/>")

            except:
                if DEBUG:
                    print(coder, "coder has not voted on any abstracts yet, passing")
                coders_left_todo += coder + " nothing started<br/>"


    confetti_num = int(
        Path(PATH_confetti_rollover).read_text().strip()
    ) + 1
    return render_template(
        "index.html",
        abstract=this_abstract,
        title=this_title,
        url=this_url,
        user=session["name"],
        counter=session["user_counter"],
        goals=session["user_goals"],
        dones=session["dones"],
        confetti=confetti_num,
        other_coders_have_what_left=coders_left_todo,
    )


###
# we will update the abstract based on primary key here
###
@app.route("/serviceidlookup", methods=["GET", "POST"])
def serviceidlookup():
    print("--------------")
    print(session["name"])
    serviceid = request.form.get("serviceid")
    answer = request.form.get("answer")
    user_goal = request.form.get("users_goals")
    try:
        dones = request.form.get("dones")
    except:
        dones = None
    if user_goal != 0:
        session["user_goals"] = user_goal
        if session["dones"] is None or dones is None:
            session["dones"] = 0
        else:
            session["dones"] = int(dones) + 1

    # serviceid2 = serviceid + " extra"
    if DEBUG:
        print("<> abstract ID selected:", serviceid)
    if DEBUG:
        print("<>answer selected:", answer)
    this_path = default_path + str(serviceid) + ".csv"
    file_path = this_path
    lock_path = file_path + ".lock"
    lock = FileLock(lock_path, timeout=timeout_for_locks)
    try:
        with lock.acquire():
            temp_df = pd.read_csv(this_path, names=colnames, header=None)
            if temp_df["user"].value_counts()[session["name"]] > 1:
                # early break out, this may occur if a user has clicked a button too quickly
                return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))
            else:
                if DEBUG:
                    print(temp_df["user"].value_counts()[session["name"]])
                last_row = temp_df.iloc[-1]
                current_review_count = int(last_row["review_count"])
                current_abstract = last_row["abstract"]
                current_title = last_row["title"]
                current_url = last_row["url"]
                last_row["in_progress"] = "no"
                current_review_count += 1
                temp_df.loc[len(temp_df.index)] = [
                    serviceid,
                    current_review_count,
                    current_url,
                    current_title,
                    current_abstract,
                    session["name"],
                    answer,
                    "no",
                    str(time.time()),
                ]
                # clear local progress here
                nonce = open(DEFAULT_PATH + session["name"] + ".txt", "w+")
                nonce.close()

                if DEBUG:
                    print("-------------------------")
                if DEBUG:
                    print(temp_df.head(50))
                temp_df.to_csv(file_path, index=False, header=False)
                if DEBUG:
                    print(temp_df.head(50))
                if DEBUG:
                    print("-------------------------")
                checker = pd.read_csv(this_path, names=colnames, header=None)

                # reset the open review checker
                session["incomplete_review"] = "none"
                session["abstract"] = "none"
                session["title"] = "none"
                session["url"] = "none"

                # update the user counter
                session["user_counter"] = int(session["user_counter"]) + 1

                if DEBUG:
                    print(checker.head(50))
                if DEBUG:
                    print("[+] successful lock process, returning now")
                return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))
                # return render_template('index.html', value="thanks")
    except Timeout:
        if DEBUG:
            print(
                "[---] Another instance of this application currently holds the lock."
            )
        return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))


###
# update progress log and return
###
@app.route("/log_progress", methods=["GET", "POST"])
def log_progress():
    session["user_goals"] = 0
    session["dones"] = 0
    return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))


@app.route("/start", methods=["GET", "POST"])
def startSelector():

    provided_coders = [line.rstrip() for line in open(CODERS)]
    provided_coders_html = ""
    for coder in provided_coders:
        line = '<option value="' + coder + '">' + coder + "</option>"
        provided_coders_html += line

    # check if we have a username yet, else go back to username selection page
    try:
        check_user = session["name"]
        try:
            check_open_reviews = session["incomplete_review"]
        except:
            check_open_reviews = "none"
        try:
            check_curr_title = session["title"]
        except:
            check_curr_title = "none"
        try:
            check_curr_counter = session["user_counter"]
        except:
            check_curr_counter = "none"
        return render_template(
            "start.html",
            value=session["name"],
            open_reivew=check_open_reviews,
            curr_title=check_curr_title,
            curr_counter=check_curr_counter,
        )
    except:
        user = request.form.get("operator")
        if user != None:
            session["name"] = user
            if DEBUG:
                print("<> user selected", user)
            session["user_goals"] = 0
            session["dones"] = 0
            # time.sleep(2)
            session["incomplete_review"] = "need full review"
            return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))
        else:
            return render_template(
                "start.html", value="--empty--", coders=provided_coders_html
            )


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    time.sleep(2)
    return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))


@app.route("/reset_all_data", methods=["GET", "POST"])
def reset():
    if DEBUG: print("RESETTING <=========================================== ***")
    session.clear()
    # time.sleep(2)
    for file in glob.glob(PATH_TO_ABSTRACTS):
        if os.path.isfile(file + ".lock"):
            temp_df = pd.read_csv(file, names=colnames, header=None)
            print(temp_df.head())
            temp_df = temp_df.iloc[1:]
            first_row = temp_df.iloc[0]
            tmp = [str(first_row['unique_id']), '0', first_row['url'], first_row['title'], first_row['abstract'], 'none', 'none', 'no', first_row['time']]
            new_df = pd.DataFrame([tmp], columns=colnames)
            new_df.to_csv(file, index=False, header=True)
            os.remove(file + ".lock") 
            if DEBUG: print("reset: reset ", file)
    # remove metadata 
    curr_coders = [line.rstrip() for line in open(CODERS)]
    for coder in curr_coders:
        try:
            os.remove(DEFAULT_PATH + coder + ".txt")
        except:
            if DEBUG: print("reset: user has not logged in yet")
    # remove names of coders
    try: 
        os.remove(CODERS) 
    except:
        if DEBUG: print("reset: coders .txt already gone")
    if DEBUG: print("reset: removed coders log")
    os.remove(PATH_confetti_rollover)
    if DEBUG: print("reset: removed confetti log")
    local_updater = open(PATH_ngrok_authtoken, "w+")
    local_updater.write('none' + "\n")
    local_updater.close()
    if DEBUG: print("reset: reset ngrok auth token")
    os.remove(PATH_ngrok_domain) 
    if DEBUG: print("reset: reset ngrok domain")
    os.remove(PATH_num_reviews_per_abstract)
    if DEBUG: print("reset: reset number reviewers per abstract")
    if DEBUG: print("reset: *done* removing all data, fresh restart")
    time.sleep(5)
    if DEBUG: print(shutdown_server())
    else: shutdown_server()

    # os._exit(0)
    # kill -9 "$(pgrep ngrok)"
    # return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))
    # return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))



@app.route("/info", methods=["GET", "POST"])
def info():

    user_is_set = None
    try:
        this_user = session["name"]
        if DEBUG:
            print(this_user)
        user_is_set = True
    except:
        user_is_set = False

    if user_is_set:
        text_of_info = None
        with open("info/info.txt", "r+") as f:
            text_of_info = f.read()
            # backup periodic, on odd days when editing, 0 is monday I guess
            isNow = datetime.today().weekday()
            if (isNow % 2) == 0 or (isNow % 2) != 0:
                list_of_files = glob.glob(
                    "info/backups/*"
                )  # * means all if need specific format then *.csv
                if len(list_of_files) > 0:
                    latest_file = max(list_of_files, key=os.path.getctime)
                    with open(latest_file, "r") as curr_b:
                        curr = curr_b.read()
                        # print(curr)
                        if DEBUG:
                            print(
                                "is this a new edit, should we save this:",
                                curr != text_of_info,
                            )
                        if curr != text_of_info:
                            with open(
                                "info/backups" + str(int(time.time())) + ".txt", "w+"
                            ) as b:
                                b.write(text_of_info)
                else:
                    with open(
                        "info/backups" + str(int(time.time())) + ".txt", "w+"
                    ) as b:
                        b.write(text_of_info)

        curr = request.form.get("data")
        if curr != None and len(curr) != 0:
            text_of_info = curr
            # print(curr)
            with open("info/info.txt", "w") as f:
                f.write(str(text_of_info))
        return render_template("info.html", value=text_of_info)
    else:
        return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))


@app.route("/progress")
def visualize():
    user_is_set = None
    try:
        print(session["name"])
        user_is_set = True
    except:
        user_is_set = False
    if user_is_set:
        provided_coders = [line.rstrip() for line in open(CODERS)]
        coders = {}
        for this_coder in provided_coders:
            coders[this_coder] = 0
        # coders = {'user1': 0, 'user2': 0,  'user3': 0,'user4': 0, 'user5': 0}
        coders_list = coders.keys()
        coders_dones = []
        for coder in coders_list:
            try:
                to_read = DEFAULT_PATH + coder + ".txt"
                f = open(to_read, "r")
                lines = f.readlines()[1]
                number_done = int(lines)
                coders_dones.append([coder, number_done])
            except:
                if DEBUG:
                    print(coder, "coder has not voted on any abstracts yet, passing")
        df_visual = pd.DataFrame(coders_dones, columns=["user", "counts"])
        df_visual = df_visual.sort_values("counts", ascending=False)
        sum = df_visual["counts"].sum()
        fig = px.bar(
            df_visual,
            x="user",
            y="counts",
            color="user",
        )
        graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        return render_template("progress.html", graphJSON=graphJSON, total_done=sum)

    else:
        return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))


@app.route("/history")
def history():
    user_is_set = None
    try:
        this_user = session["name"]
        if DEBUG:
            print(this_user)
        user_is_set = True
    except:
        user_is_set = False
    if user_is_set:

        all_dfs = []
        if DEBUG:
            print("getting all abstracts")
        # get all abstracts
        for file in glob.glob(PATH_TO_ABSTRACTS):
            if os.path.isfile(file + ".lock"):
                all_dfs.append(file)
        if DEBUG:
            print("---mid done with getting list")
        pool = Pool(2)  # number of cores you want to use
        df_list = pool.map(reader, all_dfs)  # creates a list of the loaded df's
        df = pd.concat(df_list)  # concatenates all the df's into a single df
        # df = pd.concat(all_dfs)
        if DEBUG:
            print("getting all abstracts____DONE")
        if DEBUG:
            print("narrowing down list")
        # only consider those by this user
        df = df[df.user == session["name"]]
        if DEBUG:
            print("narrowing down list____DONE")
        # sort these by time
        if DEBUG:
            print("sort by time")
        df = df.sort_values("time", ascending=False)
        if DEBUG:
            print("sort by time____DONE")

        # ignore everything that is not in-progress or completed
        keepers = []
        count = 0
        only_keep_this_many = 50
        for index, row in df.iterrows():
            as_str = row["time"]
            # this_time = row['time']
            parsed_time = moment.unix(float(as_str))
            simple_time = parsed_time.format("YYYY-M-D H:m")

            # do not show older in-list items
            # if you want to keep the inprogress one: and 'no' in row['in_progress']
            if "none" in row["vote"] or row["in_progress"] == "yes":
                if DEBUG:
                    print(
                        "kill it, it is not voted and in progress",
                        " ======>",
                        row["vote"],
                        row["in_progress"],
                    )
            else:
                keepers.append(
                    [
                        "<b><hr>"
                        + str(row["title"])
                        + "</b><hr></br></br/>"
                        + str(row["abstract"]),
                        str(row["unique_id"]),
                        simple_time,
                        str(row["vote"]),
                        '<a href="' + str(row["url"]) + '">link</a>',
                    ]
                )
                count += 1
                if count >= only_keep_this_many:
                    break
        ret = pd.DataFrame(
            keepers,
            columns=[
                "abstract",
                "unique_id",
                "time_reviewed",
                "vote",
                "url",
            ],
        )

        # Use render_template to pass graphJSON to html
        # return render_template('history.html', tables=[ret.to_html(index=False)], user=session['name'])
        return render_template(
            "history.html",
            only_keep_this_many=only_keep_this_many,
            user=session["name"],
            column_names=ret.columns.values,
            row_data=list(ret.values.tolist()),
            big_column="abstract",
            link_column="vote",
            zip=zip,
        )

    else:
        return redirect(url_for("startSelector", _scheme=HTTP_VARIANT, _external=True))


###
# change selection based on new input
###
@app.route("/editChoice", methods=["GET", "POST"])
def editChoice():
    selected_it = request.form.get("operator")
    changed_vote = None
    if selected_it == "yes":
        changed_vote = "yes, is relevant"
    elif selected_it == "no":
        changed_vote = "no, not relevant"
    else:
        changed_vote = "not_a_paper"
    original_vote = request.form.get("original_vote")
    revised_choice = False
    if original_vote == "yes," and selected_it != "yes":
        revised_choice = changed_vote
    if original_vote == "no," and selected_it != "no":
        revised_choice = changed_vote
    if original_vote == "not_a_paper" and selected_it != "not_a_paper":
        revised_choice = changed_vote
    # not_a_paper cannot be edited!
    # answer = request.form.get('name')
    if revised_choice != False:
        abstract_id = request.form.get("abstract_id")
        if DEBUG:
            print("<> revised chioce:", revised_choice)
        if DEBUG:
            print("<> abstract to edit:", abstract_id)
        this_path = default_path + str(abstract_id) + ".csv"
        file_path = this_path
        lock_path = file_path + ".lock"
        lock = FileLock(lock_path, timeout=timeout_for_locks)
        try:
            with lock.acquire():
                temp_df = pd.read_csv(this_path, names=colnames, header=None)
                for index, row in temp_df.iterrows():
                    if (
                        row["user"] == session["name"]
                        and row["unique_id"] == abstract_id
                        and row["vote"] != revised_choice
                        and row["vote"] != "none"
                    ):
                        if DEBUG:
                            print("this is value to switch")
                        if DEBUG:
                            print(row)
                        temp_df.at[index, "vote"] = revised_choice
                        temp_df.at[index, "time"] = str(time.time())
                temp_df.to_csv(file_path, index=False, header=False)
                if DEBUG:
                    print("[+] successful lock process, returning now")
                return redirect(
                    url_for("history", _scheme=HTTP_VARIANT, _external=True)
                )

        except Timeout:
            if DEBUG:
                print(
                    "[---] Another instance of this application currently holds the lock."
                )
            return redirect(url_for("index", _scheme=HTTP_VARIANT, _external=True))

    return redirect(url_for("history", _scheme=HTTP_VARIANT, _external=True))


if __name__ == "__main__":

    print(
"""
#
#
# ,-. ,-. ,-. |- 
# |   ,-| |   |  
# `-' `-^ '   `' 
#
#
# < DEMO: python3 cart.py -c user1 -c user2 > 
"""
    )

    ### sanity check that we have what we need
    # there are papers in the directory
    how_many_papers = len(glob.glob(PATH_TO_ABSTRACTS))
    if DEBUG: print("how many papers am i seeing", len(glob.glob(PATH_TO_ABSTRACTS)))
    if how_many_papers == 0:
        print("error, need to exit, there are no papers found in the '/abstracts' directory")
        sys.exit()
    # the papers are properly formed 
    check_n_abstracts = 30
    checker_count = 0
    for file in glob.glob(PATH_TO_ABSTRACTS):
        temp_df = pd.read_csv(file, names=colnames, header=None)
        temp_df = temp_df.iloc[1:]

        has_these_columns = set(temp_df.columns)
        should_have_these_columns = set(colnames)

        expected_types = {'unique_id': 'str', 'review_count': 'int', 'url': 'str', 'title': 'str', 'abstract': 'str', 'user': 'str', 'vote': 'str', 'in_progress': 'str', 'time': 'time'}
        for index,row in temp_df.iterrows():
            for col in colnames:
                if DEBUG: print(col, type(row[col]))
                if expected_types[col] == 'str':
                    if isinstance(row[col], str) == False:
                        print("error, need to exit, you have columns in your .csv paper files that do not conform. You should be passing in ", col, "as", expected_types[col], "See documentation: assumptions")
                        sys.exit()
                if expected_types[col] == 'int':
                    as_int = None
                    try:
                        as_int = int(row[col])
                    except:
                        print('error, need to exit, you have passed in the column "', col, '" a format that is incorrect:', type(row[col]), "this should be a ", expected_types[col])
                        sys.exit()
                    if isinstance(as_int, int) == False:
                        print("error, need to exit, you have columns in your .csv paper files that do not conform. You should be passing in ", col, "as", expected_types[col], "See documentation: assumptions")
                        sys.exit()
                if expected_types[col] == 'time':
                    try: 
                        as_str = row[col]
                        parsed_time = moment.unix(float(as_str))
                        simple_time = parsed_time.format("YYYY-M-D H:m")
                    except:
                        print("error, need to exit, you have columns in your .csv paper files that do not conform. You should be passing in ", col, "as", expected_types[col], "See documentation: assumptions")
                        sys.exit()
        if (len(should_have_these_columns.difference(has_these_columns))) == 0:
            if DEBUG: print("good check")
        else:
            print("error, need to exit, you have misformatted .csv paper files. See documentation: assumptions")
            sys.exit()
       
        checker_count += 1 
        if checker_count >= check_n_abstracts:
            print("great, abstract sampling looks good!")
            break;
    # check that ngrok_auth exists, or create it 
    if os.path.isfile(PATH_ngrok_authtoken) == False:
        local_updater = open(PATH_ngrok_authtoken, "w+")
        local_updater.write("none" + "\n")
        local_updater.close()
    

    ## parse options 
    parser = argparse.ArgumentParser("python3 cart.py")
    parser.add_argument(
        "-c",
        "--coders",
        action="append",
        help="username of each coder: <<< -c user1 -c user2 >>> would be two users",
        required=True,
    )
    parser.add_argument(
        "-r",
        "--reviewsPerAbstract",
        help="how many reviews per abstract, default is two",
        required=False,
    )
    parser.add_argument(
        "-p", "--port", help="what port should this live on", required=False
    )
    parser.add_argument(
        "-n",
        "--ngrok_authtoken",
        help="what is your ngrok authToken: https://dashboard.ngrok.com/get-started/your-authtoken",
        required=False,
    )
    parser.add_argument(
        "-d",
        "--ngrok_domain",
        help="what is your ngrok static domain: https://dashboard.ngrok.com/cloud-edge/domains",
        required=False,
    )
    parser.add_argument(
        "-cf",
        "--confetti",
        help="after how many votes cast should the website 'reward' the work with a confetti splash",
        required=False,
    )
    args = parser.parse_args()
    coder_IDs = args.coders
    if coder_IDs:
        local_updater = open(CODERS, "w+")
        for coder in args.coders:
            # store coders progress here
            local_updater.write(coder + "\n")
        local_updater.close()
    num_reviews_per_abstract = args.reviewsPerAbstract
    if num_reviews_per_abstract:
        local_updater = open(PATH_num_reviews_per_abstract, "w+")
        local_updater.write(num_reviews_per_abstract + "\n")
        local_updater.close()
    else:
        local_updater = open(PATH_num_reviews_per_abstract, "w+")
        local_updater.write("2" + "\n")
        local_updater.close()
    confetti_rollover = args.confetti
    if confetti_rollover:
        local_updater = open(PATH_confetti_rollover, "w+")
        local_updater.write(confetti_rollover + "\n")
        local_updater.close()
    else:
        local_updater = open(PATH_confetti_rollover, "w+")
        local_updater.write("50" + "\n")
        local_updater.close()
    ngrok_domain = args.ngrok_domain
    if ngrok_domain:
        local_updater = open(PATH_ngrok_domain, "w+")
        local_updater.write(ngrok_domain + "\n")
        local_updater.close()
    else:
        local_updater = open(PATH_ngrok_domain, "w+")
        local_updater.write("none" + "\n")
        local_updater.close()
    ngrok_auth = args.ngrok_authtoken
    if ngrok_auth:
        local_updater = open(PATH_ngrok_authtoken, "w+")
        local_updater.write(ngrok_auth + "\n")
        local_updater.close()
        HTTP_VARIANT = "https"
        if ngrok_domain:
            run_with_ngrok(
                app=app, domain='--domain='+Path(PATH_ngrok_domain).read_text().strip(), auth_token=Path(PATH_ngrok_authtoken).read_text().strip()
            )
        else:
            run_with_ngrok(
                app=app, domain=None, auth_token=Path(PATH_ngrok_authtoken).read_text().strip()
            )
        ## need to execute "Press CTRL+C to quit" twice because this starts up the non-ngrok flask
        app.run(use_reloader=False)
    else:
        this_port = args.port
        if this_port:
            port = this_port
        else:
            port = "8081"
        app.run(debug=False, host="0.0.0.0", port=port)
