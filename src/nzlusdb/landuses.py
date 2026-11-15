"""Land Uses of the NZLUSDB."""

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
    "-r",
    "--run",
    default="workflow",
    type=click.Choice(["workflow", "lsa", "nir", "stats", "figs", "doc"]),
    help="Type of analysis to run.",
    show_default=True,
)
@click.option(
    "-res",
    "--resolution",
    multiple=True,
    default=("5km", "1km"),
    type=click.Choice(["5km", "1km"]),
    show_default=True,
)
@click.option(
    "-scen",
    "--scenario",
    multiple=True,
    default=("historical", "ssp126", "ssp245", "ssp370", "ssp585"),
    type=click.Choice(["historical", "ssp126", "ssp245", "ssp370", "ssp585"]),
    help="Climate scenario to consider.",
    show_default=True,
)
@click.option("--run-lsa", is_flag=True, help="If 'workflow' is selected, run LSA.")
@click.option(
    "--rerun-lsa", is_flag=True, help="If 'workflow' is selected, rerun LSA even if LSA output files already exist."
)
@click.option("--run-nir", is_flag=True, help="If 'workflow' is selected, run NIR computation.")
@click.option(
    "--rerun-nir",
    is_flag=True,
    help="If 'workflow' is selected, rerun NIR computation even if NIR output files already exist.",
)
@click.option(
    "-od", "--overwrite-doc", is_flag=True, help="If 'doc' is selected, whether to overwrite existing documentation."
)
def cli(landuse, run, resolution, scenario, run_lsa, rerun_lsa, run_nir, rerun_nir, overwrite_doc):
    """Command line interface for NZLUSDB land uses."""
    lu = nzlusdb.db[landuse]

    if run == "workflow":
        click.echo(f"Running workflow for land use: {landuse} at resolution(s): {', '.join(resolution)}")
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
                click.echo(f"Running LSA for land use: {landuse} at resolution: {r}")
                lu.run_lsa(scenario=scenario, rerun=rerun_lsa)
            elif run == "nir":
                click.echo(f"Running NIR computation for land use: {landuse} at resolution: {r}")
                lu.compute_nir(scenario=scenario, recompute=rerun_nir)
            elif run == "stats":
                click.echo(f"Generating stats for land use: {landuse} at resolution: {r}")
                lu.stats_summary()
            elif run == "figs":
                click.echo(f"Generating figures for land use: {landuse} at resolution: {r}")
                lu.summary_figs()
    elif run == "doc":
        click.echo(f"Generating documentation for land use: {landuse}")
        lu.add_to_doc(overwrite=overwrite_doc)


if __name__ == "__main__":
    cli()
