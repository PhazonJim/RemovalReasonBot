import praw
import csv
import json
import os
import re
import yaml
from praw.models import MoreComments

#===Constants===#
CONFIG_FILE = os.path.join(os.path.dirname(__file__),"config.yaml")
CACHE_FILE =  os.path.join(os.path.dirname(__file__), "cache.json")

#===Globals===#
#Config file
config = None

def loadConfig():
    global config
    #Load configs
    try:
        config = yaml.load(open(CONFIG_FILE).read(), Loader=yaml.FullLoader)
    except:
        print("'config.yaml' could not be located. Please ensure 'config.example' has been renamed")
        exit()

def initReddit():
    client = config["client"]
    reddit = praw.Reddit(**client)
    return reddit

def loadCache():
    postCache = {}
    try:
        with open(CACHE_FILE, "r") as fin:
            postCache = json.load(fin)
    except Exception as e:
        print (e)
    return postCache

def getRuleFromRegexMatch(flair):
    regexes = config["regexes"]
    if not flair:
        return None
    #Remove whitespace and force lowercase for the flair
    flair = flair.strip().replace(" ", "").lower()
    #If we match a single rule return back with the first one (we can add additional logic to grab all rules violated)
    for regex in regexes:
        if (re.search(regexes[regex], flair)):
            return regex
    return None

def getRemovalReasons(reddit):
    #Grab the removal reasons from the wiki
    wikiPage = reddit.subreddit(config["wiki_subreddit"]).wiki[config["removal_reasons_wiki"]].content_md
    return yaml.load(wikiPage, Loader=yaml.FullLoader)

def checkForDuplicateComments(submissionObj):
    #Check top level comments in the submission object
    submissionObj.comments.replace_more(limit=0)
    return any(comment.distinguished for comment in submissionObj.comments)

def postComment(submissionObject, submissionRule, removalReasons):
    #Build up comment body from wiki
    commentBody = ""
    commentBody += removalReasons["header"]
    commentBody += removalReasons["rules"][submissionRule]
    commentBody += removalReasons["footer"]
    try:
        #Leave a comment
        comment = submissionObject.reply(commentBody)
        comment.mod.distinguish(how="yes",sticky=True)
        comment.mod.lock()
        return comment
    except Exception as e:
        print (e)
        #If anything bad happens, return back false
        return False

def saveCache(postCache):
    with open(CACHE_FILE, "w") as fout:
        for chunk in json.JSONEncoder().iterencode(postCache):
            fout.write(chunk)

if __name__ == "__main__":
    #Intialize 
    loadConfig()
    postCache = loadCache()
    reddit = initReddit()
    moderator = reddit.subreddit(config["subreddit"]).mod
    removalReasons = getRemovalReasons(reddit)
    #Local vars
    submissions = {}
    #Only check for removelink actions, grab last X since we dont want to spend too much time grabbing post information
    for log in moderator.log(action="removelink",limit=config["mod_log_depth"]):
        if log._mod not in config["ignore_mods"]:
            submissionId = log.target_fullname.split("_")[1]
            if submissionId not in postCache:
                submissionObject = reddit.submission(id=submissionId)
                if submissionObject.removed:
                    submissionFlair = submissionObject.link_flair_text
                    rule = getRuleFromRegexMatch(submissionFlair)
                    if rule != None:
                        submissions[submissionId] = {"rule": rule, "_self": submissionObject}

    #Leave removal reason comments
    for submission in submissions:
        submissionObject = submissions[submission]["_self"]
        submissionRule = submissions[submission]["rule"]
        if not checkForDuplicateComments(submissionObject):
            result = postComment(submissionObject, submissionRule, removalReasons)
            if result:
                postCache[submission] = result.id
    #Write out
    if postCache:
        saveCache(postCache)