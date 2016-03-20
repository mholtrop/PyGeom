"""
class GeometryEngine

@author: Maurik Holtrop (UNH) maurik@physics.unh.edu

A Helper library for GEANT4 geometries that plays well with GEMC geometries. 

This is the main "engine" for using the PyGeom package to create GEMC geometries and to render GEMC geometries in ROOT.

"""

import re
import sys
import warnings
from __builtin__ import file
from Geometry import Geometry

try:
    import MySQLdb
    import _mysql_exceptions
    warnings.filterwarnings("error",category=MySQLdb.Warning)
except ImportError:
    print("warning MySQLdb not found - no database functionality.")

class GeometryEngine():
    """A class for building GEANT4 geometries.
    The initial purpose is to build the geometries for the MySQL database or text files used by Gemc1 or Gemc2.
    Each GeometryEngine object represents ONE 'detector' (as defined by Gemc).
    Expansion to other geometry formats is possible, see for instance the GeometryROOT class.
    """

    _DataBase=None
    _cursor=None
    _Detector=""
    _Geometry=None    # Stores all the geometries objects for the current detector part.
    _Materials=None
    _Parameters=None  # Paraeters to go into __parameter table
    _Sensitive_Detector=None        # 
    _Geometry_Table=None
    _Parameters_Table=None
    _Hit_Table=None
    _Banks_Table=None
    
    table_variation=0
    table_id = 0
    GemcVersion=0
    debug=0
    
# Special controls. Should not be needed.    
    _always_commit = 0 # Set to 1 to commit immediately after each sql_execute()
    
    def __init__(self,detector,variation="original",iden=1,machine=0,user=0,passwd=0,database=0,gemcversion=2):
        """ Does nothing. Can print a hello """
        # print "Init the GeometryEngine "
        self._Detector = detector
        self.GemcVersion=gemcversion
        self.table_variation=variation
        self.table_id = iden
        self._Geometry=[]  # Must be done here, otherwise [] will leak across instances.
        self._Parameters=[]
        self._Sensitive_Detector=[]
        self._Materials=[]
        if machine != 0:
            self.MySQL_OpenDB(machine, user, passwd, database)
            
    def __del__(self):
        """ Clean up at exit """
        if self._DataBase:
            self._DataBase.commit()
            self._DataBase.close()

    def get_database(self):
        """ Return the database handle. You can use this to initialize other
        GeometryEngine objects with the same database. """
        return(self._DataBase)

    def set_database(self,db):
        """ Set the database handle to db. You can use this to initialize this
        GeometryEngine objects with the same database as another. """
        self._DataBase = db
        self._cursor = self._DataBase.cursor()

    def add(self,geom):
        """ Add a Geometry class object to the list of geometry objects """
        self._Geometry.append(geom)
        
    def add_sensitivity(self,sens):
        """ Add a Sensitive_Detector object to the hits definitions """
        self._Sensitive_Detector.append(sens)

    def add_material(self,material):
        self._Materials.append(material)
  
    def find_volume_regex(self,name,flags=0):
        """ Find a particular geometry with a name that has regex match name from the Detector Geometry table.
            You can use a pattern: .*foo to search for 'foo' anywhere in the name.
            If you want to ignore case, pass flags=re.IGNORECASE (which is 2)"""
# OK, we usually have just one sensitive detector per geometry, so this might be over kill. Still it is handy.
        if not isinstance(self._Geometry,list):   # Are we initialized?
            print "This GeometryEngine appears not to be inialized"
            return(None)
        
        prog = re.compile(name,flags)
        found = [x for x in self._Geometry if prog.match(x.name)]
        if len(found)==0:
            return(None)

        return(found)
    
    def find_volume(self,name):
        """ Find a particular geometry with name=sens_name from the Detector Geometry table """
# OK, we usually have just one sensitive detector per geometry, so this might be over kill. Still it is handy.
        if not isinstance(self._Geometry,list):   # Are we initialized?
            print "GeometryEngine seems not to be inialized"
            return(None)
        
        found = [x for x in self._Geometry if x.name == name]
        if len(found)==0:
            return(None)
        
        if len(found)>1:
            print "Warning: More than one Detector Geometry with name:"+ name+" found in GeometryEngine"

        return(found[0])

    def find_children_regex(self,name,flags=0):
        """ Find those geometries that have name for their mother volume, from the Detector Geometry table.
            You can use a pattern: .*foo to search for 'foo' anywhere in the name.
            If you want to ignore case, pass flags=re.IGNORECASE (which is 2)"""
# OK, we usually have just one sensitive detector per geometry, so this might be over kill. Still it is handy.
        if not isinstance(self._Geometry,list):   # Are we initialized?
            print "The GeometryEngine is not inialized, oops."
            return(-1)
        
        prog = re.compile(name,flags)
        found = [x for x in self._Geometry if prog.match(x.mother)]
        if len(found)==0:
            return(None)

        return(found)
    
    def find_children(self,name):
        """ Find a list of geometries with mother=name from the Detector Geometry table """
# OK, we usually have just one sensitive detector per geometry, so this might be over kill. Still it is handy.
        if not isinstance(self._Geometry,list):   # Are we initialized?
            print "It seems that the GeometryEngine is not inialized"
            return(None)
        
        found = [x for x in self._Geometry if x.mother == name]
        if len(found)==0:
            return(None)
        
        return(found)
            
    def find_sensitivity(self,sens_name):
        """ Find a particular sensitivity with name=sens_name from the Sensitive Detector table """
# OK, we usually have just one sensitive detector per geometry, so this might be over kill. Still it is handy.
        if not isinstance(self._Sensitive_Detector,list):   # Are we initialized?
            print "Sensitive_Detector is not inialized"
            return(-1)
        
        found = [x for x in self._Sensitive_Detector if x.name == sens_name]
        if len(found)==0:
            if self.debug>1:
                print "Sensitive detector "+ sens_name+" not found in GeometryEngine"
            return(None)
        
        if len(found)>1:
            print "Warning: More than one Sensitive detector with name:"+ sens_name+" found in GeometryEngine"

        return(found[0])
    
            
    def quick_add_cube(self,position):
        """Quick way to add a cube of 1mm size at position pos (in cm) relative to root, for testing 
        purposes, color=red, material=vacuum"""
        cube = Geometry(
                        name="Test_Cube",
                        mother="root",
                        description="Test Cube",
                        pos= position,
                        pos_units="cm",
                        rot=[0,0,0],
                        rot_units="deg",
                        col="#ff0000",
                        g4type="Box",
                        dimensions=[0.1,0.1,0.1],
                        dims_units= "cm",
                        material="Vacuum",
                        sensitivity="no",
                        hittype="no",
                        identity="no"
                        )
        self._Geometry.append(cube)
        

    def MySQL_OpenDB(self,machine,user,passwd,database):
        """Open a MySQL database 'database' on host 'machine', with credentials 'user','passwd' """
        try:
            self._DataBase = MySQLdb.connect(machine,user,passwd,database)
            self._cursor = self._DataBase.cursor()
            self._DataBase.raise_on_warnings = True
            self._Geometry_Table = self._Detector + "__geometry"
            self._Parameters_Table = self._Detector + "__parameters"
            self._Hit_Table = self._Detector + "__hit"
            self._Banks_Table = self._Detector + "__bank"
            if self.debug:
                print "Database "+database+" opened for "+user+" on "+machine
                print self._DataBase
        except Exception as e:
            print "Error connecting to the database. Make sure MySQLdb is available."
            print e
            
    def MySQL_Table_Exists(self,table):
        """Returns True if the table exists, False if it does not. """
        if self.debug>2:
            print "Looking if table exists with name:'"+table+"'"

        sql = "show tables like '"+table+"'"
        n=self.sql_execute(sql)
        if self.debug>2:
            print "Search returns:'"+str(n)+"' = "+str(n!=0)

        return(n!=0)

    def MySQL_Get_Latest_Id(self,table,variation):
        """Find the lastest Id in the MySQL table for variation."""
        
        if self.debug>2:
            print "Looking up the max(id) for table '"+table+"'"
        if not self.MySQL_Table_Exists(table):
            if self.debug>0:
                print "ERROR: Table not found: '"+table+"'"
            return(None)

        sql = "select max(id) from "+table+" where variation = '"+variation+"';"
        n=self.sql_execute(sql)
        f = self._cursor.fetchone()
        if self.debug>2:
            print "From ID search we get '"+str(n)+"' with fetch: "+str(f)

        if f:
            if f[0]:
                return(f[0])
            else:
                return(0)
        else:
            return(0)
    
    def MySQL_Clean_Table(self,table,variation=-1,idn=-1):
        """Clean a table by deleting all entries in that table with variaion and id"""

        if not self.MySQL_Table_Exists(table):
            return(None)

        if variation == -1:
            variation = self.table_variation
        if idn == -1:
            idn = self.table_id
        
        if idn == -1:   # It is is still -1, then get the latest id from table for variation.
            idn = self.MySQL_Get_Latest_Id(table,variation)
            if not idn:
                return(0)
            
        if re.match('.*__hit',table) or re.match('.*__bank',table):
            if self.debug > 2:
                print "Cleaning a hit or bank table: "+table
            sql = "delete from "+table+" where variation = '"+variation+"'"

        else:
            if self.debug > 2:
                print "Cleaning a geometry table: "+table
            sql = "delete from "+table+" where variation = '"+variation+"' and id="+str(idn) 
            
        n=self.sql_execute(sql)         
        return(n)
            
    def MySQL_New_Tables(self):
        """ Create a new set of tables for this part of the detector. 
            For GEMC1 - Only a geometery table is created with the name of the table
            For GEMC2 - A geometry table is created with the name table__geometry,
                        plus a tables with the name table__parameters, table__hit and table__bank 
                        
            Note that an existing Geometry table will be deleted first, while a Parameters table is preseved."""

        if self._Detector ==0:
            print "ERROR -- The detector does not appear to be correctly initialized."
            return()
        
        self.MySQL_New_Geometry_Table()
            
        if self.GemcVersion == 2:
            # This will test to see if the parameters table exists, and if not, create one.    
            self.MySQL_New_Parameters_Table()
            self.MySQL_New_Hit_Table()
            self.MySQL_New_Bank_Table()
            
            
    def MySQL_New_Geometry_Table(self,table=0):
        """Create a new Geometry Table in the database. If the table already exists, it is cleared first"""
                    # For GEMC 2, we need to add __geomtery to the name, if not already there.

        if table:
            self._Geometry_Table = table

        if self.MySQL_Table_Exists(self._Geometry_Table):   # Table already exists
            if self.debug:
                print "Geometry table: "+self._Geometry_Table+" already exists, no need to create."
            return(False)
 
        sql="""CREATE TABLE `"""+ self._Geometry_Table +"""` (
            `name` varchar(40) DEFAULT NULL,
            `mother` varchar(100) DEFAULT NULL,
            `description` varchar(200) DEFAULT NULL,
            `pos` varchar(100) DEFAULT NULL,
            `rot` varchar(100) DEFAULT NULL,
            `col` varchar(10) DEFAULT NULL,
            `type` varchar(100) DEFAULT NULL,
            `dimensions` text,
            `material` varchar(60) DEFAULT NULL,
            `magfield` varchar(40) DEFAULT NULL,
            `ncopy` int(11) DEFAULT NULL,
            `pMany` int(11) DEFAULT NULL,
            `exist` int(11) DEFAULT NULL,
            `visible` int(11) DEFAULT NULL,
            `style` int(11) DEFAULT NULL,
            `sensitivity` varchar(40) DEFAULT NULL,
            `hitType` varchar(100) DEFAULT NULL,
            `identity` varchar(200) DEFAULT NULL,
            `rmin` int(11) DEFAULT NULL,
            `rmax` int(11) DEFAULT NULL,
            `time` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"""
        if self.GemcVersion == 2:
            sql += """ `variation` varchar(200) DEFAULT 'original',
                       `id`   int(11)  DEFAULT 0, """    
        sql+= """UNIQUE KEY (`variation`,`id`,`name`)) ENGINE=MyISAM DEFAULT CHARSET=latin1;"""
        if self.debug:
            print "Creating Geometry table: "+self._Geometry_Table+"."

        n=self.sql_execute(sql)
        return(n)
       
    def MySQL_New_Parameters_Table(self):
        """Create a new Parameters table if it does not already exists.
           If it does already exist, keep the old one."""
           
        self._Parameters_Table = self._Detector + "__parameters"

        if self.MySQL_Table_Exists(self._Parameters_Table):   # Table already exists
            if self.debug:
                print "Parameters table: "+self._Parameters_Table+" already exists, no need to create."

            return(False)
        
        sql="""create table IF NOT EXISTS """+ self._Parameters_Table +"""(
                       name              VARCHAR(250),
                       value             FLOAT,
                       units             VARCHAR(50),
                       description       VARCHAR(250),
                       author            VARCHAR(250),
                       author_email      VARCHAR(250),
                       pdf_drawing_link  VARCHAR(250),
                       drawing_varname   VARCHAR(250),
                       drawing_authors   VARCHAR(250),
                       drawing_date      VARCHAR(250),
                       upload_date       TIMESTAMP,
                       variation         VARCHAR(250),
                       rmin              INT,
                       rmax              INT,
                       id                INT,
                       PRIMARY KEY (variation, id, name) );"""
        if self.debug:
            print "Creating Parameters table: "+self._Parameters_Table+"."
        n=self.sql_execute(sql)
        return(n)
            
    def MySQL_New_Hit_Table(self):
        """Create a new hit table """
        
        if self.MySQL_Table_Exists(self._Hit_Table):   # Table already exists
            if self.debug:
                print "Hit table: "+self._Hit_Table+" already exists, no need to create."
            return(False)

        sql="""create table IF NOT EXISTS """+ self._Hit_Table +"""( \
                        name            VARCHAR(100),        \
                        description     VARCHAR(200),        \
                        identifiers     TEXT,                \
                        signalThreshold VARCHAR(30),         \
                        timeWindow      VARCHAR(30),         \
                        prodThreshold   VARCHAR(30),         \
                        maxStep         VARCHAR(30),         \
                        riseTime        VARCHAR(30),         \
                        fallTime        VARCHAR(30),         \
                        mvToMeV               FLOAT,         \
                        pedestal              FLOAT,         \
                        delay           VARCHAR(30),         \
                        time              TIMESTAMP,         \
                        variation       VARCHAR(200),        \
                        PRIMARY KEY (variation, name)        );"""
        if self.debug:
            print "Creating Hit table: "+self._Hit_Table+"."
        n=self.sql_execute(sql)
        return(n)

    def MySQL_New_Bank_Table(self):
        """Create a new bank table """

        if self.MySQL_Table_Exists(self._Banks_Table):   # Table already exist
            if self.debug:
                print "Bank table: "+self._Banks_Table+" already exists, no need to create."            
            return(False)
        
        sql = """create table IF NOT EXISTS """ + self._Banks_Table + """ ( \
                        bankname        VARCHAR(100),            \
                        name            VARCHAR(100),            \
                        description     VARCHAR(200),            \
                        num             int,                     \
                        type            VARCHAR(10),             \
                        time            TIMESTAMP,               \
                        variation       VARCHAR(200),            \
                        PRIMARY KEY (bankname, name, variation)  );"""
        if self.debug:
            print "Creating Bank table: "+self._Banks_Table+"."
        
        n=self.sql_execute(sql)        
        return(n)
        
    def MySQL_Write_Volume_RAW(self,name,mother,description,pos,rot,col,g4type,dimensions,material,magfield="no",ncopy=1,pmany=1,exist=1,visible=1,style=1,sensitivity="no",hittype="",identity="",rmin=1,rmax=10000):
        """ 
        You should not really need to use this call. Build geometries instead, then push them out to a DB or TXT.
        Write a line to the database table, for a volume described by args.
        Note that the database must have been initialized with MySQL_OpenDB and the table must exist.
        If the table does not exist or needs to be overwritten, call MySQL_New_Table first."""
#
# Note: Future update could check for the existence of table and the existence of "name" in the table.
#       If name already exists, print warning and update name instead of insert.
#
        sql="INSERT INTO "+self._Detector +" VALUES ('"
        sql+=name+"','"+mother+"','"+description+"','"
        sql+=pos+"','"+rot+"','"+col+"','"+g4type+"','"
        sql+=dimensions+"','"
        sql+=material+"','"
        sql+=magfield+"',"
        sql+=str(ncopy)+","
        sql+=str(pmany)+","
        sql+=str(exist)+","
        sql+=str(visible)+","
        sql+=str(style)+",'"
        sql+=sensitivity+"','"
        sql+=hittype+"','"
        sql+=identity+"',"
        sql+=str(rmin)+","
        sql+=str(rmax)+",now())"
        self._cursor.execute(sql)
    
    def sql_execute(self,sql):
        """Utility to wrap the SQL executing in a nice way. """
        n=0
#        n=self._cursor.execute(sql)
        
        if self.debug>3:
            print "SQL = " + sql
        
        try:
            n=self._cursor.execute(sql)
            if self.debug>3:
                print "n = " + str(n)
                print "#rows = "+str( self._DataBase.affected_rows() )
        except _mysql_exceptions.Warning as e:
            if self.debug:
                print "MySQL Warning: "+str(e)
                print "For SQL: "+sql
        except Exception as e:
            print e
            print "Unexpected error:", sys.exc_info()[0]
            print "For SQL: "+sql
            raise

        if self._always_commit:
            self._DataBase.commit()  # Make sure the transaction is completed.       
        return(n)

    def MySQL_Write(self):
        """ Write out all the tables for the detector to the database.
            Note that the database must be initialized first with MySQL_OpenDB """
    
        if not self._DataBase:
            print "ERROR -- Database was not initialized."
            return()
        
        self.MySQL_New_Tables()
        self.MySQL_Write_Geometry()
        self.MySQL_Write_Hit()
        self.MySQL_Write_Bank()

        
    def MySQL_Write_Geometry(self):
        """ Write the entire geometry to the MySQL table _Detector. """  
        
        if self.table_id <= 0:
            self.table_id = self.MySQL_Get_Latest_Id(self._Geometry_Table,self.table_variation) +1
        
        self.MySQL_Clean_Table(self._Geometry_Table, self.table_variation,self.table_id)
        
        if self.debug:
            print "Writing out the geometry MySQL table for "+self._Detector+" with variation="+self.table_variation+" and id="+str(self.table_id)
        
        for geo in self._Geometry:
            self.MySQL_Write_Volume(geo)

        
    def MySQL_Write_Volume(self,volume):
        """ Write the Geometry class object 'volume' to the MySQL table _Detector with 'variation' and 'iden' """

        if not isinstance(volume,Geometry):
            print "ERROR: Asked to write an object that is not a Geometry to the MySQL tables."
            return(1)

        if self.debug >3:
            print "Writing the geometry: "+volume.name
        sql = volume.MySQL_str(self._Geometry_Table,self.table_variation,self.table_id)
#        if self.debug > 30:
#            print "Insertion SQL: "+ sql
        n=self.sql_execute(sql)
        return(n)
        

    def MySQL_Write_Hit(self):
        """ Write the MySQL detector__hit table. """

        self.MySQL_Clean_Table(self._Hit_Table, self.table_variation,self.table_id)

        for sens in self._Sensitive_Detector:
            sql = sens.hit_MySQL_str(self._Hit_Table,self.table_variation,self.table_id)
            if self.debug>2:
                print "Writing the hit:"+sens.name
                print "SQL: "+sql
            self.sql_execute(sql)

    def MySQL_Write_Bank(self):
        """ Write the MySQL detector__bank table. """

        self.MySQL_Clean_Table(self._Banks_Table, self.table_variation,self.table_id)

        for sens in self._Sensitive_Detector:
            sql = sens.bank_MySQL_str(self._Banks_Table,self.table_variation,self.table_id)
            if self.debug>2:
                print "Writing the hit:"+sens.name
                print "SQL: "+sql
            self.sql_execute(sql)



    def MySQL_Read_Geometry(self,table,variation='original',idn=0):
        """Read the geometry from the MySQL table and store the result in this GeometryEngine.
           For GEMC 2 tables, specify which variation ('original' is default) and
           and which id (idn=0 is default) you want."""
#
# We first determine if this is a GEMC 1 or GEMC 2 table.
# If it has a column called "variation" then assume it is GEMC 2
# We find out by having MySQL describe the table.
        sql = "describe "+table
        err = self._cursor.execute(sql)
        if err <= 0:
            print "Error executing MySQL command: describe "+table
            return()
        
        ltable = self._cursor.fetchall()
        vari = [x for x in ltable if x[0] == "variation"]
        table_version = 2
        if len(vari) == 0:  # variation not found
            table_version = 1
            print "Note: GEMC version 1 table found. Variation and id ignored"
        
        sql = "select name,mother,description,pos,rot,col,type,dimensions,"
        sql+= "material,magfield,ncopy,pMany,exist,visible,style,sensitivity,hitType,identity,"
        sql+= "rmin,rmax,time from "+table
        if table_version == 2:
            sql+=" where variation='"+variation+"' and id="+idn
            
        self._cursor.execute(sql)
        result = self._cursor.fetchall() # Get the whole table in one call
        
        for x in result:
            self.add(Geometry(x))   # Store each line in a Geometry, place Geometry in GeometryEngine
        
        return

    def Python_Write(self,variation=0,idn=0,indent=0):
        """Write the Geometries out as a template Python method: calculate_<detector>_geometry
           into a file called Template_<detector>.py
           The code will be indented by 'indent' spaces.
            """
        fname = "Template_"+self._Detector+".py"
        ff= file(fname,"w")
        
        s = ' '*indent+"from GeometryEngine import Geometry\n\n"
        ff.write(s)
        s = ' '*indent+"def calculate_"+self._Detector+"_geometry(g_en):\n"
        ff.write(s)
        s = ' '*(indent+4)+'"""Auto generated method. """\n\n'
        ff.write(s)
        
        for geo in self._Geometry:
            s = geo.python_str(indent+4)
            ff.write(s+'\n')
            ff.write(' '*(indent+4)+"g_en.add(geo)\n\n")
        
        return
    
    def TXT_Read_Geometry(self,mfile=0):   
        """Read in a GEMC TXT file format geometry.
           If you specify 'file=' then exactly that file will be read.
           If you specify nothing, then the detectorname__geometry_original.txt will be read. """
        if not mfile:
            mfile= self._Detector+"__geometry_original.txt"
        
        fin = open(mfile,"r")
        
        for line in fin:
            obs = map(str.strip,line.split("|"))   # Split line on the |
            if len(obs) < 2:
                continue
            if self.debug > 1:
                print obs
            geo = Geometry()
            geo.debug = self.debug
            geo.__init__(obs)
            nerr = geo.validate()
            if nerr:
                print "Validation error number="+str(nerr)+" for line:"
                print line
            self.add(geo)         # Create a Geometry based on line and put in GeometryEngine 

        return
        
    def TXT_Write(self,variation=0):
        """ Write all the TXT files"""
        if variation == 0:
            variation=self.table_variation

        self.TXT_Write_Geometry(variation)
        self.TXT_Write_Banks(variation)
        self.TXT_Write_Hits(variation)
        self.TXT_Write_Materials(variation)
        
    def TXT_Write_Geometry(self,variation="original"):
        """ Write the entire geometry to a TXT file called detector__geometry_variation.txt """

        fname = self._Detector + "__geometry_" + variation + ".txt"
        ff = file(fname,"w")
        
        for geo in self._Geometry:
                ff.write(str(geo)+"\n")
        
        ff.close()

    def TXT_Write_Hits(self,variation="original"):
        """ Write the hit definitions to a TXT file called detector__hits_variation.txt """

        fname = self._Detector + "__hit_" + variation + ".txt"
        ff = file(fname,"w")
        
        if self._Sensitive_Detector == 0:
            print "ERROR:  No hits were defined!"
            return()
        
        for hit  in self._Sensitive_Detector:
                ff.write(hit.hit_str()+"\n")
        
        ff.close()

    def TXT_Write_Banks(self,variation="original"):
        """ Write the bank definitions to a TXT file called detector__banks.txt """

        fname = self._Detector + "__bank.txt"
        ff = file(fname,"w")
        
        if self._Sensitive_Detector == 0:
            print "ERROR:  No hits were defined!"
            return()
        
        for hit  in self._Sensitive_Detector:
                ff.write(hit.bank_str()+"\n")
        
        ff.close()
        
    def TXT_Write_Materials(self,variation="original"):
        """Write the materials to a TXT file called detector__materials_variation.txt """

        if self._Materials == 0:
            if self.debug >0:
                print "No materials defined. Not writing the materials txt file."
                
            return()

        fname = self._Detector + "__materials_"+variation+".txt"
        ff = file(fname,"w")
        
        for mat in self._Materials:
                ff.write(str(mat)+"\n")
        
        ff.close()

    def __str__(self):
        """ Return string with list of what the geometry currently contains. """
        s_out=""
        
        if self._DataBase and isinstance(self._DataBase,MySQLdb.connection):
            s_out = "Database: " + self._DataBase.get_host_info() + "\n"
        else:
            s_out = "Database:  NOT OPENED \n"
        s_out+= "Table   : " + self._Detector + "\n"
        s_out+= "Geometry: \n"
        for i in self._Geometry:
            s_out+= "     "+i.name+" in "+i.mother+ " ::"+i.description+"\n"

        return(s_out)
    
    def __getitem__(self,item):
        """ Return the Geometry object asked for in item. Allows for gen[0] or gen['paddle'] """
        
        if type(item) is str:
            return(self.find_volume(item))
        elif type(item) is int:
            if item < 0 or item > len(self._Geometry):
                return("Geometry Object out of bounds for index"+str(item))
            else:
                return(self._Geometry[item])

 
def testsuite():
    """Test the GeometryEngine class, currently does nothing, sorry"""
    print "I am not really implemented yet. Sorry"

if __name__ == "__main__":
    testsuite()
