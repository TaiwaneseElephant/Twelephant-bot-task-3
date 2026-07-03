import requests, json, os, re, datetime
apiurl = "https://zh.wikipedia.org/w/api.php"
headers = {
    "user-agent": "Twelephant-bot"
}
config = json.loads(list(requests.get(apiurl, headers=headers, params={"action":"query", "prop":"revisions", "rvprop":"content", \
          "titles":"User:Twelephant-bot/task/3/config.json", "format":"json"}).json()["query"]["pages"].values())[0]["revisions"][0]["*"])
pageid = config["pageid"]
archivemainpageid = config["archivemainpageid"]
banlogtemplate = config["banlogtemplate"]
banlogarchivepageheader = config["banlogarchivepageheader"]
banlogarchivepagetitleformat = config["banlogarchivepagetitleformat"]
banlogarchivemainpageoldformat = config["banlogarchivemainpageoldformat"]
banlogarchivemainpagenewformat = config["banlogarchivemainpagenewformat"]
banlogpage = requests.get(apiurl, headers=headers, params={"action":"query", "prop":"revisions", "rvprop":"content", "pageids":pageid, "format":"json"})\
.json()["query"]["pages"][pageid]
archivemainpage = requests.get(apiurl, headers=headers, params={"action":"query", "prop":"revisions", "rvprop":"content", "pageids":archivemainpageid, "format":"json"})\
          .json()["query"]["pages"][archivemainpageid]["revisions"][0]["*"]
archivemainpagechanged = False
banlogcontent = banlogpage["revisions"][0]["*"]
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
      banlogcontent = banlogcontent.replace(ban, "")
banlogarchivepages = {}
for ban, year in banlogs:
  if year in banlogarchivepages.keys():
    banlogarchivepages[year] += ban
  else:
    banlogarchivepage = list(requests.get(apiurl, headers=headers, params={"action":"query", \
    "prop":"revisions", "rvprop":"content", "titles":(banlogarchivepagetitleformat % (banlogtitle, year)), "format":"json"}).json()["query"]["pages"].values())[0]
    if"missing" in banlogarchivepage.keys():
      banlogarchivepages[year] = banlogarchivepageheader + ban
      archivemainpage = re.sub(r"(.+)$", (banlogarchivemainpageoldformat % r"\1"), archivemainpage)
      archivemainpage += banlogarchivemainpagenewformat %  (banlogarchivepagetitleformat % (banlogtitle, year))
      archivemainpagechanged = True
    else:
      banlogarchivepages[year] = banlogarchivepage["revisions"][0]["*"] + ban
if len(banlogarchivepages.keys()) > 0:
  session = requests.Session()
  logintoken = session.get(apiurl, headers=headers, params={"action":"query", "meta":"tokens", "type":"login", "format":"json"}).json()["query"]["tokens"]["logintoken"]
  session.post(apiurl, headers=headers, params={"action":"login"}, data={"lgname":"Twelephant-bot", "lgpassword":os.environ["BOTPWD"], "lgtoken":logintoken})
  csrftoken = session.get(apiurl, headers=headers, params={"action":"query", "meta":"tokens", "type":"csrf", "format":"json"}).json()["query"]["tokens"]["csrftoken"]
  for year, content in banlogarchivepages.items():
    session.post(apiurl, headers=headers, params={"action":"edit"}, data={"title":(banlogarchivepagetitleformat % (banlogtitle, year)), \
                                                                          "text":content, "summary":"自動存檔已過期的禁制", "minor":True, "bot":True, "token":csrftoken})
  session.post(apiurl, headers=headers, params={"action":"edit"}, data={"pageid":int(pageid), "text":banlogcontent, "summary":"自動存檔已過期的禁制", \
                                                                        "minor":True, "bot":True, "token":csrftoken})
if archivemainpagechanged:
    session.post(apiurl, headers=headers, params={"action":"edit"}, data={"pageid":int(archivemainpageid), "text":archivemainpage, "summary":"自動更新禁制存檔列表", \
                                                                        "minor":True, "bot":True, "token":csrftoken})
