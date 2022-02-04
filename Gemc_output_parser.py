#!/usr/bin/env python
#
"""
This tool parses the output log file of Gemc (or other GEANT4 based code) to look for the error statements that
indicate a geometry overlap. It will then use the PyGeom and GeometryROOT to build a geometry where each overlap
is represented by a small red box. Use -h to get a set of options for controlling the behavior of the code.
"""

import sys
import PyGeom as Geom
import re

if sys.version_info[0] < 3:
    print("Please upgrade your Python to version 3. or higher.")
    sys.exit(1)

def g4_exception_bloc(lines, search_start):
    """Given a list of lines as input, return a block of lines for a GEANT4 exception statement.
    Input: list of lines and point in list to start searching.
    Output: start and end index of block
    Note: If no start is found, start will be -1. If no end is found, end will be last line +1"""

    patt_start = re.compile(r"G4Exception-START", re.IGNORECASE)
    patt_end = re.compile(r"G4Exception-END", re.IGNORECASE)
    start = -1
    end = len(lines)
    for i in range(search_start, end):
        if patt_start.search(lines[i]):
            start = i+1
        if start > 0 and patt_end.search(lines[i]):
            end = i-1
            break
    return start, end


def g4_geomnav_exception_parser(lines, block_start, block_end):
    """Function that parses the exceptions from GEANT4 when you have overlaps that were
    found during particle navigation. I.e. a particle traverses the overlap and is confused
    as to which volume it is supposed to be in."""
    patt_current_phys_vol = re.compile(r"Current\s+phys volume:\s+'(.*)'", re.IGNORECASE)
    patt_previous_phys_vol = re.compile(r"Current\s+phys volume:\s+'(.*)'", re.IGNORECASE)
    patt_position = re.compile(r"at position\s*:\s*\(\s*([-+\d.]+)\*?,\s?([-+\d.]+)\s*,\s?([-+\d.]+)\s*\)",
                               re.IGNORECASE)
    patt_direction = re.compile(r"in direction\s*:\s*\(\s*([-+\d.]+)\*?,\s?([-+\d.]+)\s*,\s?([-+\d.]+)\s*\)",
                                re.IGNORECASE)

    current_phys_vol = None
    previous_phys_vol = None
    position = None
    direction = None
    for i in range(block_start, block_end):
        m = patt_current_phys_vol.search(lines[i])
        if m:
            current_phys_vol = m.group(1)
        m = patt_previous_phys_vol.search(lines[i])
        if m:
            previous_phys_vol = m.group(1)
        m = patt_position.search(lines[i])
        if m:
            position = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
        m = patt_direction.search(lines[i])
        if m:
            direction = (float(m.group(1)), float(m.group(2)), float(m.group(3)))

    return position, current_phys_vol, previous_phys_vol, direction


def g4_overlap_exception_parser(lines, block_start, block_end, debug=False):
    """Function that parses the exceptions from GEANT4 when you have overlaps that were found
    with the overlap checker. This is turned on for GEMC with the option: -CHECK_OVERLAPS=1 """
    patt_current_phys_vol = re.compile(r"Overlap is detected for volume\s+(.*)\s+\((.*)\)", re.IGNORECASE)
    patt_previous_phys_vol1 = re.compile(r"with its mother volume\s+(.*)\s+\((.*)\)", re.IGNORECASE)
    patt_previous_phys_vol2 = re.compile(r"with\s+(.*)\s+\((.*)\) volume", re.IGNORECASE)
    patt_position1 = re.compile(r"local point\s+\(\s*([-+\d.]+)\*?,\s?([-+\d.]+)\s*,\s?([-+\d.]+)\s*\),"
                                r"\s+overlapping by at least:\s*(.*)",
                                re.IGNORECASE)

    current_phys_vol = None
    current_phys_type = None
    previous_phys_vol = None
    previous_phys_type = None
    position = None
    overlap = None
    for i in range(block_start, block_end):
        m = patt_current_phys_vol.search(lines[i])
        if m:
            current_phys_vol = m.group(1)
            current_phys_type = m.group(2)
            m = patt_previous_phys_vol1.search(lines[i+1])
            if m:
                previous_phys_vol = m.group(1)
                previous_phys_type = m.group(2)
            else:
                m = patt_previous_phys_vol2.search(lines[i + 1])
                if m:
                    previous_phys_vol = m.group(1)
                    previous_phys_type = m.group(2)
            m = patt_position1.search(lines[i+2])
            if m:
                position = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
                overlap = m.group(4)

    if debug and (position is None or current_phys_vol is None):
        print("Could not parse: ")
        for i in range(block_start, block_end+1):
            print(lines[i].rstrip())

    return position, current_phys_vol, previous_phys_vol, current_phys_type, previous_phys_type, overlap


def overlap_parser(infile):
    """Read the infile, the log output from Gemc, and search for the GEANT4 overlap statements.
    Infile:  Input, Gemc log file.
    Returns: List containing tuples with:
            3-D space points where overlaps occurred.
            Name of current volume.
            Name of previous volume.

            Then either: 3 vector direction of track
            Or: current volume type, previous volume type, overlap length.
    """

    patt_type_geomnav = re.compile(r"\*\*\* G4Exception\s+:\s+GeomNav", re.IGNORECASE)
    patt_type_geomvol = re.compile(r"\*\*\* G4Exception\s+:\s+GeomVol.*", re.IGNORECASE)

    with open(infile) as fp:
        lines = fp.readlines()  # Just greedily read in the entire file.

    parser_out = []
    block_end = -1
    while block_end < len(lines):
        block_start, block_end = g4_exception_bloc(lines, block_end + 1)
        if patt_type_geomnav.search(lines[block_start]):
            overlap = g4_geomnav_exception_parser(lines, block_start, block_end)
        elif patt_type_geomvol:
            overlap = g4_overlap_exception_parser(lines, block_start, block_end)
        else:
            # Not a Geometry navigation issue
            # print(lines[block_start:block_end])
            pass
        if overlap[0] is not None:
            parser_out.append(overlap)
    return parser_out


def make_gemc_geometry(overlaps, geo=None, color="#ff0000", size=10.):
    """Convert the list of overlaps into a gemc table that puts a small marker dot at each location."""
    if geo is None:
        geo = Geom.GeometryEngine("overlaps")

    i = 1
    for overlap in overlaps:
        pos = overlap[0]
        geo.add(Geom.Geometry(
            name=f"Overlap{i}",
            mother="root",
            description="Overlap point",
            g4type="Box",
            pos=pos,
            pos_units="mm",
            rot=(0., 0., 0.),
            rot_units="deg",
            col=color,
            dimensions=[size, size, size],
            dims_units="mm",
            material="Vacuum",
            sensitivity="no",
            identity="no"
        ))
        i += 1

    return geo


def main(argv=None):
    import argparse

    if argv is None:
        argv = sys.argv
    else:
        argv = argv.split()
        argv.insert(0, sys.argv[0])  # add the program name.

    parser = argparse.ArgumentParser(
        description="""Parse the output of a Gemc run to look for log messages about overlapping volumes. 
        Then create a geometry table where each overlap is marked as small dot.""",
        epilog="""
        For more info, read the script ^_^, or email maurik@physics.unh.edu.""")

    parser.add_argument('-d', '--debug', action="count", help="Be more verbose if possible. ", default=0)
    parser.add_argument('-i', '--interactive', action="store_true",
                        help="Give an interactive python prompt after processing.")
    parser.add_argument('-G', '--GeoDir', type=str, default=None,
                        help="Add a geometry directory which will be prepended to each argument in -g.")
    parser.add_argument('-g', '--geometry', type=str, nargs="+",
                        help="Add a GEMC txt geometry or gcard to be displayed in light grey." 
                             "Multiple geometry files can be added, separated by a space.")
    parser.add_argument('-s', '--show', action="store_true",
                        help="Show the resulting geometry after processing.")
    parser.add_argument('-S', '--size', type=int, help="Set the size of the overlap marker. default =10.mm",
                        default=10)
    parser.add_argument('-e', '--excel', type=str, help="Write the overlaps to an excel file with specified name.",
                        default=None)
    parser.add_argument('-o', '--outfile', type=str, default=None,
                        help="Set the GEMC geometry output txt file name. Default is not to write a file.")
    parser.add_argument('-r', '--rootfile', type=str, default=None,
                        help="Set the output root file name. Default is not to write a file.")
    parser.add_argument('InputFile', type=str, help='Input file to parse.')
    args = parser.parse_args(argv[1:])
    if args.debug:
        print(f"Debug set to {args.debug}")

    print(f"Parsing {args.InputFile }")
    overlaps = overlap_parser(args.InputFile)

    print(f"Found {len(overlaps)} overlaps.")

    if args.excel:
        # Re-write the data for excel export.
        excel_data = []
        if len(overlaps[0]) == 6:
            excel_col_names = ["x", "y", "z", "Name", "Previous", "CurrentVolType", "PrevVolType", "overlap"]
            for o in overlaps:
                excel_row = [o[0][0], o[0][1], o[0][2], o[1], o[2], o[3]]
                for i in range(4, len(o)):
                    excel_row.append(o[i])
                excel_data.append(excel_row)

        elif len(overlaps[0]) == 4:
            excel_col_names = ["x", "y", "z", "Name", "Previous", "dir_x", "dir_y", "dir_z"]
            for o in overlaps:
                excel_row = [o[0][0], o[0][1], o[0][2], o[1], o[2], o[3][0], o[3][1], o[3][2]]
                excel_data.append(excel_row)

        else:
            print(f"No header. We got len(overlaps[0]) = {len(overlaps[0])}")
            print(overlaps[0])

        import pandas as pd
        pd_dat = pd.DataFrame(excel_data, columns=excel_col_names)
        pd_dat.to_excel(args.excel)

    geo = make_gemc_geometry(overlaps, size=args.size)
    geo.debug = args.debug

    if args.outfile is not None:
        geo.txt_write_geometry(name_overwrite=args.outfile)

    last_overlap = len(geo._Geometry) - 1  ## Fixme: GeometryEngine should have a better way of getting this.
    if args.debug:
        print(f"Found {last_overlap+1:6d} overlaps.")

    if args.geometry is not None and len(args.geometry):
        prepend = args.GeoDir + "/" if args.GeoDir is not None else ""
        for vol in args.geometry:
            if re.match('.*\.gcard', vol):
                if args.debug:
                    print(f"Add the gcard file: {vol}")
                geo.parse_gcard(vol)
            else:
                full_path = prepend + vol
                last_count = len(geo._Geometry)
                geo.txt_read_geometry(full_path)
                if args.debug:
                    print(f"Added geometry file {full_path} with {len(geo._Geometry)- last_count} volumes.")

        for x in geo._Geometry[last_overlap:]:
            x.col = "cccccc9"

    if args.show or args.rootfile:
        rr = Geom.GeometryROOT()
        rr.debug = args.debug
        rr.build_volumes(geo, "root")
        rr.close_geometry()
        if args.rootfile is not None:
            rr.SaveAs(args.rootfile)
        if args.show:
            rr.Draw("ogl")
            input("Just waiting until you enter something ...")
        if args.interactive:
            rr.interact()

if __name__ == '__main__':
    main()
