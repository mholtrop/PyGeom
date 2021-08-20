"""
class GeometryROOT

@author: Maurik Holtrop (UNH) maurik@physics.unh.edu

This class allows for conversion of the GEANT4 based GEMC geometries to TGeo based ROOT geometries. Because ROOT geometries are a bit different
from GEANT4 geometries, this class is a bit involved, translating each object to the correct form. As such, it is possible that a particular
object shape is not implemented. If that is the case, and you need it, please email me.
Similarly, it tries to handle the materials. Materials are  only critical if you try to use the ROOT geometry to trace particles. Since mostly
this class will be  used for rendering pretty pictures, the code automatically substitutes "Aluminum" for each unknown material.

Note that this class requires the ROOT (i.e. PyROOT) package to be installed correctly on your system.
It has been tested with ROOT 5.34 and with ROOT 6.
"""
#
import re
import sys
import atexit
import code
import readline
import rlcompleter
import numpy

try:
    import ROOT
    #
    # The following lines are possible work-arounds if ROOT gives trouble opening the OpenGL display.
    # This seems no longer needed as of ROOT 6.25
    #
    # ROOT.PyConfig.StartGuiThread = 'inputhook'  # Allow the OpenGL display to work without a crash.
    # ROOT.TGeoMaterial.__init__._creates = False   # This is supposed to prevent python from crashing on exit,
    # ROOT.TGeoMedium.__init__._creates = False     # but it doesn't.

except ImportError as err:
    print(err)
    print("It seems you did not enable ROOT properly on your system. Please source 'thisroot.sh' or 'thisroot.csh' "
          "from the ROOT distribution.")
    sys.exit()

from .GeometryEngine import GeometryEngine
from .Geometry import Geometry
from .Rotation import Rotation
from .Vector import Vector


class GeometryROOT:
    """A class for construction a PyROOT geometry tree from the geometry data in a GeometryEngine class.
    """
    _geom = 0
    _geo_engine = 0
    _geo_engine_current = 0
    _materials = 0  # Dictionary of available materials
    _mats_table = 0
    _mediums = 0  # Dictionary of available mediums.
    _shapes = 0  # The shapes used to create the volumes. In priciple, these could be recycled.
    _volumes = 0  # Dictionary of volumes.
    _translations = 0  # Dictionary of the translation with which volumes are placed in mother. (not needed, but handy)
    _top = "root"  # The volume considered to be the top, usually "root"
    debug = 0
    _conv_dict = 0
    _trans_dict = 0

    def __init__(self, geo=None, name="GEMC", description="Python ROOT Geometry Engine for GEMC"):
        """ Initialize the GeometryEngine class, starting up the ROOT.TGeoManager and define materials."""

        self._geo_engine = []  # Make sure this is a clean list, not a global list.
        self._materials = {}
        self._mediums = {}
        self._shapes = {}
        self._volumes = {}
        self._translations = {}
        self._color_idx = None

        # Get a unit conversion table from the Geometry class. Yes, it needs a minimal init.
        if geo is None or len(geo) == 0:
            self._conv_dict, self._trans_dict = Geometry(name="convert", g4type="").unit_convert_dict("cm deg")
            self._geom = ROOT.TGeoManager(name, description)
            self._mats_table = self._geom.GetElementTable()
            self._geom.SetVisOption(0)

        else:
            self._conv_dict, self._trans_dict = geo[0].unit_convert_dict("cm deg")
            self._geom = ROOT.TGeoManager(geo.get_name(), geo.get_description())
            self._mats_table = self._geom.GetElementTable()
            self._geom.SetVisOption(0)

            if geo.find_volume('root') is None:
                if self.debug > 0:
                   print("No root volume found, creating one.")
                self.create_root_volume()
            self.build_volumes(geo)
        #
        # Setup the materials to be used.
        #
        # self.Create_Mats()

    # The following code was an attempt for us to clean up after ROOT. As of ROOT 6.25 this seems
    # to be detrimental rather than helpful.
    # We do still see a "already deleted" error, which seems relatively harmless.
    #
    #     atexit.register(self.__atexit__)

    # def __atexit__(self):
    #     """ Try to clean up after ourselves. """
    #     print("Calling cleanup crew.")
    #     del self._geom  # -- This doesn't work. ROOT has already badly cleaned this with the hook.

    def close_geometry(self):
        """Close the ROOT GeometryManager:
        Closing geometry implies checking the geometry validity, fixing shapes
        with negative parameters (run-time shapes)building the cache manager,
        voxelizing all volumes, counting the total number of physical nodes and
        registering the manager class to the browser. """
        self._geom.CloseGeometry()

    def find_element(self, elem):
        """Wrapper to ROOT.TGeoManager.GetElementTable().FindElement() to avoid crashes when element not found. """
        try:
            stuff = self._mats_table.FindElement(elem)
        except Exception as e:
            print(e)
            print("Error finding the element: " + str(elem) + " please check your code.")
            return None

        if stuff is None:
            print("Could not find the element: " + str(elem) + ", check the periodic table.")
            return None

        return stuff

    def add_element(self, matname, elem, fract):
        """ Wrapper to ROOT.TGeoMixture().AddElement() to avoid crashes and simplify usage. """

        if type(elem) is str:
            elem = self.find_element(elem)  # Overwrite the elem with the ROOT TElement object, not the name.
        elif not isinstance(elem, ROOT.TGeoElement):  # type(elem) is not type(ROOT.TGeoElement()):
            print("There is something wrong with the 2nd argument to add_element: " + str(elem))
            return None

        if type(matname) is str:
            if matname in self._materials:
                self._materials[matname].AddElement(elem, fract)
                return self._materials[matname]
        elif isinstance(matname, ROOT.TGeoMixture):
            matname.AddElement(elem, fract)
            return matname
        else:
            print("There is something wrong with the 1st argument to add_element: " + str(matname))
            return None

    def find_material(self, material, trans=0):
        """ Find the material (actually medium in ROOT speak) for a volume.
            Because transparency is linked with the material in ROOT, a new
            material needs to be made for each transparency level (0-9).
        """
        g = 1.
        cm3 = 1.
        med_index = len(self._mediums)

        if material == "Component":
            return 0

        if trans:
            matname = material + "_" + str(trans / 10)
        else:
            matname = material

        if matname in self._mediums:
            return self._mediums[matname]

        #
        # We didn't find it, so let's build it.
        #
        if self.debug > 1:
             print("Creating material: " + matname)

        for geo in self._geo_engine:
            for mmat in geo._Materials:
                if self.debug > 2:
                     print("mmat" + str(mmat))
                if mmat.name == material or mmat.name == matname:
                    self._materials[matname] = ROOT.TGeoMixture(matname, len(mmat.components), mmat.density * g / cm3)
                    for cc in mmat.components:
                        if cc[0].startswith("G4_"):
                            name = cc[0][3:]
                        else:
                            name = cc[0]
                        rotation_mat = self._mats_table.FindElement(name)
                        if not rotation_mat:
                            print("Cannot find element ", name, " in the _mats_table!!!!")
                        else:
                            self._materials[matname].AddElement(rotation_mat, cc[1])

                    self._mediums[matname] = ROOT.TGeoMedium(matname, med_index, self._materials[matname])
                    self._materials[matname].SetTransparency(trans)
                    return self._mediums[matname]

        if self.debug > 2:
            print("Not found yet, see how to make one of those.")

        if material == "Vacuum":

            self._materials[matname] = ROOT.TGeoMaterial(matname, 0, 0, 0)
            if trans == 0:
                trans = 80

        elif material == "Air":

            self._materials[matname] = ROOT.TGeoMixture(matname, 2, 1.29 * g / cm3)
            self._materials[matname].AddElement(self._mats_table.FindElement("N"), 0.7)
            self._materials[matname].AddElement(self._mats_table.FindElement("O"), 0.3)

        elif material == "Fe" or material == "Iron" or material == "G4_Fe":

            self._materials[matname] = ROOT.TGeoMaterial("Fe", 55.845, 26, 7.87)

        elif material == "Cu" or material == "Copper" or material == "G4_Cu":

            self._materials[matname] = ROOT.TGeoMaterial("Cu", 63.546, 29, 8.96)

        elif material == "Quartz" or material == "Silicon" or material == "G4_Si" or material == "Si":

            self._materials[matname] = ROOT.TGeoMaterial("Si", 63.546, 29, 8.96)

        elif material == "StainlessSteel":

            self._materials[matname] = ROOT.TGeoMixture(matname, 5, 8.02 * g / cm3)
            self._materials[matname].AddElement(self._mats_table.FindElement("Mn"), 0.02)
            self._materials[matname].AddElement(self._mats_table.FindElement("Si"), 0.01)
            self._materials[matname].AddElement(self._mats_table.FindElement("Cr"), 0.19)
            self._materials[matname].AddElement(self._mats_table.FindElement("Ni"), 0.10)
            self._materials[matname].AddElement(self._mats_table.FindElement("Fe"), 0.68)

        elif material == "G4_Concrete":

            #components = [("G4_H", 0.01), ("G4_C", 0.001), ("G4_O", 0.529107), ("G4_Na", 0.016), ("G4_Mg", 0.002),
            #              ("G4_Al", 0.033872), ("G4_Si", 0.337021), ("G4_K", 0.013),
            #              ("G4_Ca", 0.044), ("G4_Fe", 0.014)]

            self._materials[matname] = ROOT.TGeoMixture(matname, 10, 2.4 * g / cm3)
            self._materials[matname].AddElement(self._mats_table.FindElement("H"), 0.01)
            self._materials[matname].AddElement(self._mats_table.FindElement("C"), 0.001)
            self._materials[matname].AddElement(self._mats_table.FindElement("O"), 0.529107)
            self._materials[matname].AddElement(self._mats_table.FindElement("Na"), 0.016)
            self._materials[matname].AddElement(self._mats_table.FindElement("Mg"), 0.002)
            self._materials[matname].AddElement(self._mats_table.FindElement("Al"), 0.033872)
            self._materials[matname].AddElement(self._mats_table.FindElement("Si"), 0.337021)
            self._materials[matname].AddElement(self._mats_table.FindElement("K"), 0.013)
            self._materials[matname].AddElement(self._mats_table.FindElement("Ca"), 0.044)
            self._materials[matname].AddElement(self._mats_table.FindElement("Fe"), 0.014)

        elif material == "G4_W" or material == "Tungsten":

            self._materials[matname] = ROOT.TGeoMaterial("W", 183.84, 74, 19.25 * g / cm3)

        elif material == "LeadTungsten":

            self._materials[matname] = ROOT.TGeoMixture(matname, 3, 8.28 * g / cm3)
            self._materials[matname].AddElement(self._mats_table.FindElement("Pb"), 1)
            self._materials[matname].AddElement(self._mats_table.FindElement("W"), 1)
            self._materials[matname].AddElement(self._mats_table.FindElement("O"), 4)

        elif material == "Scintillator" or material == "ScintillatorB" or material == "scintillator":

            #             self._materials[matname]= ROOT.TGeoMixture(matname, 2, 1.032*g/cm3)
            #             self._materials[matname].AddElement(self._mats_table.FindElement("C"),9);
            #             self._materials[matname].AddElement(self._mats_table.FindElement("H"), 10);

            self._materials[matname] = ROOT.TGeoMixture(matname, 2, 1.032 * g / cm3)
            self.add_element(self._materials[matname], "C", 9)
            self.add_element(matname, "H", 10)

        elif material == "Aluminum":

            self._materials[matname] = ROOT.TGeoMaterial(matname, 26.98, 13, 2.7);  # A,Z,rho

        else:
            if self.debug:
                print("OOPS, the material: " + material + " has not yet been defined in Python world. ", )
                print("I'll pretend it is Aluminum...")
            return self.find_material("Aluminum", trans)

        self._mediums[matname] = ROOT.TGeoMedium(matname, med_index, self._materials[matname])
        self._materials[matname].SetTransparency(trans)
        return self._mediums[matname]

    def create_root_volume(self, rmaterial="Vacuum", size=[1000, 1000, 1000], visible=0):
        """Setup the mother of all volumes, the hall or 'root' volume everything else goes into. """
        vacmat = self.find_material("Vacuum")
        self._volumes["root"] = self._geom.MakeBox("root", vacmat, size[0], size[1], size[2])
        self._volumes["root"].SetLineColor(18)  # ROOT light gray color.
        self._geom.SetTopVolume(self._volumes["root"])
        self._geom.SetTopVisible(visible)

    def create_color_for_root(self, color):
        """Root has a 'color index', the rest of the world has RGB values. Create a new color with
        the specified RGBa value string. """

        # The following regex captures the 3 color groups + the optional alpha channel.
        m = re.match("#?([A-F0-9][A-F0-9])([A-F0-9][A-F0-9])([A-F0-9][A-F0-9])([0-9]?)", color, re.I)
        if not m:
            print("ERROR, I could not conver the color: '" + color + "' to an RGBa group")
            return 21

        red = int(m.group(1), 16)
        green = int(m.group(2), 16)
        blue = int(m.group(3), 16)
        alpha = int(m.group(4))

        newcol = ROOT.TColor(self._color_idx, red / 255., green / 255., blue / 255.)
        newcol.SetAlpha(alpha)

        return self._color_idx

    def find_root_color(self, color):
        """Return the ROOT color, or create it if not found. color is an #rgb string. """

        if not color[0] == "#":
            color = "#" + color

        col_found = ROOT.TColor.GetColor(color)
        return col_found

    def get_color_alpha(self, color):
        """ Extract the color and the alpha (0-9) for the color. Returns ROOT color and Alpha"""
        # The following regex captures the 3 color groups + the optional alpha channel.
        m = re.match("#?([A-F0-9][A-F0-9][A-F0-9][A-F0-9][A-F0-9][A-F0-9])([0-9]?)", color, re.I)
        if not m:
            print("ERROR, I could not convert the color: '" + color + "' to an RGBa group")
            return 21, 0
        color = self.find_root_color(m.group(1))
        if m.group(2):
            alpha = int(m.group(2))
        else:
            alpha = 0

        return color, alpha

    def convert(self, value, unit, new_unit):
        """Conversion of a value with unit to new_unit """
        if new_unit == "cm" or new_unit == "deg":  # What we expect
            new_value = value * self._conv_dict[unit.strip()]
            return new_value
        else:
            conv_dict, _ = Geometry(name="convert", g4type="", dimensions="").unit_convert_dict(new_unit)
            new_value = value * conv_dict[unit]
            return new_value

    def build_volumes(self, geo, mother="root"):
        """Take the GeometryEngine geo argument and build a tree of ROOT volumes from it.
           The tree starts at the geo volume mother and then recureses down for each daughter.
           Note that this means that an orphan (volume with mother that is not part of this tree)
           will NOT be placed!
           Multiple geometry trees can be build by subsequent calls to build_volumes."""

        if not isinstance(geo, GeometryEngine):
            print("The argument to Build_root_volumes MUST be a GeometryEngine object")
            return

        self._geo_engine.append(geo)  # Store the GeometryEngine in case needed later.
        self._geo_engine_current = geo

        #
        # Check to see if the "mother" exists.
        # If not found,
        #   If "mother"="root", then
        #       create a root volume.
        #   else:
        #       look for mother in file and create it as master.
        if mother not in self._volumes:
            if mother == "root":  # Place the root
                self.create_root_volume()
            else:
                root_vol = geo.find_volume(mother)
                if root_vol is None:
                    print("Cannot place root volume: " + mother + " because I cannot find it.")
                    raise NameError("Volume not found.")
                else:
                    if "root" not in self._volumes:
                        self.create_root_volume()

                    self.place_volume(root_vol, "root")

        # We need to go through the geometry and first place all the geometries that are
        # in the mother of geo in our mother.
        # By GEMC definition the geo mother = "root"
        #

        objl = geo.find_children(mother)  # Return list of Geometry object with mother as mother.

        if objl is None or type(objl) is int:
            if self.debug > 4:
                print("I could not find volumes with '" + mother + "' for mother volume. ")
            return

        if self.debug > 1:
            sys.stdout.write("build_volumes: placing in '" + mother + "' volumes: ['")
            for x in objl:
                sys.stdout.write(x.name + "','")
            print("']")

        for vol in objl:
            self.place_volume(vol, mother)
            self.build_volumes(geo, vol.name)  # Recurse to find the children of this volume and build them.

    def compute_combi_trans(self, name, vector, rotation):
        """Compute the TGeoCombiTrans for the geometry in geo_vol
           A TGeoCombiTrans is considered to be a rotation of the object, followed by a translation.
           The actual rotation we store is an inverse rotation....
           The arguments here are a Vector (expected in 'cm') and a Rotation (in 'radians') """

        if not type(vector) is Vector:
            print("compute_combi_trans expected a Vector. Other types not yet implemented")
            return
        if not type(rotation) is Rotation:
            print("compute_combi_trans expected a Rotation. Other types not yet implemented")
            return

        rotate = ROOT.TGeoRotation(name + "_rot")

        (theta, phi, psi) = rotation.GetXYZ()

        rotate.RotateZ(-self.convert(psi, "rad", "deg"))
        rotate.RotateY(-self.convert(phi, "rad", "deg"))
        rotate.RotateX(-self.convert(theta, "rad", "deg"))

        transrot = ROOT.TGeoCombiTrans(vector.x(),
                                       vector.y(),
                                       vector.z(),
                                       rotate)
        return transrot

    def compute_trans_vector(self, geo_vol):
        """ Return a Rotation.Vector object from the position """

        if type(geo_vol.pos_units) is str:
            unit = geo_vol.pos_units
            geo_vol.pos_units = [unit, unit, unit]

        vec = Vector([self.convert(geo_vol.pos[0], geo_vol.pos_units[0], "cm"),
                      self.convert(geo_vol.pos[1], geo_vol.pos_units[1], "cm"),
                      self.convert(geo_vol.pos[2], geo_vol.pos_units[2], "cm")])
        return vec

    def compute_trans_rotation(self, geo_vol):
        """ Compute the Rotation from the geo_vol rot """

        if type(geo_vol.rot_units) is str:
            unit = geo_vol.rot_units
            geo_vol.rot_units = [unit, unit, unit]

        if len(geo_vol.rot) < 3:
            print("Incomplete rotation for ", str(geo_vol))

        if len(geo_vol.rot_units) < 3:
            print("Incomplete rotation units for ", str(geo_vol))

        if geo_vol.rot_order == "" or geo_vol.rot_order == "xyz":

            rot = Rotation()
            rot = rot.rotateX(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateY(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateZ(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        #
        # NOTE: This should be rewritten to parsse the xyz string, and then call the appropriate rotations
        #

        elif geo_vol.rot_order == "zxy":

            rot = Rotation()
            rot = rot.rotateZ(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateX(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateY(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        elif geo_vol.rot_order == "yxz":

            rot = Rotation()
            rot = rot.rotateY(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateX(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateZ(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        elif geo_vol.rot_order == "zyx":

            rot = Rotation()
            rot = rot.rotateZ(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateY(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateX(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        elif geo_vol.rot_order == "yzx":

            rot = Rotation()
            rot = rot.rotateY(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateZ(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateX(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        elif geo_vol.rot_order == "yxz":

            rot = Rotation()
            rot = rot.rotateY(self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "rad"))
            rot = rot.rotateX(self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "rad"))
            rot = rot.rotateZ(self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "rad"))

        else:
            raise NameError('===== OOPS ==== I do not know about a ', geo_vol.rot_order, ' rotation. Sorry. ')

        return rot

    def compute_combi_trans_2(self, geo_vol):
        """Compute the TGeoCombiTrans for the geometry in geo_vol
           A TGeoCombiTrans is considered to be a rotation +  translation."""
        rotate = ROOT.TGeoRotation(geo_vol.name + "_rot")
        if type(geo_vol.rot_units) is str:
            unit = geo_vol.rot_units
            geo_vol.rot_units = [unit, unit, unit]

        rotate.RotateX(-self.convert(geo_vol.rot[0], geo_vol.rot_units[0], "deg"))
        rotate.RotateY(-self.convert(geo_vol.rot[1], geo_vol.rot_units[1], "deg"))
        rotate.RotateZ(-self.convert(geo_vol.rot[2], geo_vol.rot_units[2], "deg"))

        if type(geo_vol.pos_units) is str:
            unit = geo_vol.pos_units
            geo_vol.pos_units = [unit, unit, unit]

        transrot = ROOT.TGeoCombiTrans(self.convert(geo_vol.pos[0], geo_vol.pos_units[0], "cm"),
                                       self.convert(geo_vol.pos[1], geo_vol.pos_units[1], "cm"),
                                       self.convert(geo_vol.pos[2], geo_vol.pos_units[2], "cm"),
                                       rotate)
        return transrot

    def get_volume_shape(self, geo_vol):
        """From the geo_vol description strings, return a new TGeoVolume shape.
           For Operations, the shape is computed from previously stored shapes and translation."""

        if geo_vol.g4type == "Box":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit, unit, unit]

            newgeo_shape = ROOT.TGeoBBox(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                         self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                         self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"))
        elif geo_vol.g4type == "Tube":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit, unit, unit]

            if len(geo_vol.dimensions) == 3 or geo_vol.dimensions[3] <= 0. and self.convert(geo_vol.dimensions[4],
                                                                                            geo_vol.dims_units[4],
                                                                                            "deg") >= 360.:
                newgeo_shape = ROOT.TGeoTube(geo_vol.name + "_shape",
                                             self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                             self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                             self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"))

            else:

                phi_start = self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "deg")
                phi_end = phi_start + self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "deg")

                # print("Tube: Phi_start = "+str(phi_start)+"  Phi_end = "+str(phi_end))

                newgeo_shape = ROOT.TGeoTubeSeg(geo_vol.name + "_shape",
                                                self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                                self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                                self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"),
                                                phi_start,
                                                phi_end)

        elif geo_vol.g4type == "Sphere":
            if type(geo_vol.dims_units) is str:
                print("We have a problem. Parallelepiped " + geo_vol.name + " has bad units = string.")

            start_phi = self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "deg")
            delta_phi = self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "deg")
            end_phi = start_phi + delta_phi
            start_tht = self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "deg")
            delta_tht = self.convert(geo_vol.dimensions[5], geo_vol.dims_units[5], "deg")
            end_tht = start_tht + delta_tht

            newgeo_shape = ROOT.TGeoSphere(geo_vol.name + "_shape",
                                           self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                           self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                           start_phi, end_phi,
                                           start_tht, end_tht)

        elif geo_vol.g4type == "Parallelepiped":
            if type(geo_vol.dims_units) is str:
                print("We have a problem. Parallelepiped " + geo_vol.name + " has bad units = string.")

            newgeo_shape = ROOT.TGeoPara(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                         self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                         self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"),
                                         self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "deg"),
                                         self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "deg"),
                                         self.convert(geo_vol.dimensions[5], geo_vol.dims_units[5], "deg"))

        elif geo_vol.g4type == "Trd":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit, unit, unit, unit, unit]

            newgeo_shape = ROOT.TGeoTrd2(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                         self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                         self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"),
                                         self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "cm"),
                                         self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "cm"))
        elif geo_vol.g4type == "G4Trap":
            if type(geo_vol.dims_units) is str:
                print("We have a problem. G4Trap " + geo_vol.name + " has bad units = string.")

            newgeo_shape = ROOT.TGeoTrap(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                         self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "deg"),
                                         self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "deg"),
                                         self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "cm"),
                                         self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "cm"),
                                         self.convert(geo_vol.dimensions[5], geo_vol.dims_units[5], "cm"),
                                         self.convert(geo_vol.dimensions[6], geo_vol.dims_units[6], "deg"),
                                         self.convert(geo_vol.dimensions[7], geo_vol.dims_units[7], "cm"),
                                         self.convert(geo_vol.dimensions[8], geo_vol.dims_units[8], "cm"),
                                         self.convert(geo_vol.dimensions[9], geo_vol.dims_units[9], "cm"),
                                         self.convert(geo_vol.dimensions[10], geo_vol.dims_units[10], "deg"))
        # Double_t dz, Double_t theta, Double_t phi, Double_t h1, Double_t bl1, Double_t tl1,
        # Double_t alpha1, Double_t h2, Double_t bl2, Double_t tl2, Double_t alpha2)
        elif geo_vol.g4type == "G4GenericTrap":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit] * len(geo_vol.dims)

            newgeo_shape = ROOT.TGeoArb8(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"))

            if self.debug > 1:
                print("Creating TGeoArb8: ", )

            for i in range(8):
                if self.debug > 1:
                    print("[", i, ",", self.convert(geo_vol.dimensions[i * 2 + 1], geo_vol.dims_units[i * 2 + 1], "cm"),
                          ",",
                          self.convert(geo_vol.dimensions[i * 2 + 2], geo_vol.dims_units[i * 2 + 2], "cm"), "]", )

                newgeo_shape.SetVertex(i,
                                       self.convert(geo_vol.dimensions[i * 2 + 1], geo_vol.dims_units[i * 2 + 1], "cm"),
                                       self.convert(geo_vol.dimensions[i * 2 + 2], geo_vol.dims_units[i * 2 + 2], "cm"))

            if self.debug > 1:
                print()

        elif geo_vol.g4type == "EllipticalTube" or geo_vol.g4type == "Eltu":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit, unit, unit]

            newgeo_shape = ROOT.TGeoEltu(geo_vol.name + "_shape",
                                         self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                         self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                         self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"))

        elif geo_vol.g4type == "Paraboloid":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit] * 3

            newgeo_shape = ROOT.TGeoParaboloid(geo_vol.name + "+shape",
                                               self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),  # Rlo
                                               self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"),  # Rhi
                                               self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"))  # Dz

        elif geo_vol.g4type == "Ellipsoid":
            if type(geo_vol.dims_units) is str:
                unit = geo_vol.dims_units
                geo_vol.dims_units = [unit] * 5
            #
            # This one is a bit tricky. There is no Ellipsoid in ROOT world, so we will need to approximate
            # it by creating a sphere, which is then stretched in x,y to right shape, and clipped at the
            # ends by a box. This should have been WAY easier....
            #
            dx = self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm")
            dy = self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm")
            radius = self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm")
            z1 = self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "cm")
            z2 = self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "cm")

            sx = dx / radius
            sy = dy / radius
            sz = 1

            if (z1 == 0 and z2 == 0) or z1 >= z2:
                z1 = -radius
                z2 = +radius

            tmp_sph = ROOT.TGeoSphere(0, radius)
            tmp_scale = ROOT.TGeoScale("", sx, sy, sz)
            tmp_shape = ROOT.TGeoScaledShape(geo_vol.name + "_ellip", tmp_sph, tmp_scale)
            #
            # This gives a stretched sphere = ellipsoid.
            # Now cut the top and bottom....
            #
            z = 0.5 * (z1 + z2)
            dz = 0.5 * (z2 - z1)
            tmp_cut_box = ROOT.TGeoBBox(geo_vol.name + "_cutbox", dx, dy, dz, numpy.array([0., 0., z]))
            tmp_bool_node = ROOT.TGeoIntersection(tmp_shape, tmp_cut_box, 0, 0)
            newgeo_shape = ROOT.TGeoCompositeShape(geo_vol.name + "_shape", tmp_bool_node)

        elif geo_vol.g4type == "Cons":
            if type(geo_vol.dims_units) is str:
                print("We have a problem. Cons " + geo_vol.name + " has bad units = string.")
            #
            # Note the arguments have different order from GEANT4.
            #
            start_phi = self.convert(geo_vol.dimensions[5], geo_vol.dims_units[5], "deg")
            delta_phi = self.convert(geo_vol.dimensions[6], geo_vol.dims_units[6], "deg")
            end_phi = start_phi + delta_phi

            newgeo_shape = ROOT.TGeoConeSeg(geo_vol.name + "_shape",
                                            self.convert(geo_vol.dimensions[4], geo_vol.dims_units[4], "cm"),
                                            self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "cm"),
                                            self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "cm"),
                                            self.convert(geo_vol.dimensions[2], geo_vol.dims_units[2], "cm"),
                                            self.convert(geo_vol.dimensions[3], geo_vol.dims_units[3], "cm"),
                                            start_phi, end_phi)

        elif geo_vol.g4type == "Polycone":
            # A Polycone maps to a G4Polycone
            #   http://geant4.web.cern.ch/geant4/UserDocumentation/UsersGuides/ForApplicationDeveloper/html/ch04.html
            # In ROOT: TGeoPcon
            # https://root.cern.ch/root/html534/guides/users-guide/Geometry.html#polycone-tgeopcon-class
            if type(geo_vol.dims_units) is str:
                raise NameError("We have a problem. Polycone " + geo_vol.name + " has bad units = string. ")

            # Note: Mauri's definition is: Initial phi, total phi, #planes, rInner[i], rOuter[i], z[i]

            start_phi = self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "deg")
            delta_phi = self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "deg")
            nplanes = int(geo_vol.dimensions[2])

            if self.debug > 2:
                print("Polycone: s_phi=" + str(start_phi) + " delta_phi=" + str(delta_phi) + " nplanes=" + str(
                    nplanes) + " name="
                      + geo_vol.name)

            newgeo_shape = ROOT.TGeoPcon(geo_vol.name + "_shape", start_phi, delta_phi, nplanes)

            for np in range(nplanes):
                rmin = self.convert(geo_vol.dimensions[3 + 0 * nplanes + np], geo_vol.dims_units[3 + 0 * nplanes + np],
                                    "cm")
                rmax = self.convert(geo_vol.dimensions[3 + 1 * nplanes + np], geo_vol.dims_units[3 + 1 * nplanes + np],
                                    "cm")
                z = self.convert(geo_vol.dimensions[3 + 2 * nplanes + np], geo_vol.dims_units[3 + 2 * nplanes + np],
                                 "cm")
                newgeo_shape.DefineSection(np, z, rmin, rmax)
                if self.debug > 2:
                    print("rmax = " + str(rmax) + " rmin= " + str(rmin) + "  z= " + str(z))

        elif geo_vol.g4type == "Pgon" or geo_vol.g4type == "Polyhedra":
            if type(geo_vol.dims_units) is str:
                raise NameError("We have a problem. Polycone " + geo_vol.name + " has bad units = string. ")

            start_phi = self.convert(geo_vol.dimensions[0], geo_vol.dims_units[0], "deg")
            delta_phi = self.convert(geo_vol.dimensions[1], geo_vol.dims_units[1], "deg")
            nsides = int(geo_vol.dimensions[2])
            nplanes = int(geo_vol.dimensions[3])

            newgeo_shape = ROOT.TGeoPgon(geo_vol.name + "_shape", start_phi, delta_phi, nsides, nplanes)

            for np in range(nplanes):
                rmin = self.convert(geo_vol.dimensions[4 + 0 * nplanes + np], geo_vol.dims_units[3 + 0 * nplanes + np],
                                    "cm")
                rmax = self.convert(geo_vol.dimensions[4 + 1 * nplanes + np], geo_vol.dims_units[3 + 1 * nplanes + np],
                                    "cm")
                z = self.convert(geo_vol.dimensions[4 + 2 * nplanes + np], geo_vol.dims_units[3 + 2 * nplanes + np],
                                 "cm")
                newgeo_shape.DefineSection(np, z, rmin, rmax)

        elif re.match("Operation:.*", geo_vol.g4type):
            #
            # Operations combine two shapes with either +, - or *
            # Important Note:
            # ROOT and GEANT4 behave slightly different when it comes to combining volumes.
            # For the ROOT Geo system, object1 and object2 are first located relative to the mother volume,
            # then they are added or subtracted, and then the result is translated to the final location with
            # the translation parameters of the final volume.
            # For GEANT4, object1, is in it's own coordinate system at the origin. Object2 is then moved and/or
            # rotated relative to this origin, and then the addition or subtraction takes place. Then the
            # final result is translated to the final location + rotation.
            # The upshot is that the positioning of the FIRST object must be ignored, if we follow the
            # GEANT4 rules, which we are bound to here.
            # GEMC has the added feature that you can have BOTH volumes specified relative to the coordinates
            # of the mother volume. It achieves this with a calculation. You can tell GEMC to do this with
            # an @ right after the "Operation:" statement (i.e. "Operation:@")
            # This is almost what ROOT does. The difference, is that for ROOT the final positioning is
            # then relative to the origin of the MOTHER volume, i.e. the original center. For GEMC the
            # final positioning is relative to the center of the FIRST object.
            # Because the combo object can be put into another combo, we cannot get the same behavior
            # by simply placing the new shape at trans = -trans_1 + trans_final
            # We need to follow the GEMC calculation.

            match = re.match(r"Operation:([~@])?\W*(\w*)\W*([*+-])\W*(\w*)\W*",
                             geo_vol.g4type)  # * must be first in char list: [*+-]
            special = match.group(1)
            shape1_name = match.group(2)
            oper = match.group(3)
            shape2_name = match.group(4)
            if self.debug > 4:
                print(
                    "Operation found: " + geo_vol.g4type + " = '" + shape1_name + "' " +
                    oper + " '" + shape2_name + "'")

            #
            # The following is effectively a recursive call. If the lines for placing the required shapes had not
            # been processed yet, then process them now.
            # Find the volume description line from the GeometryEngine, and place the volume.
            # Since these are most likely "Component" volumes, they will not actually be placed, but the
            # shape and translation will be created in "Place_Volume()
            #
            if shape1_name not in self._shapes.keys():
                f_geo = self._geo_engine_current.find_volume(
                    shape1_name)  # The volume isn't there yet. Find it and place it.
                self.place_volume(f_geo)  # place in same mother.

            if shape2_name not in self._shapes.keys():
                f_geo = self._geo_engine_current.find_volume(
                    shape2_name)  # The volume isn't there yet. Find it and place it.
                self.place_volume(f_geo)  # place in same mother.

            shape1 = self._shapes[shape1_name]
            shape2 = self._shapes[shape2_name]
            #  transrot2 = self.compute_combi_trans(self._geo_engine_current.find_volume(shape2_name))

            trans1, rot1 = self._translations[shape1_name]
            trans2, rot2 = self._translations[shape2_name]
            transrot1 = 0

            if special == "@":
                if self.debug > 4:
                    print("Special operation: " + str(special))

                net_trans = trans2 - trans1
                net_trans_rot = rot1 * net_trans
                #
                net_rot = (rot2 * rot1.I)
                #                net_rot = (rot1*rot2.I).I
                transrot2 = self.compute_combi_trans(geo_vol.name, net_trans_rot, net_rot)

            else:
                transrot2 = self.compute_combi_trans(shape2_name, trans2, rot2)

            if oper == "-":
                opshape = ROOT.TGeoSubtraction(shape1, shape2, transrot1, transrot2)
            elif oper == "+":
                opshape = ROOT.TGeoUnion(shape1, shape2, transrot1, transrot2)
            elif oper == "*":
                opshape = ROOT.TGeoIntersection(shape1, shape2, transrot1, transrot2)
            else:
                print("WARNING: Operation " + oper + " is not implemented.")

            newgeo_shape = ROOT.TGeoCompositeShape(geo_vol.name + "_shape", opshape)

        elif re.match("CopyOf .*", geo_vol.g4type):
            match = re.match("CopyOf (.*)", geo_vol.g4type)
            shape_name = match.group(1)
            if self.debug: print("Making and placing a copy of " + shape_name)
            find_shape = self._shapes[shape_name]
            if find_shape is None:
                print("The Shape " + shape_name + " was not found, or not yet placed!")
                raise
            else:
                newgeo_shape = find_shape
        else:
            raise NameError("The geometry shape: " + geo_vol.g4type + " is not yet defined.")

        self._shapes[geo_vol.name] = newgeo_shape

        return newgeo_shape

    def place_volume(self, geo_vol, mother=None):
        """ Place the Geometry object geo_vol onto the ROOT geometry tree under the volume 'mother' """

        if not isinstance(geo_vol, Geometry):
            print("We can only build Geometry objects and argument is not a Geometry")
            return

        if mother is None:
            mother = geo_vol.mother  # If mother is not explicit, get it from the geometry line.

        try:
            mother_vol = self._volumes[mother]
        except KeyError:
            print("Error -- Mother volume: " + mother + " is not found, so cannot build " + geo_vol.name)
            return

        if geo_vol.name in list(self._shapes.keys()):
            if self.debug > 7:
                print("We have done the shape for '" + geo_vol.name + "' already. Skip.")
            return

        color, transp = self.get_color_alpha(geo_vol.col)
        transp = transp * 10
        if geo_vol.style == 0 and transp < 70:  # Outline only, instead make semi transparent.
            transp = 70

        medium = self.find_material(geo_vol.material, transp)

        # Make the translation and the rotation.
        translate = self.compute_trans_vector(geo_vol)
        rotate = self.compute_trans_rotation(geo_vol)

        self._translations[geo_vol.name] = (translate, rotate)  # Each shape has a translation in GEMC
        transrot = self.compute_combi_trans(geo_vol.name, translate, rotate)

        if geo_vol.exist == 0:  # I don't exist, so don't bother.
            return

        if self.debug > 1:
            print(
                "Mother: " + mother + " Volume: " + geo_vol.name + "  Type:" + geo_vol.g4type + "  Material:" +
                geo_vol.material + " Vis:" + str(geo_vol.visible))
            print("    dimension:" + str(geo_vol.dimensions) + " units:" + str(geo_vol.dims_units))
            print("    position :" + str(geo_vol.pos) + "  pos units:" + str(geo_vol.pos_units))
            print("    rotation :" + str(geo_vol.rot) + "  rot units:" + str(geo_vol.rot_units))
            print("    color: " + str(color))
            print("")
        newgeo_shape = self.get_volume_shape(geo_vol)

        if newgeo_shape == 0 or newgeo_shape is None:
            if self.debug:
                print("Cannot place this volume on the stack.")
                return

        if self.debug > 6:
            print("Put '" + geo_vol.name + "' put on shapes table ")

        if medium == 0:
            if self.debug > 5:
                print("Component volume '" + geo_vol.name + "' put on shapes table only")
        else:
            newgeo = ROOT.TGeoVolume(geo_vol.name, newgeo_shape, medium)
            newgeo.SetLineColor(color)
            newgeo.SetVisibility(geo_vol.visible)
            self._volumes[geo_vol.name] = newgeo
            mother_vol.AddNode(newgeo, 1, transrot)

    def Draw(self, option="ogl"):
        """For ROOT standard compatibility, also implement this with a capital D. This simply calls draw()"""
        return self.draw(option)

    def draw(self, option=""):
        """ draw an wireframe version of the objects """
        topvol = self._geom.GetTopVolume()
        self._geom.SetVisOption(0)
        self._geom.SetTopVisible(0)
        topvol.SetVisibility(0)
        topvol.Draw(option)

    def __str__(self):
        """ Print information about this class """
        strout = "GeometryROOT object, containing:\n"
        for name, vol in self._volumes.iteritems():
            match = re.match('<ROOT\.(.*) .*', str(vol.GetShape()))
            shape_name = match.group(1)

            match = re.match(r'.*\(\"(.*)\"\) .*', str(vol.GetMedium()))
            medium_name = match.group(1)
            strout += name + " rname:" + vol.GetName() + " type: " + shape_name + " medium:" + str(
                vol.GetMedium()) + "\n"

        return strout

    def interact(self, local_vars=None, init_view=1):
        """This wicked cool bit of code calls the Python environment, so you can mess with the geometry
            from the command line."""

        # This used to work, but not as well as the code below.
        #     context = globals().copy()

        # use exception trick to pick up the current frame
        try:
            raise NameError("dummy")
        except NameError:
            frame = sys.exc_info()[2].tb_frame.f_back

        # evaluate commands in current context
        context = frame.f_globals.copy()
        context.update(frame.f_locals)

        if local_vars:
            context.update(local_vars)

        readline.set_completer(rlcompleter.Completer(context).complete)
        readline.parse_and_bind("tab: complete")
        shell = code.InteractiveConsole(context)  # See: https://docs.python.org/2/library/code.html
        print("")
        print("You can now access the geometry through the ROOT browser")
        print("You are in a Python shell. Exit by crtl-D (EOF).")

        if init_view:
            # shell.push("import ROOT")
            # shell.push("browser=ROOT.TBrowser()")
            shell.push("rr.draw('ogl')")
        shell.interact()

    def SaveAs(self, filename=None):
        if filename is None:
            filename = self._geo_engine_current._Detector+".root"

        self._geom.SaveAs(filename)
