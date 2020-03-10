from pytest import raises

import numpy as np
from numpy.testing import assert_equal

from h5py._hl.selections import Selection

from ..backend import CHUNK_SIZE
from ..api import VersionedHDF5File, spaceid_to_slice

from .test_backend import setup

def test_stage_version():
    with setup() as f:
        file = VersionedHDF5File(f)

        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                                    2*np.ones((CHUNK_SIZE,)),
                                    3*np.ones((CHUNK_SIZE,))))


        with file.stage_version('version1', '') as group:
            group['test_data'] = test_data

        version1 = file['version1']
        assert version1.attrs['prev_version'] == '__first_version__'
        assert_equal(version1['test_data'], test_data)

        ds = f['/_version_data/test_data/raw_data']

        assert ds.shape == (3*CHUNK_SIZE,)
        assert_equal(ds[0:1*CHUNK_SIZE], 1.0)
        assert_equal(ds[1*CHUNK_SIZE:2*CHUNK_SIZE], 2.0)
        assert_equal(ds[2*CHUNK_SIZE:3*CHUNK_SIZE], 3.0)

        with file.stage_version('version2', 'version1') as group:
            group['test_data'][0] = 0.0

        version2 = file['version2']
        assert version2.attrs['prev_version'] == 'version1'
        test_data[0] = 0.0
        assert_equal(version2['test_data'], test_data)

        assert ds.shape == (4*CHUNK_SIZE,)
        assert_equal(ds[0:1*CHUNK_SIZE], 1.0)
        assert_equal(ds[1*CHUNK_SIZE:2*CHUNK_SIZE], 2.0)
        assert_equal(ds[2*CHUNK_SIZE:3*CHUNK_SIZE], 3.0)
        assert_equal(ds[3*CHUNK_SIZE], 0.0)
        assert_equal(ds[3*CHUNK_SIZE+1:4*CHUNK_SIZE], 1.0)

def test_version_int_slicing():
    with setup() as f:
        file = VersionedHDF5File(f)
        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                               2*np.ones((CHUNK_SIZE,)),
                               3*np.ones((CHUNK_SIZE,))))

        with file.stage_version('version1', '') as group:
            group['test_data'] = test_data

        with file.stage_version('version2', 'version1') as group:
            group['test_data'][0] = 2.0

        with file.stage_version('version3', 'version2') as group:
            group['test_data'][0] = 3.0

        with file.stage_version('version2_1', 'version1', make_current=False) as group:
            group['test_data'][0] = 2.0


        assert file[0]['test_data'][0] == 3.0

        with raises(KeyError):
            file['bad']

        with raises(IndexError):
            file[1]

        assert file[-1]['test_data'][0] == 2.0
        assert file[-2]['test_data'][0] == 1.0, file[-2]
        with raises(IndexError):
            file[-3]

        file.current_version = 'version2'

        assert file[0]['test_data'][0] == 2.0
        assert file[-1]['test_data'][0] == 1.0
        with raises(IndexError):
            file[-2]

        file.current_version = 'version2_1'

        assert file[0]['test_data'][0] == 2.0
        assert file[-1]['test_data'][0] == 1.0
        with raises(IndexError):
            file[-2]

        file.current_version = 'version1'

        assert file[0]['test_data'][0] == 1.0
        with raises(IndexError):
            file[-1]

def test_version_name_slicing():
    with setup() as f:
        file = VersionedHDF5File(f)
        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                               2*np.ones((CHUNK_SIZE,)),
                               3*np.ones((CHUNK_SIZE,))))

        with file.stage_version('version1', '') as group:
            group['test_data'] = test_data

        with file.stage_version('version2', 'version1') as group:
            group['test_data'][0] = 2.0

        with file.stage_version('version3', 'version2') as group:
            group['test_data'][0] = 3.0

        with file.stage_version('version2_1', 'version1', make_current=False) as group:
            group['test_data'][0] = 2.0


        assert file[0]['test_data'][0] == 3.0

        with raises(IndexError):
            file[1]

        assert file[-1]['test_data'][0] == 2.0
        assert file[-2]['test_data'][0] == 1.0, file[-2]

def test_iter_versions():
    with setup() as f:
        file = VersionedHDF5File(f)
        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                               2*np.ones((CHUNK_SIZE,)),
                               3*np.ones((CHUNK_SIZE,))))

        with file.stage_version('version1', '') as group:
            group['test_data'] = test_data

        with file.stage_version('version2', 'version1') as group:
            group['test_data'][0] = 2.0

        assert set(file) == {'version1', 'version2'}

        # __contains__ is implemented from __iter__ automatically
        assert 'version1' in file
        assert 'version2' in file
        assert 'version3' not in file

def test_create_dataset():
    with setup() as f:
        file = VersionedHDF5File(f)


        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                                    2*np.ones((CHUNK_SIZE,)),
                                    3*np.ones((CHUNK_SIZE,))))


        with file.stage_version('version1', '') as group:
            group.create_dataset('test_data', data=test_data)

        version1 = file['version1']
        assert version1.attrs['prev_version'] == '__first_version__'
        assert_equal(version1['test_data'], test_data)

        ds = f['/_version_data/test_data/raw_data']

        assert ds.shape == (3*CHUNK_SIZE,)
        assert_equal(ds[0:1*CHUNK_SIZE], 1.0)
        assert_equal(ds[1*CHUNK_SIZE:2*CHUNK_SIZE], 2.0)
        assert_equal(ds[2*CHUNK_SIZE:3*CHUNK_SIZE], 3.0)

def test_unmodified():
    with setup() as f:
        file = VersionedHDF5File(f)

        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                                    2*np.ones((CHUNK_SIZE,)),
                                    3*np.ones((CHUNK_SIZE,))))

        with file.stage_version('version1') as group:
            group.create_dataset('test_data', data=test_data)
            group.create_dataset('test_data2', data=test_data)

        assert set(f['_version_data/versions/version1']) == {'test_data', 'test_data2'}
        assert set(file['version1']) == {'test_data', 'test_data2'}
        assert_equal(file['version1']['test_data'], test_data)
        assert_equal(file['version1']['test_data2'], test_data)
        assert file['version1'].datasets().keys() == {'test_data', 'test_data2'}

        with file.stage_version('version2') as group:
            group['test_data2'][0] = 0.0

        assert set(f['_version_data/versions/version2']) == {'test_data', 'test_data2'}
        assert set(file['version2']) == {'test_data', 'test_data2'}
        assert_equal(file['version2']['test_data'], test_data)
        assert_equal(file['version2']['test_data2'][0], 0.0)
        assert_equal(file['version2']['test_data2'][1:], test_data[1:])

def test_delete():
    with setup() as f:
        file = VersionedHDF5File(f)

        test_data = np.concatenate((np.ones((2*CHUNK_SIZE,)),
                                    2*np.ones((CHUNK_SIZE,)),
                                    3*np.ones((CHUNK_SIZE,))))

        with file.stage_version('version1') as group:
            group.create_dataset('test_data', data=test_data)
            group.create_dataset('test_data2', data=test_data)

        with file.stage_version('version2') as group:
            del group['test_data2']

        assert set(f['_version_data/versions/version2']) == {'test_data'}
        assert set(file['version2']) == {'test_data'}
        assert_equal(file['version2']['test_data'], test_data)
        assert file['version2'].datasets().keys() == {'test_data'}

def test_spaceid_to_slice():
    with setup() as f:
        shape = 10
        a = f.create_dataset('a', data=np.arange(shape))

        for start in range(0, shape):
            for count in range(0, shape):
                for stride in range(1, shape):
                    for block in range(0, shape):
                        if count != 1 and block != 1:
                            # Not yet supported. Doesn't seem to be supported
                            # by HDF5 either (?)
                            continue

                        spaceid = a.id.get_space()
                        spaceid.select_hyperslab((start,), (count,),
                                                 (stride,), (block,))
                        sel = Selection((shape,), spaceid)
                        try:
                            a[sel]
                        except ValueError:
                            # HDF5 doesn't allow stride/count combinations
                            # that are impossible (the count must be the exact
                            # number of elements in the selected block).
                            # Rather than trying to enumerate those here, we
                            # just check what doesn't give an error.
                            continue
                        try:
                            s = spaceid_to_slice(spaceid)
                        except:
                            print(start, count, stride, block)
                            raise
                        assert_equal(a[s], a[sel], f"{(start, count, stride, block)}")

def test_large_dataset():
    # Test that large datasets aren't read into memory.
    with setup() as f:
        # A dataset of zeros that would take 80 GB if put into memory.
        # However, since the dataset is empty, hdf5 is able to represent it
        # without storing very much data on disk.
        file = VersionedHDF5File(f)
        with file.stage_version('version1') as group:
            group.create_dataset('large', shape=(10000000000,), dtype=np.float64)
