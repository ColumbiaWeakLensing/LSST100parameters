#!/usr/bin/env python

import sys
sys.modules["mpi4py"] = None

import argparse,json

from library.featureDB import LSSTSimulationBatch
from library.driver_mpi import cosmo_constraints
from library.defaults import settings

#Command line options
parser = argparse.ArgumentParser()
parser.add_argument("-e","--environment",dest="environment",action="store",default="environment.ini",help="INI file with the batch location")
parser.add_argument("-f","--features",dest="features",action="store",default="combine_default.json",help="JSON file containing the specifications of the features to combine")
parser.add_argument("-v","--verbose",dest="verbose",action="store_true",default=False,help="Turn on verbosity")

#Main
def main():

	#Parse arguments
	cmd_args = parser.parse_args()

	#Init batch
	batch = LSSTSimulationBatch.current(cmd_args.environment)

	#Read json specs and sanitize input
	with open(cmd_args.features,"r") as fp:
		specs = json.load(fp)

	for feature in specs["features"]:
		for l in ["feature_filter","redshift_filter","realization_filter"]:
			if specs[feature][l]=="None":
				specs[feature][l] = None
		
	#Execute
	cosmo_constraints(batch,specs,settings,cmd_args.verbose)


if __name__=="__main__":
	main()

