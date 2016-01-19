#!/usr/bin/env python
from __future__ import print_function

from getpass import getpass
import sys
from subprocess import Popen, PIPE
from tempfile import mkdtemp
from shutil import rmtree
import shlex

import smtplib
import os
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders

# class specific variables
CLASS = 'cs361'
SEMESTER = 's16'
TA_NETIDS = 'schowd6 zshi22'
CC_ADDR = 'Chris Kanich <ckanich@uic.edu>'
INSTRUCTOR_NETID = "ckanich"
SERVER = 'git.uicbits.net'
GITOLITE_USER = 'git'

SEND_FROM_ADDR = CC_ADDR

CLASSID = "%s-%s" % (CLASS,SEMESTER)


email_text = '''
id_rsa (attached to this email) is your ssh private key. To use it by default
in a *nix environment, place it in ~/.ssh/ and make sure that it is unreadable
by group or other.

Using your private key, everyone in class has read access to the public repository. If you would like to check the code out by itself, you can do so at:

git clone {user}@{server}:{classid}/public.git

This will make a subdirectory called "public" with the current version of all published skeleton code for the class.

You can use 'git pull' within the public directory to check out any updates. Note that if you change files in this directory, you might confuse git pull, so don't change files in this directory - change them within your personal directory.

You can also checkout your personal repository like so:

git clone {user}@{server}:{classid}/{netid}.git

Only you and the course admins can read or make updates to that repository. You will turn in your code by pushing updates to this repository.


You can also use the Microsoft Azure cloud platform to deploy your class virtual machine. You can redeem this code at http://www.microsoftazurepass.com/

{azure_code}

Check the course web page for more instructions on creating and connecting to your VM.

'''

 
mail_username = raw_input("enter your uic netid:")
mail_password = getpass()

def send_mail(send_from, send_to, send_cc, subject, text, files={}, server="mail.uic.edu."):
  assert type(files)==dict

  msg = MIMEMultipart()
  msg['From'] = send_from
  msg['To'] = send_to
  msg['CC'] = send_cc
  msg['Date'] = formatdate(localtime=True)
  msg['Subject'] = subject

  msg.attach( MIMEText(text) )

  for fname,fbody in files.items():
    part = MIMEBase('application', "octet-stream")
    part.set_payload( fbody )
    Encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment; filename="%s"' % fname)
    msg.attach(part)

  smtp = smtplib.SMTP(server)
  smtp.starttls()
  smtp.login(mail_username,mail_password)
  # smtp.set_debuglevel(True)
  smtp.sendmail(send_from, (send_to,send_cc), msg.as_string())
  smtp.close()



def create_local_keypair(username):
  mydir = mkdtemp()
  args = shlex.split('ssh-keygen -t rsa -N "" -f %s/prefix -C %s' % (mydir,username))
  print(' '.join(args))
  p = Popen(args, stdout=PIPE)
  stdout = p.communicate()[0]
  if p.returncode != 0:
    raise Exception("could not create ssh key")
  public_key = open(mydir + '/prefix.pub').read()
  private_key = open(mydir + '/prefix').read()
  rmtree(mydir)
  return public_key, private_key

class Student:
  def __init__(self,csvline):
    # must be in format from my bookmarklet
    # that format is:
    # lastname; firstname, uin, registration status, email address
    name, uin, status, email = csvline.split(',')
    lastname, firstname = name.split(';')
    self.name = firstname.strip() + " " + lastname.strip()
    self.email = email
    self.username = self.email.split('@')[0]

  def emailto(self):
    return "%s <%s>" % (self.name, self.email)

  def send_mail(self):
    assert hasattr(self,'private_key')
    files = {'id_rsa':self.private_key}
    send_mail(SEND_FROM_ADDR,self.emailto(),CC_ADDR,"Your %s ssh credentials" % CLASS,email_text.format(user=GITOLITE_USER,server=SERVER,classid=CLASSID,netid=self.username,azure_code=self.azure_code),files)


def create_key_pair(username):
  pubkey,privkey = create_local_keypair(username)
  return pubkey,privkey


def create_class(classlist,codes):
  keydir = CLASSID 
  try:
    os.mkdir(keydir)
  except:
    pass
  students = []

  for student in classlist:
    student_id = '%s-%s' % (CLASSID,student.username)
    student.student_id = student_id
    student.azure_code = codes.pop()
    # create student ssh keypair
    public_key,private_key = create_key_pair(student_id)
    student.public_key = public_key
    student.private_key = private_key
    with open(keydir + '/' + student.username + '.pub','w') as f:
      f.write(public_key)
    student.send_mail()


def read_student_file(filename):
  students = []
  with open(filename) as f:
    for line in f:
      try:
        students.append(Student(line.strip()))
      except IndexError:
        pass

  return students

def read_azure_file(filename):
  codes = []
  with open(filename) as f:
    for line in f:
      tokens = line.strip().split()
      # assuming azure codes are always 14 chars long
      if len(tokens) == 1 and len(tokens[0]) == 14:
        codes.append(tokens[0])
  
  return codes

def dump_azure_file(filename, codes):
  with open(filename,'w') as f:
    for k in codes:
      f.write("%s\n" % k)

def create_gitolite_conf(students):
  allstudents = ' '.join([x.username for x in students])
  with open("%s.conf" % CLASSID,'w') as f:
    print("\n# BEGIN %s" % (CLASSID),file=f)
    print("@%s-ta = %s" % (CLASSID,TA_NETIDS),file=f)
    print("@%s-students = %s\n"%(CLASSID, allstudents) ,file=f)

    print("repo %s/public" % CLASSID,file=f)
    print("  R = @%s-students" % CLASSID,file=f)
    print("  RW+ = %s @%s-ta\n" % (INSTRUCTOR_NETID,CLASSID),file=f)

    for u in allstudents.split():
      print("repo %s/%s" % (CLASSID,u),file=f)
      print("  RW+ = %s" % u,file=f)
      print("  RW+ = %s @%s-ta\n" % (INSTRUCTOR_NETID,CLASSID),file=f)

    print("# END %s" % CLASSID,file=f)



# students = read_student_file('cs450.csv')
students = read_student_file(sys.argv[1])

codes = read_azure_file(sys.argv[2])

# create_access_keys(students)

# this method removes entries from the codes list
create_class(students, codes)

dump_azure_file(sys.argv[2],codes)

create_gitolite_conf(students)

