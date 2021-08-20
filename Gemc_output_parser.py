#!/usr/bin/env python
#
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

    return position, current_phys_vol, current_phys_type, previous_phys_vol, previous_phys_type, overlap


def overlap_parser(infile):
    """Read the infile, the log output from Gemc, and search for the GEANT4 overlap statements.
    Infile:  Input, Gemc log file.
    Returns: List containting tupples with:
            Name of current volume.
            Name of previous volume.
            3-D space points where overlaps occurred.
            3-D directions of track at that point.
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


def make_gemc_geometry(overlaps, geo=None, color="#ff0000"):
    """Convert the list of overlaps into a gemc table that puts a small marker dot at each location."""
    if geo is None:
        geo = Geom.GeometryEngine("overlaps")

    size = 10.
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
    parser.add_argument('-s', '--show', action="store_true",
                        help="Show the resulting geometry after processing.")
    parser.add_argument('-o', '--output', type=str, default="Gemc_output_parser.root",
                        help="Set the output file name. Default is Gemc_output_parser.root")
    parser.add_argument('InputFile', type=str, help='Input file to parse.')
    args = parser.parse_args(argv[1:])

    print(f"Parsing {args.InputFile }")
    overlaps = overlap_parser(args.InputFile)
    geo = make_gemc_geometry(overlaps)
    geo.txt_write_geometry()
    rr = Geom.GeometryROOT()
    rr.build_volumes(geo, "root")
    rr.close_geometry()
    rr.SaveAs(args.output)
    if args.show:
        rr.Draw("ogl")
        input("Just waiting until you enter something ...")
    if args.interactive:
        rr.interact()

if __name__ == '__main__':
    main()
