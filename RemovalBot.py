import praw
import csv
import json
import os
import re
import yaml
from pprint import pprint
from praw.models import MoreComments

#===Globals===#
#Config file
config = None

def loadConfig():
    global config
    #Load configs
    try:
        config = yaml.load(open(os.path.join(os.path.dirname(__file__),'config.yaml')).read(), Loader=yaml.FullLoader)
    except:
        print("'config.yaml' could not be located. Please ensure 'config.example' has been renamed")
        exit()

def initReddit():
    client = config['client']
    reddit = praw.Reddit(**client)
    return reddit

def loadCache():
    postCache = {}
    postCacheName = os.path.join(os.path.dirname(__file__), "cache.json")
    try:
        with open(postCacheName, 'r') as fin:
            cache = fin.read()
        postCache = json.loads(cache)
    except Exception as e:
        print (e)
    return postCache

def getRuleFromRegexMatch(flair):
    #Get regex patterns from the config file
    regexes = config['regexes']
    #If there is no flair in the post, return nothing
    if not flair:
        return None
    #Remove whitespace and force lowercase for the flair
    flair = flair.strip().replace(' ', '').lower()
    #If we match a single rule return back with the first one (we can add additional logic to grab all rules violated)
    for regex in regexes:
        if (re.search(regexes[regex], flair)):
            return regex

def getRemovalReasons(reddit):
    #Grab the removal reasons from the wiki
    wikiPage = reddit.subreddit(config['wiki_subreddit']).wiki[config['removal_reasons_wiki']].content_md
    return yaml.load(wikiPage)

def checkForDuplicateComments(submissionObj):
    #Check top level comments in the submission object
    for top_level_comment in submissionObj.comments:
        if isinstance(top_level_comment, MoreComments):
            continue
        #If there is a top level comment from the bot username, return true
        if top_level_comment.author == 'PhazonJim':
            return True
    return False

def postComment(submissionObject, submissionRule, removalReasons):
    #Build up comment body from wiki
    commentBody = ''
    commentBody += removalReasons['header']
    commentBody += removalReasons['rules'][submissionRule]
    commentBody += removalReasons['footer']
    try:
        #Leave a comment
        comment = submissionObject.reply(commentBody)
        #Lock it
        comment.mod.lock()
        #Distinguish and Sticky 
        comment.mod.distinguish(how='yes', sticky=True)
        return comment
    except:
        #If anything bad happens, return back false
        return False

def saveCache(postCache):
    postCacheName = os.path.join(os.path.dirname(__file__), "cache.json")
    with open(postCacheName, 'w') as fout:
        for chunk in json.JSONEncoder().iterencode(postCache):
            fout.write(chunk)

if __name__ == '__main__':
    #load configuration yaml
    loadConfig()
    #Load in post cache
    postCache = loadCache()
    #Get moderator object from PRAW
    reddit = initReddit()
    moderator = reddit.subreddit(config['subreddit']).mod
    #Load Removal Reasons
    removalReasons = getRemovalReasons(reddit)
    #Local vars
    submissions = {}
    #Only check for removelink actions, grab last X since we dont want to spend too much time grabbing post information
    for log in moderator.log(action='removelink',limit=config['mod_log_depth']):
        #Don't check for removals by AutoMod
        if log._mod not in config['ignore_mods']:
            #Submission ID from mod log
            submissionId = log.target_fullname.split('_')[1]
            if submissionId not in postCache:
                submissionObject = reddit.submission(id=submissionId)
                if submissionObject.removed:
                    submissionFlair = submissionObject.link_flair_text
                    rule = getRuleFromRegexMatch(submissionFlair)
                    if rule:
                        #If a rule was found in the flair, add the rule and submission object to our submissions dict
                        submissions[submissionId] = {"rule": rule, "_self": submissionObject}

    #Leave comments
    for submission in submissions:
        submissionObject = submissions[submission]['_self']
        submissionRule = submissions[submission]['rule']
        if not checkForDuplicateComments(submissionObject):
            result = postComment(submissionObject, submissionRule, removalReasons)
            if result:
                postCache[submission] = result.id
    #Write out
    if postCache:
        saveCache(postCache)