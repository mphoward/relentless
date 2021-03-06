"""Unit tests for dilute module."""
import tempfile
import unittest

import numpy as np

import relentless

from ..potential.test_pair import LinPot

class test_Dilute(unittest.TestCase):
    """Unit tests for relentless.simulate.Dilute"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = relentless.data.Directory(self._tmp.name)

    def test_run(self):
        """Test run method."""
        analyzer = relentless.simulate.dilute.AddEnsembleAnalyzer()
        ens = relentless.ensemble.Ensemble(T=1.0, V=relentless.volume.Cube(L=2.0), N={'A':2,'B':3})

        #set up potentials
        pot = LinPot(ens.types,params=('m',))
        for pair in pot.coeff:
            pot.coeff[pair]['m'] = 2.0
        pots = relentless.simulate.Potentials()
        pots.pair.potentials.append(pot)
        pots.pair.rmax = 3.0
        pots.pair.num = 4

        d = relentless.simulate.dilute.Dilute(operations=analyzer)
        sim = d.run(ensemble=ens, potentials=pots, directory=self.directory)
        ens_ = analyzer.extract_ensemble(sim)
        self.assertAlmostEqual(ens_.P, -207.5228556)

        #invalid ensemble (non-NVT)
        ens_ = relentless.ensemble.Ensemble(T=1, V=relentless.volume.Cube(1), N={'A':2}, mu={'B':0.2})
        d = relentless.simulate.dilute.Dilute(analyzer)
        with self.assertRaises(ValueError):
            d.run(ensemble=ens_, potentials=pots, directory=self.directory)

    def tearDown(self):
        self._tmp.cleanup()

if __name__ == '__main__':
    unittest.main()
