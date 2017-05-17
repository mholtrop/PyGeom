#!/usr/bin/env python
#
import sys
import argparse
import re

try:
    import ROOT
except:
    print("You are using Python: ",sys.version)
    print("It seems you do not have ROOT setup for this version of Python, or PyROOT is not enabled in your ROOT distribution,",
          " or not working properly. Try: python -c 'import ROOT' to diagnose problem. Sorry.")
    sys.exit()

from PyGeom import GeometryROOT
from PyGeom import GeometryEngine


try:
#    from PyGeom import Geometry
    pass
    
except:
    print("The GeometryEngine and/or  GeometryROOT Python packages were not found in your PythonPath. Please add them!")
    sys.exit()


def main(argv=None):
        ################################################################################################################################
    if argv is None:
        argv = sys.argv
        
    parser = argparse.ArgumentParser(
                description="""Python-ROOT Geometry Viewer 
                This code will read in a GEMC geometry table and render it through the ROOT TGeoManager engine.""",
                epilog="""For more information, or errors, please email: maurik@physics.unh.edu """)

    parser.add_argument('-q','--quiet',action="store_true",help='Tries to suppress extra output (depends also on the included Write engines!)')
    parser.add_argument('-d','--debug',action="count",help='Increase the general debug level by one.')
    parser.add_argument('-rd','--rootdebug',action="count",help='Increase the ROOT debug level by one.')
    parser.add_argument('-gd','--geomdebug',action="count",help='Increase the Geometry debug level by one.')
    parser.add_argument('-m','--mother',type=str,default="root",help='Specify the mother volume. Only below this volume is shown. default: root')
    parser.add_argument('tables',type=str,nargs="+",help='list of geometry files to render')

    args = parser.parse_args(argv[1:])

    if args.debug:
        print("Debug level is: "+str(args.debug))

    if args.debug >1:
        print("Rendering ",args.tables)


    gen = GeometryEngine("clas12")
    gen.debug = args.geomdebug
    
    # Run down the list of tables and load each of them into the Geometry

    for ff in args.tables:
        if re.match('.*_geometry_*',ff):  # This is a geoemtry file.
            if args.debug: print("Parsing geometry file",ff)

            gen.TXT_Read_Geometry(ff)

        if re.match('.*_materials_*',ff):  # This is a materials file.
            if args.debug: print("Parsing materials file",ff)
            
            print("So sorry, but I don't have a materials parser... yet ...")


    # Now render the geometry and drop into interactive mode.
    
    rr=GeometryROOT()
    rr.debug = args.rootdebug
    rr.build_volumes(gen,args.mother)
    rr.close_geometry()
    rr.interact()


if __name__ == "__main__":
    sys.exit(main())

