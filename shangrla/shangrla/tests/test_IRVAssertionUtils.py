import typing
import sys
import pytest
import coverage
from numpy import testing
from collections import OrderedDict, defaultdict
from cryptorandom.cryptorandom import SHA256, random, int_from_hash
from cryptorandom.sample import random_permutation
from cryptorandom.sample import sample_by_index


from shangrla.Audit import Audit, Assertion, Assorter, Contest, CVR, Stratum
from shangrla.NonnegMean import NonnegMean
from shangrla.Dominion import Dominion
from shangrla.Hart import Hart
from shangrla.IRVAssertionUtils import NEN, NEB

#######################################################################################################

class TestAudit:

    def test_from_assertions(self):
        candidate_set = {'45','15','16','17','18'}
        neb_assertions = [
            {
                    "winner": "18",
                    "loser": "15",
                    "already_eliminated": "",
                    "assertion_type": "WINNER_ONLY",
                    "explanation": "Rules out case where 18 is eliminated before 15"
            }
        ]
        nen_assertions = [
            {
                "winner": "18",
                "loser": "17",
                "already_eliminated": [
                    "15",
                    "16",
                    "45"
                ],
                "assertion_type": "IRV_ELIMINATION",
                "explanation": "Rules out outcomes with tail [... 18 17]"
            },
            {
                "winner": "17",
                "loser": "16",
                "already_eliminated": [
                    "15",
                    "18",
                    "45"
                ],
                "assertion_type": "IRV_ELIMINATION",
                "explanation": "Rules out outcomes with tail [... 17 16]"
            }
        ]
        test_neb = NEB(neb_assertions[0]["winner"], neb_assertions[0]["loser"])
        assert test_neb.winner == '18'
        assert test_neb.loser == '15'

        test_nen1 = NEN(nen_assertions[0]["winner"], nen_assertions[0]["loser"], nen_assertions[0]["already_eliminated"], candidate_set)
        assert test_nen1.winner == nen_assertions[0]["winner"]
        assert test_nen1.loser == nen_assertions[0]["loser"]
        assert test_nen1.standing == {'17','18'}
        assert test_nen1.standing == {'18','17'}

        test_nen2 = NEN(nen_assertions[0]["winner"], nen_assertions[0]["loser"], {}, candidate_set)
        assert test_nen2.standing == candidate_set

        test_nen3 = NEN(nen_assertions[0]["winner"], nen_assertions[0]["loser"], {"17","18"}, candidate_set)
        assert test_nen3.standing == {'15','16','45'}

        ##TODO - think about bad input, e.g. when already_eliminated is not a subset of candidate_set, or the winners
        # and losers are not in the candidates set, and decide what to do about it.


##########################################################################################
if __name__ == "__main__":
    sys.exit(pytest.main(["-qq"], plugins=None))
