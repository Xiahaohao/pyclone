'''
Created on 2011-12-15

@author: Andrew Roth
'''
from __future__ import division

from collections import namedtuple

from pydp.base_measures import BaseMeasure

from pydp.densities import Density, log_binomial_pdf
from pydp.partition import Partition

from pydp.samplers.atom import BaseMeasureAtomSampler
from pydp.samplers.concentration import GammaPriorConcentrationSampler
from pydp.samplers.partition import AuxillaryParameterPartitionSampler

from pydp.rvs import uniform_rvs
from pydp.utils import log_sum_exp

class DirichletProcessSampler(object):
    def __init__(self, tumour_content, alpha=None):
        self.base_measure = PyCloneBaseMeasure(tumour_content)
        
        cluster_density = PyCloneDensity()
        
        self.partition_sampler = AuxillaryParameterPartitionSampler(self.base_measure, cluster_density)
        
        self.atom_sampler = BaseMeasureAtomSampler(self.base_measure, cluster_density)           
        
        if alpha is None:
            self.alpha = 1
            
            self.update_alpha = True
            
            self.concentration_sampler = GammaPriorConcentrationSampler(1, 1)
        else:
            self.alpha = alpha
            
            self.update_alpha = False 
        
        self.num_iters = 0
    
    @property
    def state(self):
        return {
                'alpha' : self.alpha,
                'cellular_frequencies' : [param.phi for param in self.partition.item_values],
                'labels' : self.partition.labels,
                'phi' : [param.phi for param in self.partition.cell_values]
                }
    
    def initialise_partition(self, data):
        self.partition = Partition()
        
        for item, _ in enumerate(data):
            self.partition.add_cell(self.base_measure.random())
            
            self.partition.add_item(item, item)        
    
    def sample(self, data, results_db, num_iters, print_freq=100):
        self.initialise_partition(data)
        
        print "Tumour Content :", self.base_measure.tumour_content
        
        for i in range(num_iters):
            if i % print_freq == 0:
                print self.num_iters, self.partition.number_of_cells, self.alpha
            
            self.interactive_sample(data)
            
            results_db.update_trace(self.state)
            
            self.num_iters += 1
    
    def interactive_sample(self, data):
        if self.update_alpha:
            self.alpha = self.concentration_sampler.sample(self.alpha,
                                                           self.partition.number_of_cells,
                                                           self.partition.number_of_items)
        
        self.partition_sampler.sample(data, self.partition, self.alpha)
        
        self.atom_sampler.sample(data, self.partition)
    
    def _init_partition(self, base_measure):
        self.partition = Partition()
        
        for item, _ in enumerate(self.data):
            self.partition.add_cell(base_measure.random())
            
            self.partition.add_item(item, item)

class PyCloneBaseMeasure(BaseMeasure):
    def __init__(self, tumour_content):
        self.tumour_content = tumour_content
        
    def random(self):
        phi = uniform_rvs(0, 1)
        
        return PyCloneParameter(phi, self.tumour_content)

#=======================================================================================================================
# Data class
#=======================================================================================================================
PyCloneData = namedtuple('PyCloneData', ['a', 'd', 'mu_r', 'mu_v', 'log_pi_r', 'log_pi_v'])

PyCloneParameter = namedtuple('PyCloneParameter', ['phi', 's'])

class PyCloneDensity(Density):
    def log_p(self, data, params):
        ll = []
        
        for mu_r, log_pi_r in zip(data.mu_r, data.log_pi_r):
            for mu_v, log_pi_v in zip(data.mu_v, data.log_pi_v):
                temp = log_pi_r + log_pi_v + self._log_binomial_likelihood(data.a, data.d, params.phi, params.s, mu_r, mu_v)
                
                ll.append(temp)
        
        return log_sum_exp(ll)
    
    def _log_binomial_likelihood(self, a, d, phi, s, mu_r, mu_v):
        mu_N = mu_r
        
        mu_T = (1 - phi) * mu_r + phi * mu_v
        
        mu = (1 - s) * mu_N + s * mu_T
        
        return log_binomial_pdf(a, d, mu) 
