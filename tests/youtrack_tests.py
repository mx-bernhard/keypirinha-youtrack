import os
import unittest
from typing import Sequence

from lib.api import Api, IntellisenseResult

TESTDATA_FILENAME = os.path.join(os.path.dirname(__file__), 'intellisense_result.xml')

class TestApi:

    def setup_class(self):
        self.testdata = open(TESTDATA_FILENAME).read()

    def test_read_issues(self):
        dummyDbg = lambda x: None
        fixture = Api("no token", "https://foo.com", dummyDbg)
        #fixture.get_intellisense_suggestions("test")

        res: Sequence[IntellisenseResult] = fixture.parse_intellisense_suggestions(self.testdata.encode("UTF-8"))
        assert len(res) == 4
        assert self.equals(res[0],IntellisenseResult(start=0,end=2,description="by updated",option="updated",full_option="updated:",prefix=None,suffix=":"))

    def equals(self, one:IntellisenseResult, two:IntellisenseResult):
        return one.description == two.description \
               and one.suffix == two.suffix \
               and one.end ==two.end \
               and one.full_option == two.full_option \
               and one.option==two.option \
               and one.prefix==two.prefix \
               and one.start==two.start