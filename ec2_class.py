#!/usr/bin/env python

import boto
from optparse import OptionParser
import sys
from time import sleep,time
from subprocess import Popen, PIPE
from tempfile import mkdtemp
from shutil import rmtree
import shlex


iam = boto.connect_iam()
ec2 = boto.connect_ec2()
cloudwatch = boto.connect_cloudwatch()

# class specific variables
CLASS = 'cs450'
SEMESTER = 'f13'
AMI = 'ami-d0f89fb9' # for now, standard ubuntu 12.04.2 LTS
ACCOUNT = '020404094600'
SAFE = True # in case of errors, bomb out instead of wiping old



policy_boilerplate = '''
{
   "Version": "2012-10-17",
   "Statement": [{
      "Effect": "Allow",
      "Action": [
        "ec2:StopInstances", 
        "ec2:StartInstances",
        "ec2:DescribeInstances"
      ],
      "Resource": "arn:aws:ec2:us-east-1:%s:instance/%s"
    }
   ]
}
'''

config_boilerplate = '''
[Credentials]
aws_access_key_id = %s
aws_secret_access_key = %s
'''

'''
create keyfiles locally
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
    except:
      print "instance not visible,retrying"
    sleep(retry)
  print "instance did not come up before timeout. Aborting."
  sys.exit(1)

def create_class(classlist):
  group = create_security_group("%s.%s" % (CLASS, SEMESTER))
  previous_rules = [str(x) for x in group.rules]
  for portnum in (22,80,443):
    if 'IPPermissions:tcp(%d-%d)' % (portnum,portnum) not in previous_rules:
      group.authorize('tcp',portnum,portnum,'0.0.0.0/0')
  if 'IPPermissions:udp(53-53)' not in previous_rules:
    group.authorize('udp',53,53,'0.0.0.0/0')

  for student in classlist:
    student_id = '%s.%s.%s' % (CLASS,SEMESTER,student)
    # create student
    response = create_user(student_id)
    print "user created:",repr(response)
    user_id = response.user_id
    response = create_access_key(student_id)
    access_key = response.access_key_id
    secret_key = response.secret_access_key
    # create student ssh keypair
    public_key,private_key = create_key_pair(student_id)

    # create VM
    reservation = ec2.run_instances(AMI,
                      instance_type='t1.micro',
                      security_groups=(group.name,),
                      key_name=student_id
                      )
    print "instance run:",repr(reservation.instances[0])
    instance = reservation.instances[0]
    instance.add_tag('Name',student_id)
    instance_id = instance.id
    wait_for_instance(instance_id)
    ec2.stop_instances((instance_id,))

    # allow student to stop and start the instance:
    result = iam.put_user_policy(student_id,student_id,policy_boilerplate.strip() % (ACCOUNT,instance_id))
    print "student policy installed."

    
    # add cloudwatch metric to shut down if net_out/hour < 100KB for 6 hours
    action='arn:aws:automate:us-east-1:ec2:stop'
    alarm = boto.ec2.cloudwatch.alarm.MetricAlarm(name=student_id,namespace="AWS/EC2",metric="NetworkOut",dimensions={"InstanceId":instance_id}, comparison="<=",threshold=(100*1024),period=60*60,evaluation_periods=6,statistic="Sum",unit="Bytes",alarm_actions=[action,])
    metric = cloudwatch.put_metric_alarm(alarm)


    with os.fdopen(os.open('id_aws', os.O_WRONLY | os.O_CREAT, 0600), 'w') as handle:
      handle.write(private_key)

    with os.fdopen(os.open(student,'.boto', os.O_WRONLY | os.O_CREAT, 0600), 'w') as handle:
      handle.write(config_boilerplate % (access_key,secret_key))

    instance_id_file = open('my_vm_id','w')
    instance_id_file.write(instance_id)
    instance_id_file.close()


def start_student_vm():
  try:
    f = open('my_vm_id')
    my_vm_id = f.read().strip()
  except:
    print "couldn't open file my_vm_id in the current directory."
    sys.exit()
  ret = start_vm(my_vm_id) 
  if ret == False:
    print "could not start your VM."
    sys.exit(1)
  wait_for_instance(my_vm_id)
  # tell student what the VM's IP is
  reservations = ec2.get_all_instances(instance_ids=(my_vm_id,))
  print "you can ssh to your VM at %s" % reservations[0].instances[0].public_dns_name
 


def start_vm(vm_id):
  now = time()
  retry = 5
  success = False
  while time() < (now + 5*60):
    try:
      # start the VM
      started = ec2.start_instances((vm_id,))
      return True
    except boto.exception.EC2ResponseError:
      sleep(retry)
  return False
 

public,private = create_local_keypair('ckanich')
print public
print private

# start_student_vm()

# create_class(['ckanich-testing',])
