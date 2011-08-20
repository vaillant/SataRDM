'''
Created on Jul 30, 2011

@author: vaillant
'''
import unittest
import vmksatardm

class Test(unittest.TestCase):

    def testGetDiskInfo(self):
        (chdir, disks) = vmksatardm.getDiskInfo("storage-1ide.xml")
        self.assertEquals(chdir, "/vmfs/volumes/4e3144a9-545ea006-7f1c-000c292e315e")
        self.assertEqual(len(disks), 5)
        self.assertEqual(disks[0].name,"mpx.vmhba1:C0:T2:L0")
        self.assertEqual(disks[0].vendor,"VMware, ")
        self.assertEqual(disks[0].size,"4294967296")
        self.assertEqual(disks[0].getpreferredpathuid(), "pscsi.vmhba1-pscsi.0:2-mpx.vmhba1:C0:T2:L0")
        self.assertEqual(disks[0].getpartitiontypes(), ["0"])
  
        self.assertEqual(disks[2].getpartitiontypes(), ["0", "5", "6", "251", "4", "6", "6", "252", "6"])
  
        self.assertEqual(disks[3].name, "t10.ATA_____VMware_Virtual_IDE_Hard_Drive___________00000000000000000001")
        self.assertEqual(disks[3].size, "6442450944")
        self.assertEqual(disks[3].getpreferredpathuid(), "ide.vmhba0-ide.0:0-t10.ATA_____VMware_Virtual_IDE_Hard_Drive___________00000000000000000001")
        self.assertEqual(disks[3].getpartitiontypes(), ["0"])
        self.assertEqual(disks[3].getpartitiontypes().count("251"), 0)
        self.assertEqual(disks[3].getDeviceUID(), "vml.01000000003030303030303030303030303030303030303031564d77617265")
       
    def testStringToIntList(self):


        (error, list) = vmksatardm.stringToIntList("a",1)
        self.assertNotEqual(error, None)
          
        (error, list) = vmksatardm.stringToIntList("0",1)
        self.assertNotEqual(error, None)

        (error, list) = vmksatardm.stringToIntList("1,2,3",2)
        self.assertNotEqual(error, None)

        (error, list) = vmksatardm.stringToIntList("",1)
        self.assertEqual(error, None)
        self.assertEqual(list, [])
 
        (error, list) = vmksatardm.stringToIntList("none",1)
        self.assertEqual(error, None)
        self.assertEqual(list, [])
          
        (error, list) = vmksatardm.stringToIntList("all",1)
        self.assertEqual(error, None)
        self.assertEqual(list, [1])

        (error, list) = vmksatardm.stringToIntList("all",4)
        self.assertEqual(error, None)
        self.assertEqual(list, [1,2,3,4])

        (error, list) = vmksatardm.stringToIntList("1,2,3,4",4)
        self.assertEqual(error, None)
        self.assertEqual(list, [1,2,3,4])

        (error, list) = vmksatardm.stringToIntList("1,4",4)
        self.assertEqual(error, None)
        self.assertEqual(list, [1,4])


if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testGetDiskInfo']
    unittest.main()