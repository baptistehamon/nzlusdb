"""Land Uses of the NZLUSDB."""

import argparse
import sys

import click

import nzlusdb
from nzlusdb.core.landuse import LandUse

nzlusdb.db.register(LandUse(name="apple", version="1.0"))
nzlusdb.db.register(LandUse(name="avocado", version="1.0"))
nzlusdb.db.register(LandUse(name="blueberry", version="1.0"))
nzlusdb.db.register(LandUse(name="cherry", version="1.0"))
nzlusdb.db.register(LandUse(name="citrus", version="1.0"))
nzlusdb.db.register(LandUse(name="hops", version="1.0"))
nzlusdb.db.register(LandUse(name="kiwifruit", version="1.0"))
nzlusdb.db.register(LandUse(name="maizeearly", long_name="Early ripening maize", version="1.0"))
nzlusdb.db.register(LandUse(name="maizelate", long_name="Late ripening maize", version="1.0"))
# Maize used only for NIR as same parameters as Early ripening maize and Late ripening maize
nzlusdb.db.register(LandUse(name="maize", version="1.0"))
nzlusdb.db.register(LandUse(name="manuka", version="1.0"))
nzlusdb.db.register(LandUse(name="pinotnoir", long_name="Pinot noir", version="1.0"))
nzlusdb.db.register(LandUse(name="sauvignonblanc", long_name="Sauvignon blanc", version="1.0"))
# Grapevines used only for NIR as same parameters as Pinot noir and Sauvignon blanc
nzlusdb.db.register(LandUse(name="grapevines", version="1.0"))
nzlusdb.db.register(LandUse(name="wheatearly", long_name="Early ripening wheat", version="1.0"))
nzlusdb.db.register(LandUse(name="wheatlate", long_name="Late ripening wheat", version="1.0"))
# Wheat used only for NIR as same parameters as Early ripening wheat and Late ripening wheat
nzlusdb.db.register(LandUse(name="wheat", version="1.0"))

@click.command()
@click.argument("landuse", type=click.Choice(list(nzlusdb.db._lu_names)))
@click.option(
    "-r", "--run",
    default="workflow",
    type=click.Choice(["workflow", "lsa", "nir", "stats", "figs", "doc"]),
    help="Type of analysis to run.",
    show_default=True,
)
@click.option(
    "-res", "--resolution",
    multiple=True,
    default=("5km", "1km"),
    type=click.Choice(["5km", "1km"]),
    show_default=True,
)
@click.option(
    "-scen", "--scenario",
    multiple=True,
    default=("historical", "ssp126", "ssp245", "ssp370", "ssp585"),
    type=click.Choice(["historical", "ssp126", "ssp245", "ssp370", "ssp585"]),
    help="Climate scenario to consider.",
    show_default=True,
)
@click.option(
    "--run-lsa",
    is_flag=True,
    default=False,
    help="If 'workflow' is selected, whether to run LSA.",
    show_default=True,
)
@click.option(
    "--rerun-lsa",
    is_flag=True,
    default=False,
    help="If 'workflow' is selected, whether to rerun LSA even if LSA output files already exist.",
    show_default=True,
)
@click.option(
    "--run-nir",
    is_flag=True,
    default=False,
    help="If 'workflow' is selected, whether to run NIR computation.",
    show_default=True,
)
@click.option(
    "--rerun-nir",
    is_flag=True,
    default=False,
    help="If 'workflow' is selected, whether to rerun NIR computation even if NIR output files already exist.",
    show_default=True,
)
@click.option(
    "-od", "--overwrite-doc",
    is_flag=True,
    default=False,
    help="If 'doc' is selected, whether to overwrite existing documentation.",
    show_default=True,
)
def cli(landuse, run, resolution, scenario, run_lsa, rerun_lsa, run_nir, rerun_nir, overwrite_doc):
    """Command line interface for NZLUSDB land uses."""

    lu = nzlusdb.db[landuse]

    if run == "workflow":
        print(f"Running workflow for land use: {landuse} at resolution(s): {', '.join(resolution)}")
        lu.run_workflow(
            resolution=resolution,
            lsa=run_lsa,
            rerun_lsa=rerun_lsa,
            nir=run_nir,
            rerun_nir=rerun_nir,
        )
    elif run in ["lsa", "nir", "stats", "figs"]:
        for r in resolution:
            lu.resolution = r
            if run == "lsa":
                print(f"Running LSA for land use: {landuse} at resolution: {r}")
                lu.run_lsa(scenario=scenario, rerun=rerun_lsa)
            elif run == "nir":
                print(f"Running NIR computation for land use: {landuse} at resolution: {r}")
                lu.compute_nir(scenario=scenario, recompute=rerun_nir)
            elif run == "stats":
                print(f"Generating stats for land use: {landuse} at resolution: {r}")
                lu.stats_summary()
            elif run == "figs":
                print(f"Generating figures for land use: {landuse} at resolution: {r}")
                lu.summary_figs()
    elif run == "doc":
        print(f"Generating documentation for land use: {landuse}")
        lu.add_to_doc(overwrite=overwrite_doc)


if __name__ == "__main__":
    cli()

    # parser = argparse.ArgumentParser(description="Run NZLUSDB workflow for a given land use")
    # parser.add_argument("-l", "--list", action="store_true", help="List available land uses")
    # parser.add_argument(
    #     "landuse",
    #     nargs="?",
    #     choices=list(nzlusdb.db._lu_names),
    #     help="Land use",
    # )
    # parser.add_argument(
    #     "-r",
    #     "--run",
    #     default="workflow",
    #     choices=["workflow", "lsa", "nir", "stats", "figs", "doc"],
    #     help="Method to run",
    # )
    # parser.add_argument(
    #     "-res", "--resolution", nargs="+", default=["5km", "1km"], choices=["5km", "1km"], help="Resolution(s)"
    # )
    # parser.add_argument(
    #     "-scen",
    #     "--scenario",
    #     nargs="?",
    #     choices=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
    #     default=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
    #     help="Climate scenario (for LSA)",
    # )
    # parser.add_argument(
    #     "--run-lsa",
    #     action="store_true",
    #     default=False,
    #     help="Whether to run LSA in workflow mode (default: False).",
    # )
    # parser.add_argument(
    #     "--rerun-lsa",
    #     action="store_true",
    #     default=False,
    #     help="Whether to rerun LSA even if LSA output files already exist.",
    # )
    # parser.add_argument(
    #     "--run-nir",
    #     action="store_true",
    #     default=False,
    #     help="Whether to run NIR computation in workflow mode (default: False).",
    # )
    # parser.add_argument(
    #     "--rerun-nir",
    #     action="store_true",
    #     default=False,
    #     help="Whether to rerun NIR computation even if NIR output files already exist.",
    # )
    # parser.add_argument(
    #     "-o",
    #     "--overwrite",
    #     action="store_true",
    #     default=False,
    #     help="Overwrite existing documentation",
    # )
    # args = parser.parse_args()

    # if args.list:
    #     print("Available land uses:")
    #     for lu_name in nzlusdb.db._lu_names:
    #         print(f" - {lu_name}")
    #     sys.exit(0)

    # if not args.landuse:
    #     print("Error: Please specify a land use or use --list to see available land uses.")
    #     sys.exit(1)

    # if args.run == "workflow":
    #     print(f"Running workflow for land use: {args.landuse} at resolution(s): {', '.join(args.resolution)}")
    #     nzlusdb.db[args.landuse].run_workflow(
    #         resolution=args.resolution,
    #         lsa=args.run_lsa,
    #         rerun_lsa=args.rerun_lsa,
    #         nir=args.run_nir,
    #         rerun_nir=args.rerun_nir,
    #     )
    #     sys.exit(0)

    # if args.run in ["lsa", "nir", "stats", "figs"]:
    #     if isinstance(args.resolution, str):
    #         res = [args.resolution]
    #     for r in args.resolution:
    #         nzlusdb.db[args.landuse].resolution = r
    #         if args.run == "lsa":
    #             print(f"Running LSA for land use: {args.landuse} at resolution: {r}")
    #             nzlusdb.db[args.landuse].run_lsa(scenario=args.scenario, rerun=args.rerun_lsa)
    #         if args.run == "nir":
    #             print(f"Running NIR computation for land use: {args.landuse} at resolution: {r}")
    #             nzlusdb.db[args.landuse].compute_nir(scenario=args.scenario, recompute=args.rerun_nir)
    #         if args.run == "stats":
    #             print(f"Generating stats for land use: {args.landuse} at resolution: {r}")
    #             nzlusdb.db[args.landuse].stats_summary()
    #         elif args.run == "figs":
    #             print(f"Generating figures for land use: {args.landuse} at resolution: {r}")
    #             nzlusdb.db[args.landuse].summary_figs()
    #     sys.exit(0)

    # if isinstance(args.resolution, list):
    #     nzlusdb.db[args.landuse].resolution = args.resolution[0]
    # else:
    #     nzlusdb.db[args.landuse].resolution = args.resolution

    # if args.run == "doc":
    #     print("Generating documentation...")
    #     nzlusdb.db[args.landuse].add_to_doc(overwrite=args.overwrite)
    #     sys.exit(0)
