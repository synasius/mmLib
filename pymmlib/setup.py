#!/usr/bin/env python

## Copyright 2002 by PyMMLib Development Group (see AUTHORS file)
## This code is part of the PyMMLib distrobution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.

## Distutils script to ease installation
## python setup.py doc             : runs happydoc creating "doc" dir
## python setup.py sdist           : creates a .tar.gz distribution
## python setup.py bdist_wininst   : creates a window binary installer
## python setup.py bdist_rpm       : creates a rpm distribution

import os
import sys

from distutils.core import setup, Extension
from distutils.command.install_data import install_data


class package_install_data(install_data):
    def run(self):
        ## need to change self.install_dir to the actual library dir
        install_cmd = self.get_finalized_command('install')
        self.install_dir = getattr(install_cmd, 'install_lib')
        return install_data.run(self)

def library_data():
    """Install mmLib/Data/Monomer library.
    """
    ## start with the mmLib data files
    inst_list = [
        os.path.join(os.curdir, "mmLib", "Data", "elements.cif"),
        os.path.join(os.curdir, "mmLib", "Data", "monomers.cif")
    ]
  
    ## add all the monomer mmCIF files 
    mon_dir = os.path.join(os.curdir, "mmLib", "Data", "Monomers")
    
    for dir1 in os.listdir(mon_dir):
        dir2 = os.path.join(mon_dir, dir1)

        inst_dir = os.path.join("mmLib", "Data", "Monomers", dir1)

        file_list = []
        inst_list.append((inst_dir, file_list)) 
        
        for fil in os.listdir(dir2):
            file_list.append(os.path.join(dir2, fil))
            
    return inst_list

def extension_list():
    """Assemble the list of C extensions which need to be compiled.
    """
    elist = [
        ## PDB File Accelerator
        Extension(
            "pdbmodule", 
            ["src/pdbmodule.c"],
            include_dirs = [],
            library_dirs = [],
            libraries    = []),

        ## OpenGL Accelerator
        Extension(
            "glaccel", 
            ["src/glaccel.c"],
            include_dirs = ["/usr/X11/include",
                            "/usr/X11R6/include"],
            library_dirs = ["/usr/X11/lib",
                            "/usr/X11R6/lib"],
            libraries    = ["m", "X11", "Xi", "Xext", "Xmu", "GL", "GLU",
                            "glut"]),
    ]
    return elist

def run_setup():
    """Invoke the Python Distutils setup function.
    """
    s0 = setup(
        cmdclass = {'install_data': package_install_data},
        
        name         = "pymmlib",
        version      = "0.7",
        author       = "Jay Painter",
        author_email = "jpaint@u.washington.edu",
        url          = "http://pymmlib.sourceforge.net/",
        packages     = ["mmLib", "mmLib/Extensions"],
        ext_modules  = extension_list(),
        data_files   = library_data()
        )

def make_doc():
    """This is a special function to generate the documentation with
    Epidoc.  It once used happydoc.
    """
    #os.system("happydoc -d doc -t 'PyMMLib Documentation' --no-comments "\
    #          "--no-private-names mmLib")
    os.system(
        'epydoc --html --output doc --name "mmLib Documentation" '\
        'mmLib mmLib/Extensions') 


if __name__ == "__main__":
    if sys.argv[1] == "doc":
        make_doc()
    else:
        run_setup()
