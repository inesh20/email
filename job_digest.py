#!/usr/bin/env python3
# (shorter header to keep the file concise)
import os, sys, ssl, smtplib, time, feedparser, yaml
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from dateutil import parser as dateparser

def load_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def parse_rss(url):
    feed = feedparser.parse(url)
    source = feed.feed.get('title', url)
    items = []
    for e in feed.entries:
        title, link = e.get('title',''), e.get('link','')
        pub = e.get('published') or e.get('updated','')
        dt = None
        for key in ('published_parsed','updated_parsed'):
            if e.get(key):
                try: dt=datetime.fromtimestamp(time.mktime(e[key]),tz=timezone.utc)
                except: pass
        if not dt and pub:
            try:
                dt = dateparser.parse(pub)
                if not dt.tzinfo: dt = dt.replace(tzinfo=timezone.utc)
            except: pass
        items.append({'title':title,'link':link,'published':dt,'summary':e.get('summary',''),'source':source})
    return source, items

def within_window(dt, now, hours): return True if dt is None else (now-dt)<=timedelta(hours=hours)

def send_email(cfg, subject, html):
    smtp = cfg['email']['smtp']
    msg = EmailMessage()
    msg['Subject']=subject; msg['From']=cfg['email'].get('from',smtp['username']); msg['To']=', '.join(cfg['email']['to'])
    msg.set_content('HTML required'); msg.add_alternative(html, subtype='html')
    ctx = ssl.create_default_context()
    with smtplib.SMTP(smtp['host'],smtp.get('port',587)) as s:
        if smtp.get('use_tls',True): s.starttls(context=ctx)
        s.login(smtp['username'],smtp['password']); s.send_message(msg)

def main():
    cfg=load_config('config.yaml'); now=datetime.now(timezone.utc)
    all_items=[]
    for u in cfg.get('rss_feeds',[]): 
        try:
            src, items=parse_rss(u)
            all_items+=[it for it in items if within_window(it['published'],now,cfg.get('hours_window',24))]
        except Exception as e: print(e,file=sys.stderr)
    html='<h2>Veille emploi</h2>'+'<br>'.join(f"<a href='{i['link']}'>{i['title']}</a> - {i['source']}" for i in all_items)
    send_email(cfg,cfg.get('email_subject','Veille emploi'),html)

if __name__=='__main__': main()
