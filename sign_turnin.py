import csv
import os
import subprocess
import sys
import time

PIPE=subprocess.PIPE

def run(cmd):
  proc = subprocess.Popen(cmd, universal_newlines=True,stdout=PIPE, stderr=PIPE)
  return proc.communicate()
  

if len(sys.argv) != 4:
  print("usage: {} classlist tag-to-sign repo_base".format(sys.argv[0]))
  sys.exit(1)

classlist = sys.argv[1]
hw_tagname = sys.argv[2]
baseurl = sys.argv[3]
netids = []

tag_suffix = time.strftime("%Y%m%d",time.localtime())

with open(classlist) as f:
  for line in csv.reader(f):
    name, uin, status, email = line
    netid = email.split('@')[0]
    netids.append(netid)

os.chdir('testing')

for netid in netids:
  stdo,stde = run(["git","clone","{}{}.git".format(baseurl,netid)])
  if 'fatal' not in stde or 'already exists' in stde:
    print("{} repo cloned.".format(netid))
  elif 'fatal' in stde:
    print("fatal error cloning:\n{}".format(stde))
    sys.exit(1)
  else:
    print("unexpected error:\n{}".format(stde))
    sys.exit(1)
  os.chdir(netid)
  stdo,stde = run(["git","fetch","--all","--tags"])
  if 'fatal' in stde:
    print("error fetching all remote crap:\n{}".format(stde))
    continue
  stdo,stde = run(["git","checkout",hw_tagname])
  if "error: pathspec '{}' did not match".format(hw_tagname) in stde:
    print("{} did not tag correctly.".format(netid))
    continue
  elif 'error' in stde:
    print("some error:\n{}".format(stde))
    continue
  # else:
  #   print("{} tagged {}.".format(netid,hw_tagname))

  stdo,stde = run(["git","tag","-s",hw_tagname + "_" + tag_suffix,'-m','signed turnin commit'])
  if stdo == '' and stde == '':
    stdo,stde = run(["git","push","--tags"])
    print(stdo)
    print(stde)
  else:
    print(stdo)
    print(stde)

  os.chdir("..")

