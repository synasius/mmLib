#!/usr/bin/env python
## This program exersizes the PDB parser by walking through a directory
## of PDB files and processing each one.  The MyPDBProcessor class is a
## very simple custom PDB file processor

import os, sys
from mmLib import PDB


class MyPDBProcessor(PDB.RecordProcessor):
    """Implement callbacks for PDB record types.  If you want the callback
    with the raw mmLib.PDB classes, prefix the method name with 'process_',
    if you want callback argument to be the result of the mmLib.PDB record
    class's 'process' method, then use the prefix 'preprocess_'.
    Implement only the callback you want to handle.
    """
    def process_HEADER(self, pdb_record):
        print "REC: HEADER"
        print pdb_record
        print
    
    def preprocess_COMPND(self, pdb_record):
        print "REC: COMPND"
        print pdb_record
        print

    def preprocess_OBSLTE(self, pdb_record):
        print "REC: OBSLTE"
        print pdb_record
        print
        
    def preprocess_REVDAT(self, pdb_record):
        print "REC: REVDAT"
        print pdb_record
        print

    def preprocess_SPRSDE(self, pdb_record):
        print "REC: SPRSDE"
        print pdb_record
        print

    def process_default(self, pdb_record):
        """This method will be called, if it exists, for any PDB handler
        without its own method handler.
        """
        print "DEFAULT: "
        print pdb_record


def main(path):
    fileobj = open(path, "r")

    proc = MyPDBProcessor()
    proc.process_pdb_records(PDB.iter_pdb_records(iter(fileobj)))


if __name__ == "__main__":
    import os

    try:
        path = sys.argv[1]
    except IndexError:
        print "usage: pdb_test.py <PDB file or directory of PDB files>"
        sys.exit(1)

    if os.path.isfile(path):
        main(path)
    elif os.path.isdir(path):
        for name in os.listdir(path):
            name = os.path.join(path, name)
            if not os.path.isfile(name):
                continue
            try:
                main(name)
            except:
                print "ERROR: ",name
                raise
