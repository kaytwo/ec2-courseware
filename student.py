import boto
from time import time,sleep

ec2 = boto.connect_ec2()

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
    except Exception, e:
      print e
      print "instance not visible,retrying"
    sleep(retry)
  raise SystemExit("instance did not come up before timeout. Aborting.")

def start_student_vm():
  my_vm_id = boto.config.get_value('Custom','my_vm')
  ret = start_vm(my_vm_id) 
  if ret == False:
    raise SystemExit("could not start your VM.")
  else:
    print "instance started."
  wait_for_instance(my_vm_id)
  reservations = ec2.get_all_instances(instance_ids=(my_vm_id,))
  return reservations[0].instances[0].public_dns_name

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


vm_name = start_student_vm()
print "your vm has started. You can ssh to it at %s" % vm_name
