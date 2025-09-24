"""Land Uses of the NZLUSDB."""

import argparse

import nzlusdb
from nzlusdb.core.landuse import LandUse

nzlusdb.db.register(LandUse(name="manuka", version="1.0"))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run NZLUSDB workflow.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()

    nzlusdb.db["manuka"].run_workflow(resolution=args.res)
