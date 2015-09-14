#!/usr/bin/env python-mpi

import sys

from library.featureDB import FeatureDatabase

from lenstools.pipeline import SimulationBatch
from lenstools.statistics.ensemble import Ensemble
from lenstools.utils.decorators import Parallelize

import numpy as np
import pandas as pd

#Measure the cross spectrum of a list of convergence maps
def cross_power(maps,ell_edges,indices):

	"""

	:param maps: list of convergence maps (one for each redshift bin)
	:type maps: list.
		
	:param ell_edges: multipoles
	:type ell_edges: array

	:param indices: pairs of indices; each pair corresponds to a pair of redshift bins to cross correlate
	:type indices: list of tuples

	:returns: Ensemble

	"""

	#Allocate memory
	cross_power_array = np.zeros((len(indices),len(ell_edges)-1))
		
	#Measure the auto and cross power spectrum
	for n,(i,j) in enumerate(indices):
		ell,cross_power_array[n] = maps[i].cross(maps[j],statistic="power_spectrum",l_edges=ell_edges)

	#Build the Ensemble
	columns = [ "l{0}".format(n) for n in range(1,len(ell)+1) ]
	ensemble = Ensemble(cross_power_array,columns=columns)

	#Add the indices labels
	ensemble["b1"],ensemble["b2"] = zip(*indices)

	#Return
	return ensemble


#Main execution
@Parallelize.masterworker
def main(pool):

	#Handle on the current batch
	batch = SimulationBatch.current()

	#Cross power spectrum database
	db = FeatureDatabase("../data/cross_spectra.sqlite")

	#Process these models
	models = batch.models

	#Use these bin edges and cross bins
	ell_edges = pd.read_pickle("../data/edges.pkl")["ell_edges"].values
	indices = zip(*np.triu_indices(db.map_specs["nzbins"]))

	#Execute
	for n,model in enumerate(models):
		for s,sc in enumerate(model.getCollection("512b260").getCatalog("Shear").subcatalogs):
			print("[+] Measuring cross spectrum in model {0}, sub-catalog {1}...".format(n+1,s+1))
			db.add_features("features",sc,measurer=cross_power,extra_columns={"model":n+1,"sub_catalog":s+1},pool=pool,ell_edges=ell_edges,indices=indices)


if __name__=="__main__":
	main(None)