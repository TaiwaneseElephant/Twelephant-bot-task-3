import pywikibot
from pywikibot import textlib
import datetime
import time
import re
import json

signature_pattern = r"(?i)\[\[(?:(?:User(?:[ _]talk)?|UT?|用[戶户]|使用者):|Special:(?:Contrib(?:ution)?s|(?:用[戶户]|使用者)?(?:[貢贡][獻献]))/)"
time_stamp_pattern = r"\d{4}年\d{1,2}月\d{1,2}日 \([一二三四五六日]\) \d{2}:\d{2} \(UTC\)"
rx1 = re.compile(f"{signature_pattern}.*?{time_stamp_pattern}")
config_page_pattern = re.compile(r"User:([^/]+)/subscription\.json")

def save(site, page, text:str, summary:str = "", add:bool = False, minor:bool = True, max_retry_times:int = 3):
    if not page.botMayEdit():
        return False
    e = None
    oringinal_text = ""
    if add and page.exists():
        oringinal_text = page.get(force = True, get_redirect = True)
    for _ in range(max_retry_times):
        try:
            if add and page.exists():
                page.text = textlib.add_text(oringinal_text, text, site = site)
            else:
                page.text = text
            page.save(summary, minor = minor)
            return True
        except pywikibot.exceptions.EditConflictError as e:
            print(f"Warning! There is an edit conflict on page '{page.title()}'!")
            oringinal_text = page.get(force = True, get_redirect = True)
        except pywikibot.exceptions.LockedPageError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the page is protected!")
            break
        except pywikibot.exceptions.AbuseFilterDisallowedError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the AbuseFilter!")
            break
        except pywikibot.exceptions.SpamblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed by the SpamFilter because the edit add blacklisted URL!")
            break
        except pywikibot.exceptions.TitleblacklistError as e:
            print(f"Warning! The edit attempt on page '{page.title()}' was disallowed because the title is blacklisted!")
            break
    print(f"The attempt to edit the page '{page.title()}' was stopped because of the error below:\n{e}\nThe edit is '{text[:100]}', and the summary is '{summary}'.")
    return False

def send_message(site, talk_page_name:str, message:str, summary:str = "message send by twelephant-bot"):
    talk_page = pywikibot.Page(site, talk_page_name)
    save(site, talk_page, message, summary, add = True, minor = False)

def check_subscribed_pages(site, user, pages):
    rx2 = re.compile(f"{signature_pattern}\\s*{user.replace(' ', '[ _]')}.*?{time_stamp_pattern}")
    for page in pages:
        latest_revision_id  = page.latest_revision_id
        if latest_revision_id != pages[page]["latest_revision_id"]:
            latest_revision = page.get(force = True)
            sections_then = textlib.extract_sections(pages[page]["latest_revision"], site)
            sections_now = textlib.extract_sections(latest_revision, site)
            subscribed_sections = {}
            for i in sections_then.sections:
                title = i.title
                if title in pages[page]["section_names"] and not title in subscribed_sections:
                    subscribed_sections[title] = rx1.findall(i.content)
            for i in sections_now.sections:
                title = i.title
                if title in subscribed_sections:
                    self_talk = rx2.findall(i.content)
                    ignore_talk = set(subscribed_sections[title] + self_talk)
                    for j in rx1.findall(i.content):
                        if j not in ignore_talk:
                            send_message(site, talk_page_name = f"User talk:{user}", message = f"{{{{subst:User:Twelephant-bot/talkback|{page.title()}|{title}}}}}", summary = "回覆通知")
                            break
            pages[page]["latest_revision_id"] = latest_revision_id
            pages[page]["latest_revision"] = latest_revision

def set_page_dict(template):
    page_dict = {}
    for json_page in template.getReferences(follow_redirects = True, only_template_inclusion = True, filter_redirects = False, namespaces = 2, content = True):
        match = config_page_pattern.match(json_page.title())
        if match is None:
            continue
        user = match.groups()[0].replace("_", " ")
        try:
            config = json.loads(json_page.get())
            assert isinstance(config, list)
            config = config[:-1]
            page_list = [(pywikibot.Page(site, i[0]), i[1]) for i in config]
            page_dict[user] = {page : {"latest_revision" : page.get(), "latest_revision_id" : page.latest_revision_id, "section_names" : section_names} \
                               for page, section_names in page_list if page.exists()}
        except:
            continue
    return page_dict

site = pywikibot.Site("wikipedia:zh")
template = pywikibot.Page(site, "User:Twelephant-bot/subscription")
page_dict = set_page_dict(template = template)
while True:
    for _ in range(6):
        time.sleep(600)
        for user, pages in page_dict.items():
            check_subscribed_pages(site, user, pages)
    try:
        page_dict = set_page_dict(template = template)
    except:
        pass
