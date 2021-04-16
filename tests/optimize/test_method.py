"""Unit tests for method module."""
import unittest

import relentless

from .test_objective import QuadraticObjective

class test_LineSearch(unittest.TestCase):
    """Unit tests for relentless.optimize.LineSearch"""

    def test_init(self):
        """Test creation with data."""
        x = relentless.variable.DesignVariable(value=3.0)
        q = QuadraticObjective(x=x)

        l = relentless.optimize.LineSearch(rel_tol=1e-8, max_iter=1000)
        self.assertAlmostEqual(l.rel_tol, 1e-8)
        self.assertEqual(l.max_iter, 1000)

        #test invalid parameters
        with self.assertRaises(ValueError):
            l.max_iter = 0
        with self.assertRaises(TypeError):
            l.max_iter = 100.0
        with self.assertRaises(ValueError):
            l.rel_tol = -1e-9
        with self.assertRaises(TypeError):
            l.rel_tol = {x:1e-9}
        with self.assertRaises(ValueError):
            l.rel_tol = 1

    def test_find(self):
        """Test find method."""
        l = relentless.optimize.LineSearch(rel_tol=1e-8, max_iter=1000)
        x = relentless.variable.DesignVariable(value=-3.0)
        q = QuadraticObjective(x=x)
        res_1 = q.compute()

        #bracketing the minimum (find step size that takes function to minimum)
        x.value = 3.0
        res_2 = q.compute()
        x.value = -3.0
        res_new = l.find(objective=q, start=res_1, end=res_2)
        self.assertAlmostEqual(res_new.design_variables[x], 1.0)
        self.assertAlmostEqual(res_new.gradient[x], 0.0)
        self.assertEqual(q.x.value, -3.0)

        #not bracketing the minimum (accept "maximum" step size)
        x.value = -1.0
        res_3 = q.compute()
        x.value = -3.0
        res_new = l.find(objective=q, start=res_1, end=res_3)
        self.assertAlmostEqual(res_new.design_variables[x], -1.0)
        self.assertAlmostEqual(res_new.gradient[x], -4.0)
        self.assertEqual(q.x.value, -3.0)

        #bound does not include current objective value
        res_new = l.find(objective=q, start=res_3, end=res_2)
        self.assertAlmostEqual(res_new.design_variables[x], 1.0)
        self.assertAlmostEqual(res_new.gradient[x], 0.0)
        self.assertEqual(q.x.value, -3.0)

        #invalid search interval (not descent direction)
        with self.assertRaises(ValueError):
            res_new = l.find(objective=q, start=res_3, end=res_1)

        #invalid search interval (0 distance from start to end)
        with self.assertRaises(ValueError):
            res_new = l.find(objective=q, start=res_3, end=res_3)

class test_SteepestDescent(unittest.TestCase):
    """Unit tests for relentless.optimize.SteepestDescent"""

    def test_init(self):
        """Test creation with data."""
        x = relentless.variable.DesignVariable(value=3.0)
        q = QuadraticObjective(x=x)
        t = relentless.optimize.AbsoluteGradientTest(tolerance=1e-8)

        o = relentless.optimize.SteepestDescent(stop=t, max_iter=1000, step_size=0.25)
        self.assertEqual(o.stop, t)
        self.assertEqual(o.max_iter, 1000)
        self.assertAlmostEqual(o.step_size, 0.25)
        self.assertAlmostEqual(o.scale, 1.0)
        self.assertIsNone(o.line_search)

        #test scalar scaling parameter
        o.scale = 0.5
        self.assertEqual(o.stop, t)
        self.assertEqual(o.max_iter, 1000)
        self.assertAlmostEqual(o.step_size, 0.25)
        self.assertAlmostEqual(o.scale, 0.5)
        self.assertIsNone(o.line_search)

        #test dictionary of scaling parameters
        o.scale = {x:0.3}
        self.assertEqual(o.stop, t)
        self.assertEqual(o.max_iter, 1000)
        self.assertAlmostEqual(o.step_size, 0.25)
        self.assertDictEqual(o.scale, {x:0.3})
        self.assertIsNone(o.line_search)

        #test using line search
        l = relentless.optimize.LineSearch(rel_tol=1e-9, max_iter=100)
        o.line_search = l
        self.assertEqual(o.stop, t)
        self.assertEqual(o.max_iter, 1000)
        self.assertAlmostEqual(o.step_size, 0.25)
        self.assertDictEqual(o.scale, {x:0.3})
        self.assertEqual(o.line_search, l)

        #test invalid parameters
        with self.assertRaises(TypeError):
            o.stop = 1e-8
        with self.assertRaises(ValueError):
            o.max_iter = 0
        with self.assertRaises(TypeError):
            o.max_iter = 100.0
        with self.assertRaises(ValueError):
            o.step_size = -0.25
        with self.assertRaises(ValueError):
            o.scale = -0.5
        with self.assertRaises(ValueError):
            o.scale = {x:-0.5}
        with self.assertRaises(TypeError):
            o.line_search = q

    def test_run(self):
        """Test run method."""
        x = relentless.variable.DesignVariable(value=3.0)
        q = QuadraticObjective(x=x)
        t = relentless.optimize.AbsoluteGradientTest(tolerance=1e-8)
        o = relentless.optimize.SteepestDescent(stop=t, max_iter=1000, step_size=0.25)

        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test insufficient maximum iterations
        x.value = 1.5
        o.max_iter = 1
        self.assertFalse(o.optimize(objective=q))

        #test with nontrivial scalar scaling parameter
        x.value = 50
        o.scale = 0.85
        o.max_iter = 1000
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test with nontrivial dictionary of scaling parameters
        x.value = -35
        o.scale = {x:1.5}
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test using line search option
        x.value = 3
        o.line_search = relentless.optimize.LineSearch(rel_tol=1e-5, max_iter=100)
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

class test_FixedStepDescent(unittest.TestCase):
    """Unit tests for relentless.optimize.FixedStepDescent"""

    def test_run(self):
        """Test run method."""
        x = relentless.variable.DesignVariable(value=3.0)
        q = QuadraticObjective(x=x)
        t = relentless.optimize.AbsoluteGradientTest(tolerance=1e-8)
        o = relentless.optimize.FixedStepDescent(stop=t, max_iter=1000, step_size=0.25)

        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test insufficient maximum iterations
        x.value = 1.5
        o.max_iter = 1
        self.assertFalse(o.optimize(objective=q))

        #test step size that does not converge
        x.value = 1.5
        o.step_size = 0.42
        o.max_iter = 10000
        self.assertFalse(o.optimize(objective=q))

        #test with nontrivial scalar scaling parameter
        x.value = 50
        o.step_size = 0.25
        o.scale = 4.0
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test with nontrivial dictionary of scaling parameters
        x.value = -35
        o.scale = {x:1.5}
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)

        #test using line search option
        x.value = 3
        o.line_search = relentless.optimize.LineSearch(rel_tol=1e-5, max_iter=100)
        self.assertTrue(o.optimize(objective=q))
        self.assertAlmostEqual(x.value, 1.0)
