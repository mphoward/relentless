from __future__ import division

import json
import warnings

import numdifftools
import numpy as np
import scipy.optimize

from .core import PairMatrix

class CoefficientMatrix(PairMatrix):
    """ Pair coefficient matrix.
    """
    def __init__(self, types, params, default={}):
        super(CoefficientMatrix, self).__init__(types)

        self.params = tuple(params)

        for key in self:
            for p in self.params:
                v = default[p] if p in default else None
                self[key][p] = v

    def evaluate(self, pair):
        params = {}
        for p in self.params:
            v = self[pair][p]
            params[p] = v(self) if callable(v) else v
            if params[p] is None:
                raise ValueError('Parameter {} is not set for ({},{}).'.format(p,pair[0],pair[1]))

        return params

    def perturb(self, pair, key, param, value):
        if param not in self.params:
            raise KeyError('Parameter {} is not part of the coefficient matrix.'.format(param))

        old_value = self[key][param]
        if old_value is None:
            raise ValueError('Cannot perturb parameter {}, not set for ({},{}).'.format(param,*key))
        elif callable(old_value):
            raise KeyError('Cannot perturb a callable parameter; it is chained.')

        # evaluate old values first
        old_params = self.evaluate(pair)

        # swap in new value
        self[key][param] = value
        new_params = self.evaluate(pair)

        # restore old value
        self[key][param] = old_value

        return new_params, old_params

    def save(self, filename):
        all_params = {}
        for key in self:
            all_params[str(key)] = self.evaluate(key)
        with open(filename, 'w') as f:
            json.dump(all_params, f, sort_keys=True, indent=4)

    def __setitem__(self, key, value):
        """ Set coefficients for the (i,j) pair.
        """
        for p in value:
            if p not in self.params:
                raise KeyError('Only the known parameters can be set in coefficient matrix.')
            self[key][p] = value[p]

class PairPotential(object):
    """ Generic pair potential evaluator.
    """
    _id = 0

    def __init__(self, types, params, default={}, shift=False):
        assert 'rmin' in params, 'rmin must be in PairPotential parameters'
        assert 'rmax' in params, 'rmax must be in PairPotential parameters'

        self.coeff = CoefficientMatrix(types, params, default)
        self.free = PairMatrix(types)
        self.shift = shift

        self.id = PairPotential._id
        PairPotential._id += 1

    def __call__(self, r, pair):
        """ Evaluate energy for a (i,j) pair.
        """
        params = self.coeff.evaluate(pair)
        u = self.energy(r, **params)
        if self.shift:
            u[np.atleast_1d(r) <= params['rmax']] -= self.energy(params['rmax'], **params)
        return u

    def energy(self, r, **kwargs):
        """ Evaluate the potential energy.
        """
        raise NotImplementedError()

    def force(self, r, pair):
        """ Evaluate the force for a (i,j) pair.
        """
        params = self.coeff.evaluate(pair)
        dudr = numdifftools.Derivative(lambda x: self.energy(x, **params))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            f = -dudr(r)
        return f

    def derivative(self, r, pair, key, param):
        """ Evaluate derivative for a (i,j) pair with respect to a key parameter.
        """
        if callable(self.coeff[key][param]):
            raise KeyError('Cannot differentiate a callable parameter; it is chained.')

        # setup derivative
        def u(p):
            params,_ = self.coeff.perturb(pair,key,param,p)
            return self.energy(r, **params)
        dudp = numdifftools.Derivative(u)

        # evaluate derivative at current value of param
        # numdifftools raises a deprecation FutureWarning via NumPy, so silence.
        params = self.coeff.evaluate(pair)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            deriv = dudp(params[param])

        return deriv

    def save(self):
        self.coeff.save('{}.{}.json'.format(self.id,self.__class__.__name__))

    def _zeros(self, r):
        # coerce input shape and create zeros for output
        r = np.asarray(np.atleast_1d(r))
        if len(r.shape) != 1:
            raise TypeError('Expecting 1D array for r')
        return r,np.zeros_like(r)

    def __iter__(self):
        return iter(self.coeff)

    def __next__(self):
        return next(self.coeff)

class LJPotential(PairPotential):
    def __init__(self, types, shift=False):
        super(LJPotential,self).__init__(types=types,
                                         params=('epsilon','sigma','n','rmin','rmax'),
                                         default={'n': 6, 'rmin': 0.},
                                         shift=shift)

    def energy(self, r, epsilon, sigma, n, rmin, rmax):
        r,u = self._zeros(r)

        zero_flags = np.isclose(r, 0)
        range_flags = np.logical_and(r >= rmin, r <= rmax)

        # evaluate potential for r in range, but nonzero
        flags = np.logical_xor(range_flags, zero_flags)
        rn_inv = np.power(sigma/r[flags], n)
        u[flags] = 4.*epsilon*(rn_inv**2 - rn_inv)

        # evaluate potential for r in range, but zero
        flags = np.logical_and(range_flags, zero_flags)
        u[flags] = np.inf

        return u

    def force(self, r, pair):
        # load parameters for the pair
        params = self.coeff.evaluate(pair)
        epsilon = params['epsilon']
        sigma = params['sigma']
        n = params['n']
        rmin = params['rmin']
        rmax = params['rmax']

        # evaluate cutoff force
        r,f = self._zeros(r)

        zero_flags = np.isclose(r, 0)
        range_flags = np.logical_and(r >= rmin, r <= rmax)

        # evaluate force for r in range, but nonzero
        flags = np.logical_xor(range_flags, zero_flags)
        rinv = 1./r[flags]
        rn_inv = np.power(sigma*rinv, n)
        f[flags] = (8.*n*epsilon*rinv)*(rn_inv**2-0.5*rn_inv)

        # evaluate force for r in range, but zero
        flags = np.logical_and(range_flags, zero_flags)
        f[flags] = np.inf

        return f

class Tabulator(object):
    def __init__(self, nbins, rmin, rmax, fmax=None, fcut=None, edges=True):
        self._nbins = nbins
        self._rmin = rmin
        self._rmax = rmax

        self.fmax = fmax
        self.fcut = fcut

        self._dr = (rmax-rmin)/nbins
        if edges:
            self._r = np.linspace(rmin, rmax, nbins+1, dtype=np.float64)
        else:
            self._r = rmin + self._dr*(np.arange(nbins, dtype=np.float64)+0.5)

    @property
    def dr(self):
        return self._dr

    @property
    def r(self):
        return self._r

    def __call__(self, pair, potentials):
        u = np.zeros_like(self.r)
        for pot in potentials:
            if pair in pot.coeff.pairs:
                u += pot(self.r, pair)
        return u

    def force(self, pair, potentials):
        f = np.zeros_like(self.r)
        for pot in potentials:
            if pair in pot.coeff.pairs:
                f += pot.force(self.r, pair)
        return f

    def regularize(self, u, f, trim=True):
        if len(u) != len(self.r):
            raise IndexError('Potential must have the same length as r.')
        if len(f) != len(self.r):
            raise IndexError('Force must have the same length as r.')

        # find first point from beginning that is within energy tolerance
        if self.fmax is not None:
            cut = np.argmax(np.abs(f) <= self.fmax)
            if cut > 0:
                u[:cut] = u[cut] - f[cut]*(self.r[:cut] - self.r[cut])
                f[:cut] = f[cut]

        # find first point from end with sufficient force and cutoff the potential after it
        if self.fcut is not None:
            flags = np.abs(np.flip(f)) >= self.fcut
            cut = len(f)-1 - np.argmax(flags)
            u -= u[cut]
            if cut < len(f)-1:
                u[(cut+1):] = 0.
                f[(cut+1):] = 0.

        # trim off trailing zeros
        r = self.r.copy()
        if trim:
            flags = np.abs(np.flip(f)) > 0
            cut = len(f) - np.argmax(flags)
            if cut < len(f)-1:
                r = r[:(cut+1)]
                u = u[:(cut+1)]
                f = f[:(cut+1)]

        return np.column_stack((r,u,f))
