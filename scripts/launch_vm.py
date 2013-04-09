#!/usr/bin/python
import shlex, subprocess
import os
import pprint
import sys
import time
import commands

command = ['bash', '-c', 'source /root/keystonerc_admin && env']
proc = subprocess.Popen(command, stdout = subprocess.PIPE)
for line in proc.stdout:
  (key, _, value) = line.partition("=")
  os.environ[key] = value
proc.communicate()
#pprint.pprint(dict(os.environ))


def getFlavorID(flavor):
    command = "nova --os-username " + os.environ["OS_USERNAME"] + " --os-password " + os.environ["OS_PASSWORD"] + " --os-tenant-name " + os.environ["OS_TENANT_NAME"] + " --os-auth-url " +  os.environ["OS_AUTH_URL"] + " flavor-list"
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", flavor], stdin=p1.stdout, stdout=subprocess.PIPE)
    out, err = p2.communicate()
    result = out.split()
    return result[1]
    
def getImageID(image):
    command = "nova --os-username " + os.environ["OS_USERNAME"] + " --os-password " + os.environ["OS_PASSWORD"] + " --os-tenant-name " + os.environ["OS_TENANT_NAME"] + " --os-auth-url " +  os.environ["OS_AUTH_URL"] + " image-list"
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", image], stdin=p1.stdout, stdout=subprocess.PIPE)
    out, err = p2.communicate()
    result = out.split()
    return result[1]
  
def launchVM(flavorID, imageID, vmName):
    print "Launching VM " + vmName
    command = "nova --os-username " + os.environ["OS_USERNAME"] + " --os-password " + os.environ["OS_PASSWORD"] + " --os-tenant-name " + os.environ["OS_TENANT_NAME"] + " --os-auth-url " +  os.environ["OS_AUTH_URL"] + " boot --flavor "+ flavorID + " --image " + imageID + " --key-name guna-kp-1" + " " + vmName
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", " id"], stdin=p1.stdout, stdout=subprocess.PIPE)
    out, err = p2.communicate()
    result = out.split()
    if len(result) >= 4:
       vmID = result[3]
       print "VM ID: " + vmID
       return vmID
    return None

def createVolume(name, size):
    command = "cinder --os-username " + os.environ["OS_USERNAME"].rstrip() + " --os-password " + os.environ["OS_PASSWORD"].rstrip() + " --os-tenant-name " + os.environ["OS_TENANT_NAME"].rstrip() + " --os-auth-url " +  os.environ["OS_AUTH_URL"].rstrip() + " create --display_name " + name + " " + str(size)
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    p2 = subprocess.Popen(["grep", " id"], stdin=p1.stdout, stdout=subprocess.PIPE)
    out, err = p2.communicate()
    result = out.split()
    return result[3]

def attachVolume(vmID, volID):
    command = "nova --os-username " + os.environ["OS_USERNAME"].rstrip() + " --os-password " + os.environ["OS_PASSWORD"].rstrip() + " --os-tenant-name " + os.environ["OS_TENANT_NAME"].rstrip() + " --os-auth-url " +  os.environ["OS_AUTH_URL"].rstrip() + " volume-attach " + vmID + " " + volID + " auto"
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = p1.communicate()
    print out


def waitForVM(vmID):
    print "Waiting for VM " + vmID + " to reach status ACTIVE"
    for i in range(1,600): # 600 seconds, 10 minutes max wait
      command = "nova --os-username " + os.environ["OS_USERNAME"].rstrip() + " --os-password " + os.environ["OS_PASSWORD"].rstrip() + " --os-tenant-name " + os.environ["OS_TENANT_NAME"].rstrip() + " --os-auth-url " +  os.environ["OS_AUTH_URL"].rstrip() + " list"
      args = shlex.split(command)
      p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
      p2 = subprocess.Popen(["grep", vmID], stdin=p1.stdout, stdout=subprocess.PIPE)
      out, err = p2.communicate()
      result = out.split()
      status = result[5]
      if i%5==0:
         print ".",
         sys.stdout.flush()
      if status != "ACTIVE":
         time.sleep(1)
      else:
         time.sleep(10)
         break
    print "STATUS: " + status

def getVMIP(vmID):
    for i in range(1,10):
      command = "nova --os-username " + os.environ["OS_USERNAME"].rstrip() + " --os-password " + os.environ["OS_PASSWORD"].rstrip() + " --os-tenant-name " + os.environ["OS_TENANT_NAME"].rstrip() + " --os-auth-url " +  os.environ["OS_AUTH_URL"].rstrip() + " show " + vmID
      #print command
      args = shlex.split(command)
      p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
      p2 = subprocess.Popen(["grep", " network"], stdin=p1.stdout, stdout=subprocess.PIPE)
      out, err = p2.communicate()
      result = out.split()
      #print result
      if len(result) >= 5:
         ip = result[4]
         return ip
      return None

import commands

def waitForSSHD(vmIP):
    print "Waiting for SSHD on " + vmIP
    for i in range(1,600): # 600 seconds, 10 minutes max wait
      ret, out = commands.getstatusoutput("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /root/received/guna-kp-1.pem root@"+vmIP+" ls /")
      if ret == 0:
         break
      else:
         #print ret
         #print out
         print ".",
         sys.stdout.flush()
         time.sleep(1)

def runCommand(command):
    args = shlex.split(command)
    p1 = subprocess.Popen(args, stdout=subprocess.PIPE)
    out, err = p1.communicate()
    result = None
    if out is not None:
       print out
       result = out
    if err is not None:
       print err
       result = err
    return result

if len(sys.argv) < 3:
    sys.stderr.write('Usage: ' + sys.argv[0] + ' <tenantName> <jobName> <instance>\n')
    sys.exit(1)

tenant = sys.argv[1]
job = sys.argv[2]
instance = sys.argv[3]
flavorID = getFlavorID("m1.large")
imageID = getImageID("Ubuntu-CDH4-SnapShot")
vmName = tenant+"-"+job+"-vm-" + instance
vmID = launchVM(flavorID, imageID, vmName)
waitForVM(vmID)
vmIP = getVMIP(vmID)   
print "IP address is: " + vmIP

if vmIP is not None:
   waitForSSHD(vmIP)
   print "Copying BDS software on to the VM"
   sys.stdout.flush()
   runCommand("scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -q -i /root/received/guna-kp-1.pem BD_Setup.tgz root@"+vmIP+":/root/")
   sys.stdout.flush()
   runCommand("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -q -i /root/received/guna-kp-1.pem root@"+vmIP+" tar xvf BD_Setup.tgz")
   sys.stdout.flush()
   runCommand("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -q -i /root/received/guna-kp-1.pem root@"+vmIP+" /root/BD_Setup/setup_bds_job.sh")
   sys.stdout.flush()
   runCommand("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -q -i /root/received/guna-kp-1.pem root@"+vmIP+" /root/BD_Setup/run_bds_job.sh")
   sys.stdout.flush()


#volName = "tenant-"+job+"-vm-vol-" + str(i+1)
#   volID = createVolume(volName, volumeSize)
# wait for instance to be in running state
#   attachVolume(vmID, volID)
 
