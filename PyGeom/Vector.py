##############################################################################################################
#
#  Useful methods for working with vectors = column matrixes, or row matrizes.
#
##############################################################################################################
import numpy as np
import math

from . import Rotation

class Vector(np.matrix):
    """ A class to simplify the matrix objects that behave as 3 vectors, i.e. a 1-d column matrix. 
        This is a type of vector that you can multiply by a Rotation at Rotarion*Vector"""
    
    def __new__(self, data=None, dtype=None, copy=False):
        submatrix=1
        if data is not None:
            if isinstance(data,float) or isinstance(data,int):
                if data == 0:
                    submatrix = np.matrix((0,0,0)).T
                elif data == 1:
                    submatrix = np.matrix((1,0,0)).T
                elif data == 2:
                    submatrix = np.matrix((0,1,0)).T
                elif data == 3:
                    submatrix = np.matrix((0,0,1)).T
                else:
                    print("Not understanding initializiation parameter: ",data)
                    raise ValueError

            elif isinstance(data,Rotation.Rotation) or isinstance(data,Vector) or isinstance(data,np.matrix) or isinstance(data,np.ndarray) or isinstance(data,list) or isinstance(data,tuple):
                submatrix= np.matrix(data,dtype=dtype,copy=copy)
                if submatrix.shape == (1,3):
                    submatrix = submatrix.T
                elif submatrix.shape != (3,1):
                    print("A vector must be a (3,1) shape column matrix type. This is ",submatrix.shape)
                    raise ValueError
                else:
                    print("Unexpected type to a Vector")
                    raise TypeError
        else:
            submatrix = np.matrix((0,0,0))

        submatrix = submatrix.view(self)   # Transform matrix to Vector type.                              
        return submatrix

    def length(self):
        """Return the length of the vector """
        return math.sqrt(self.item(0)*self.item(0) + self.item(1)*self.item(1) + self.item(2)*self.item(2) )

    def rho(self):
        """Return the lenght of the vector in the x-y plane"""
        return math.sqrt(self.item(0)*self.item(0) + self.item(1)*self.item(1) )

    def theta(self):
        """Return the polar angle of the vector in radians """
        z = self.item(2)
        rho = self.rho()
        return math.atan2(rho,z)

    def phi(self):
        """Return the azimuthal angle of the vector, i.e. angle wrt to the x axis around the z axis"""
        return math.atan2( self.item(1),self.item(0))
    
    def x(self):
        """ Return the x component, or actually self.item(0) """
        return self.item(0)
    
    def y(self):
        """ Return the x component, or actually self.item(1) """
        return self.item(1)
    
    def z(self):
        """ Return the x component, or actually self.item(2) """
        return self.item(2)

    def list(self):
        """ Return the list [x,y,z] """
        l = [self.item(i) for i in range(3)]
        return l
    
    
    def __mul__(self,other):
        """Redefined multiply calls np.matrix.__mult__ and then casts to Vector """
        out = self.view(np.matrix)*other
        if isinstance(other,Rotation.Rotation) or isinstance(other,np.matrix):

            out = out.view(Vector)



        return out
