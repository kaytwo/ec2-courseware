import sys

allstudents = []

for line in open(sys.argv[1]).readlines():
  emailaddr = line.strip()
  username = emailaddr.split('@')[0]
  allstudents.append(username)

print "\n# BEGIN cs450-f15"
print "@cs450-f15-ta = psnyde2"
print "@cs450-f15-students = " + ' '.join(allstudents) + '\n'

print "repo cs450-f15/public"
print "  R = @cs450-f15-students"
print "  RW+ = ckanich @cs450-f15-ta\n"

for u in allstudents:
  print "repo cs450-f15/%s" % u
  print "  RW = %s" % u
  print "  RW+ = @directors @cs450-f15-ta\n"

print "# END cs450-f15"
