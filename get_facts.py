#!/usr/bin/env python
import tweepy
import datetime
import praw
import difflib
import sqlite3 as lite
import time
import keys

auth = tweepy.OAuthHandler(keys.consumer_key, keys.consumer_secret)
auth.set_access_token(keys.access_token, keys.access_token_secret)
api = tweepy.API(auth)
con = lite.connect('/home/ubuntu/twitter/facts.db')

def similar(arg1, arg2):
    ratio = 0.8
    return difflib.SequenceMatcher(None, arg1.lower(), arg2.lower()).ratio() >= ratio

def get_existing_facts():
    with con:
        cur = con.cursor()
        cur.execute('SELECT Fact FROM Facts')
        tweets = [row[0] for row in cur.fetchall() if len(row[0]) < 141] #TODO remove facts that are too long
        return tweets

def get_long_facts():
    with con:
        cur = con.cursor()
        cur.execute('SELECT Fact FROM Facts')
        tweets = [row[0] for row in cur.fetchall() if len(row[0]) > 140] #TODO remove facts that are too long
        return tweets

def get_tweets(user):
    timeline = api.user_timeline(user)
    tweets = [ t.text for t in timeline if '@' not in t.text and 'bit.ly' not in t.text and 'http' not in t.text and '#' not in t.text and len(t.text) < 141 ]
    return tweets

def save_facts(facts):
    print 'appending', len(facts), 'new facts'
    with con:
        cur = con.cursor()
        for f in [ f.replace("'", '').replace('"', '').replace('TIL that ', '').replace('TIL ', '') for f in facts ]:
            if len(f) < 141:
                cur.execute("INSERT INTO Facts(`Fact`) VALUES('%s')" % f)

def get_til():
    r = praw.Reddit('example')
    return [ til.title.replace('TIL that ', '').replace('TIL ', '').replace('TIL', '').capitalize() for til in r.get_subreddit('todayilearned').get_hot() if len(til.title.replace('TIL that ', '').replace('TIL ', '').replace('TIL', ''    ).capitalize()) < 141]

def tweet():
    with con:
        cur = con.cursor()
        success = False
        while success == False:
            try:
                cur.execute('SELECT fact FROM facts WHERE used IS NULL ORDER BY RANDOM() LIMIT 1')
                fact = cur.fetchall()[0][0]
                if len(fact) < 141:
                    api.update_status(fact)
                    success = True
                else:
                    cur.execute("DELETE FROM facts WHERE id='%s'" % fact )
                    tweet()
            except Exception,e:
                    print 'error tweeting,sleeping 15min', e
                    time.sleep(940)
                    tweet()

def get_users():
    with con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM friends")
        num_friends = cur.fetchall()[0][0]
        print 'current userbase',num_friends
        cur.execute("SELECT COUNT(*) FROM friends WHERE favorited IS NOT NULL")
        total_favorited = cur.fetchall()[0][0]
        if total_favorited > num_friends / 2:
            #cur.execute("CREATE TABLE IF NOT EXISTS friends(id INT, favorited INT, lurked TEXT)")
            cur.execute("SELECT id FROM friends WHERE lurked IS NULL ORDER BY RANDOM() LIMIT 1")
            base = cur.fetchall()[0][0]
            friends = api.friends_ids(base)
            cur.execute("UPDATE friends SET lurked=1 WHERE id='%s'" % base)
            for f in friends:
                cur.execute("SELECT id FROM friends WHERE id = '%s'" % f)
                if cur.fetchall() == []:
                    cur.execute("INSERT INTO friends('id') VALUES('%s')" % f)

def favorite():
    with con:
        cur = con.cursor()
        cur.execute("SELECT id FROM friends WHERE favorited IS NULL ORDER BY RANDOM() LIMIT 100")
        users = [f[0] for f in cur.fetchall()]
        count = 0
        liked = []
        for u in users:
            success = False
            #print 'favoriting',api.get_user(u).screen_name
            while success == False:
                try:
                    api.get_user(u).status.favorite()
                    liked.append(u)
                    count += 1
                    print 'faved'
                    success = True
                except Exception,e:
                    print 'error on',u,e
                    if str(e) == "[{'message': 'You have already favorited this status', 'code': 139}]":
                        print 'setting faved...'
                        cur.execute("UPDATE friends SET favorited=1 WHERE id='%s'" % u)
                        success = True
                    elif str(e) == "'User' object has no attribute 'status'":
                        print 'deleting^^^'
                        try:
                            cur.execute("DELETE FROM friends WHERE id='%s'" % u )
                            success = True
                        except Exception,e:
                            time.sleep(10)
                            cur.execute("DELETE FROM friends WHERE id='%s'" % u )

                    elif str(e) == "[{'message': 'Rate limit exceeded', 'code': 88}]":
                        print 'rate exceeded,sleeping 15'
                        time.sleep(300)
                        print '10min'
                        time.sleep(300)
                        print '5 min remaining'
                        time.sleep(330)
                        print 'trying again'
                        break
        print 'favorited',count
        for i in liked:
            cur.execute("UPDATE friends SET favorited=1 WHERE id='%s'" % i)
        cur.execute("SELECT COUNT(*) FROM friends WHERE favorited IS NOT NULL")
        print 'total favorited',cur.fetchall()[0][0]
        cur.execute("SELECT COUNT(*) FROM friends")
        print 'total friends',cur.fetchall()[0][0]

if __name__ == '__main__':
    print 'started at:',datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    print 'tweeting'
    tweet()
    print 'gathering facts'
    existing_facts = get_existing_facts()
    handles = ['uberfacts', 'factsandtrivia','omglifehacks']
    new_facts = get_tweets('uberfacts')
    new_facts.extend(get_til())
    print 'saving facts'
    found = False
    add_facts = []
    for n in new_facts:
        for e in existing_facts:
            if similar(n, e):
                found = True
        if found is False:
            add_facts.append(n)
        found = False
    save_facts(add_facts)
    print 'appending',len(add_facts),'facts, done.'
#get_users()
#favorite()




