import json
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
from shangrla.IRVAssertionUtils import NEN, NEB, parseAuditFileIntoAuditsArray, \
    parseAssertionsAndApparentWinnersAndLosers, parseAssertionsIntoDict


#######################################################################################################

class TestIRVAssertionUtils:

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
        assert test_nen1.continuing == {'17','18'}
        assert test_nen1.continuing == {'18','17'}

        test_nen2 = NEN(nen_assertions[0]["winner"], nen_assertions[0]["loser"], {}, candidate_set)
        assert test_nen2.continuing == candidate_set

        test_nen3 = NEN(nen_assertions[0]["winner"], nen_assertions[0]["loser"], {"17","18"}, candidate_set)
        assert test_nen3.continuing == {'15','16','45'}

        ##TODO - think about bad input, e.g. when already_eliminated is not a subset of candidate_set, or the winners
        # and losers are not in the candidates set, and decide what to do about it.

    def test_RCV_RAIRE_json_data_parsing(self):
        # An example assertion-only file used by RAIRE.
        a_file = open("../../Examples/Data/SF2019Nov8Assertions.json")
        # An example log file output by the SHANGRLA audit process
        # a_file = open("Data/log.json")
        auditfile = json.load(a_file)

        c_file = open("../../Examples/Data/CandidateManifest.json")
        candidatefile = json.load(c_file)

        IsRLALogFile: bool
        (auditsArray, IsRLALogFile) = parseAuditFileIntoAuditsArray(auditfile, candidatefile)
        assert IsRLALogFile == False
        assert len(auditsArray) == 1

        (assertions,apparentWinner,apparentNonWinners) = parseAssertionsAndApparentWinnersAndLosers(auditsArray[0], candidatefile, IsRLALogFile)
        assert apparentWinner == "SUZY LOFTUS"
        assert apparentNonWinners == [('45', 'Write-in'), ('16', 'LEIF DAUTCH'), ('17', 'NANCY TUNG'), ('18', 'CHESA BOUDIN')]

        assertionDict = parseAssertionsIntoDict(auditsArray[0],IsRLALogFile)
        print(assertionDict)

    def test_rcv_assorter(self):
        import json
        with open('./Data/334_361_vbm.json') as fid:
            data = json.load(fid)
            AvB = Contest.from_dict({'id': 'AvB',
                     'name': 'AvB',
                     'risk_limit': 0.05,
                     'cards': 10**4,
                     'choice_function': Contest.SOCIAL_CHOICE_FUNCTION.IRV,
                     'n_winners': 1,
                     'test': NonnegMean.alpha_mart,
                     'use_style': True
                })
            assertions = {}
            for audit in data['audits']:
                cands = [audit['winner']]
                for elim in audit['eliminated']:
                    cands.append(elim)
                all_assertions = Assertion.make_assertions_from_json(contest=AvB, candidates=cands,
                                                                     json_assertions=audit['assertions'])
                assertions[audit['contest']] = all_assertions

            # winner only assertion
            assorter = assertions['334']['5 v 47'].assorter

            votes = CVR.from_vote({'5': 1, '47': 2})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'47': 1, '5': 2})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'3': 1, '6': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'3': 1, '47': 2})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'3': 1, '5': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            # elimination assertion
            assorter = assertions['334']['5 v 3 elim 1 6 47'].assorter

            votes = CVR.from_vote({'5': 1, '47': 2})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'47': 1, '5': 2})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'6': 1, '1': 2, '3': 3, '5': 4})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'3': 1, '47': 2})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'6': 1, '47': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'6': 1, '47': 2, '5': 3})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            # winner-only assertion
            assorter = assertions['361']['28 v 50'].assorter

            votes = CVR.from_vote({'28': 1, '50': 2})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'27': 1, '28': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1, '28': 2})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'27': 1, '26': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            # elimination assertion
            assorter = assertions['361']['27 v 26 elim 28 50'].assorter

            votes = CVR.from_vote({'27': 1})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1, '27': 2})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1, '50': 2, '27': 3})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1, '27': 2, '50': 3})
            assert assorter.assort(votes) == 1, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'26': 1})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1, '26': 2})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1, '50': 2, '26': 3})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1, '26': 2, '50': 3})
            assert assorter.assort(votes) == 0, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'50': 1, '28': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

            votes = CVR.from_vote({'28': 1, '50': 2})
            assert assorter.assort(votes) == 0.5, f'{assorter.assort(votes)=}'

##########################################################################################
if __name__ == "__main__":
    sys.exit(pytest.main(["-qq"], plugins=None))
