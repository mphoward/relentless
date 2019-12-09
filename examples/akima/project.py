import numpy as np

import relentless

class Desktop(relentless.environment.Environment):
    mpiexec = 'mpirun -np {np}'
    always_wrap = False

# target lj potential
lj = relentless.potential.LJPotential(types=('1',), shift=True)
lj.coeff['1','1'] = {'epsilon': 1.0, 'sigma': 1.0, 'rmax': 3.0}

# reference ensemble
tgt = relentless.ensemble.NVT(N={'1': 50}, V=1000., T=1.0)
dr = 0.1
rs = np.arange(0.5*dr,4.0,dr)
tgt.rdf['1','1'] = np.column_stack((rs,np.exp(-tgt.beta*lj(rs,('1','1')))))

# spline potential
spline = relentless.potential.AkimaSpline(types=('1',), num_knots=5, shift=True)
spline.coeff['1','1'] = {'rmin': 2.**(1./6.), 'rmax': 3.0}
for i in range(spline.num_knots):
    spline.coeff['1','1']['knot-{}'.format(i)] = 0
lj.coeff['1','1']['rmax'] = 2.**(1./6.)

# mock simulation engine & rdf (dilute limit)
sim = relentless.engine.Mock()
rdf = relentless.rdf.Mock(ensemble=tgt, dr=dr, rcut=3.0, potential=lambda r,pair: lj(r,pair)+spline(r,pair))
tab = relentless.potential.Tabulator(nbins=1000, rmin=0.0, rmax=3.0, fmax=100., fcut=1.e-6)

# relative entropy
re = relentless.optimize.RelativeEntropy(tgt, sim, rdf, tab)
re.add_potential(lj)
re.add_potential(spline)

# steepest descent
opt = relentless.optimize.GradientDescent(re)

with Desktop(path='./workspace') as env:
    opt.run(env=env, maxiter=100, rates={('1','1'): 1.e-2})
