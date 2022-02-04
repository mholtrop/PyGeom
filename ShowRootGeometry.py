#!/usr/bin/env python
#
import sys
import argparse
import re

try:
    import ROOT
except ImportError as e:
    print("You are using Python: ", sys.version)
    print("It seems you do not have ROOT setup for this version of Python, or PyROOT is not "
          "enabled in your ROOT distribution,",
          " or not working properly. Try: python -c 'import ROOT' to diagnose problem. Sorry.")
    print(e)
    sys.exit()

from PyGeom import GeometryROOT
from PyGeom import GeometryEngine

def main(argv=None):
    #############################################################################################################
    if argv is None:
        argv = sys.argv

    parser = argparse.ArgumentParser(
                description="""Python-ROOT Geometry Viewer
                This code will read in a GEMC geometry table and render it through the ROOT TGeoManager engine.""",
                epilog="""For more information, or errors, please email: maurik@physics.unh.edu """)

    parser.add_argument('-q', '--quiet', action="store_true",
                        help='Tries to suppress extra output (depends also on the included Write engines!)')
    parser.add_argument('-d', '--debug', action="count", default=0,
                        help='Increase the general debug level by one.')
    parser.add_argument('-s', '--save', type=str, help="Save the resulting geometry in a ROOT file.", default=None)
    parser.add_argument('-c', '--check', action="store_true", help="Run the ROOT geometry checker.")
    parser.add_argument('-rd', '--rootdebug', action="count", help='Increase the ROOT debug level by one.')
    parser.add_argument('-gd', '--geomdebug', action="count", help='Increase the Geometry debug level by one.')
    parser.add_argument('-r', '--rootfile', type=str, help='Preload a geometry from rootfile.', default=None)
    parser.add_argument('-m', '--mother', type=str, default="root",
                        help='Specify the mother volume. Only below this volume is shown. default: root')
    parser.add_argument('tables', type=str, nargs="+", help='List of geometry files or gcard files to render')

    args = parser.parse_args(argv[1:])

    if args.debug:
        print("Debug level is: "+str(args.debug))

    if args.debug > 1:
        print("Rendering ", args.tables)

    gen = GeometryEngine("pygeom")
    if args.geomdebug:
        gen.debug = args.geomdebug
    
    # Run down the list of tables and load each of them into the Geometry

    for ff in args.tables:
        if re.match('.*\.gcard', ff):      # This is a gcard file.
            if args.debug:
                print("Parsing the gcard ", ff)
            gen.parse_gcard(ff)
        elif re.match('.*_geometry_*', ff):  # This is a geoemtry file.
            if args.debug:
                print("Parsing geometry file ", ff)

            gen.txt_read_geometry(ff)

        elif re.match('.*_materials_*', ff):  # This is a materials file.
            if args.debug:
                print("Parsing materials file ", ff)

            print("So sorry, but I don't have a materials parser... yet ...")


    # Now render the geometry and drop into interactive mode.

    print("Parsing the input files is done. Now building the ROOT geometry for viewing.")
    print(f"There were {len(gen)} objects in the input files.")

    rr = None
    if args.rootdebug:
        rr.debug = args.rootdebug

    if args.rootfile:
        print(f"Loading geometry from {args.rootfile}")
        rr = GeometryROOT(geo=args.rootfile)
    else:
        rr = GeometryROOT()
    rr.build_volumes(gen, args.mother)
    rr.close_geometry()

    if args.save:
        rr.SaveAs(args.save)

    rr.interact()


if __name__ == "__main__":
    sys.exit(main())
