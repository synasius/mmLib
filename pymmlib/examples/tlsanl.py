#!/usr/bin/env python

## Copyright 2002 by PyMMLib Development Group (see AUTHORS file)
## This code is part of the PyMMLib distrobution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.

import sys
import re
import string

from mmLib.PDB import PDBFile
from mmLib.Structure import *
from mmLib.FileLoader import LoadStructure, SaveStructure
from mmLib.Extensions.TLS import *


def usage():
    print "tlsanl.py <xxx.pdb> [REFMAC TLS File]"
    print
    print "description:"
    print "    Compute anisotropic ADP records from the given TLS"
    print "    description.  The TLS description is taken from the"
    print "    REMARK fields in the PDB file, or from the TLSOUT file"
    print "    written by REFMAC."
    print


def astr(a):
    a0 = "%.3f" % (a[0])
    a1 = "%.3f" % (a[1])
    a2 = "%.3f" % (a[2])

    return a0.rjust(7) + a1.rjust(7) + a2.rjust(7)

def print_TLS(text, Tt, T, Lt, L, St, S):
    print text

    s0 = "%s TENSOR" % (Tt)
    s1 = "%s TENSOR" % (Lt)
    s2 = "%s TENSOR" % (St)

    print "".ljust(5) + s0.ljust(24) + s1.ljust(24) + s2
    print "     (A^2)                   (DEG^2)                 (A DEG)"

    L = L * rad2deg2
    S = S * rad2deg

    for i in range(3):
        print "   %s   %s   %s" % (astr(T[i]), astr(L[i]), astr(S[i]))

def print_TLSGroup(tls):
    print "TLS GROUP NAME: %s" % (tls.name)

    calcs = tls.calc_COR()

    print_TLS(
        "INPUT TENSOR MATRICES WRT ORTHOGONAL AXES USING ORIGIN "\
        "OF CALCULATIONS",
        "T", tls.T,
        "L", tls.L,
        "S", tls.S)

    print
    print "TRACE OF TRANSLATION TENSOR               %.3f" % (
        trace(tls.T))
    print "MEAN TRANSLATION (TRACE/3)                %.3f" % (
        trace(tls.T)/3.0)
    print "MEAN LIBRATION   (TRACE/3)                %.3f" % (
        trace(tls.L * rad2deg2)/3.0)
    print

    print_TLS(
        "TENSOR MATRICES WRT LIBRATION AXES USING ORIGIN OF CALCULATIONS",
        "T^", calcs["T^"],
        "L^", calcs["L^"],
        "S^", calcs["S^"])

    print
    print "ORIGIN SHIFT RHO(O)^ TO CENTRE WRT LIBRATION AXES (A): "+\
          astr(calcs["RHO^"])
    print "ORIGIN SHIFT TO CENTRE WRT ORTHOGONAL AXES        (A): "+\
          astr(calcs["RHO"])
    print "TLS CENTRE OF REACTION WRT ORTHOGONAL AXES        (A): "+\
          astr(calcs["COR"])
    print

    print_TLS(
        "TENSOR MATRICES WRT LIBRATION AXES USING CENTRE OF REACTION",
        "T'^", calcs["T'^"],
        "L'^", calcs["L'^"],
        "S'^", calcs["S'^"])

    print

    print_TLS(
        "TENSOR MATRICES WRT ORTHOGONAL AXES USING CENTRE OF REACTION",
        "T'", calcs["T'"],
        "L'", calcs["L'"],
        "S'", calcs["S'"])

    print
    print "TRACE(T')/3.0   (A^2): %.3f" % (trace(calcs["T'"])/3.0)
    print "TRACE(L')/3.0 (DEG^2): %.3f" % (trace(calcs["L'"])/3.0*rad2deg2)
    print "TRACE(S')/3.0 (A*DEG): %.3f" % (trace(calcs["S'"])/3.0*rad2deg)
    print

    print
    print "SHIFT OF LIBRATION AXES TO DIAGNOLIZE S WRT ORTHOGONAL AXES USING"
    print "FROM THE ORIGIN OF CALCULATION (A): "
    print "L1 (A): " + astr(calcs["L1_rho"] + calcs["COR"])
    print "L2 (A): " + astr(calcs["L2_rho"] + calcs["COR"])
    print "L3 (A): " + astr(calcs["L3_rho"] + calcs["COR"])
    print

    print
    print "SHIFT OF LIBRATION AXES TO DIAGNOLIZE S WRT ORTHOGONAL AXES"
    print "FROM THE CENTER OF REACTION (A): "
    print "L1 (A): " + astr(calcs["L1_rho"])
    print "L2 (A): " + astr(calcs["L2_rho"])
    print "L3 (A): " + astr(calcs["L3_rho"])
    print

    print "SCREW PITCH OF THE 3 NON-INTERSECTING LIBRATION AXES"

    for Lx, Lx_pitch in [
        ("L1", "L1_pitch"),
        ("L2", "L2_pitch"),
        ("L3", "L3_pitch")]:

        print "%s PITCH (A/DEG): %10.3f" % (
            Lx, calcs[Lx_pitch]/rad2deg)


def main(pdb_path, tls_out_path, calc_tls):

    struct = LoadStructure(fil = pdb_path)

    ## calculate one set of TLS tensors from all the amino acid atoms
    if calc_tls == True:
        tls = TLSGroup()

        for res in struct.iter_amino_acids():
            for atm in res.iter_atoms():
                tls.append(atm)

        tls.origin = tls.calc_centroid()
        tls.calc_tls_tensors()
        print_TLSGroup(tls)

    else:
        tls_file = TLSFile()

        ## get TLS groups from REMARK statments in PDB file
        if tls_out_path == None:
            tls_file.set_file_format(TLSFileFormatPDB())
            try:
                tls_file.load(open(pdb_path, "r"), pdb_path)
            except IOError, e:
                print "[Error] %s: %s" % (str(e), pdb_path)
            
        ## or get TLS groups from REFMAC TLSOUT file
        else:
            tls_file.set_file_format(TLSFileFormatTLSOUT())
            try:
                tls_file.load(open(tls_out_path, "r"), tls_out_path)
            except IOError, e:
                print "[Error] %s: %s" % (str(e), tls_out_path)

        ## print the TLS groups
        for tls_group in tls_file.generate_tls_group_list(struct):
            print_TLSGroup(tls_group)
            print
        

if __name__ == "__main__":

    ## calculate TLS tensors -- do not read from file
    if "-c" in sys.argv:
        sys.argv.remove("-c")
        calc_tls = True
    else:
        calc_tls = False

    try:
        pdb_path = sys.argv[1]
    except IndexError:
        usage()
        sys.exit(1)

    try:
        tls_out_path = sys.argv[2]
    except IndexError:
        tls_out_path = None

    main(pdb_path, tls_out_path, calc_tls)
