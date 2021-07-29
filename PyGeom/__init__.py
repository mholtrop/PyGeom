#
# This is the PyGeom package, a set of Python classes that help in building Geant4
# geometry for GEMC.
#
#
__all__ = ["GeometryEngine","Geometry","GeometryROOT","SensitiveDetector","Material","Rotation","Vector"]

from .GeometryEngine import GeometryEngine
from .Geometry import Geometry
from .SensitiveDetector import SensitiveDetector
from .Material import Material
from .Vector import Vector
from .Rotation import Rotation

try:
    import ROOT
    from .GeometryROOT import GeometryROOT
except ImportError as e:
    print("Python was not able to import ROOT (i.e. PyROOT), so showing geometry with "
          "GeometryROOT will not be available.")
    print(e)

#from GeometryROOT import GeometryROOT
