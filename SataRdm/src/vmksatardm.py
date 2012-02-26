#!/usr/bin/python
'''
Created on Jul 30, 2011

@author: vaillant
'''

from xml.etree.ElementTree import parse
from optparse import OptionParser
from subprocess import Popen, PIPE
import exceptions
import os
import StringIO

RDM_DIR = "RDMs"  # in which folder to create the RDMs
FILE_EXT = ".vmdk"
TYPE_MAP = { "physical": "-z", "virtual": "-r"}  # maps options to vmkfstools option
GIBIBYTES = 1024 * 1024 * 1024
VMLPATH = "/vmfs/devices/disks/"

def getValueFor(element, s):
    ''' return v, where <value name=x>v</value> and x==s'''
    result = [ v.text for v in element.getchildren() if v.tag == "value" and v.attrib['name'] == s]
    assert len(result) == 1, "expecting element with <value name='%s'> under %s element" % (s, element.tag)
    return result[0]

def stringToIntList(str,maximum):
    # return (error, [int])
    # i.e. (None, [1,2]) = stringToIntList("1,2", 2)
    error = None
    result = []
    if str=="all":
        result = range(1,maximum+1)
    elif str=="none" or str=="":
        result = []
    else:
        try:
            result = [int(s) for s in str.split(",") ]
            for r in result:
                if not r in range(1,maximum+1):
                    error = "value '%d' out of range (1..%d)" % (r,maximum)
        except exceptions.ValueError, e:
            error = "%s" % (e)
    return (error,result)

def executeCmd(strs, noprint, noexec):
    result = ""
    if not noprint:
        print " ".join(strs)
    if not noexec:
        if strs[0] == "cd":
            os.chdir(strs[1])
        elif strs[0] == "mkdir":
            os.mkdir(strs[1])
        else:
            result = Popen(strs)
        return result    

class DiskInfo(object):
    def __init__(self,root,dict):
        self.__dict__.update(dict)
        self.root = root
    def getpreferredpathuid(self):
        e = self.root.find("lun/nmp-device-configuration/fixed-path-selection-policy")
#        result = [ v.text for v in e.iter("value") if v.attrib['name'] == "preferred-path-uid" ]
#        assert len(result) == 1, "expecting element with <value name='preferred-path-uid'> under <lun> element"
        return getValueFor(e, "preferred-path-uid")
    def getpartitiontypes(self):
        parts = self.root.findall("partitions/disk-lun-partition")
        result = [ getValueFor(p, "partition-type")  for p in parts ]
        return result
    def getDeviceUID(self):
        uids = self.root.findall("lun/device-uids/device-uid")
        result = [ getValueFor(p, "uid")  for p in uids if getValueFor(p, "uid").startswith("vml.")]
        assert len(result) > 0, "The device must have one UID starting with 'vml.'"
        return result[0]
    def getRDMFile(self):
        def convert(str):
            return str.replace(" ", "")
        def convert2(str):
            return str.replace(" ", "-",1).replace(" ","")
        def serialnumber():
            return self.devfspath.split("_")[-1]
        basename = "%s-%s-%dGB" % (convert2(self.model), serialnumber(), long(self.size) / GIBIBYTES)
        if os.path.exists(basename + FILE_EXT):
            i = 0
            while os.path.exists(basename + "-" + i + FILE_EXT): i=i+1
            basename = basename + "-" + i
        return basename + FILE_EXT
    def getCmd(self, options):
        #return command to create RDM as string[]
        vmlfile = VMLPATH + self.getDeviceUID()
        # removed, fails always in MacOS test env: assert os.path.exists(vmlfile)
        return ["vmkfstools",TYPE_MAP[options.dtype], vmlfile, self.getRDMFile(), "-a", options.adapter]

def getDiskInfo(filename):
    tree = parse(filename)
    luns = tree.findall("all-luns/disk-lun")
    disks = []
    for lun in luns:
        d = dict()
        for v in lun.find("lun").getchildren():
            if v.tag == "value":
                d[v.attrib['name'].replace("-","")] = v.text
        disks.append(DiskInfo(lun,d))
        
    chdir = None
    allvmfs = tree.findall("vmfs-filesystems/vm-filesystem")
    if len(allvmfs) > 0:
        chdir = getValueFor(allvmfs[0],"console-path")
    return (chdir,disks)

def main():
    usage = "usage: %prog [options]\n   Create raw device mapping for (S)ATA disks."
    parser = OptionParser(usage)
    parser.add_option("-f", "--file", dest="filename",
                      help="read storage config from FILENAME instead of using 'esxcfg-info -s -F xml', used mainly for testing")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet", default=False,
                      help="Run quiet, do not show information. Implies -all")
    parser.add_option("-n", "--noexec", dest="noexec", action="store_true",
                      help="show only commands, do not execute")
    parser.add_option("-l", "--all", dest="all", action="store_true",
                      help="create mapping for all disks without asking")
    parser.add_option("-a", "--adapter", dest="adapter", default="lsilogic",
                      help="adapter type: buslogic|lsilogic|ide [default: %default]")
    parser.add_option("-t", "--type", dest="dtype", default="physical", choices=['physical', 'virtual'], type="choice",
                      help="type of RDM: virtual|physical [default: %default] ")
    parser.add_option("-c", "--nochdir", dest="nochdir", action="store_true",
                      help="do not change directory to <first vmfs>/RDMs. If you specify this, execute command in correct VMFS folder. ")
    (options, args) = parser.parse_args()
    if len(args) != 0:
        parser.error("no argument allowed")
    assert options.dtype in TYPE_MAP
    if options.quiet:
        options.all = True

    ''' Reading configuration'''
    filename = ""
    if options.filename:
        if not options.quiet: print "reading from file %s..." % options.filename
        filename = options.filename
    else:
        if not options.quiet: print "reading from file 'esxcfg-info -s'..."
        if not os.path.exists("/sbin/esxcfg-info"):
            parser.error("Cannot find executable '/sbin/esxcfg-info', do you run on ESXi?")
        content = Popen(["esxcfg-info", "-s", "-F", "xml"], stdout=PIPE).communicate()[0]
        filename = StringIO.StringIO(content)
    (chdir,disks) = getDiskInfo(filename)
    if not options.nochdir and chdir == None:
        parser.error("Cannot find a VMFS file system for RDM files")
    if not options.nochdir and not options.quiet:
        print "RDM folder: " + chdir + "/" + RDM_DIR

    ''' Show possible disks (ataDisks)'''
    allAtaDisks = [d for d in disks if d.getpreferredpathuid().startswith("ide") or d.getpreferredpathuid().startswith("sata")]
    ataDisks = [d for d in allAtaDisks if d.getpartitiontypes().count("251") == 0]
    if not options.quiet:
        print "Found %d relevant ATA disks, not relevant:\n      %d other disks,\n      %d ATA disks with VMFS partition" % (
            len(ataDisks), len(disks)-len(allAtaDisks), len(allAtaDisks)-len(ataDisks))
        for i in range(0,len(ataDisks)):
            disk = ataDisks[i]
            print "%d) %s -> " % (i+1, disk.getRDMFile())
            print "          " + disk.getDeviceUID()

    ''' Ask for to-be mapped disks (rdmDisks)''' 
    rdmDisks = []
    if options.all:
        rdmDisks = ataDisks       
    elif ataDisks != []:
        inputList = [] # list of int's
        error = "dummy"
        while error:
            input = raw_input("Create Raw Device Mapping for which disks? [1..%d,all,none]" % len(ataDisks))
            (error,inputList) = stringToIntList(input, len(ataDisks))
            if error: print "Wrong input, please repeat (%s)" % error
        rdmDisks = [ataDisks[i-1] for i in inputList]
    
    '''execute commands for disks'''
    if rdmDisks != []:
        if not options.nochdir:
            # optionally create and cd to $chdir/RDMs
            assert os.path.exists(chdir)  # the filesystem discovered must exists
            rdmpath = chdir + "/" + RDM_DIR
            if not os.path.exists(rdmpath):
                executeCmd(["mkdir", rdmpath], options.quiet, options.noexec)
            executeCmd(["cd", rdmpath], options.quiet, options.noexec)
        for d in rdmDisks:
            executeCmd( d.getCmd(options), options.quiet, options.noexec)
    exit(0)

if __name__ == "__main__":
    main()
    

        
