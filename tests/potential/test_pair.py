"""Unit tests for pair module."""
import json
import tempfile
import unittest

import numpy as np

import relentless

class test_PairParameters(unittest.TestCase):
    """Unit tests for relentless.pair.PairParameters"""

    def test_init(self):
        """Test creation from data"""
        types = ('A','B')
        pairs = (('A','B'), ('B','B'), ('A','A'))
        params = ('energy', 'mass')

        #test construction with tuple input
        m = relentless.potential.PairParameters(types=('A','B'), params=('energy','mass'))
        self.assertEqual(m.types, types)
        self.assertEqual(m.params, params)
        self.assertCountEqual(m.pairs, pairs)

        #test construction with list input
        m = relentless.potential.PairParameters(types=['A','B'], params=('energy','mass'))
        self.assertEqual(m.types, types)
        self.assertEqual(m.params, params)
        self.assertCountEqual(m.pairs, pairs)

        #test construction with mixed tuple/list input
        m = relentless.potential.PairParameters(types=('A','B'), params=['energy','mass'])
        self.assertEqual(m.types, types)
        self.assertEqual(m.params, params)
        self.assertCountEqual(m.pairs, pairs)

        #test construction with int type parameters
        with self.assertRaises(TypeError):
            m = relentless.potential.PairParameters(types=('A','B'), params=(1,2))

        #test construction with mixed type parameters
        with self.assertRaises(TypeError):
            m = relentless.potential.PairParameters(types=('A','B'), params=('1',2))

    def test_param_types(self):
        """Test various get and set methods on pair parameter types"""
        m = relentless.potential.PairParameters(types=('A','B'), params=('energy', 'mass'))

        self.assertEqual(m.shared['energy'], None)
        self.assertEqual(m.shared['mass'], None)
        self.assertEqual(m['A','A']['energy'], None)
        self.assertEqual(m['A','A']['mass'], None)
        self.assertEqual(m['A','B']['energy'], None)
        self.assertEqual(m['A','B']['mass'], None)
        self.assertEqual(m['B','B']['energy'], None)
        self.assertEqual(m['B','B']['mass'], None)
        self.assertEqual(m['A']['energy'], None)
        self.assertEqual(m['A']['mass'], None)
        self.assertEqual(m['B']['energy'], None)
        self.assertEqual(m['B']['mass'], None)

        #test setting shared params
        m.shared.update(energy=1.0, mass=2.0)

        self.assertEqual(m.shared['energy'], 1.0)
        self.assertEqual(m.shared['mass'], 2.0)
        self.assertEqual(m['A','A']['energy'], None)
        self.assertEqual(m['A','A']['mass'], None)
        self.assertEqual(m['A','B']['energy'], None)
        self.assertEqual(m['A','B']['mass'], None)
        self.assertEqual(m['B','B']['energy'], None)
        self.assertEqual(m['B','B']['mass'], None)
        self.assertEqual(m['A']['energy'], None)
        self.assertEqual(m['A']['mass'], None)
        self.assertEqual(m['B']['energy'], None)
        self.assertEqual(m['B']['mass'], None)

        #test setting per-pair params
        m['A','A'].update(energy=1.5, mass=2.5)
        m['A','B'].update(energy=2.0, mass=3.0)
        m['B','B'].update(energy=0.5, mass=0.7)

        self.assertEqual(m.shared['energy'], 1.0)
        self.assertEqual(m.shared['mass'], 2.0)
        self.assertEqual(m['A','A']['energy'], 1.5)
        self.assertEqual(m['A','A']['mass'], 2.5)
        self.assertEqual(m['A','B']['energy'], 2.0)
        self.assertEqual(m['A','B']['mass'], 3.0)
        self.assertEqual(m['B','B']['energy'], 0.5)
        self.assertEqual(m['B','B']['mass'], 0.7)
        self.assertEqual(m['A']['energy'], None)
        self.assertEqual(m['A']['mass'], None)
        self.assertEqual(m['B']['energy'], None)
        self.assertEqual(m['B']['mass'], None)

        #test setting per-type params
        m['A'].update(energy=0.1, mass=0.2)
        m['B'].update(energy=0.2, mass=0.1)

        self.assertEqual(m.shared['energy'], 1.0)
        self.assertEqual(m.shared['mass'], 2.0)
        self.assertEqual(m['A','A']['energy'], 1.5)
        self.assertEqual(m['A','A']['mass'], 2.5)
        self.assertEqual(m['A','B']['energy'], 2.0)
        self.assertEqual(m['A','B']['mass'], 3.0)
        self.assertEqual(m['B','B']['energy'], 0.5)
        self.assertEqual(m['B','B']['mass'], 0.7)
        self.assertEqual(m['A']['energy'], 0.1)
        self.assertEqual(m['A']['mass'], 0.2)
        self.assertEqual(m['B']['energy'], 0.2)
        self.assertEqual(m['B']['mass'], 0.1)

class LinPot(relentless.potential.PairPotential):
    """Linear potential function used to test relentless.potential.PairPotential"""

    def __init__(self, types, params):
        super().__init__(types, params)

    def _energy(self, r, m, **params):
        r,u,s = self._zeros(r)
        u[:] = m*r
        if s:
            u = u.item()
        return u

    def _force(self, r, m, **params):
        r,f,s = self._zeros(r)
        f[:] = -m
        if s:
            f = f.item()
        return f

    def _derivative(self, param, r, **params):
        r,d,s = self._zeros(r)
        if param == 'm':
            d[:] = r
        if s:
            d = d.item()
        return d

class TwoVarPot(relentless.potential.PairPotential):
    """Mock potential function used to test relentless.potential.PairPotential.derivative"""

    def __init__(self, types, params):
        super().__init__(types, params)

    def _energy(self, r, x, y, **params):
        pass

    def _force(self, r, x, y, **params):
        pass

    def _derivative(self, param, r, **params):
        #not real derivative, just used to test functionality
        r,d,s = self._zeros(r)
        if param == 'x':
            d[:] = 2*r
        elif param == 'y':
            d[:] = 3*r
        if s:
            d = d.item()
        return d

class test_PairPotential(unittest.TestCase):
    """Unit tests for relentless.potential.PairPotential"""

    def test_init(self):
        """Test creation from data"""
        #test creation with only m
        p = LinPot(types=('1',), params=('m',))
        p.coeff['1','1']['m'] = 3.5

        coeff = relentless.potential.PairParameters(types=('1',), params=('m','rmin','rmax','shift'))
        coeff['1','1']['m'] = 3.5
        coeff['1','1']['rmin'] = False
        coeff['1','1']['rmax'] = False
        coeff['1','1']['shift'] = False

        self.assertCountEqual(p.coeff.types, coeff.types)
        self.assertCountEqual(p.coeff.params, coeff.params)
        self.assertDictEqual(p.coeff.evaluate(('1','1')), coeff.evaluate(('1','1')))

        #test creation with m and rmin
        p = LinPot(types=('1',), params=('m','rmin'))
        p.coeff['1','1']['m'] = 3.5
        p.coeff['1','1']['rmin'] = 0.0

        coeff = relentless.potential.PairParameters(types=('1',), params=('m','rmin','rmax','shift'))
        coeff['1','1']['m'] = 3.5
        coeff['1','1']['rmin'] = 0.0
        coeff['1','1']['rmax'] = False
        coeff['1','1']['shift'] = False

        self.assertCountEqual(p.coeff.types, coeff.types)
        self.assertCountEqual(p.coeff.params, coeff.params)
        self.assertDictEqual(p.coeff.evaluate(('1','1')), coeff.evaluate(('1','1')))

        #test creation with m and rmax
        p = LinPot(types=('1',), params=('m','rmax'))
        p.coeff['1','1']['m'] = 3.5
        p.coeff['1','1']['rmax'] = 1.0

        coeff = relentless.potential.PairParameters(types=('1',), params=('m','rmin','rmax','shift'))
        coeff['1','1']['m'] = 3.5
        coeff['1','1']['rmin'] = False
        coeff['1','1']['rmax'] = 1.0
        coeff['1','1']['shift'] = False

        self.assertCountEqual(p.coeff.types, coeff.types)
        self.assertCountEqual(p.coeff.params, coeff.params)
        self.assertDictEqual(p.coeff.evaluate(('1','1')), coeff.evaluate(('1','1')))

        #test creation with m and shift
        p = LinPot(types=('1',), params=('m','shift'))
        p.coeff['1','1']['m'] = 3.5
        p.coeff['1','1']['shift'] = True

        coeff = relentless.potential.PairParameters(types=('1',), params=('m','rmin','rmax','shift'))
        coeff['1','1']['m'] = 3.5
        coeff['1','1']['rmin'] = False
        coeff['1','1']['rmax'] = False
        coeff['1','1']['shift'] = True

        self.assertCountEqual(p.coeff.types, coeff.types)
        self.assertCountEqual(p.coeff.params, coeff.params)
        self.assertDictEqual(p.coeff.evaluate(('1','1')), coeff.evaluate(('1','1')))

        #test creation with all params
        p = LinPot(types=('1',), params=('m','rmin','rmax','shift'))
        p.coeff['1','1']['m'] = 3.5
        p.coeff['1','1']['rmin'] = 0.0
        p.coeff['1','1']['rmax'] = 1.0
        p.coeff['1','1']['shift'] = True

        coeff = relentless.potential.PairParameters(types=('1',), params=('m','rmin','rmax','shift'))
        coeff['1','1']['m'] = 3.5
        coeff['1','1']['rmin'] = 0.0
        coeff['1','1']['rmax'] = 1.0
        coeff['1','1']['shift'] = True

        self.assertCountEqual(p.coeff.types, coeff.types)
        self.assertCountEqual(p.coeff.params, coeff.params)
        self.assertDictEqual(p.coeff.evaluate(('1','1')), coeff.evaluate(('1','1')))

    def test_energy(self):
        """Test energy method"""
        p = LinPot(types=('1',), params=('m',))
        p.coeff['1','1']['m'] = 2.0

        #test with no cutoffs
        u = p.energy(pair=('1','1'), r=0.5)
        self.assertAlmostEqual(u, 1.0)
        u = p.energy(pair=('1','1'), r=[0.25,0.75])
        np.testing.assert_allclose(u, [0.5,1.5])

        #test with rmin set
        p.coeff['1','1']['rmin'] = 0.5
        u = p.energy(pair=('1','1'), r=0.6)
        self.assertAlmostEqual(u, 1.2)
        u = p.energy(pair=('1','1'), r=[0.25,0.75])
        np.testing.assert_allclose(u, [1.0,1.5])

        #test with rmax set
        p.coeff['1','1'].update(rmin=False, rmax=1.5)
        u = p.energy(pair=('1','1'), r=1.0)
        self.assertAlmostEqual(u, 2.0)
        u = p.energy(pair=('1','1'), r=[0.25,1.75])
        np.testing.assert_allclose(u, [0.5,3.0])

        #test with rmin and rmax set
        p.coeff['1','1']['rmin'] = 0.5
        u = p.energy(pair=('1','1'), r=0.75)
        self.assertAlmostEqual(u, 1.5)
        u = p.energy(pair=('1','1'), r=[0.25,0.5,1.5,1.75])
        np.testing.assert_allclose(u, [1.0,1.0,3.0,3.0])

        #test with shift set
        p.coeff['1','1'].update(shift=True)
        u = p.energy(pair=('1','1'), r=0.5)
        self.assertAlmostEqual(u, -2.0)
        u = p.energy(pair=('1','1'), r=[0.25,0.75,1.0,1.5])
        np.testing.assert_allclose(u, [-2.0,-1.5,-1.0,0.0])

        #test with shift set without rmax
        p.coeff['1','1'].update(rmax=False)
        with self.assertRaises(ValueError):
            u = p.energy(pair=('1','1'), r=0.5)

    def test_force(self):
        """Test force method"""
        p = LinPot(types=('1',), params=('m',))
        p.coeff['1','1']['m'] = 2.0

        #test with no cutoffs
        f = p.force(pair=('1','1'), r=0.5)
        self.assertAlmostEqual(f, -2.0)
        f = p.force(pair=('1','1'), r=[0.25,0.75])
        np.testing.assert_allclose(f, [-2.0,-2.0])

        #test with rmin set
        p.coeff['1','1']['rmin'] = 0.5
        f = p.force(pair=('1','1'), r=0.6)
        self.assertAlmostEqual(f, -2.0)
        f = p.force(pair=('1','1'), r=[0.25,0.75])
        np.testing.assert_allclose(f, [0.0,-2.0])

        #test with rmax set
        p.coeff['1','1'].update(rmin=False, rmax=1.5)
        f = p.force(pair=('1','1'), r=1.0)
        self.assertAlmostEqual(f, -2.0)
        f = p.force(pair=('1','1'), r=[0.25,1.75])
        np.testing.assert_allclose(f, [-2.0,0.0])

        #test with rmin and rmax set
        p.coeff['1','1']['rmin'] = 0.5
        f = p.force(pair=('1','1'), r=0.75)
        self.assertAlmostEqual(f, -2.0)
        f = p.force(pair=('1','1'), r=[0.25,0.5,1.5,1.75])
        np.testing.assert_allclose(f, [0.0,-2.0,-2.0,0.0])

        #test with shift set
        p.coeff['1','1'].update(shift=True)
        f = p.force(pair=('1','1'), r=0.5)
        self.assertAlmostEqual(f, -2.0)
        f = p.force(pair=('1','1'), r=[1.0,1.5])
        np.testing.assert_allclose(f, [-2.0,-2.0])

    def test_derivative_values(self):
        """Test derivative method with different param values"""
        p = LinPot(types=('1',), params=('m',))
        x = relentless.variable.DesignVariable(value=2.0)
        p.coeff['1','1']['m'] = x

        #test with no cutoffs
        d = p.derivative(pair=('1','1'), var=x, r=0.5)
        self.assertAlmostEqual(d, 0.5)
        d = p.derivative(pair=('1','1'), var=x, r=[0.25,0.75])
        np.testing.assert_allclose(d, [0.25,0.75])

        #test with rmin set
        rmin = relentless.variable.DesignVariable(value=0.5)
        p.coeff['1','1']['rmin'] = rmin
        d = p.derivative(pair=('1','1'), var=x, r=0.6)
        self.assertAlmostEqual(d, 0.6)
        d = p.derivative(pair=('1','1'), var=x, r=[0.25,0.75])
        np.testing.assert_allclose(d, [0.5,0.75])

        #test with rmax set
        rmax = relentless.variable.DesignVariable(value=1.5)
        p.coeff['1','1'].update(rmin=False, rmax=rmax)
        d = p.derivative(pair=('1','1'), var=x, r=1.0)
        self.assertAlmostEqual(d, 1.0)
        d = p.derivative(pair=('1','1'), var=x, r=[0.25,1.75])
        np.testing.assert_allclose(d, [0.25,1.5])

        #test with rmin and rmax set
        p.coeff['1','1']['rmin'] = rmin
        d = p.derivative(pair=('1','1'), var=x, r=0.75)
        self.assertAlmostEqual(d, 0.75)
        d = p.derivative(pair=('1','1'), var=x, r=[0.25,0.5,1.5,1.75])
        np.testing.assert_allclose(d, [0.5,0.5,1.5,1.5])

        #test w.r.t. rmin and rmax
        d = p.derivative(pair=('1','1'), var=rmin, r=[0.25,1.0,2.0])
        np.testing.assert_allclose(d, [2.0,0.0,0.0])
        d = p.derivative(pair=('1','1'), var=rmax, r=[0.25,1.0,2.0])
        np.testing.assert_allclose(d, [0.0,0.0,2.0])

        #test parameter derivative with shift set
        p.coeff['1','1'].update(shift=True)
        d = p.derivative(pair=('1','1'), var=x, r=0.5)
        self.assertAlmostEqual(d, -1.0)
        d = p.derivative(pair=('1','1'), var=x, r=[0.25,1.0,1.5,1.75])
        np.testing.assert_allclose(d, [-1.0,-0.5,0.0,0.0])

        #test w.r.t. rmin and rmax, shift set
        d = p.derivative(pair=('1','1'), var=rmin, r=[0.25,1.0,2.0])
        np.testing.assert_allclose(d, [2.0,0.0,0.0])
        d = p.derivative(pair=('1','1'), var=rmax, r=[0.25,1.0,2.0])
        np.testing.assert_allclose(d, [-2.0,-2.0,0.0])

    def test_derivative_types(self):
        """Test derivative method with different param types."""
        q = LinPot(types=('1',), params=('m',))
        x = relentless.variable.DesignVariable(value=4.0)
        y = relentless.variable.DesignVariable(value=64.0)
        z = relentless.variable.GeometricMean(x, y)
        q.coeff['1','1']['m'] = z

        #test with respect to dependent variable parameter
        d = q.derivative(pair=('1','1'), var=z, r=2.0)
        self.assertAlmostEqual(d, 2.0)

        #test with respect to independent variable on which parameter is dependent
        d = q.derivative(pair=('1','1'), var=x, r=1.5)
        self.assertAlmostEqual(d, 3.0)
        d = q.derivative(pair=('1','1'), var=y, r=4.0)
        self.assertAlmostEqual(d, 0.5)

        #test invalid derivative w.r.t. scalar
        a = 2.5
        q.coeff['1','1']['m'] = a
        with self.assertRaises(TypeError):
            d = q.derivative(pair=('1','1'), var=a, r=2.0)

        #test with respect to independent variable which is related to a SameAs variable
        r = TwoVarPot(types=('1',), params=('x','y'))

        r.coeff['1','1']['x'] = x
        r.coeff['1','1']['y'] = relentless.variable.SameAs(x)
        d = r.derivative(pair=('1','1'), var=x, r=4.0)
        self.assertAlmostEqual(d, 20.0)

        r.coeff['1','1']['y'] = x
        r.coeff['1','1']['x'] = relentless.variable.SameAs(x)
        d = r.derivative(pair=('1','1'), var=x, r=4.0)
        self.assertAlmostEqual(d, 20.0)

    def test_iteration(self):
        """Test iteration on PairPotential object"""
        p = LinPot(types=('1','2'), params=('m',))
        for pair in p.coeff:
            p.coeff[pair]['m'] = 2.0
            p.coeff[pair]['rmin'] = 0.0
            p.coeff[pair]['rmax'] = 1.0

        self.assertDictEqual(p.coeff['1','1'].todict(), {'m':2.0, 'rmin':0.0, 'rmax':1.0, 'shift':False})
        self.assertDictEqual(p.coeff['1','2'].todict(), {'m':2.0, 'rmin':0.0, 'rmax':1.0, 'shift':False})
        self.assertDictEqual(p.coeff['2','2'].todict(), {'m':2.0, 'rmin':0.0, 'rmax':1.0, 'shift':False})

    def test_save(self):
        """Test saving to file"""
        temp = tempfile.NamedTemporaryFile()
        p = LinPot(types=('1',), params=('m','rmin','rmax'))
        p.coeff['1','1']['m'] = 2.0
        p.coeff['1','1']['rmin'] = 0.0
        p.coeff['1','1']['rmax'] = 1.0
        p.coeff['1','1']['shift'] = True

        p.save(temp.name)
        with open(temp.name, 'r') as f:
            x = json.load(f)

        self.assertEqual(p.coeff['1','1']['m'], x["('1', '1')"]['m'])
        self.assertEqual(p.coeff['1','1']['rmin'], x["('1', '1')"]['rmin'])
        self.assertEqual(p.coeff['1','1']['rmax'], x["('1', '1')"]['rmax'])
        self.assertEqual(p.coeff['1','1']['shift'], x["('1', '1')"]['shift'])

        temp.close()

class test_LennardJones(unittest.TestCase):
    """Unit tests for relentless.potential.LennardJones"""

    def test_init(self):
        """Test creation from data"""
        lj = relentless.potential.LennardJones(types=('1',))
        coeff = relentless.potential.PairParameters(types=('1',),
                                                    params=('epsilon','sigma','rmin','rmax','shift'))
        for pair in coeff.pairs:
            coeff[pair]['rmin'] = False
            coeff[pair]['rmax'] = False
            coeff[pair]['shift'] = False
        self.assertCountEqual(lj.coeff.types, coeff.types)
        self.assertCountEqual(lj.coeff.params, coeff.params)

    def test_energy(self):
        """Test _energy method"""
        lj = relentless.potential.LennardJones(types=('1',))

        #test scalar r
        r_input = 0.5
        u_actual = 0
        u = lj._energy(r=r_input, epsilon=1.0, sigma=0.5)
        self.assertAlmostEqual(u, u_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        u_actual = np.array([np.inf,-0.061523438,-0.0054794417])
        u = lj._energy(r=r_input, epsilon=1.0, sigma=0.5)
        np.testing.assert_allclose(u, u_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            u = lj._energy(r=r_input, epsilon=1.0, sigma=-1.0)

    def test_force(self):
        """Test _force method"""
        lj = relentless.potential.LennardJones(types=('1',))

        #test scalar r
        r_input = 0.5
        f_actual = 48
        f = lj._force(r=r_input, epsilon=1.0, sigma=0.5)
        self.assertAlmostEqual(f, f_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        f_actual = np.array([np.inf,-0.36328125,-0.02188766])
        f = lj._force(r=r_input, epsilon=1.0, sigma=0.5)
        np.testing.assert_allclose(f, f_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            u = lj._force(r=r_input, epsilon=1.0, sigma=-1.0)

    def test_derivative(self):
        """Test _derivative method"""
        lj = relentless.potential.LennardJones(types=('1',))

        #w.r.t. epsilon
        #test scalar r
        r_input = 0.5
        d_actual = 0
        d = lj._derivative(param='epsilon', r=r_input, epsilon=1.0, sigma=0.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        d_actual = np.array([np.inf,-0.061523438,-0.0054794417])
        d = lj._derivative(param='epsilon', r=r_input, epsilon=1.0, sigma=0.5)
        np.testing.assert_allclose(d, d_actual)

        #w.r.t. sigma
        #test scalar r
        r_input = 0.5
        d_actual = 48
        d = lj._derivative(param='sigma', r=r_input, epsilon=1.0, sigma=0.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        d_actual = np.array([np.inf,-0.7265625,-0.06566298])
        d = lj._derivative(param='sigma', r=r_input, epsilon=1.0, sigma=0.5)
        np.testing.assert_allclose(d, d_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            u = lj._derivative(param='sigma', r=r_input, epsilon=1.0, sigma=-1.0)

        #test invalid param
        with self.assertRaises(ValueError):
            u = lj._derivative(param='simga', r=r_input, epsilon=1.0, sigma=1.0)

class test_PairSpline(unittest.TestCase):
    """Unit tests for relentless.potential.PairSpline"""

    def test_init(self):
        """Test creation from data"""
        #test diff mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3)
        self.assertEqual(s.num_knots, 3)
        self.assertEqual(s.mode, 'diff')
        coeff = relentless.potential.PairParameters(types=('1',),
                                                    params=('r-0','r-1','r-2','knot-0','knot-1','knot-2','rmin','rmax','shift'))
        self.assertCountEqual(s.coeff.types, coeff.types)
        self.assertCountEqual(s.coeff.params, coeff.params)

        #test value mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='value')
        self.assertEqual(s.num_knots, 3)
        self.assertEqual(s.mode, 'value')
        coeff = relentless.potential.PairParameters(types=('1',),
                                                    params=('r-0','r-1','r-2','knot-0','knot-1','knot-2','rmin','rmax','shift'))
        self.assertCountEqual(s.coeff.types, coeff.types)
        self.assertCountEqual(s.coeff.params, coeff.params)

        #test invalid number of knots
        with self.assertRaises(ValueError):
            s = relentless.potential.PairSpline(types=('1',), num_knots=1)

        #test invalid mode
        with self.assertRaises(ValueError):
            s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='val')

    def test_from_array(self):
        """Test from_array method and knots generator"""
        r_arr = [1,2,3]
        u_arr = [9,4,1]
        u_arr_diff = [5,3,1]

        #test diff mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3)
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)

        for i,(r,k) in enumerate(s.knots(pair=('1','1'))):
            self.assertAlmostEqual(r.value, r_arr[i])
            self.assertAlmostEqual(k.value, u_arr_diff[i])
            self.assertEqual(r.const, True)
            if i == s.num_knots-1:
                self.assertEqual(k.const, True)
            else:
                self.assertEqual(k.const, False)

        #test value mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='value')
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)

        for i,(r,k) in enumerate(s.knots(pair=('1','1'))):
            self.assertAlmostEqual(r.value, r_arr[i])
            self.assertAlmostEqual(k.value, u_arr[i])
            self.assertEqual(r.const, True)
            if i == s.num_knots-1:
                self.assertEqual(k.const, True)
            else:
                self.assertEqual(k.const, False)

        #test invalid r and u shapes
        r_arr = [2,3]
        with self.assertRaises(ValueError):
            s.from_array(pair=('1','1'), r=r_arr, u=u_arr)

        r_arr = [1,2,3]
        u_arr = [1,2]
        with self.assertRaises(ValueError):
            s.from_array(pair=('1','1'), r=r_arr, u=u_arr)

    def test_energy(self):
        """Test energy method"""
        r_arr = [1,2,3]
        u_arr = [9,4,1]

        #test diff mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3)
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        u_actual = np.array([6.25,2.25,1])
        u = s.energy(pair=('1','1'), r=[1.5,2.5,3.5])
        np.testing.assert_allclose(u, u_actual)

        #test value mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='value')
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        u_actual = np.array([6.25,2.25,1])
        u = s.energy(pair=('1','1'), r=[1.5,2.5,3.5])
        np.testing.assert_allclose(u, u_actual)

        #test PairSpline with 2 knots
        s = relentless.potential.PairSpline(types=('1',), num_knots=2, mode='value')
        s.from_array(pair=('1','1'), r=[1,2], u=[4,2])
        u = s.energy(pair=('1','1'), r=1.5)
        self.assertAlmostEqual(u, 3)

    def test_force(self):
        """Test force method"""
        r_arr = [1,2,3]
        u_arr = [9,4,1]

        #test diff mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3)
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        f_actual = np.array([5,3,0])
        f = s.force(pair=('1','1'), r=[1.5,2.5,3.5])
        np.testing.assert_allclose(f, f_actual)

        #test value mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='value')
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        f_actual = np.array([5,3,0])
        f = s.force(pair=('1','1'), r=[1.5,2.5,3.5])
        np.testing.assert_allclose(f, f_actual)

        #test PairSpline with 2 knots
        s = relentless.potential.PairSpline(types=('1',), num_knots=2, mode='value')
        s.from_array(pair=('1','1'), r=[1,2], u=[4,2])
        f = s.force(pair=('1','1'), r=1.5)
        self.assertAlmostEqual(f, 2)

    def test_derivative(self):
        """Test derivative method"""
        r_arr = [1,2,3]
        u_arr = [9,4,1]

        #test diff mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3)
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        d_actual = np.array([1.125,0.625,0])
        param = list(s.knots(('1','1')))[1][1]
        d = s.derivative(pair=('1','1'), var=param, r=[1.5,2.5,3.5])
        np.testing.assert_allclose(d, d_actual)

        #test value mode
        s = relentless.potential.PairSpline(types=('1',), num_knots=3, mode='value')
        s.from_array(pair=('1','1'), r=r_arr, u=u_arr)
        d_actual = np.array([0.75,0.75,0])
        param = list(s.knots(('1','1')))[1][1]
        d = s.derivative(pair=('1','1'), var=param, r=[1.5,2.5,3.5])
        np.testing.assert_allclose(d, d_actual)

class test_Yukawa(unittest.TestCase):
    """Unit tests for relentless.potential.Yukawa"""

    def test_init(self):
        """Test creation from data"""
        y = relentless.potential.Yukawa(types=('1',))
        coeff = relentless.potential.PairParameters(types=('1',), params=('epsilon','kappa','rmin','rmax','shift'))
        for pair in coeff.pairs:
            coeff[pair]['rmin'] = False
            coeff[pair]['rmax'] = False
            coeff[pair]['shift'] = False
        self.assertCountEqual(y.coeff.types, coeff.types)
        self.assertCountEqual(y.coeff.params, coeff.params)

    def test_energy(self):
        """Test _energy method"""
        y = relentless.potential.Yukawa(types=('1',))

        #test scalar r
        r_input = 0.5
        u_actual = 1.5576016
        u = y._energy(r=r_input, epsilon=1.0, kappa=0.5)
        self.assertAlmostEqual(u, u_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        u_actual = np.array([np.inf,0.60653066,0.31491104])
        u = y._energy(r=r_input, epsilon=1.0, kappa=0.5)
        np.testing.assert_allclose(u, u_actual)

        #test negative kappa
        with self.assertRaises(ValueError):
            u = y._energy(r=r_input, epsilon=1.0, kappa=-1.0)

    def test_force(self):
        """Test _force method"""
        y = relentless.potential.Yukawa(types=('1',))

        #test scalar r
        r_input = 0.5
        f_actual = 3.8940039
        f = y._force(r=r_input, epsilon=1.0, kappa=0.5)
        self.assertAlmostEqual(f, f_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        f_actual = np.array([np.inf,0.90979599,0.36739621])
        f = y._force(r=r_input, epsilon=1.0, kappa=0.5)
        np.testing.assert_allclose(f, f_actual)

        #test negative kappa
        with self.assertRaises(ValueError):
            u = y._force(r=r_input, epsilon=1.0, kappa=-1.0)

    def test_derivative(self):
        """Test _derivative method"""
        y = relentless.potential.Yukawa(types=('1',))

        #w.r.t. epsilon
        #test scalar r
        r_input = 0.5
        d_actual = 1.5576016
        d = y._derivative(param='epsilon', r=r_input, epsilon=1.0, kappa=0.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        d_actual = np.array([np.inf,0.60653066,0.31491104])
        d = y._derivative(param='epsilon', r=r_input, epsilon=1.0, kappa=0.5)
        np.testing.assert_allclose(d, d_actual)

        #w.r.t. kappa
        #test scalar r
        r_input = 0.5
        d_actual = -0.77880078
        d = y._derivative(param='kappa', r=r_input, epsilon=1.0, kappa=0.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([0,1,1.5])
        d_actual = np.array([-1,-0.60653066,-0.47236655])
        d = y._derivative(param='kappa', r=r_input, epsilon=1.0, kappa=0.5)
        np.testing.assert_allclose(d, d_actual)

        #test negative kappa
        with self.assertRaises(ValueError):
            u = y._derivative(param='kappa', r=r_input, epsilon=1.0, kappa=-1.0)

        #test invalid param
        with self.assertRaises(ValueError):
            u = y._derivative(param='kapppa', r=r_input, epsilon=1.0, kappa=1.0)

class test_Depletion(unittest.TestCase):
    """Unit tests for relentless.potential.Depletion"""

    def test_init(self):
        """Test creation from data"""
        dp = relentless.potential.Depletion(types=('1','2'))
        coeff = relentless.potential.PairParameters(types=('1','2'),
                                                    params=('P','sigma_i','sigma_j','sigma_d','rmin','rmax','shift'))
        self.assertCountEqual(dp.coeff.types, coeff.types)
        self.assertCountEqual(dp.coeff.params, coeff.params)

    def test_cutoff_init(self):
        """Test creation of Depletion.Cutoff from data"""
        #create object dependent on scalars
        w = relentless.potential.Depletion.Cutoff(sigma_i=1.0, sigma_j=2.0, sigma_d=0.25)
        self.assertAlmostEqual(w.value, 1.75)
        self.assertCountEqual(w.params, ('sigma_i','sigma_j','sigma_d'))
        self.assertDictEqual({p:v.value for p,v in w.depends},
                             {'sigma_i':1.0, 'sigma_j':2.0, 'sigma_d':0.25})

        #change parameter value
        w.sigma_j.value = 4.0
        self.assertAlmostEqual(w.value, 2.75)
        self.assertCountEqual(w.params, ('sigma_i','sigma_j','sigma_d'))
        self.assertDictEqual({p:v.value for p,v in w.depends},
                             {'sigma_i':1.0, 'sigma_j':4.0, 'sigma_d':0.25})

        #create object dependent on variables
        a = relentless.variable.DesignVariable(value=1.0)
        b = relentless.variable.DesignVariable(value=2.0)
        c = relentless.variable.DesignVariable(value=0.25)
        w = relentless.potential.Depletion.Cutoff(sigma_i=a, sigma_j=b, sigma_d=c)
        self.assertAlmostEqual(w.value, 1.75)
        self.assertCountEqual(w.params, ('sigma_i','sigma_j','sigma_d'))
        self.assertDictEqual({p:v for p,v in w.depends},
                             {'sigma_i':a, 'sigma_j':b, 'sigma_d':c})

        #change parameter value
        b.value = 4.0
        self.assertAlmostEqual(w.value, 2.75)
        self.assertCountEqual(w.params, ('sigma_i','sigma_j','sigma_d'))
        self.assertDictEqual({p:v for p,v in w.depends},
                             {'sigma_i':a, 'sigma_j':b, 'sigma_d':c})

    def test_cutoff_derivative(self):
        """Test Depletion.Cutoff._derivative method"""
        w = relentless.potential.Depletion.Cutoff(sigma_i=1.0, sigma_j=2.0, sigma_d=0.25)

        #calculate w.r.t. sigma_i
        dw = w._derivative('sigma_i')
        self.assertEqual(dw, 0.5)

        #calculate w.r.t. sigma_j
        dw = w._derivative('sigma_j')
        self.assertEqual(dw, 0.5)

        #calculate w.r.t. sigma_d
        dw = w._derivative('sigma_d')
        self.assertEqual(dw, 1.0)

        #invalid parameter calculation
        with self.assertRaises(ValueError):
            dw = w._derivative('sigma')

    def test_energy(self):
        """Test _energy and energy methods"""
        dp = relentless.potential.Depletion(types=('1',))

        #test scalar r
        r_input = 3
        u_actual = -4.6786414
        u = dp._energy(r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(u, u_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        u_actual = np.array([-16.59621119,0])
        u = dp._energy(r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(u, u_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            u = dp._energy(r=r_input, P=1, sigma_i=-1, sigma_j=1, sigma_d=1)
        with self.assertRaises(ValueError):
            u = dp._energy(r=r_input, P=1, sigma_i=1, sigma_j=-1, sigma_d=1)
        with self.assertRaises(ValueError):
            u = dp._energy(r=r_input, P=1, sigma_i=1, sigma_j=1, sigma_d=-1)

        #test energy outside of low/high bounds
        dp.coeff['1','1'].update(P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        r_input = np.array([1,5])
        u_actual = np.array([-25.7514468,0])
        u = dp.energy(pair=('1','1'), r=r_input)
        np.testing.assert_allclose(u, u_actual)
        self.assertAlmostEqual(dp.coeff['1','1']['rmax'].value, 4.25)

    def test_force(self):
        """Test _force and force methods"""
        dp = relentless.potential.Depletion(types=('1',))

        #test scalar r
        r_input = 3
        f_actual = -7.0682426
        f = dp._force(r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(f, f_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        f_actual = np.array([-11.54054444,0])
        f = dp._force(r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(f, f_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            f = dp._force(r=r_input, P=1, sigma_i=-1, sigma_j=1, sigma_d=1)
        with self.assertRaises(ValueError):
            f = dp._force(r=r_input, P=1, sigma_i=1, sigma_j=-1, sigma_d=1)
        with self.assertRaises(ValueError):
            f = dp._force(r=r_input, P=1, sigma_i=1, sigma_j=1, sigma_d=-1)

        #test force outside of low/high bounds
        dp.coeff['1','1'].update(P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        r_input = np.array([1,5])
        f_actual = np.array([-12.5633027,0])
        f = dp.force(pair=('1','1'), r=r_input)
        np.testing.assert_allclose(f, f_actual)
        self.assertAlmostEqual(dp.coeff['1','1']['rmax'].value, 4.25)

    def test_derivative(self):
        """Test _derivative and derivative methods"""
        dp = relentless.potential.Depletion(types=('1',))

        #w.r.t. P
        #test scalar r
        r_input = 3
        d_actual = -4.6786414
        d = dp._derivative(param='P', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        d_actual = np.array([-16.59621119,0])
        d = dp._derivative(param='P', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(d, d_actual)

        #w.r.t. sigma_i
        #test scalar r
        r_input = 3
        d_actual = -4.25424005
        d = dp._derivative(param='sigma_i', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        d_actual = np.array([-8.975979,0])
        d = dp._derivative(param='sigma_i', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(d, d_actual)

        #w.r.t. sigma_j
        #test scalar r
        r_input = 3
        d_actual = -4.04970928
        d = dp._derivative(param='sigma_j', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        d_actual = np.array([-7.573482,0])
        d = dp._derivative(param='sigma_j', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(d, d_actual)

        #w.r.t. sigma_d
        #test scalar r
        r_input = 3
        d_actual = -8.30394933
        d = dp._derivative(param='sigma_d', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        self.assertAlmostEqual(d, d_actual)

        #test array r
        r_input = np.array([1.75,4.25])
        d_actual = np.array([-16.549461,0])
        d = dp._derivative(param='sigma_d', r=r_input, P=1, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        np.testing.assert_allclose(d, d_actual)

        #test negative sigma
        with self.assertRaises(ValueError):
            d = dp._derivative(param='P', r=r_input, P=1, sigma_i=-1, sigma_j=1, sigma_d=1)
        with self.assertRaises(ValueError):
            d = dp._derivative(param='P', r=r_input, P=1, sigma_i=1, sigma_j=-1, sigma_d=1)
        with self.assertRaises(ValueError):
            d = dp._derivative(param='P', r=r_input, P=1, sigma_i=1, sigma_j=1, sigma_d=-1)

        #test invalid param
        with self.assertRaises(ValueError):
            d = dp._derivative(param='sigmaj', r=r_input, P=1, sigma_i=1, sigma_j=1, sigma_d=1)

        #test derivative outside of low/high bounds
        P_var = relentless.variable.DesignVariable(value=1.0)
        dp.coeff['1','1'].update(P=P_var, sigma_i=1.5, sigma_j=2, sigma_d=2.5)
        r_input = np.array([1,5])
        d_actual = np.array([-25.7514468,0])
        d = dp.derivative(pair=('1','1'), var=P_var, r=r_input)
        np.testing.assert_allclose(d, d_actual)
        self.assertAlmostEqual(dp.coeff['1','1']['rmax'].value, 4.25)

if __name__ == '__main__':
    unittest.main()
