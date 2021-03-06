#!/usr/bin/env python
from __future__ import division

import sys,os,argparse
sys.modules["mpi4py"] = None

import itertools

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from lenstools.catalog.shear import Catalog

from lenstools.statistics.ensemble import SquareMatrix
from lenstools.statistics.constraints import FisherAnalysis
from lenstools.simulations.design import Design

from library.featureDB import FisherDatabase

#Options
parser = argparse.ArgumentParser()
parser.add_argument("-t","--type",dest="type",default="png",help="format of the figure to save")
parser.add_argument("fig",nargs="*")

#Plot labels
par2label = {

"Om" : r"$\Omega_m$" ,
"w" : r"$w$" ,
"sigma8" : r"$\sigma_8$"

}

#Fiducial value
par2value = {

"Om" : 0.26 ,
"w" : -1. ,
"sigma8" : 0.8

}

###################################################################################################
###################################################################################################

def design(cmd_args,fontsize=22):

	#Set up plot
	fig,ax = plt.subplots(1,3,figsize=(24,8))

	#Read in the simulation design
	design = Design.read("md/design.pkl")
	parameters = [("Om","w"),("Om","sigma8"),("sigma8","w")]

	#Plot the points
	for n,(p1,p2) in enumerate(parameters):
		ax[n].scatter(design[p1],design[p2],marker="x")
		ax[n].scatter(par2value[p1],par2value[p2],marker="x",color="red",s=50)
		ax[n].set_xlabel(par2label[p1],fontsize=fontsize)
		ax[n].set_ylabel(par2label[p2],fontsize=fontsize)

	#Save figure
	fig.savefig("design."+cmd_args.type)

###################################################################################################
###################################################################################################

def galdistr(cmd_args,fontsize=22):

	#Set up plot
	fig,ax = plt.subplots()

	#Read in galaxy redshifts
	colors = ["blue","green","red","purple","yellow"]
	position_files = [os.path.join("data","positions_bin{0}.fits".format(n)) for n in range(1,6)]
	for n,f in enumerate(position_files):
		z = Catalog.read(f)["z"]

		#Make the histogram
		ng,zb = np.histogram(z,bins=np.arange(z.min(),z.max(),0.02))
		ax.plot(0.5*(zb[1:]+zb[:-1]),ng,color=colors[n],label=r"$z\in[{0:.2f},{1:.2f}]$".format(z.min(),z.max()))
		ax.fill_between(0.5*(zb[1:]+zb[:-1]),np.zeros_like(ng),ng,color=colors[n],alpha=0.3)

	#Labels
	ax.set_xlabel(r"$z$",fontsize=fontsize)
	ax.set_ylabel(r"$N_g(z)$",fontsize=fontsize)
	ax.legend()

	#Ticks
	ax.tick_params(axis="both",which="major",labelsize=fontsize)

	#Save figure
	fig.savefig("galdistr."+cmd_args.type)

###################################################################################################
###################################################################################################

def scibook_photo(cmd_args,fontsize=22):

	#Set up plot
	fig,ax = plt.subplots()

	#Read in bias and sigma
	z,b = np.loadtxt("data/photoz/SciBook_bias_gold.out",unpack=True)
	z,s = np.loadtxt("data/photoz/SciBook_sigma_gold.out",unpack=True)

	#Plot
	ax.plot(z,b,label=r"$b_{\rm ph}(z_s)$ ${\rm optimistic}$",color="black")
	ax.plot(z,s,label=r"$\sigma_{\rm ph}(z_s)$ ${\rm optimistic}$",color="red")

	#Read in bias and sigma
	z,b = np.loadtxt("data/photoz/weightcombo_bias_gold.out",unpack=True)
	z,s = np.loadtxt("data/photoz/weightcombo_sigma_gold.out",unpack=True)

	#Plot
	ax.plot(z,b,label=r"$b_{\rm ph}(z_s)$ ${\rm pessimistic}$",color="black",linestyle="--")
	ax.plot(z,s,label=r"$\sigma_{\rm ph}(z_s)$ ${\rm pessimistic}$",color="red",linestyle="--")

	ax.plot(z,0.003*(1+z),label=r"$b_{\rm ph}(z_s)=0.003(1+z_s)$",color="blue",linestyle="-",linewidth=3)
	ax.plot(z,0.02*(1+z),label=r"$\sigma_{\rm ph}(z_s)=0.02(1+z_s)$",color="blue",linestyle="--",linewidth=3)

	#Labels
	ax.set_xlabel(r"$z_s$",fontsize=fontsize)
	ax.legend(loc="upper left")

	#Save figure
	fig.savefig("scibook."+cmd_args.type)


###################################################################################################
###################################################################################################

def constraints_no_pca(cmd_args,db_name="data/fisher/constraints_combine.sqlite",feature="power_spectrum",base_color="black",tomo_color="magenta",pca_components=[5,10],colors=["red","blue","green"],parameter="w",ylim=None,fontsize=22):

	#Set up plot
	fig,ax = plt.subplots()

	#Axes bounds
	if ylim is not None:
		ax.set_ylim(*ylim)

	#Construct title
	title = r"${\rm " + feature.replace("_","\,\,") + r"}$"

	#Plot each feature 
	with FisherDatabase(db_name) as db:
		
		#Query parameter variance
		var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise_no_pca'.format(parameter))

		#Plot feature without PCA
		var_feature = var_db[var_db["feature_label"].str.contains(feature)]["{0}-{0}".format(parameter)].values
		var_highest_z = var_feature[-1]
		ax.bar(range(len(var_feature)),np.sqrt(var_feature),width=1,fill=False,edgecolor=base_color,label=r"${\rm No}$ ${\rm PCA}$",alpha=0.3)

		#Plot features with PCA
		for n,nc in enumerate(pca_components):
			var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise WHERE bins={1}'.format(parameter,nc))
			var_feature = var_db[var_db["feature_label"].str.contains(feature+"_pca_z")]["{0}-{0}".format(parameter)].values
			ax.bar(range(len(var_feature)),np.sqrt(var_feature),width=1,fill=False,edgecolor=colors[n],label=r"$N_c={0}$".format(nc))

		#Plot tomographic constraint with the maximum number of pca components
		var_db = db.query('SELECT "{0}-{0}",bins,feature_label FROM pcov_noise'.format(parameter))
		var_feature_tomo,nc,label = var_db.query("feature_label=='{0}'".format(feature+"_pca")).tail(1).values.flat
		ax.bar(5,np.sqrt(var_feature_tomo),width=1,fill=False,edgecolor=tomo_color,label=r"$N_c={0}$".format(int(nc)))

		#Put a percent value on the last bar of the graph
		#ax.text(5.5,np.sqrt(var_highest_z),r"$-{0}\%$".format(int(100*(np.sqrt(var_highest_z/var_feature_tomo)-1))),fontsize=fontsize)

	#Axes labels
	xticks = np.arange(len(var_feature)+1)+0.5
	ax.set_xticks(xticks)
	ax.set_xticklabels([r"$\bar{z}_" + str(n+1) + r"$" for n in range(len(var_feature))] + [r"${\rm Tomo}$"],fontsize=fontsize)
	ax.set_ylabel(r"$\Delta$"+par2label[parameter],fontsize=fontsize)
	ax.legend(prop={"size":25})

	#Title
	ax.set_title(title,fontsize=30)

	#Save the figure
	fig.savefig("{0}_{1}_no_pca.{2}".format(parameter,feature,cmd_args.type))

def constraints_no_pca_power(cmd_args):
	constraints_no_pca(cmd_args,feature="power_spectrum",pca_components=[5,10])

def constraints_no_pca_peaks(cmd_args):
	constraints_no_pca(cmd_args,feature="peaks",pca_components=[12,24,27])

def constraints_no_pca_moments(cmd_args):
	constraints_no_pca(cmd_args,feature="moments",pca_components=[7,9])

###################################################################################################
###################################################################################################

#Comparison with NICAEA
def sims_vs_nicaea(cmd_args,db_name="data/fisher/constraints_combine.sqlite",feature="power_spectrum",parameter="w",ylim=None,fontsize=22):

	#Set up plot
	fig,ax = plt.subplots()

	#Axes bounds
	if ylim is not None:
		ax.set_ylim(*ylim)

	#Plot the power spectrum 
	with FisherDatabase(db_name) as db:
		
		#Query parameter variance obtained with the simulations
		var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise_no_pca'.format(parameter))
		var_feature = var_db[var_db["feature_label"].str.contains(feature)]["{0}-{0}".format(parameter)].values
		ax.bar(range(len(var_feature)),np.sqrt(var_feature),width=1,fill=False,edgecolor="black",label=r"${\rm No}$ ${\rm PCA}$",alpha=0.3)

		#Overlay the results obtained with PCA
		var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise WHERE bins=10'.format(parameter))
		var_feature = var_db[var_db["feature_label"].str.contains(feature+"_pca_z")]["{0}-{0}".format(parameter)].values
		ax.bar(range(len(var_feature)),np.sqrt(var_feature),width=1,fill=False,edgecolor="red",label=r"$N_c=10$")

		var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise WHERE bins=70'.format(parameter))
		var_feature = var_db[var_db["feature_label"].str.contains(feature+"_pca")]["{0}-{0}".format(parameter)].values
		ax.bar(5,np.sqrt(var_feature),width=1,fill=False,edgecolor="magenta",label=r"$N_c=70$")

		#Query parameter variance obtained with NICAEA
		var_db = db.query('SELECT "{0}-{0}",feature_label FROM pcov_noise_nicaea'.format(parameter))
		var_feature = var_db[var_db["feature_label"].str.contains(feature)]["{0}-{0}".format(parameter)].values
		ax.bar(range(len(var_feature)),np.sqrt(var_feature),width=1,fill=False,edgecolor="black",linestyle="--",label=r"${\rm NICAEA}$")


	#Axes labels
	xticks = np.arange(len(var_feature))+0.5
	ax.set_xticks(xticks)
	ax.set_xticklabels([r"$\bar{z}_" + str(n+1) + r"$" for n in range(len(var_feature)-1)] + [r"${\rm Tomo}$"],fontsize=fontsize)
	ax.set_ylabel(r"$\Delta$"+par2label[parameter],fontsize=fontsize)
	ax.set_title(r"${\rm power}$ ${\rm spectrum}$",fontsize=30)
	ax.legend(prop={"size":25})

	#Save the figure
	fig.savefig("{0}_{1}_no_pca.{2}".format(parameter,feature,cmd_args.type))

###################################################################################################
###################################################################################################

def pca_components(cmd_args,db_name="data/fisher/constraints_combine.sqlite",feature_label="power_spectrum_pca",parameter="w",fontsize=22):

	#Use automatic plot routine
	with FisherDatabase(db_name) as db:
		fig,axes = db.plot_by_feature([feature_label],table_name="pcov_noise",parameter="w")

	#Labels
	axes[0].set_ylabel(r"$\Delta$"+par2label[parameter],fontsize=fontsize)

	#Ticks
	axes[0].tick_params(axis="both",which="major",labelsize=fontsize)

	#Save figure
	fig.savefig("{0}_{1}.".format(parameter,feature_label)+cmd_args.type)

def pca_components_power_spectrum(cmd_args):
	pca_components(cmd_args,feature_label="power_spectrum_pca")

def pca_components_peaks(cmd_args):
	pca_components(cmd_args,feature_label="peaks_pca")

def pca_components_moments(cmd_args):
	pca_components(cmd_args,feature_label="moments_pca")

###################################################################################################
###################################################################################################

feature_properties = {

"ps" : {"name":"power_spectrum_pca","table_name" : "pcov_noise", "pca_components" : 30, "color" : "red", "label" : r"$P^{\kappa\kappa}(N_c=30)$","linestyle" : "--", "marker" : "x"},
"ps70" : {"name":"power_spectrum_pca","table_name" : "pcov_noise", "pca_components" : 70, "color" : "red", "label" : r"$P^{\kappa\kappa}(N_c=70)$","linestyle" : "-", "marker" : "+"},

"mu" : {"name":"moments_pca","table_name" : "pcov_noise", "pca_components" : 30, "color" : "blue", "label" : r"$\mathbf{\mu}(N_c=30)$","linestyle" : "--", "marker" : "x"},
"mu40" : {"name":"moments_pca","table_name" : "pcov_noise", "pca_components" : 40, "color" : "blue", "label" : r"$\mathbf{\mu}(N_c=40)$","linestyle" : "-", "marker" : "+"},

"pk" : {"name":"peaks_pca", "table_name": "pcov_noise", "pca_components" : 40, "color" : "green", "label" : r"$n_{\rm pk}(N_c=40)$","linestyle" : "--", "marker" : "x"},
"pk70" : {"name":"peaks_pca", "table_name": "pcov_noise", "pca_components" : 70, "color" : "green", "label" : r"$n_{\rm pk}(N_c=70)$","linestyle" : "-", "marker" : "+"},

"ps+pk" : {"name" : "power_spectrum+peaks" , "table_name" : "pcov_noise_combine", "pca_components" : 30+40, "color" : "orange", "label" : r"$P^{\kappa\kappa}(N_c=30)+n_{\rm pk}(N_c=40)$","linestyle" : "-", "marker" : "x"},
"ps+mu" : {"name" : "power_spectrum+moments" , "table_name" : "pcov_noise_combine", "pca_components" : 30+30, "color" : "purple", "label" : r"$P^{\kappa\kappa}(N_c=30)+\mathbf{\mu}(N_c=30)$","linestyle" : "-", "marker" : "x"},
"ps+pk+mu" : {"name" : "power_spectrum+peaks+moments" , "table_name" : "pcov_noise_combine", "pca_components" : 30+30+40, "color" : "black", "label" : r"$P^{\kappa\kappa}(N_c=30)+n_{\rm pk}(N_c=40)+\mathbf{\mu}(N_c=30)$","linestyle" : "-", "marker" : "x"}

}

def parameter_constraints(cmd_args,db_name="data/fisher/constraints_combine.sqlite",features_to_show=["ps","ps70","pk","pk70","mu","mu40","ps+pk","ps+mu","ps+pk+mu"],parameters=["Om","w"],all_parameters=["Om","w","sigma8"],xlim=(0.252,0.267),ylim=(-1.04,-0.96),cmb_prior_fisher=None,suffix="lensing",fontsize=22):

	#Init figure
	fig,ax = plt.subplots()
	ellipses = list()
	labels = list()

	#CMB prior
	if cmb_prior_fisher is not None:
		fisher_cmb = SquareMatrix.read(cmb_prior_fisher)[all_parameters]

	#Plot the features 
	with FisherDatabase(db_name) as db:
		for f in features_to_show:

			#Query parameter covariance
			pcov = db.query_parameter_covariance(feature_properties[f]["name"],nbins=feature_properties[f]["pca_components"],table_name=feature_properties[f]["table_name"],parameters=parameters)

			#Show the ellipse
			center = (par2value[parameters[0]],par2value[parameters[1]])
			ellipse = FisherAnalysis.ellipse(center=center,covariance=pcov.values,p_value=0.677,fill=False,edgecolor=feature_properties[f]["color"],linestyle=feature_properties[f]["linestyle"])
			ax.add_artist(ellipse)

			#Labels
			ellipses.append(ellipse)
			labels.append(feature_properties[f]["label"])

			#If there is a CMB prior to include, add the fisher matrices
			if cmb_prior_fisher is not None:

				#Fisher matrix addition in quadrature
				pcov_lensing = db.query_parameter_covariance(feature_properties[f]["name"],nbins=feature_properties[f]["pca_components"],table_name=feature_properties[f]["table_name"],parameters=all_parameters)
				pcov_lensing_cmb = (pcov_lensing.invert() + fisher_cmb).invert()[parameters]

				#Add additional ellipses for the constraints with prior
				ax.add_artist(FisherAnalysis.ellipse(center=center,covariance=pcov_lensing_cmb.values,p_value=0.677,fill=False,edgecolor=feature_properties[f]["color"],linestyle=feature_properties[f]["linestyle"],linewidth=4))

	#Plot the CMB ellipse too
	#if cmb_prior_fisher is not None:
		#ax.add_artist(FisherAnalysis.ellipse(center=center,covariance=fisher_cmb.invert()[parameters].values,p_value=0.677,color="black",alpha=0.3))

	#Axes bounds
	ax.set_xlim(*xlim)
	ax.set_ylim(*ylim)

	#Axes labels and legend
	ax.set_xlabel(par2label[parameters[0]],fontsize=fontsize)
	ax.set_ylabel(par2label[parameters[1]],fontsize=fontsize)
	ax.legend(ellipses,labels,prop={"size" : 20},bbox_to_anchor=(0.,1.02,1.,.102),loc=3,ncol=len(features_to_show)//4,mode="expand",borderaxespad=0.)

	#Save figure
	fig.savefig("constraints_{0}_{1}.{2}".format("-".join(parameters),suffix,cmd_args.type))


def parameter_constraints_with_cmb(cmd_args):
	parameter_constraints(cmd_args,features_to_show=["ps70","pk70","mu40","ps+pk","ps+mu","ps+pk+mu"],cmb_prior_fisher="data/planck/planck_base_w_TT_lowTEB.pkl",suffix="lensing_cmb")

###################################################################################################
###################################################################################################

def photoz_bias(cmd_args,db_name="data/fisher/constraints_photoz.sqlite",parameters=["Om","w"],features_to_show=["ps","ps70","pk","pk70","mu","mu40"],fontsize=22):
	
	#Init figure
	fig,ax = plt.subplots()

	#Ellipses and labels
	ellipses = list()
	labels = list()

	#Cycle over features
	for f in features_to_show:

		#Feature properties
		feature_label = feature_properties[f]["name"]
		nbins = feature_properties[f]["pca_components"]
		color = feature_properties[f]["color"]
		plot_label = feature_properties[f]["label"]
		marker = feature_properties[f]["marker"]
		linestyle = feature_properties[f]["linestyle"]

		############
		#No photo-z#
		############

		with FisherDatabase(db_name) as db:
			pfit = db.query_parameter_fit(feature_label,table_name="mocks_without_photoz",parameters=parameters).query("bins=={0}".format(nbins))
			p1f,p2f = [ pfit[parameters[n]+"_fit"].values for n in [0,1] ]

		############################
		#With photo-z: requirements#
		############################

		with FisherDatabase(db_name) as db:
			pfit = db.query_parameter_fit(feature_label,table_name="mocks_photoz_requirement",parameters=parameters).query("bins=={0}".format(nbins))
			p1,p2 = [ pfit[parameters[n]+"_fit"].values for n in [0,1] ]
			ax.scatter(p1-p1f,p2-p2f,color=color,marker=marker)
			ax.scatter((p1-p1f).mean(),(p2-p2f).mean(),color=color,marker="s",s=60)

			#Draw an error ellipse around the mean bias
			center = ((p1-p1f).mean(),(p2-p2f).mean())
			pcov = np.cov([p1-p1f,p2-p2f]) 
			ellipses.append(FisherAnalysis.ellipse(center,pcov,p_value=0.677,fill=False,edgecolor=color,linestyle=linestyle))
			ax.add_artist(ellipses[-1])
			labels.append(plot_label)

	#Get axes bounds
	xlim = np.abs(np.array(ax.get_xlim())).max()
	ylim = np.abs(np.array(ax.get_ylim())).max()

	#Show the fiducial value
	ax.plot(np.zeros(100),np.linspace(-ylim,ylim,100),linestyle="--",color="black")
	ax.plot(np.linspace(-xlim,xlim,100),np.zeros(100),linestyle="--",color="black")

	#Set the axes bounds
	ax.set_xlim(-xlim,xlim)
	ax.set_ylim(-ylim,ylim)

	#Legends
	ax.set_xlabel(r"$\delta$" + par2label[parameters[0]],fontsize=fontsize)
	ax.set_ylabel(r"$\delta$" + par2label[parameters[1]],fontsize=fontsize)
	ax.legend(ellipses,labels,loc="upper right",prop={"size":25})

	#Save figure
	fig.savefig("photoz_bias_{0}.{1}".format("-".join(parameters),cmd_args.type))

###################################################################################################
###################################################################################################

def bias_vs_sigma(cmd_args,db_name="data/fisher/constraints_photoz.sqlite",parameters=["Om","w"],features_to_show=["ps70","pk70","mu40"],fontsize=22):

	#Init figure
	fig,ax = plt.subplots()
	ellipses = list()
	labels = list()

	#Cycle over features
	for f in features_to_show:

		#Feature properties
		feature_label = feature_properties[f]["name"]
		nbins = feature_properties[f]["pca_components"]
		color = feature_properties[f]["color"]
		plot_label = feature_properties[f]["label"]
		marker = feature_properties[f]["marker"]

		############
		#No photo-z#
		############

		with FisherDatabase(db_name) as db:
			pfit = db.query_parameter_fit(feature_label,table_name="mocks_without_photoz",parameters=parameters).query("bins=={0}".format(nbins))
			p1f,p2f = [ pfit[parameters[n]+"_fit"].values for n in [0,1] ]

		###########################
		#With photo-z: (bias only)#
		###########################

		with FisherDatabase(db_name) as db:
			pfit = db.query_parameter_fit(feature_label,table_name="mocks_photoz_requirement_bias",parameters=parameters).query("bins=={0}".format(nbins))
			p1,p2 = [ pfit[parameters[n]+"_fit"].values for n in [0,1] ]
			ax.scatter((p1-p1f).mean(),(p2-p2f).mean(),color=color,marker="s",s=60)

			#Draw an error ellipse around the mean bias
			center = ((p1-p1f).mean(),(p2-p2f).mean())
			pcov = np.cov([p1-p1f,p2-p2f]) 
			ellipses.append(FisherAnalysis.ellipse(center,pcov,p_value=0.677,fill=False,edgecolor=color,linestyle="-"))
			labels.append(feature_properties[f]["label"] + r"$({\rm bias})$")
			ax.add_artist(ellipses[-1])

		############################
		#With photo-z: (sigma only)#
		############################

		with FisherDatabase(db_name) as db:
			pfit = db.query_parameter_fit(feature_label,table_name="mocks_photoz_requirement_sigma",parameters=parameters).query("bins=={0}".format(nbins))
			p1,p2 = [ pfit[parameters[n]+"_fit"].values for n in [0,1] ]
			ax.scatter((p1-p1f).mean(),(p2-p2f).mean(),color=color,marker="x",s=60)

			#Draw an error ellipse around the mean bias
			center = ((p1-p1f).mean(),(p2-p2f).mean())
			pcov = np.cov([p1-p1f,p2-p2f]) 
			ellipses.append(FisherAnalysis.ellipse(center,pcov,p_value=0.677,fill=False,edgecolor=color,linestyle="--"))
			labels.append(feature_properties[f]["label"] + r"$(\sigma)$")
			ax.add_artist(ellipses[-1])

	#Get axes bounds
	xlim = np.abs(np.array(ax.get_xlim())).max()
	ylim = np.abs(np.array(ax.get_ylim())).max()

	#Show the fiducial value
	ax.plot(np.zeros(100),np.linspace(-ylim,ylim,100),linestyle="--",color="black")
	ax.plot(np.linspace(-xlim,xlim,100),np.zeros(100),linestyle="--",color="black")

	#Set the axes bounds
	ax.set_xlim(-xlim,xlim)
	ax.set_ylim(-ylim,ylim)

	#Legends
	ax.set_xlabel(r"$\delta$" + par2label[parameters[0]],fontsize=fontsize)
	ax.set_ylabel(r"$\delta$" + par2label[parameters[1]],fontsize=fontsize)
	ax.legend(ellipses,labels,loc="upper right",prop={"size":15})

	#Save figure
	fig.savefig("bias_vs_sigma_{0}.{1}".format("-".join(parameters),cmd_args.type))


###################################################################################################
###################################################################################################

rows = {

"ps5" : {"name" : "power_spectrum_pca_z4" , "table_name" : "pcov_noise" ,"bins" : 14 , "label" : r"Power spectrum ($\bar{z}_5$)"},
"ps-tomo" : {"name" : "power_spectrum_pca" , "table_name" : "pcov_noise" , "bins" : 70 , "label" : "Power spectrum (tomo)"},
"peaks5" : {"name" : "peaks_pca_z4" , "table_name" : "pcov_noise" , "bins" : 27 , "label" : r"Peaks ($\bar{z}_5$)"},
"peaks-tomo" : {"name" : "peaks_pca" , "table_name" : "pcov_noise" , "bins" : 70 , "label" : "Peaks (tomo)"},
"moments5" : {"name" : "moments_pca_z4" , "table_name" : "pcov_noise" , "bins" : 9 , "label" : r"Moments ($\bar{z}_5$)"},
"moments-tomo" : {"name" : "moments_pca" , "table_name" : "pcov_noise" , "bins" : 40 , "label" : "Moments (tomo)"},

"ps+pk5" : {"name" : "power_spectrum+peaks_z4" , "table_name" : "pcov_noise_combine" , "bins" : 14+27 , "label" : r"Power spectrum + peaks ($\bar{z}_5$)"},  
"ps+pk" : {"name" : "power_spectrum+peaks" , "table_name" : "pcov_noise_combine" , "bins" : 70 , "label" : "Power spectrum + peaks (tomo)"},
"ps+mu5" : {"name" : "power_spectrum+moments_z4" , "table_name" : "pcov_noise_combine" , "bins" : 14+9 , "label" : r"Power spectrum + moments ($\bar{z}_5$)"},
"ps+mu" : {"name" : "power_spectrum+moments" , "table_name" : "pcov_noise_combine" , "bins" : 60 , "label" : "Power spectrum + moments (tomo)"},
"ps+pk+mu5" : {"name" : "power_spectrum+peaks+moments_z4" , "table_name" : "pcov_noise_combine" , "bins" : 14+27+9 , "label" : r"Power spectrum + peaks + moments ($\bar{z}_5$)"},
"ps+pk+mu" : {"name" : "power_spectrum+peaks+moments" , "table_name" : "pcov_noise_combine" , "bins" : 100 , "label" : "Power spectrum + peaks + moments (tomo)"} 

}

columns = {
	
	"labels" : [r"$\Delta \Omega_m$",r"$\Delta w$",r"$\Delta \sigma_8$",r"$10^6{\rm Area} (\Omega_m,w)$",r"$10^9{\rm Volume}$ $(\Omega_m,w,\sigma_8)$"] ,
	r"$\Delta \Omega_m$" : lambda pcov:np.sqrt(pcov["Om"]),
	r"$\Delta w$" : lambda pcov:np.sqrt(pcov["w"]),
	r"$\Delta \sigma_8$" : lambda pcov:np.sqrt(pcov["sigma8"]),
	r"$10^6{\rm Area} (\Omega_m,w)$" : lambda pcov : int(1.0e6*np.sqrt(np.linalg.det(pcov[["Om","w"]].values))),
	r"$10^9{\rm Volume}$ $(\Omega_m,w,\sigma_8)$" : lambda pcov: int(1.0e9*np.sqrt(np.linalg.det(pcov.values)))

}

#Table with errors, ellipse contours, etc...
def constraint_table(cmd_args,db_name="data/fisher/constraints_combine.sqlite",cmb_prior_fisher=None,print_to=sys.stdout,features_to_show=["ps5","ps-tomo","peaks5","peaks-tomo","moments5","moments-tomo","ps+pk5","ps+pk","ps+mu5","ps+mu","ps+pk+mu5","ps+pk+mu"],all_parameters=["Om","w","sigma8"],rows=rows,columns=columns):

	#Prepare the Table with the appropriate number of rows and columns
	table = pd.DataFrame([rows[r]["label"] for r in features_to_show],columns=["Statistic"])
	for c in columns["labels"]:
		table[c] = None

	#CMB prior
	if cmb_prior_fisher is not None:
		fisher_cmb = SquareMatrix.read(cmb_prior_fisher)[all_parameters]

	#Query the database and fill in the data
	with FisherDatabase(db_name) as db:
		for nf,feature in enumerate(features_to_show):

			#Query the parameter covariance matrix
			name = rows[feature]["name"]
			db_table_name = rows[feature]["table_name"]
			nbins = rows[feature]["bins"] 

			pcov = db.query_parameter_covariance(feature_label=name,nbins=nbins,parameters=all_parameters,table_name=db_table_name)

			#Maybe apply the prior
			if cmb_prior_fisher is not None:
				pcov = (pcov.invert() + fisher_cmb).invert()

			#Select entries in the row to put in the table
			for c in columns["labels"]:
				table[c].iloc[nf] = columns[c](pcov)

	#Output the table
	latex_kwargs = {"escape":False,"index":False,"float_format":lambda n:"{0:.4f}".format(n)}


	if type(print_to)==file:
		print_to.write(table.to_latex(**latex_kwargs))
	else:
		with open(print_to,"w") as fp:
			fp.write(table.to_latex(**latex_kwargs))

def constraint_table_cmb(cmd_args):
	constraint_table(cmd_args,cmb_prior_fisher="data/planck/planck_base_w_TT_lowTEB.pkl")


###################################################################################################
###################################################################################################
###################################################################################################

#Method dictionary
method = dict()

method["1"] = design
method["2"] = galdistr

method["3a"] = pca_components_power_spectrum
method["3b"] = pca_components_peaks
method["3c"] = pca_components_moments

method["4a"] = sims_vs_nicaea
method["4b"] = constraints_no_pca_peaks
method["4c"] = constraints_no_pca_moments

method["5"] = parameter_constraints
method["5b"] = parameter_constraints_with_cmb

method["6"] = photoz_bias

method["7"] = bias_vs_sigma

method["t1"] = constraint_table
method["t2"] = constraint_table_cmb

#Main
def main():
	cmd_args = parser.parse_args()
	for fig in cmd_args.fig:
		method[fig](cmd_args)

if __name__=="__main__":
	main()