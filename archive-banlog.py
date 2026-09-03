import requests, json, re, datetime, time
site = "zh.wikipedia.org"
apiurl = f"https://{site}/w/api.php"
headers = {
    "user-agent": "Twelephant-bot"
}
config = requests.get(f"https://{site}/w/index.php?title=User:Twelephant-bot/task/3/config.json&action=raw&ctype=application/json", headers=headers).json()
pageid = config["pageid"]
banlogtemplate = config["banlogtemplate"]
banlogarchivepageheader = config["banlogarchivepageheader"]
banlogarchivepagetitleformat = config["banlogarchivepagetitleformat"]
summary = config["summary"]
banlogpage = requests.get(apiurl, headers=headers, params={"action":"query", "prop":"revisions", "rvprop":"content", "pageids":pageid, "formatversion":2, "format":"json"})\
.json()["query"]["pages"][0]
banlogcontent = banlogpage["revisions"][0]["content"]
banlognewcontent = ""
banlogtitle = banlogpage["title"]
banlogs = []
now = datetime.datetime.now(datetime.timezone.utc)
for ban in re.finditer(f"\\{{\\{{\\s*{banlogtemplate}\\s*\\|[\\s\\S]+?\\}}\\}}\\n", banlogcontent):
  ban = ban.group()
  print(ban)
  ban_has_end = re.search(r"\|\s*end\s*=\s*(\d+)", ban)
  if ban_has_end:
    date = datetime.datetime.strptime((ban_has_end.groups()[0]), "%Y%m%d%H%M").replace(tzinfo=datetime.timezone.utc)
    print(date)
    if date < now:
      print(ban)
      banlogs.append([ban, date.year])
banlogarchivepages = {}
banlogarchivepagesbannum = {}
for ban, year in banlogs:
  banlogcontent = banlogcontent.replace(ban, "")
  if year in banlogarchivepages.keys():
    banlogarchivepages[year] += ban
    banlogarchivepagesbannum[year] += 1
  else:
    banlogarchivepage = requests.get(apiurl, headers=headers, params={"action":"query", \
    "prop":"revisions", "rvprop":"content", "titles":(banlogarchivepagetitleformat % (banlogtitle, year)), "formatversion":2, "format":"json"}).json()["query"]["pages"][0]
    if"missing" in banlogarchivepage.keys():
      banlogarchivepages[year] = banlogarchivepageheader + ban
    else:
      banlogarchivepages[year] = banlogarchivepage["revisions"][0]["content"] + ban
    banlogarchivepagesbannum[year] = 1
print(banlogcontent)
if len(banlogarchivepages.keys()) > 0:
  session = requests.Session()
  logintoken = session.get(apiurl, headers=headers, params={"action":"query", "meta":"tokens", "type":"login", "format":"json"}).json()["query"]["tokens"]["logintoken"]
  session.post(apiurl, headers=headers, params={"action":"login"}, data={"lgname":"Twelephant-bot", "lgpassword":BOTPWD, "lgtoken":logintoken})
  csrftoken = session.get(apiurl, headers=headers, params={"action":"query", "meta":"tokens", "type":"csrf", "format":"json"}).json()["query"]["tokens"]["csrftoken"]
  for year, content in banlogarchivepages.items():
    session.post(apiurl, headers=headers, params={"action":"edit"}, data={"title":(banlogarchivepagetitleformat % (banlogtitle, year)), \
                                                                          "text":content, "summary":(summary % banlogarchivepagesbannum[year]), "minor":True, "bot":True, "token":csrftoken})
  response =session.post(apiurl, headers=headers, params={"action":"edit"}, data={"pageid":pageid, "text":banlogcontent, "summary":(summary % len(banlogs)), \
                                                                        "minor":True, "bot":True, "token":csrftoken, "format": "json"})
  print(response.json())
time.sleep(300)
