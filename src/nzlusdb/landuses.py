"""Land Uses of the NZLUSDB."""

import argparse
import sys

import nzlusdb
from nzlusdb.core.landuse import LandUse

nzlusdb.db.register(LandUse(name="apple", version="1.0"))
nzlusdb.db.register(LandUse(name="citrus", version="1.0"))
nzlusdb.db.register(LandUse(name="manuka", version="1.0"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NZLUSDB workflow for a given land use")
    parser.add_argument("-l", "--list", action="store_true", help="List available land uses")
    parser.add_argument(
        "landuse",
        nargs="?",
        choices=list(nzlusdb.db._lu_names),
        help="Land use",
    )
    parser.add_argument(
        "-r",
        "--run",
        default="workflow",
        choices=["workflow", "lsa", "stats", "figs", "doc"],
        help="Method to run",
    )
    parser.add_argument(
        "-res", "--resolution", nargs="+", default=["5km", "1km"], choices=["5km", "1km"], help="Resolution(s)"
    )
    parser.add_argument(
        "-scen",
        "--scenario",
        nargs="?",
        choices=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        default=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        help="Climate scenario (for LSA)",
    )
    parser.add_argument(
        "-lsa-m",
        "--lsa-method",
        nargs="?",
        default="mean",
        choices=["mean", "wmean", "gmean", "wgmean", "median", "limfactor"],
        help="LSA aggregation method",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing documentation",
    )
    args = parser.parse_args()

    if args.list:
        print("Available land uses:")
        for lu_name in nzlusdb.db._lu_names:
            print(f" - {lu_name}")
        sys.exit(0)

    if not args.landuse:
        print("Error: Please specify a land use or use --list to see available land uses.")
        sys.exit(1)

    if args.run == "workflow":
        print(f"Running workflow for land use: {args.landuse} at resolution(s): {', '.join(args.resolution)}")
        nzlusdb.db[args.landuse].run_workflow(resolution=args.resolution)
        sys.exit(0)

    if args.run in ["lsa", "stats", "figs"]:
        if isinstance(args.resolution, str):
            res = [args.resolution]
        for r in args.resolution:
            nzlusdb.db[args.landuse].resolution = r
            if args.run == "lsa":
                print(f"Running LSA for land use: {args.landuse} at resolution: {r}")
                nzlusdb.db[args.landuse].run_lsa(scenario=args.scenario, agg_methods=args.lsa_method)
            if args.run == "stats":
                print(f"Generating stats for land use: {args.landuse} at resolution: {r}")
                nzlusdb.db[args.landuse].stats_summary()
            elif args.run == "figs":
                print(f"Generating figures for land use: {args.landuse} at resolution: {r}")
                nzlusdb.db[args.landuse].summary_figs()
        sys.exit(0)

    if isinstance(args.resolution, list):
        nzlusdb.db[args.landuse].resolution = args.resolution[0]
    else:
        nzlusdb.db[args.landuse].resolution = args.resolution

    if args.run == "doc":
        print("Generating documentation...")
        nzlusdb.db[args.landuse].add_to_doc(overwrite=args.overwrite)
        sys.exit(0)
