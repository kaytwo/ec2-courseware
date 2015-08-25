#!/usr/bin/env python

import boto
import csv
from optparse import OptionParser
import sys
from time import sleep,time
from subprocess import Popen, PIPE
from tempfile import mkdtemp
from shutil import rmtree
import shlex
from random import choice
import string

import smtplib
import os
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.Utils import COMMASPACE, formatdate
from email import Encoders


passwordcharacters = string.letters + string.digits
def generate_password(length=8):
  return ''.join(choice(passwordcharacters) for _ in xrange(length))
  

def send_mail(send_from, send_to, send_cc, subject, text, files={}, server="bcuda-east.cc.uic.edu."):
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
  smtp.sendmail(send_from, (send_to,send_cc), msg.as_string())
  smtp.close()


# class specific variables
CLASS = 'cs450'
SEMESTER = 'f15'
# AMI = 'ami-d0f89fb9' # for now, standard ubuntu 12.04.2 LTS
AMI = 'ami-864d84ee' # ubuntu 14.04 lts (hvm)
ACCOUNT = '020404094600' # ckanich
SAFE = True # in case of errors, bomb out instead of wiping old
instance_size = "m3.medium"
root_size = 8

iip_arn = None
# iip_arn = 'arn:aws:iam::020404094600:instance-profile/read-all-s3-buckets'


LOGIN_URL = "https://ckanich.signin.aws.amazon.com/console"
# find this at https://console.aws.amazon.com/iam/home#home


INSTRUCTOR = 'Chris Kanich <ckanich@uicbits.net>' # from address
# when sending email to @uic.edu, the smtp server will reject @uic.edu from
# addr's if you don't auth, that's why I used this alternate address.


CC_ADDR = 'Chris Kanich <ckanich@uic.edu>'

SAFE = False

policy_boilerplate = '''
{
   "Version": "2012-10-17",
   "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances", 
        "ec2:StartInstances"
      ],
      "Resource": "arn:aws:ec2:us-east-1:%s:instance/%s"
    }
   ],
   "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeInstance*"
      ],
      "Resource": "*"
    }
   ]
}
'''


email_text = '''
id_rsa (attached to this email) is your ssh private key. To use it by default
in a *nix environment, place it in ~/.ssh/ and make sure that it is unreadable
by group or other.

Using your private key, everyone in class can check out the class public repository using the command line:

git clone git@git.uicbits.net:cs450-f15/public.git

You can use 'git pull' within the public directory to check out any updates. Note that if you change files in this directory, you might confuse git pull, so don't change files in this directory - change them within your personal directory.

You can also checkout your personal repository like so:

git clone git@git.uicbits.net:cs450-f15/%s.git

Only you and the course admins can make updates to that repository. You will turn in your code by pushing updates to this repository.

'''

def create_local_keypair(username):
  mydir = mkdtemp()
  args = shlex.split('ssh-keygen -t rsa -N "" -f %s/prefix -C %s' % (mydir,username))
  print ' '.join(args)
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
    self.email = csvline
    self.username = self.email.split('@')[0]

  def emailto(self):
    return "%s <%s>" % (self.username, self.email)

  def send_mail(self):
    assert hasattr(self,'private_key')
    files = {'id_rsa':self.private_key}
    send_mail(INSTRUCTOR,self.emailto(),CC_ADDR,"Your %s VM credentials" % CLASS,email_text % (self.username),files)


def create_key_pair(username):
  pubkey,privkey = create_local_keypair(username)
  return pubkey,privkey


def create_class(classlist):
  keydir = "%s-%s" % (CLASS,SEMESTER)
  try:
    os.mkdir(keydir)
  except:
    pass
  students = []

  for student in classlist:
    student_id = '%s.%s.%s' % (CLASS,SEMESTER,student.username)
    student.student_id = student_id
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
      students.append(Student(line.strip()))
  return students

# students = read_student_file('cs450.csv')
students = read_student_file(sys.argv[1])

# create_access_keys(students)

create_class(students)



# wait_for_instance(boto.config.get_value('Custom','my_vm'))

# start_student_vm()

# create_class(['ckanich-testing',])
