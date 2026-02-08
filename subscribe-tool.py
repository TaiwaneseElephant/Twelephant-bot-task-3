import pywikibot
from pywikibot import textlib
import datetime
import time
import re
import json

signature_pattern = r"(?i)\[\[(?:(?:User(?:[ _]talk)?|UT?|用[戶户]|使用者):|Special:(?:Contrib(?:ution)?s|(?:用[戶户]|使用者)?(?:[貢贡][獻献]))/)"
time_stamp_pattern = r"\d{4}年\d{1,2}月\d{1,2}日 \([一二三四五六日]\) \d{2}:\d{2} \(UTC\)"
rx1 = re.compile(f"{signature_pattern}.*?{time_stamp_pattern}")
config_page_name_pattern = re.compile(r"User:([^/]+)/subscription\.js")
config_page_content_pattern = re.compile(r'''var _addText = "\{\{User:Twelephant-bot/subscription\}\}";\n(\[[\s\S]*?\]);''')

def save(site, page, text:str, summary:str = "", add:bool = False, minor:bool = True, max_retry_times:int = 3) -> bool:
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

def check_subscribed_pages(site, user:str, pages:dict) -> None:
    rx2 = re.compile(f"{signature_pattern}\\s*{re.escape(user).replace(' ', '[ _]')}.*?{time_stamp_pattern}")
    for page_name in pages:
        try:
            page = pywikibot.Page(site, page_name)
            if not page.exists():
                continue
            latest_revision = page.get(force = True)
            latest_revision_id  = page.latest_revision_id
            if latest_revision_id != pages[page_name]["latest_revision_id"]:
                sections_then = textlib.extract_sections(pages[page_name]["latest_revision"], site).sections
                sections_now = textlib.extract_sections(latest_revision, site).sections
                subscribed_sections = {}
                for i in sections_then:
                    title = i.heading
                    level = i.level
                    for j, k in pages[page_name]["section_names"]:
                        if (title == j and level == k):
                            subscribed_sections[(title, level)] = rx1.findall(i.content)
                            break
                for i in sections_now:
                    title = i.heading
                    level = i.level
                    for j, k in subscribed_sections:
                        if (title == j and level == k):
                            self_talk = rx2.findall(i.content)
                            ignore_talk = set(subscribed_sections[(title, level)] + self_talk)
                            for j in rx1.findall(i.content):
                                if j not in ignore_talk:
                                    send_message(site, f"User talk:{user}", f"{{{{subst:User:Twelephant-bot/notification|{page_name}|{title}}}}}", "章節新留言通知 ")
                                    break
                            break
                pages[page_name]["latest_revision_id"] = latest_revision_id
                pages[page_name]["latest_revision"] = latest_revision
        except Exception as e:
            print(f"The attempt to check the page '{page_name}' was stopped because of the error below:\n{e}\nThe subscribed section are {pages[page_name]["section_names"]}.")
            continue

def set_page_dict(site, template) -> dict:
    page_dict = {}
    for config_page in template.getReferences(follow_redirects = True, only_template_inclusion = True, filter_redirects = False, namespaces = 2, content = True):
        match = config_page_name_pattern.match(config_page.title())
        if match is None:
            continue
        user = match.groups()[0].replace("_", " ")
        try:
            match = config_page_content_pattern.match(config_page.get(force = True))
            if match is None:
                continue
            config = json.loads(match.groups()[0])
            assert isinstance(config, list)
            page_list = [(pywikibot.Page(site, i[0]), i[1]) for i in config]
            page_dict[user] = {page.title() : {"latest_revision" : str(page.get()), "latest_revision_id" : int(page.latest_revision_id), "section_names" : section_names} \
                               for page, section_names in page_list if page.exists()}
        except:
            print(f"The attempt to check the page '{page_name}' was stopped because of the error below:\n{e}")
            continue
    return page_dict

def run():
    site = pywikibot.Site("wikipedia:zh")
    template = pywikibot.Page(site, "User:Twelephant-bot/subscription")
    page_dict = set_page_dict(site, template)
    record_page = pywikibot.Page(site, "User:Twelephant-bot/subscription_record.json")
    save(site, record_page, json.dumps(page_dict), "Update")
    print("Start!")
    time.sleep(600)
    for user, pages in page_dict.items():
        check_subscribed_pages(site, user, pages)
        print(user)

if __name__ == "__main__":
    run()

