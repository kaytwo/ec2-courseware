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
CLASS = 'cs491'
SEMESTER = 's16'
TA_NETIDS = 'schowd6 zshi22'
CC_ADDR = 'Chris Kanich <ckanich@uic.edu>'
INSTRUCTOR_NETID = "ckanich"
SERVER = 'git.uicbits.net'
GITOLITE_USER = 'git'

SEND_FROM_ADDR = CC_ADDR

CLASSID = "%s-%s" % (CLASS,SEMESTER)


email_text = '''

You can use the Microsoft Azure cloud platform to deploy your class virtual machine. You can redeem this code at http://www.microsoftazurepass.com/

Your promo code is:
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
  smtp.set_debuglevel(True)
  smtp.sendmail(send_from, (send_to,send_cc), msg.as_string())
  smtp.close()



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
    files = {}
    send_mail(SEND_FROM_ADDR,self.emailto(),CC_ADDR,"Your %s Azure code" % CLASS,email_text.format(user=GITOLITE_USER,server=SERVER,classid=CLASSID,netid=self.username,azure_code=self.azure_code),files)


def create_class(classlist,codes):
  students = []

  for student in classlist:
    student_id = '%s-%s' % (CLASSID,student.username)
    student.student_id = student_id
    student.azure_code = codes.pop()
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



students = read_student_file(sys.argv[1])

codes = read_azure_file(sys.argv[2])

# this method removes entries from the codes list
create_class(students, codes)

dump_azure_file(sys.argv[2],codes)

