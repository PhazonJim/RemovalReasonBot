import praw
import csv
import json
import os
import re
import yaml
from pprint import pprint
from praw.models import MoreComments

#===Globals===#
#Reddit PRAW Object
reddit = None
#Removal Reasons Pulled from wiki
removalReasons = None
#Object to keep track of submissions
submissions = {}
#Object containing list of submissions already dealt with 
postCache = None
postCacheName = None
#Config file
config = None

def init():
    global config
    global reddit
    global postCacheName
    global postCache
    global removalReasons

    config = yaml.load(open('config.yaml').read())
    client = config['client']
    reddit = praw.Reddit(**client)
    removalReasons = getRemovalReasons()
    #Load in post cache
    postCacheName = os.path.join(os.path.dirname(__file__), "cache.json")
    with open(postCacheName, 'r') as fin:
        cache = fin.read()
    postCache = json.loads(cache)

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

def getRemovalReasons():
    #Grab the removal reasons from the wiki
    wikiPage = reddit.subreddit(config['wiki_subreddit']).wiki[config['removal_reasons_wiki']].content_md
    return yaml.load(wikiPage)

def checkForDuplicateComments(submissionObj):
    #Check top level comments in the submission object
    for top_level_comment in submissionObj.comments:
        if isinstance(top_level_comment, MoreComments):
            continue
        #If there is a top level comment from the bot username, return true
        if top_level_comment.author == config['client']['username']:
            return True
    return False

def postComment(submissionObject, submissionRule):
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

def saveCache():
    with open(postCacheName, 'w') as fout:
        for chunk in json.JSONEncoder().iterencode(postCache):
            fout.write(chunk)

if __name__ == '__main__':
    #Initiate a bunch of stuff
    init()
    #Get moderator object from PRAW
    moderator = reddit.subreddit(config['subreddit']).mod
    #Only check for removelink actions, grab last X since we dont want to spend too much time grabbing post information
    for log in moderator.log(action='removelink',limit=config['mod_log_depth']):
        #Don't check for removals by AutoMod
        if log._mod not in config['ignore_mods']:
            #Submission ID from mod log
            submissionId = log.target_fullname.split('_')[1]
            submissions[submissionId] = ''
    #Figure out the rules that were flaired in each submission
    for submission in submissions:
        #If the submission has already been commented on, we don't need to worry about leaving a comment
        if submission not in postCache:
            submissionObject = reddit.submission(id=submission)
            submissionFlair = submissionObject.link_flair_text
            rule = getRuleFromRegexMatch(submissionFlair)
            if rule:
                #If a rule was found in the flair, add the rule and submission object to our submissions dict
                submissions[submission] = {"rule": rule, "_self": submissionObject}
    #Leave comments
    for submission in submissions:
        submissionObject = submissions[submission]['_self']
        submissionRule = submissions[submission]['rule']
        if not checkForDuplicateComments(submissionObject):
            result = postComment(submissionObject, submissionRule)
            if result:
                postCache[submission] = result.id
    #Write out
    saveCache()