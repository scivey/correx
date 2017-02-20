import unittest
from correx.config.pg import MetadataCodec
from copy import deepcopy

class TestMetadataCodec(unittest.TestCase):
    def test_encode_decode(self):
        metadata = {'x': 'x-val', 'y': 'y-val'}
        query = 'select col_x, col_y from bar where col_x > 10;'

        # deep copy is normally not necessary on the metadata dict.
        # only done here to be extra sure of what we're testing when
        # we compare decoded result to existing value of `metadata`
        encoded_query = MetadataCodec.encode(
            query=query,
            metadata=deepcopy(metadata)
        )
        decoded_metadata, decoded_query = MetadataCodec.decode(encoded_query)
        self.assertEqual(metadata, decoded_metadata)
        self.assertEqual(query, decoded_query.strip())


