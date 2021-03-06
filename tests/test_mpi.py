"""Unit tests for mpi module."""
import unittest

import os
import tempfile
import numpy as np

import relentless
try:
    import mpi4py.MPI as MPI
except ImportError:
    pass

has_mpi = relentless.mpi._mpi_running()

class test_Communicator(unittest.TestCase):
    def setUp(self):
        self.comm = relentless.mpi.world

    def test_init(self):
        if has_mpi:
            self.assertTrue(self.comm.comm is MPI.COMM_WORLD)
            self.assertTrue(self.comm.enabled)
            self.assertEqual(self.comm.size, MPI.COMM_WORLD.Get_size())
            self.assertEqual(self.comm.rank, MPI.COMM_WORLD.Get_rank())
            self.assertEqual(self.comm.root,0)
        else:
            self.assertTrue(self.comm.comm is None)
            self.assertFalse(self.comm.enabled)
            self.assertEqual(self.comm.size,1)
            self.assertEqual(self.comm.rank,0)
            self.assertEqual(self.comm.root,0)

    @unittest.skipUnless(has_mpi,"Needs MPI")
    def test_split(self):
        world = MPI.COMM_WORLD.Dup()
        self.assertTrue(world is not MPI.COMM_WORLD)

        comm = relentless.mpi.Communicator(world)
        self.assertTrue(comm is not relentless.mpi.world)

    def test_bcast(self):
        # broadcast from default root
        if self.comm.rank == self.comm.root:
            x = 42
        else:
            x = None
        x = self.comm.bcast(x)
        self.assertEqual(x, 42)

        # broadcast from specified root
        if self.comm.size >= 2:
            root = 1
            if self.comm.rank == root:
                x = 7
            else:
                x = None
            x = self.comm.bcast(x,root=root)
            self.assertEqual(x, 7)

    def test_bcast_numpy(self):
        # float array
        if self.comm.rank == self.comm.root:
            x = np.array([1.,2.],dtype=np.float64)
        else:
            x = None
        x = self.comm.bcast_numpy(x)
        self.assertEqual(x.shape,(2,))
        self.assertEqual(x.dtype,np.float64)
        np.testing.assert_allclose(x,[1.,2.])

        # float array from specified root
        if self.comm.size >= 2:
            root = 1
            if self.comm.rank == root:
                x = np.array([3.,4.],dtype=np.float64)
            else:
                x = None
            x = self.comm.bcast_numpy(x,root=root)
            self.assertEqual(x.shape,(2,))
            self.assertEqual(x.dtype,np.float64)
            np.testing.assert_allclose(x,[3.,4.])

        # prealloc'd float array
        if self.comm.rank == self.comm.root:
            x = np.array([5.,6.],dtype=np.float64)
        else:
            x = np.zeros((2,),dtype=np.float64)
        y = self.comm.bcast_numpy(x)
        self.assertTrue(y is x)
        self.assertEqual(y.shape,(2,))
        self.assertEqual(y.dtype,np.float64)
        np.testing.assert_allclose(y,[5.,6.])

        # incorrectly alloc'd float array
        print('')
        if self.comm.rank == self.comm.root:
            x = np.array([5.,6.],dtype=np.float64)
        else:
            x = np.zeros((2,),dtype=np.int32)
        y = self.comm.bcast_numpy(x)
        if self.comm.rank == self.comm.root:
            self.assertTrue(y is x)
        else:
            self.assertTrue(y is not x)
        self.assertEqual(y.shape,(2,))
        self.assertEqual(y.dtype,np.float64)
        np.testing.assert_allclose(y,[5.,6.])

    def test_loadtxt(self):
        # create file
        if self.comm.rank == self.comm.root:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tmp.write(b'1 2\n 3 4\n')
            tmp.close()
            filename = tmp.name
        else:
            filename = None
        filename = self.comm.bcast(filename)

        # load data
        dat = self.comm.loadtxt(filename)

        # unlink before testing in case an exception gets raised
        if self.comm.rank == self.comm.root:
            os.unlink(tmp.name)

        np.testing.assert_allclose(dat, [[1.,2.],[3.,4.]])

if __name__ == '__main__':
    unittest.main()
