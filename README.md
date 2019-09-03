# RemovalReasonBot
A reddit bot for leaving removal reasons on removed submissions that have been given a flair containing a rule number

# environment setup instructions
1. Install Python 3
2. Install PIP (https://pip.pypa.io/en/stable/installing/)
3. pip install praw
4. pip install pyyaml

# Configurations
1. Set up a reddit wikipage with YAML formatted reasons you want to have for each rule. This page must include a header, footer, and rules section. See example rule page example.yaml
2. Ensure user info, subreddit name, wikipage name, number of posts to check in moderator log, etc are set up in config.yaml

# Usage
1. Add removal reason comments to removed submissions 
    - run RemovalBot.py

# Features
1. Will only leave comments on posts that have been removed and have a rule in the flair that matches your configurations
2. Checks to ensure double comments aren't left
3. Keeps track of posts that have been commented on to save time/resources

#TODO
1. More error handling
2. Additional customizations