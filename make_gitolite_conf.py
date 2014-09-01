import sys

allstudents = []

for line in open(sys.argv[1]).readlines():
  u = line.strip()
  uin,emailaddr,name = u.split(',')
  username = emailaddr.split('@')[0]
  allstudents.append(username)

print "\n# BEGIN cs450-f14"
print "@cs450-f14-ta = igupta5"
print "@cs450-f14-students = " + ' '.join(allstudents) + '\n'

print "repo cs450-f14/public"
print "  R = @cs450-f14-students"
print "  RW+ = ckanich @cs450-f14-ta\n"

for u in allstudents:
  print "repo cs450-f14/%s" % u
  print "  RW = %s" % u
  print "  RW+ = @directors @cs450-f14-ta\n"

print "# END cs450-f14"
