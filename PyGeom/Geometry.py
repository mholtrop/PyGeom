"""
class Geometry

@author: Maurik Holtrop (UNH) maurik@physics.unh.edu

The Geometry class defines a geometry in the GEMC fashion. The Geometry class is mostly a class
to store all the parameters of the GEANT4 geometry object.

A Geometry class object behaves as a list (i.e. gen[0] returns the name, gen[1] the mother) and also as a dictionary
(i.e. gen['name'] returns the name.). If you print the gen object, it prints as a GEMC geometry.txt line. If you
call MySQL_str you get a MySQL SQL string to insert the object into a database. The python_str() will
give a Python statement to create a gen object.

A Geometry class can be created in a Python script and then added to a GeometryEngine, or
the GeometryEngine can read a GEMC text file, or MySQL database. The Geomtery class can then
be passed to a GeometryROOT class to render the object in ROOT.

A utility call calc_g4_trapezoid, is there to help create the parameters for a G4Trapezoid.
 """

import math
import re


class Geometry:
    """ A Class for storing the geometry of an objects to be rendered in the output.
    You would typicaly add these objects into a GeometryEngine object.
    Each of the paramters corresponds to the parameters defined in the GEMC text
    input format. For great detail, check the GEMC documentation.

    gobj = Geometry(
         name="unknown",  # String. Name of the object.
         mother="root",   # String. Name of the mother of this object.
         description="",  # String. Text description of the object.
         pos=[0,0,0],     # List.   Position of the object in a list of 3 floats.
         pos_units="cm",  # String. Units for the position of the object: mm, cm, inch, m
         rot=[0,0,0],     # List.   Angles defining the rotation of the object.
         rot_units="rad", # String. Units for the angles: deg, rad, mrad
         rot_order="",    # String. Order of the angles: "xyz", "zyx" etc.
         col="000000",    # String. Color for the object when it is being rendered.
         g4type="",       # String. G4Type - the type of object, eg. "box"
         dimensions="",   # List or String. The dimensions that correspond to the g4type
         dims_units="cm", # String or List. The units used for the dimensions.
                          # If string the same unit will be used for all dimensions.
         material="Vacuum",# String. The material to be used for the object.
         magfield="no",   # String. The magnetic field in the object. "no" for no field.
         ncopy=1,         # Int.    The GEMC ncopy parameter, see GEMC docs.
         pmany=1,         # Int.    The GEMC pmany parameter, see GEMC docs.
         exist=1,         # Int.    Flag whether the object is used.
         visible=1,       # Int.    Flag whether the object should be visible.
         style=1,         # Int.    Flag whether the object is wireframe(0) or solid (1)
         sensitivity="no",# String. Which type of sensitivity this object has.
         hittype="",      # String. Which hit routine should be used for this object.
         identity="",     # String. The id string for the object.
         )
    """
    #
    # Note that below are the default values for each of the geometry objects.
    # They can be modified when the Geometry class is instantiated.
    #
    debug = 0
    base_units = ["cm", "rad"]  # Set the default units to use if units are converted.
    force_unit_conversion = False  # Set to True to always convert units to the base units.
    #
    # Store the standard GEMC parameters set.
    #
    # Implementation question: Would this be cleaner if the all the data was stored in a single list?
    # data = {'name':" ",'mother':" ", etc}
    # Would make sense, but the defaults would be harder to deal with.
    #
    name = ""
    mother = ""
    description = ""
    pos = [0, 0, 0]
    pos_units = base_units[0]
    rot = [0, 0, 0]
    rot_units = base_units[1]
    rot_order = ""  # Blank is standard zyx rotation order.
    col = "000000"
    g4type = ""
    dimensions = ""
    dims_units = base_units[0]
    material = ""
    magfield = "no"
    ncopy = 1
    pmany = 1
    exist = 1
    visible = 1
    style = 1
    sensitivity = "no"
    hittype = "no"
    identity = "no"

    def __init__(self,
                 name="unknown",
                 mother="root",
                 description="",
                 pos=[0, 0, 0],
                 pos_units=base_units[0],
                 rot=[0, 0, 0],
                 rot_units=base_units[1],
                 rot_order="",
                 col="000000",
                 g4type="",
                 dimensions="",
                 dims_units=base_units[0],
                 material="Vacuum",
                 magfield="no",
                 ncopy=1,
                 pmany=1,
                 exist=1,
                 visible=1,
                 style=1,
                 sensitivity="no",
                 hittype="",
                 identity="",
                 force_unit_conversion=False,
                 base_units=["cm", "rad"]
                 ):

        if type(name) is tuple or type(name) is list:  # If first argument is a tuple, assume the full content.
            self.name = name[0]
            self.mother = name[1]
            self.description = name[2]
            self.pos, self.pos_units = self.parse_gemc_str(name[3])
            self.rot, self.rot_units, self.rot_order = self.parse_gemc_rot_str(name[4])
            self.col = name[5]
            self.g4type = name[6]
            self.dimensions, self.dims_units = self.parse_gemc_str(name[7])
            self.material = name[8]
            self.magfield = name[9]
            self.ncopy = int(name[10])
            self.pmany = int(name[11])
            self.exist = int(name[12])
            self.visible = int(name[13])
            self.style = int(name[14])
            self.sensitivity = name[15]
            self.hittype = name[16]
            self.identity = name[17]
        elif type(name) is str:
            self.name = name
            self.mother = mother
            self.description = description
            self.pos = pos
            self.set_position(pos, pos_units)
            self.set_rotation(rot, rot_units, rot_order)
            self.col = col
            self.g4type = g4type
            self.set_dimensions(dimensions, dims_units)
            self.material = material
            self.magfield = magfield
            self.ncopy = ncopy
            self.pmany = pmany
            self.exist = exist
            self.visible = visible
            self.style = style
            self.sensitivity = sensitivity
            self.hittype = hittype
            self.identity = identity
        else:
            print("Geometry does not know how to handle input of type: ", type(name))

        if force_unit_conversion:
            self.force_unit_conversion = force_unit_conversion
        if base_units:
            self.base_units = base_units

    def unit_convert_dict(self, base_unit):
        """Return a conversion dict and translation dict that provides the correct unit conversions based on base_unit
        base_unit is a string or a list and contains a unit for length and one for angles
        The conversion dict contains the numeric constant to covert to the base_unit.
        The translation dict converts the unit name to the base unit name."""
        if type(base_unit) == str:
            base_unit = base_unit.split()
        base_unit = [u.strip().strip("*") for u in base_unit]  # Split the string and remove any *
        # This default ensures that there is always a sensible conversion, no matter the contents of base_unit
        conv_dict = {'mm': 0.1, 'cm': 1., 'm': 100., 'inch': 2.54, 'inches': 2.54, 'rad': 1., 'mrad': 0.001,
                     'deg': math.radians(1)}
        trans_dict = {'mm': 'cm', 'cm': 'cm', 'm': 'cm', 'inch': 'cm', 'inches': 'cm', 'rad': 'rad', 'mrad': 'rad',
                      'deg': 'rad'}
        for u in base_unit:
            if u == "cm":
                trans_dict['mm'] = trans_dict['cm'] = trans_dict['m'] = trans_dict['inch'] = u
                conv_dict['mm'] = 0.1
                conv_dict['cm'] = 1.
                conv_dict['m'] = 100.
                conv_dict['inch'] = 2.54
            elif u == "mm":
                trans_dict['mm'] = trans_dict['cm'] = trans_dict['m'] = trans_dict['inch'] = u
                conv_dict['mm'] = 1.
                conv_dict['cm'] = 10.
                conv_dict['m'] = 1000.
                conv_dict['inch'] = 25.4
            elif u == "m":
                trans_dict['mm'] = trans_dict['cm'] = trans_dict['m'] = trans_dict['inch'] = u
                conv_dict['mm'] = 0.001
                conv_dict['cm'] = 0.01
                conv_dict['m'] = 1.
                conv_dict['inch'] = 0.0254
            elif u == "inch":
                print("Warning: Base Units of Inches is not recommended for GEANT4")
                trans_dict['mm'] = trans_dict['cm'] = trans_dict['m'] = trans_dict['inch'] = u
                conv_dict['mm'] = 0.1 / 2.54
                conv_dict['cm'] = 1. / 2.54
                conv_dict['m'] = 100. / 2.54
                conv_dict['inch'] = 1.
            elif u == "rad":
                trans_dict['rad'] = trans_dict['mrad'] = trans_dict['deg'] = u
                conv_dict['rad'] = 1
                conv_dict['mrad'] = 0.001
                conv_dict['deg'] = math.radians(1.)
            elif u == "mrad":
                trans_dict['rad'] = trans_dict['mrad'] = trans_dict['deg'] = u
                conv_dict['rad'] = 1000.
                conv_dict['mrad'] = 1.
                conv_dict['deg'] = 1000. * math.radians(1.)
            elif u == "deg":
                trans_dict['rad'] = trans_dict['mrad'] = trans_dict['deg'] = u
                conv_dict['rad'] = math.degrees(1.)
                conv_dict['mrad'] = 0.001 * math.degrees(1.)
                conv_dict['deg'] = 1

            trans_dict['counts'] = 'counts'
            conv_dict['counts'] = 1

        return conv_dict, trans_dict

    def parse_gemc_rot_str(self, string, base_unit=0):
        """Convert the Rotation GEMC MySQL string with units and ordered statement into a list and a units list
        and order, based on the base_unit """
        if base_unit == 0:
            base_unit = self.base_units
        order = ""
        tmp_list = string.split()
        #        m=re.match(' *ordered: *([xyz]+)',string)  # Could use this, but overkill really.
        if tmp_list[0].strip() == "ordered:":
            order = tmp_list[1]
            dims, dims_units = self.parse_gemc_str(' '.join(tmp_list[2:]), base_unit)
        elif len(tmp_list) == 1:  # Single statement. This is usually an erroneous "0" entry.
            print("Warning: Rotation with only one entry: " + str(tmp_list[0]))
            if not tmp_list[0] == "0":
                print("But I don't know what to do with it! Setting rotation to zero.")

            dims = [0, 0, 0]
            dims_units = [base_unit[1]] * 3

        else:
            dims, dims_units = self.parse_gemc_str(string, base_unit)

        return dims, dims_units, order

    def parse_gemc_str(self, string, base_unit=0):
        """Convert the GEMC MySQL string with units into a list and a units list based on the base_unit """
        if base_unit == 0:
            base_unit = self.base_units

        conv, trans = self.unit_convert_dict(base_unit)
        tmp_list = string.split()
        dims = []
        dims_units = []
        for p in tmp_list:
            if not re.search(r'\*', p):
                if len(p) > 1:
                    print("Warning: expected unit but none found in:" + str(tmp_list))
                ans = float(p)
                dims.append(ans)
                dims_units.append(base_unit[0])  # If there was no unit, make it base_unit length.
            else:
                try:
                    num, unit = p.split('*')
                except ValueError:
                    print("There was a problem parsing: ", p)
                    raise

                if self.force_unit_conversion:
                    if unit == "inches":
                        unit = "inch"
                    ans = float(num) * conv[unit]

                    if self.debug > 2:
                        print("Conversion: ", p, " to ", ans, " ", trans[unit])
                    dims.append(ans)
                    dims_units.append(trans[unit])
                else:
                    dims.append(float(num))
                    dims_units.append(unit)

        return dims, dims_units

    def set_position(self, pos, units):
        """ Set the position from a string or a list, in the latter case use units for the units."""
        if type(pos) == str:
            # Need to convert the string to a pos vector and a unit. Typical pos="10*mm 12*cm 1*m"
            self.pos, self.pos_units = self.parse_gemc_str(pos, units)

        else:
            # No need to convert
            self.pos = pos
            self.pos_units = units

    def set_rotation(self, rot, units, order):
        """ Set the rotation of the object from a string or a list."""
        if type(rot) == str:
            # Need to convert the string to a pos vector and a unit. Typical pos="10*mm 12*cm 1*m"
            self.rot, self.rot_units, self.rot_order = self.parse_gemc_rot_str(rot, units)

        else:
            # No need to convert
            self.rot = rot
            self.rot_units = units
            self.rot_order = order

    def set_dimensions(self, dims, units):
        """ Set the dimensions of the object from a string or a list """
        if type(dims) == str:
            # Need to convert the string to a pos vector and a unit. Typical pos="10*mm 12*cm 1*m"
            self.dimensions, self.dims_units = self.parse_gemc_str(dims, units)

        else:
            # No need to convert
            self.dimensions = dims
            self.dims_units = units

    def make_string(self, item, units):
        """ Turn a list and units into a Maurizio's MySQL Database style string. """
        strout = ""
        if type(units) == str:
            units = [units]
        if self.debug > 3:
            print("inital: item(", len(item), ")=", item, "  units(", len(units), ")=", units)

        if len(units) == len(item):  # There is one unit for each item. Units may be mixed.
            for i in range(len(item)):
                strout += str(item[i]) + "*" + units[i] + " "
        else:
            if len(units) > 1:
                print("WARNING: There seems to be an issue here, item and units are different length: item=" +
                      str(item) + " units=" + str(units))
            for i in item:
                strout += str(i) + "*" + units[0] + " "

        return strout

    def mysql_str(self, table, variation=None, idn=1):
        """ Return a MySQL statement to insert the geometry into a GEMC Table in a MySQL database"""

        sql = "INSERT INTO " + table + " VALUES ('"
        sql += self.name + "','" + self.mother + "','" + self.description + "','"
        sql += self.make_string(self.pos, self.pos_units) + "','"
        sql += self.make_string(self.rot, self.rot_units) + "','"
        sql += self.col + "','" + self.g4type + "','"
        sql += self.make_string(self.dimensions, self.dims_units) + "','"
        sql += self.material + "','"
        sql += self.magfield + "',"
        sql += str(self.ncopy) + ","
        sql += str(self.pmany) + ","
        sql += str(self.exist) + ","
        sql += str(self.visible) + ","
        sql += str(self.style) + ",'"
        sql += self.sensitivity + "','"
        sql += self.hittype + "','"
        sql += self.identity + "',"
        sql += str(0) + ","  # rmin and rmax are not used anywhere, but still in
        sql += str(100000) + ","  # MySQL definition.
        sql += "now()"

        if variation is not None:  # This is for GEMC 2.0 style tables.
            sql += ",'" + variation + "',"
            sql += str(idn)
        sql += ");"
        return sql

    def python_str(self, indent=4):
        """Return a string containing a python statement that will render this geometry.
        This can be used to create a template script from the contents of a database.
        Code will be indented by 'indent'
        """
        pstr = ' ' * indent + "geo = Geometry( \n"
        pstr += ' ' * indent + "      name='" + self.name + "',\n"
        pstr += ' ' * indent + "      mother='" + self.mother + "',\n"
        pstr += ' ' * indent + "      description='" + self.description + "',\n"
        pstr += ' ' * indent + "      pos=" + str(self.pos) + ",\n"
        pstr += ' ' * indent + "      pos_units=" + str(self.pos_units) + ",\n"
        pstr += ' ' * indent + "      rot=" + str(self.rot) + ",\n"
        pstr += ' ' * indent + "      rot_units=" + str(self.rot_units) + ",\n"
        pstr += ' ' * indent + "      col='" + self.col + "',\n"
        pstr += ' ' * indent + "      g4type='" + self.g4type + "',\n"
        pstr += ' ' * indent + "      dimensions=" + str(self.dimensions) + ",\n"
        pstr += ' ' * indent + "      dims_units=" + str(self.dims_units) + ",\n"
        pstr += ' ' * indent + "      material='" + self.material + "',\n"
        pstr += ' ' * indent + "      magfield='" + self.magfield + "',\n"
        pstr += ' ' * indent + "      ncopy=" + str(self.ncopy) + ",\n"
        pstr += ' ' * indent + "      pmany=" + str(self.pmany) + ",\n"
        pstr += ' ' * indent + "      exist=" + str(self.exist) + ",\n"
        pstr += ' ' * indent + "      visible=" + str(self.visible) + ",\n"
        pstr += ' ' * indent + "      style=" + str(self.style) + ",\n"
        pstr += ' ' * indent + "      sensitivity='" + self.sensitivity + "',\n"
        pstr += ' ' * indent + "      hittype='" + self.hittype + "',\n"
        pstr += ' ' * indent + "      identity='" + self.identity + "')\n"
        return pstr

    def validate(self):
        """Attempt to check yourself for valid entries.
          If all is OK, then return a 0.
          If an error is expected, return a integer indicating the field where the first error is expected.
          Clearly this can only catch the most simple errors, such as formatting problems."""

        if not type(self.name) is str:
            return 1

        if not type(self.mother) is str:
            return 2

        if not type(self.description) is str:
            return 3

        if type(self.pos) is list or type(self.pos) is tuple:
            if not len(self.pos) == 3:
                return 4
            for x in self.pos:
                if not (type(x) is int or type(x) is float):
                    return 41
        else:
            return 42

        try:
            self.make_string(self.pos, self.pos_units)
        except Exception as e:
            print(e)
            return 43

        if type(self.rot) is list or type(self.rot) is tuple:
            if not len(self.rot) == 3:
                return 5
            for x in self.rot:
                if not (type(x) is int or type(x) is float):
                    return 51
        else:
            return 52

        try:
            self.make_string(self.rot, self.rot_units)
        except Exception as e:
            print(e)
            return 53

        if not type(self.col) is str:
            return 6

        if not type(self.g4type) is str:
            return 7

        # The dimensions and dims_units are more difficult to check. The Operations: g4type has none!
        # Try to turn to a string, and hope for the best....
        try:
            self.make_string(self.dimensions, self.dims_units)
        except Exception as e:
            print(e)
            return 8

        if not type(self.material) is str:
            return 9

        if not type(self.magfield) is str:
            return 10

        if not type(self.ncopy) is int:
            return 11

        if not type(self.pmany) is int:
            return 12

        if not (self.exist == 0 or self.exist == 1):
            return 13

        if not (self.visible == 0 or self.visible == 1):
            return 14

        if not (self.style == 0 or self.style == 1):
            return 15

        if not type(self.sensitivity) is str:
            return 16

        if not type(self.hittype) is str:
            return 17

        if not type(self.identity) is str:
            return 18

        return 0

    def __str__(self):
        """ Return a string with the geometry as a '|' delimited string, as Maurizio's perl scripts """
        outstr = self.name + ' | '
        outstr += self.mother + ' | '
        outstr += self.description + ' | '
        outstr += self.make_string(self.pos, self.pos_units) + ' | '
        if self.rot_order != "":
            outstr += "ordered: " + self.rot_order + " "
        outstr += self.make_string(self.rot, self.rot_units) + ' | '
        outstr += self.col + ' | '
        outstr += self.g4type + ' | '
        outstr += self.make_string(self.dimensions, self.dims_units) + ' | '
        outstr += self.material + ' | '
        outstr += self.magfield + ' | '
        outstr += str(self.ncopy) + ' | '
        outstr += str(self.pmany) + ' | '
        outstr += str(self.exist) + ' | '
        outstr += str(self.visible) + ' | '
        outstr += str(self.style) + ' | '
        outstr += self.sensitivity + ' | '
        outstr += self.hittype + ' | '
        outstr += self.identity + ' '  # No bar on the end of the line.

        return outstr

    def __getitem__(self, i):
        """To treat the Geometry as a dictionary or list..."""
        if i == "name" or i == 0:
            return self.name
        elif i == "mother" or i == 1:
            return self.mother
        elif i == "description" or i == 2:
            return self.description
        elif i == "pos" or i == 3:
            return self.make_string(self.pos, self.pos_units)
        elif i == "rot" or i == 4:
            return self.make_string(self.rot, self.rot_units)
        elif i == "col" or i == 5:
            return self.col
        elif i == "g4type" or i == "type" or i == 6:
            return self.g4type
        elif i == "dimensions" or i == "dims" or i == 7:
            return self.make_string(self.dimensions, self.dims_units)
        elif i == "material" or i == 8:
            return self.material
        elif i == "magfield" or i == 9:
            return self.magfield
        elif i == "ncopy" or i == 10:
            return self.ncopy
        elif i == "pmany" or i == 11:
            return self.pmany
        elif i == "exist" or i == 12:
            return self.exist
        elif i == "visible" or i == 13:
            return self.visible
        elif i == "style" or i == 14:
            return self.style
        elif i == "sensitivity" or i == 15:
            return self.sensitivity
        elif i == "hittype" or i == 16:
            return self.hittype
        elif i == "identity" or i == 17:
            return self.identity

    def calc_g4_trapezoid(self, front, depth, p1x, p1z, theta1, p2x, p2z, theta2):
        """Utility function.
        This function calculates the parameters for a G4Trap, assuming the front is at z=front, and given the
        depth (length) of the trapezoid, and a left (p1) and right (p2) point and angle wrt z, for points on the
        left and right edges of the trapezoid.
        The function retuns cx,cz,theta,dx1,dx2  the centerpoint (x,z), the skew angle, and the front and back half
        widths.
        See HPS_Software Notebook section "G4 Trapezoid"
        """
        z1 = front
        z2 = front + depth
        #  dz=depth/2

        dx1 = ((p2x - p1x) - (z1 - p1z) * math.tan(theta1) + (z1 - p2z) * math.tan(theta2)) / 2.
        dx2 = ((p2x - p1x) - (z2 - p1z) * math.tan(theta1) + (z2 - p2z) * math.tan(theta2)) / 2.

        pp1x = p1x + ((z1 + z2) / 2. - p1z) * math.tan(theta1)  # line through midpoint on low x.
        pp2x = p2x + ((z1 + z2) / 2. - p2z) * math.tan(theta2)  # line through midpoint high x.
        c1x = p2x + (z1 - p2z) * math.tan(theta2) - dx1
        c2x = p2x + (z2 - p2z) * math.tan(theta2) - dx2

        cx = (c1x + c2x) / 2.
        cz = front + depth / 2.
        thetal = math.atan2((c2x - c1x), depth)

        if dx1 <= 0 or dx2 <= 0 or pp1x > pp2x:
            print("Probable problem with Trapezoid calculation:")
            print("front=" + str(front) + "  Depth=" + str(depth))
            print("p1x  =" + str(p1x) + "  p1z  =" + str(p1z))
            print("p2x  =" + str(p2x) + "  p2z  =" + str(p2z))
            print("pp1x =", pp1x, "  pp2x =", pp2x)
            print("dx1  =", dx1, "  dx2  =", dx2)
            print("theta1=", theta1, " theta2=", theta2)
            print("depth =" + str(depth) + "  z2 - p2z=", (z2 - p2z), "  tan(theta2)=", math.tan(theta2),
                  " (z2-p1z)*tan(theta1)=", (z2 - p1z) * math.tan(-theta2))
            print("c1x  =" + str(c1x) + "   c2x =" + str(c2x))
            print("cx =  " + str(cx) + "   cz = " + str(cz))
            print("cx'=  ", (pp1x + pp2x) / 2.)
            print("thetal=", thetal)
            print("dx1  =" + str(dx1) + "   dx2 =" + str(dx2))

        return cx, cz, thetal, dx1, dx2
