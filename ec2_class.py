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
  smtp.sendmail(send_from, send_to, msg.as_string())
  smtp.close()

iam = boto.connect_iam()
ec2 = boto.connect_ec2()
cloudwatch = boto.connect_cloudwatch()

# class specific variables
CLASS = 'cs450'
SEMESTER = 'f13'
AMI = 'ami-d0f89fb9' # for now, standard ubuntu 12.04.2 LTS
ACCOUNT = '020404094600'
SAFE = True # in case of errors, bomb out instead of wiping old
INSTRUCTOR = 'Chris Kanich <ckanich@uicbits.net>' # from address

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
Your ec2 username is %s and your password is %s. You can use 
these credentials to log in to the web interface at
https://ckanich.signin.aws.amazon.com. 

To start your VM:

In the web interface, navigate to Services -> EC2 -> Instances to see the list
of instances under my account. Your username will be the "Name" of your virtual
machine. If your virtual machine is shut off due to idleness, you can restart
it by highlighting it and selecting Actions -> Start Instance. Once it has
started, the "Public DNS" is the address you should ssh to to use the VM.

To log in to your VM:

id_rsa (attached to this email) is your ssh private key. To use it by default
in a *nix environment, place it in ~/.ssh/ and make sure that it is unreadable
by group or other. The username for sshing into your virtual machine is
'ubuntu'.

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
    for key,value in csvline.items():
      setattr(self,key,value)
    self.username = self.email.split('@')[0]

  def emailto(self):
    return "%s %s <%s>" % (self.firstname, self.lastname, self.email)

  def send_mail(self):
    assert hasattr(self,'privatekey')
    files = {'id_rsa':self.privatekey}
    send_mail(INSTRUCTOR,self.emailto(),CC_ADDR,"Your CS450 VM credentials",email_text % (self.student_id,self.pw),files)



'''
Retrieve-or-create methods
'''

def create_security_group(name):
  allgroups =  ec2.get_all_security_groups()
  thisgroup = [x  for x in allgroups if x.name == name]
  if len(thisgroup) == 0:
    return ec2.create_security_group(name,name)
  else:
    return thisgroup[0]

def create_user(username):
  everybody = iam.get_all_users().list_users_response.list_users_result.users
  thisuser = [x for x in everybody if x.user_name == username]
  if len(thisuser) == 0:
    return iam.create_user(username)
  else:
    return thisuser[0]

def create_key_pair_remote(username):
  allkeys = ec2.get_all_key_pairs()
  thisuser = [x for x in allkeys if x.name == username]
  if len(thisuser) == 1:
    if SAFE:
      raise SystemExit("user already has an ssh key")
    print "ALERT: user already has ssh key. Deleting old key and regenerating."
    print ec2.delete_key_pair(username)
  ssh_key = ec2.create_key_pair(username)
  return ssh_key

def create_key_pair(username):
  allkeys = ec2.get_all_key_pairs()
  thisuser = [x for x in allkeys if x.name == username]
  if len(thisuser) == 1:
    if SAFE:
      raise SystemExit("user already has an ssh key")
    print "ALERT: user already has ssh key. Deleting old key and regenerating."
    print ec2.delete_key_pair(username)
  pubkey,privkey = create_local_keypair(username)
  ssh_key = ec2.import_key_pair(username,pubkey)
  return pubkey,privkey


def create_access_key(student_id):
  allkeys = iam.get_all_access_keys(student_id).list_access_keys_response.list_access_keys_result.access_key_metadata
  if len(allkeys) != 0:
    print allkeys
    print "ALERT: user already has access key(s). Deleting old keys and regenerating."
    if SAFE:
      raise SystemExit("user already has an ssh key")
    for key in allkeys:
      iam.delete_access_key(key.access_key_id,user_name=student_id)
  return iam.create_access_key(student_id)

def wait_for_instance(instance_id,timeout=5*60,retry=5):
  now = time()
  while time() < (now + timeout):
    try:
      everybody = ec2.get_all_instance_status(instance_ids=(instance_id,))
      thisguy = [x for x in everybody if x.id == instance_id and getattr(x,'state_name',None) == 'running' ]
      if len(thisguy) != 0:
        print "instance started."
        return
      print "instance not yet running"
    except Exception,e:
      print e
      print "instance not visible,retrying"
    sleep(retry)
  print "instance did not come up before timeout. Aborting."
  sys.exit(1)

def create_class(classlist):
  keydir = "%s-%s" % (CLASS,SEMESTER)
  os.mkdir(keydir)
  students = []
  group = create_security_group("%s.%s" % (CLASS, SEMESTER))
  previous_rules = [str(x) for x in group.rules]
  for portnum in (22,80,443):
    if 'IPPermissions:tcp(%d-%d)' % (portnum,portnum) not in previous_rules:
      group.authorize('tcp',portnum,portnum,'0.0.0.0/0')
  if 'IPPermissions:udp(53-53)' not in previous_rules:
    group.authorize('udp',53,53,'0.0.0.0/0')

  for student in classlist:
    student_id = '%s.%s.%s' % (CLASS,SEMESTER,student.username)
    student.student_id = student_id
    # create student
    response = create_user(student_id)
    pw = generate_password()
    student.pw = pw
    iam.create_login_profile(student_id,pw)
    print "user created:",repr(response)
    user_id = response.user_id
    response = create_access_key(student_id)
    access_key = response.access_key_id
    secret_key = response.secret_access_key
    # create student ssh keypair
    public_key,private_key = create_key_pair(student_id)
    student.public_key = public_key
    student.private_key = private_key
    with open(keydir + '/' + student.username + '.pub','w') as f:
      f.write(public_key)

    # create VM
    reservation = ec2.run_instances(AMI,
                      instance_type='m1.small',
                      security_groups=(group.name,),
                      key_name=student_id
                      )
    print "instance run:",repr(reservation.instances[0])
    instance = reservation.instances[0]
    attempts = 5
    while attempts > 0:
      try:
        instance.add_tag('Name',student_id)
        break
      except e:
        print e
        sleep(5)
        attempts -= 1
      assert attempts != 0
    instance_id = instance.id
    wait_for_instance(instance_id)
    ec2.stop_instances((instance_id,))

    # allow student to stop and start and see the instance:
    result = iam.put_user_policy(student_id,student_id,policy_boilerplate.strip() % (ACCOUNT,instance_id))
    print "student policy installed."

    
    # add cloudwatch metric to shut down if net_out/hour < 100KB for 6 hours
    action='arn:aws:automate:us-east-1:ec2:stop'
    alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(name=student_id,namespace="AWS/EC2",metric="NetworkOut",dimensions={"InstanceId":instance_id}, comparison="<=",threshold=(100*1024),period=60*60,evaluation_periods=6,statistic="Sum",unit="Bytes",alarm_actions=[action,])
    metric = cloudwatch.put_metric_alarm(alarm)
    
    student.send_mail()




def read_student_file(filename):
  students = []
  with open(filename) as f:
    for item in csv.DictReader(f):
      students.append(Student(item))
  return students

students = read_student_file('cs450.csv')

create_class(students)

# wait_for_instance(boto.config.get_value('Custom','my_vm'))

# start_student_vm()

# create_class(['ckanich-testing',])
