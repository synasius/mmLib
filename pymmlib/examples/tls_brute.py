#!/usr/bin/env python

## Copyright 2002 by PyMMLib Development Group (see AUTHORS file)
## This code is part of the PyMMLib distrobution and governed by
## its license.  Please see the LICENSE file that should have been
## included as part of this package.

from __future__ import generators
import sys
import math

from mmLib.Structure      import *
from mmLib.FileLoader     import *
from mmLib.Extensions.TLS import *


def prnt_header(args):
    print "## PATH: %s" % (args["path"])
    print "## NUM GROUPS: %d" % (args["num_groups"])
    print "## SEGMENT LENGTH: %d" % (args["seg_len"])
    print "## MAINCHAIN ONLY: %s" % (str(args["mainchain_only"]))
    print "## OMIT SINGLE BONDED ATOMS: %s" % (str(args["omit_single_bonded"]))

def prnt_col_labels():
    print "## RES   NUM   Atoms    <B>     <A>   R      <DP2>   s<DP2>  "\
          "<DP2N>  s<DP2N> <S>    s<S>   t(T)    t(L)"


def prnt_stats(stats):
        ## print out results
        print str(stats["name"]).ljust(8),

        print str(stats["segment_num"]).ljust(5),

        x = "%d" % (len(stats["tls"]))
        print x.ljust(8),

        x = "%.3f" % (stats["mean_B"])
        print x.ljust(7),

        x = "%4.2f" % (stats["mean_A"])
        print x.ljust(5),

        x = "%.3f" % (stats["R"])
        print x.ljust(6),

        x = "%.4f" % (stats["mean_DP2"])
        print x.ljust(7),

        x = "%.4f" % (stats["sigma_DP2"])
        print x.ljust(7),

        x = "%.4f" % (stats["mean_DP2N"])
        print x.ljust(7),

        x = "%.4f" % (stats["sigma_DP2N"])
        print x.ljust(7),
        
        x = "%5.3f" % (stats["mean_S"])
        print x.ljust(6),

        x = "%5.3f" % (stats["sigma_S"])
        print x.ljust(6),

        x = "%6.4f" % (trace(stats["tls"].T))
        print x.ljust(7),

        x = "%6.4f" % (trace(stats["tls"].L)*rad2deg2)
        print x.ljust(10),

        print
            


def main(**args):
    prnt_header(args)

    struct = LoadStructure(fil = args["path"])
    tls_analysis = TLSStructureAnalysis(struct)

    best_splits = tls_analysis.brute_force_TLS_segments(
        num_groups          = args["num_groups"],
        min_residue_width   = args["seg_len"],
        use_side_chains     = not args["mainchain_only"],
        include_single_bond = not args["omit_single_bonded"])

    for split_info in best_splits:

        print "=============================================="
        print "DP2 TOTAL: ",split_info["total_DP2"]
        prnt_col_labels()

        for stats in split_info["stats_list"]:
            tls = stats["tls"]

            stats["segment_num"] = split_info["stats_list"].index(stats)

            ## calculate adverage temp factor and anisotropy
            Umean = 0.0
            Amean = 0.0
            for atm in tls:
                Umean += trace(atm.get_U())/3.0
                Amean += atm.calc_anisotropy()

            Umean = Umean / len(tls)
            Amean = Amean / len(tls)

            stats["mean_U"] = Umean
            stats["mean_B"] = Umean * 8.0 * math.pi**2
            stats["mean_A"] = Amean

            prnt_stats(stats)


def usage():
    print "tls_brute.py - A utility to fit TLS groups to anisotropically"
    print "                or isotropically refined protein structures for"
    print "                motion analysis."
    print
    print "DESCRIPTION:"
    print "    Compute a range of TLS tensors by walking the amino"
    print "    acid backbone one residue at a time, spanning a continous"
    print "    sequence segment of a given length.  Each TLS calculation"
    print "    produces one line of output with some interesting statistics."
    print "    Please do not assume this is a scientifically useful"
    print "    thing to do!"
    print
    print "OPTIONS:"
    print "    -n <num_groups>"
    print "        The number of groups to split each chain into."
    print "    -l <length>"
    print "        Set the length, in sequential amino acids, of the"
    print "        minimul length of any TLS segment."
    print "        default is 3."
    print "    -m  Search mainchain atoms only"
    print "    -s  Omit atoms with only one bond"
    print "    -c <chain_id>"
    print "        Only search the given chain."
    print


if __name__ == "__main__":
    import getopt

    try:
        (opts, args) = getopt.getopt(sys.argv[1:], "l:msn:c:dx")
    except getopt.GetoptError:
        usage()
        sys.exit(1)

    ## program defaults
    num_groups         = 2
    seg_len            = 3
    mainchain_only     = False
    omit_single_bonded = False
    chain              = None

    ## read program options
    for (opt, item) in opts:
        if opt=="-l":
            try:
                seg_len = int(item)
            except ValueError:
                usage()
                sys.exit(1)

        if opt=="-m":
            mainchain_only = True

        if opt=="-s":
            omit_single_bonded = True

        if opt=="-n":
            num_groups = int(item)

        if opt=="-c":
            chain = item


    ## make sure a file name was entered
    if len(args)!=1:
        usage()
        sys.exit(1)

    main(path               = args[0],
         num_groups         = num_groups,
         seg_len            = seg_len,
         mainchain_only     = mainchain_only,
         omit_single_bonded = omit_single_bonded,
         chain              = chain)
