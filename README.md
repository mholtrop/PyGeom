# PyGeom
###A Python Geometry package for Gemc

This is a package that allows you to author Gemc geometry from a bit of Python code. It allows you to use the full computational prowess of Python and all it's packages to define your geometry and then write out the result as either Gemc txt files, or write to a database, or render the result in ROOT.

The code also allows you to import a Gemc txt file, then view the geometry in ROOT, and write it all out as a skeleton Python code for further manipulation. 

The sections below give an introduction for different features.

----------
## ShowRootGeometry

The executable Python script "ShowRootGeometry" is a simple front end for the GeometryROOT class. It is a convenient way to load a Gemc txt file and then display the resulting geometry in a OGL ROOT window. 
You can see in the script itself that this is accomplished with just a few lines of code.

####How to use ShowRootGeometry
From the command line (make sure ROOT is setup properly) you just type:

    ShowRootGeometry clas12__geometry_original.txt
The program will read the geometry file and then render it. It will also start a TBrowser. In the TBrowser, you will find the rendered geomerty tree under the "GEMC" folder. Double click on "GEMC",  and then each lower object to see the whole tree. Setting or unsetting the check mark will make the object visible or invisible.
For the expert: In your terminal, you will be dropped back to a Python prompt. This is a fully interactive Python shell, with the full geometry in a GeomertyROOT object which is named "rr". You can add new objects, make existing object invisble, etc, all from the command line. 
When you are done, just type quit(), or Crtl-D in the terminal.
One useful option is to use "-m vol_name" to make "vol_name" the mother volume, and thus only render that volume and all daughters. This can really simplify your viewing if you only want to see a part of the detector.
#### Checking for Overlaps
We can now use the ROOT geomerty engine to check for overlaps. In the terminal we tell ROOT to check for overlaps, with 0.001 accuracy:

    >>>> ROOT.gGeoManager.CheckOverlaps(0.001)

ROOT will then report on overlaps and extrusions.
Another useful overlap check is to draw a particular volume with random points. If the volume is called 'my_vol' then the command is:

    >>>> rr._volumes['my_vol'].RandomPoints()
   
