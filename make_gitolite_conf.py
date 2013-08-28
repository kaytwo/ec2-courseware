allstudents = []

for line in open('classlist.temp').readlines():
  u = line.strip()
  allstudents.append(u)

print "\n# BEGIN cs450-f13"
print "@cs450-f13-ta = xiang"
print "@cs450-f13-students = " + ' '.join(allstudents) + '\n'

print "repo cs450-f13/public"
print "  R = @cs450-f13-students"
print "  RW+ = ckanich @cs450-f13-ta\n"

for u in allstudents:
  print "repo cs450-f13/%s" % u
  print "  RW = %s" % u
  print "  RW+ = @directors @cs450-f13-ta\n"

print "# END cs450-f13"
