from random import shuffle,sample
import csv
from collections import defaultdict

users = []
usernames = {}
groups = defaultdict(list)

# precondition: remove everyone from this file that asked to be in a group
with open('cs361.csv') as cf:
  reader = csv.reader(cf)
  for row in reader:
    users.append((row[0],row[3]))

shuffle(users)

while len(users) > 0:
  word_file = "/usr/share/dict/words"
  WORDS = open(word_file).read().splitlines()
  name = 'team ' + ' '.join(sample(WORDS,2))
  try:
    for i in range(3):
      nu = users.pop()
      groups[name].append(nu)
  except IndexError:
    print "uneven groups"
    break


  
for gn in groups.keys():
  print gn
  for item in groups[gn]:
    print "  %s <%s>" % (item[0],item[1])


