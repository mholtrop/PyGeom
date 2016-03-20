"""
class GeometryEngine

@author: Maurik Holtrop (UNH) maurik@physics.unh.edu

This class represents the parameters for a GEMC "sensitive detector". 
"""

class SensitiveDetector():
    """ A class to represent the sensitive, or active, detector components.
        Each active detector component has a "sensitivity", a "hitType" ("flux", "Hodo", "SVT",...), and an "identity"
        in the geometry description. Each type of "sensitivity" needs to be further specified for proper readout. 
        Note that each type of "sensitivity" also needs to have a corresponding line in HitProcess_MapRegister.cc in Gemc,
        so the contents is not something arbitrary.
        This class stores those values for one type of sensitive detector and how to read those values into EVIO banks.
    """
    
    name=""
    description=""
    identifiers=""
    signalThreshold=""
    timeWindow=""
    prodThreshold=""
    maxStep=""
    riseTime=""
    fallTime=""
    mvToMeV=""
    pedestal=""
    delay=""
    bankId=""
    _BankRows=0  # must be an array [] Defines the rows of the EVIO bank. Each row contains a tuple ("row name", "Comment", id, "type" ) 

# Type is a two char string:
# The first char:
#  R for raw integrated variables
#  D for dgt integrated variables
#  S for raw step by step variables
#  M for digitized multi-hit variables
#  V for voltage(time) variables
#
# The second char:
# i for integers
# d for doubles

    def __init__(self,name,description,identifiers,signalThreshold="0*MeV",timeWindow="10*ns",
                 prodThreshold="0*mm",maxStep="1*mm",riseTime="1*ns",fallTime="1*ns",mvToMeV="1",pedestal="0",delay="0*ns",bankId=0):
        """ Initialization of class"""
        self.name = name
        self.description=description
        self.identifiers=identifiers
        self.signalThreshold=signalThreshold
        self.timeWindow=timeWindow
        self.prodThreshold=prodThreshold
        self.maxStep=maxStep
        self.riseTime=riseTime
        self.fallTime=fallTime
        self.mvToMeV=mvToMeV
        self.pedestal=pedestal
        self.delay=delay
        self.bankId=bankId
        self._BankRows=[]

        self.add_bank_row("bankid",name+" bank id", bankId, "Di")

    def add_bank_row(self,name,comment, idn,stype):
        """ Add a row to the EVIO Bank definition 
            name = 'rowname' 
            comment = 'comment string' 
            idn   = 1 'Evio row id number'
            stype = 'Di' 
            """
        self._BankRows.append( (name,comment,idn,stype) )
        
    def hit_str(self):
        """ Return a string for the detector__hits_variation.txt style file. """
        outstr = self.name + " | " 
        outstr+= self.description + " | " 
        outstr+= self.identifiers + " | " 
        outstr+= self.signalThreshold + " | "
        outstr+= self.timeWindow + " | "
        outstr+= self.prodThreshold + " | "
        outstr+= self.maxStep + " | "
        outstr+= self.riseTime + " | "
        outstr+= self.fallTime + " | "
        outstr+= self.mvToMeV + " | "
        outstr+= self.pedestal + " | "
        outstr+= self.delay
        return(outstr)

    def bank_str(self):
        """ Return a multi line string containing the text of the EVIO bank definitions. """
        print "Number of rows:" + str(len(self._BankRows))
        outstr=""
        for row in self._BankRows:
            outstr += self.name + " | " + " | ".join(map(str,row))+"\n"  # join with | the str(row) components.
        return(outstr)
    
    def bank_MySQL_str(self,Table,variation,idn=1):
        """Return a MySQL string to fill a banks table."""
        sql="INSERT INTO "+Table+" VALUES "
        for row in self._BankRows:            
            sql+= str((self.name,)+row+('now()',variation))+","
        sql = sql[:-1] + ";"
        return(sql)
    
    def hit_MySQL_str(self,Table,variation,idn=1):
        """ Return a MySQL string to fill the hit table """
        sql="INSERT INTO "+Table+" VALUES ('"
        sql+=self.name+"','"
        sql+=self.description+"','"
        sql+=self.identifiers+"','"
        sql+=self.signalThreshold+"','"
        sql+=self.timeWindow+"','"
        sql+=self.prodThreshold+"','"
        sql+=self.maxStep + "','"
        sql+=self.riseTime+ "','"
        sql+=self.fallTime+ "',"
        sql+=str(self.mvToMeV)+","
        sql+=str(self.pedestal)+",'"
        sql+=self.delay +"',"
        sql+="now(),'"
        sql+=variation+"')"
        
        return(sql)
            
    def hitType(self):
        """ Return the correct string for the hitType entry in the Geometry definition. """
        return(self.name)

    def sensitivity(self):
        """ Return the correct sting for the sensitivity entry in the Geometry definition. """
        return(self.name)
    
    def identity(self,*indexes):   # The * means, add all the arguments into the list called indexes
        """ Given a tuple of indexes i.e. (1,2,3), return the correct string for the indentity entry in the Geometry definition"""
        outstr=""
        ids = self.identifiers.split()
        for i in range(len(ids)):
            outstr += ids[i]+" manual " + str(indexes[i]) + " "
       
        return(outstr)
        
    def __str__(self):
        """ Print information of the class to sting. Because GEMC expects 2 files, one for hits and one for banks,
            this mehod cannot be used the write these files in one line."""
        outstr= self.hit_str() + "\n"
        outstr+="-------------------------------------------------------------------------------------------------------\n"
        outstr+= self.bank_str()
        return(outstr)
