"""
class GeometryEngine

@author: Maurik Holtrop (UNH) maurik@physics.unh.edu

This class represents the parameters for a GEMC material. 
"""
       
class Material():
    """A class to represent the material of a detector component.
    Each piece of the detector is made of some material. Many materials are pre-defined by GEANT4 and GEMC.
    For those that are not predefined, you can add them using this class. """    
    
    name=""
    description=""
    density=0
    components=[]  # List of the comonents in tuple format.
    _GEMC_VERSION=0
    
    def __init__(self,name,description,density,components,
                 photonEnergy='none',indexOfRefraction='none',absorptionLength='none',reflectivity='none',efficiency='none',
                 gemc_version=2.3):
        """Initialize the class. For components, you can either give a list of tuples: [('H',0.1),('C',0.4)]
        or a string 'H 0.1 C 0.4' """
        self.name= name
        self.description = description
        self.density = density

        if type(components) == str:
            comps = components.split()
            components=[(comps[2*i],comps[2*i+1]) for i in range(len(comps)/2) ]
        else:
            self.components = components         
            
        self.photonEnergy = photonEnergy
        self.indexOfRefraction = indexOfRefraction
        self.absorptionLength = absorptionLength
        self.reflectivity = reflectivity
        self.efficiency = efficiency

        self._GEMC_VERSION = gemc_version
        
        
    def __str__(self):
        """ Return a string with the material as a '|' delimited string, as Maurizio's perl scripts """
        outstr =self.name+' | '
        outstr+=self.description+' | '
        outstr+=str(self.density)+' |'
        outstr+=str(len(self.components)) + ' |'
        outstr+=" ".join([ x[0]+" "+str(x[1]) for x in self.components ]) + ' |'
        outstr+=self.photonEnergy + ' |'
        outstr+=self.indexOfRefraction + ' |'
        outstr+=self.absorptionLength + ' |'
        outstr+=self.reflectivity + ' |'
        outstr+=self.efficiency + ' |'
        if self._GEMC_VERSION > 2.2:
            outstr += 'none | none | none | none | none | none | none'
        return(outstr)
    
    def MySQL_str(self,Table,variation=0,idn=1):
        """ Return a MySQL statement to insert the geometry into a GEMC Table in a MySQL database"""

        sql="INSERT INTO "+Table +" VALUES ('"
        sql+=self.name+"','"+self.description+"','"
        sql+=str(self.density)+"','"
        sql+=str(len(self.components)+1)+"','"
        sql+=" ".join([ x[0]+" "+str(x[1]) for x in self.components ]) +"','"
        sql+="now()',"

        if variation != 0:       # This is for GEMC 2.0 style tables.
            sql+=",'"+str(variation)+"',"
            sql+= str(idn)
        sql+=");"
        return(sql)
   