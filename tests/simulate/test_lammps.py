"""Unit tests for relentless.simulate.lammps."""
import tempfile
import unittest

import lammps
import numpy as np

import relentless
from ..potential.test_pair import LinPot

class test_LAMMPS(unittest.TestCase):
    """Unit tests for relentless.LAMMPS"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.directory = relentless.Directory(self._tmp.name)

    #mock (NVT) ensemble and potential for testing
    def ens_pot(self):
        ens = relentless.Ensemble(T=2.0, V=relentless.Cube(L=10.0), N={'1':2,'2':3})
        ens.P = 2.5

        # setup potentials
        pot = LinPot(ens.types,params=('m',))
        for pair in pot.coeff:
            pot.coeff[pair]['m'] = 2.0
        pots = relentless.simulate.Potentials()
        pots.pair.potentials.append(pot)
        pots.pair.rmax = 10.0
        pots.pair.num = 11

        return (ens,pots)

    def create_file(self):
        file_ = self.directory.file('test.data')
        with open(file_,'w') as f:
            f.write(('LAMMPS test data\n'
                     '\n'
                     '5 atoms\n'
                     '2 atom types\n'
                     '\n'
                     '0.0 10.0 xlo xhi\n'
                     '0.0 10.0 ylo yhi\n'
                     '0.0 10.0 zlo zhi\n'
                     '\n'
                     'Atoms\n'
                     '\n'
                     '1 1 1.0 1.0 1.0\n'
                     '2 1 3.0 3.0 3.0\n'
                     '3 2 5.0 5.0 5.0\n'
                     '4 2 7.0 7.0 7.0\n'
                     '5 2 9.0 9.0 9.0\n'
                     '\n'
                     'Masses\n'
                     '\n'
                     '1 0.3\n'
                     '2 0.1'))
        return file_

    def test_initialize(self):
        """Test running initialization simulation operations."""
        #InitializeFromFile
        ens,pot = self.ens_pot()
        file_ = self.create_file()
        op = relentless.simulate.lammps.InitializeFromFile(filename=file_, neighbor_buffer=0.4)
        l = relentless.simulate.lammps.LAMMPS(operations=op, quiet=False)
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertIsNotNone(pl.system)

        #InitializeRandomly
        op = relentless.simulate.lammps.InitializeRandomly(seed=1, neighbor_buffer=0.4)
        l = relentless.simulate.lammps.LAMMPS(operations=op, quiet=False)
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertIsNotNone(pl.system)

    def test_minimization(self):
        """Test running energy minimization simulation operation."""
        #MinimizeEnergy
        ens,pot = self.ens_pot()
        file_ = self.create_file()
        op = [relentless.simulate.lammps.InitializeFromFile(filename=file_, neighbor_buffer=0.4),
              relentless.simulate.lammps.MinimizeEnergy(energy_tolerance=1e-7,
                                                        force_tolerance=1e-7,
                                                        max_iterations=1000,
                                                        dt=0.01)
             ]
        l = relentless.simulate.lammps.LAMMPS(operations=op, quiet=False)
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)

    def test_integrators(self):
        """Test adding and removing integrator operations."""
        default_fixes = [{'name':''}]

        file_ = self.create_file()
        init = relentless.simulate.lammps.InitializeFromFile(filename=file_, neighbor_buffer=0.4)
        l = relentless.simulate.lammps.LAMMPS(operations=init, quiet=False)

        #LangevinIntegrator
        ens,pot = self.ens_pot()
        lgv = relentless.simulate.lammps.AddLangevinIntegrator(dt=0.5,
                                                               friction=1.5,
                                                               seed=2)
        lgv_r = relentless.simulate.lammps.RemoveLangevinIntegrator(add_op=lgv)
        l.operations = [init, lgv]
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertCountEqual(pl.fixes, default_fixes+[{'name':'1','style':'langevin','group':'all'},
                                                       {'name':'2','style':'nve','group':'all'}])
        lgv_r(sim)
        self.assertCountEqual(pl.fixes, default_fixes)

        lgv = relentless.simulate.lammps.AddLangevinIntegrator(dt=0.5,
                                                               friction={'1':2.0,'2':5.0},
                                                               seed=2)
        lgv_r = relentless.simulate.lammps.RemoveLangevinIntegrator(add_op=lgv)
        l.operations = [init, lgv]
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertCountEqual(pl.fixes, default_fixes+[{'name':'3','style':'langevin','group':'all'},
                                                       {'name':'4','style':'nve','group':'all'}])
        lgv_r(sim)
        self.assertCountEqual(pl.fixes, default_fixes)

        #NPTIntegrator
        ens_npt = relentless.Ensemble(T=100.0, P=5.5, N={'A':2,'B':3})
        ens_npt.V = relentless.Cube(L=10.0)
        npt = relentless.simulate.lammps.AddNPTIntegrator(dt=0.5,
                                                          tau_T=1.0,
                                                          tau_P=1.5)
        npt_r = relentless.simulate.lammps.RemoveNPTIntegrator(add_op=npt)
        l.operations = [init, npt]
        sim = l.run(ensemble=ens_npt, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertCountEqual(pl.fixes, default_fixes+[{'name':'1','style':'npt','group':'all'}])
        npt_r(sim)
        self.assertCountEqual(pl.fixes, default_fixes)

        #NVTIntegrator
        nvt = relentless.simulate.lammps.AddNVTIntegrator(dt=0.5,
                                                          tau_T=1.0)
        nvt_r = relentless.simulate.lammps.RemoveNVTIntegrator(add_op=nvt)
        l.operations = [init, nvt]
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)
        pl = lammps.PyLammps(ptr=sim.lammps)
        self.assertCountEqual(pl.fixes, default_fixes+[{'name':'1','style':'nvt','group':'all'}])
        nvt_r(sim)
        self.assertCountEqual(pl.fixes, default_fixes)

    def test_run(self):
        """Test run simulation operations."""
        init = relentless.simulate.lammps.InitializeRandomly(seed=1, neighbor_buffer=0.4)
        l = relentless.simulate.lammps.LAMMPS(operations=init, quiet=False)

        #Run
        ens,pot = self.ens_pot()
        run = relentless.simulate.lammps.Run(steps=1000)
        l.operations = [init,run]
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)

        #RunUpTo
        run = relentless.simulate.lammps.RunUpTo(step=999)
        l.operations = [init,run]
        sim = l.run(ensemble=ens, potentials=pot, directory=self.directory)

    def tearDown(self):
        self._tmp.cleanup()

if __name__ == '__main__':
    unittest.main()
