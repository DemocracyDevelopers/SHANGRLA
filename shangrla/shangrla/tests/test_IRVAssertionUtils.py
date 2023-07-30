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
from collections import Counter


from shangrla.Audit import Audit, Assertion, Assorter, Contest, CVR, Stratum
from shangrla.NonnegMean import NonnegMean
from shangrla.Dominion import Dominion
from shangrla.Hart import Hart
from shangrla.IRVAssertionUtils import NEN, NEB, parseAuditFileIntoAuditsArray, \
    parseAssertionsIntoAssertionList, parseApparentWinnersAndLosers, storeNEBAssertionsInArray, storeNENAssertionsInDict


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
        (auditsArray, IsRLALogFile) = parseAuditFileIntoAuditsArray(auditfile)
        assert IsRLALogFile == False
        assert len(auditsArray) == 1

        (apparentWinnerID, apparentWinner, apparentNonWinnerIDs, apparentNonWinners, candidateList) \
            = parseApparentWinnersAndLosers(auditsArray[0], candidatefile, IsRLALogFile)
        assert apparentWinner == "SUZY LOFTUS"
        assert apparentNonWinners == [('45', 'Write-in'), ('16', 'LEIF DAUTCH'), ('17', 'NANCY TUNG'), ('18', 'CHESA BOUDIN')]

        #assertionDict = parseAssertionsIntoDict(auditsArray[0],IsRLALogFile)
        (NENList, NEBList) = parseAssertionsIntoAssertionList(auditsArray[0],IsRLALogFile)
        NEBArray = storeNEBAssertionsInArray(NEBList, candidateList)
        NENDict = storeNENAssertionsInDict(NENList)
        print(NENList)
        print(NEBList)
        print(NEBArray)
        print(NENDict)

    simpleTestAudit = {
        'contest': '339',
        'winner': '15',
        'eliminated': ['16', '17'],
        'Expected Polls (#)': '71',
        'Expected Polls (%)': '1',
        'assertions': [
            {'winner': '15', 'loser': '16', 'already_eliminated': ['17'], 'assertion_type': 'IRV_ELIMINATION', 'explanation': 'Rules out outcomes with tail [... 15 16]'},
            {'winner': '15', 'loser': '17', 'already_eliminated': ['16'], 'assertion_type': 'IRV_ELIMINATION', 'explanation': 'Rules out outcomes with tail [... 15 17]'},
            {'winner': '15', 'loser': '17', 'already_eliminated': [], 'assertion_type': 'IRV_ELIMINATION', 'explanation': 'Rules out outcomes with tail [... 15 x x]'}
            ]}

    cands = frozenset(simpleTestAudit["eliminated"] + [simpleTestAudit["winner"]])
    ExpectedNENList = [NEN('15', '16', ['17'], cands), NEN('15', '17', ['16'], cands), NEN('15', '17', [], cands)]
    def test_parseNENAssertionsIntoAssertionList(self):
        audit = self.simpleTestAudit
        (NENList, NEBList) = parseAssertionsIntoAssertionList(audit, False, self.cands)
        assert NEBList == []

        # The lists don't actually need to be in the same order for the output to be correct.
        # Nevertheless, the way its implemented does produce the same order, and I can't
        # get a set-equality sort of operator to work.
        assert NENList == self.ExpectedNENList

    def test_storeNENAssertionsInDict(self):
        assertionDict = storeNENAssertionsInDict(self.ExpectedNENList)

        assert frozenset({'16', '15'}) in assertionDict
        assert frozenset({'15', '16'}) in assertionDict
        assert frozenset({'17', '15'}) in assertionDict
        assert frozenset({'15', '17'}) in assertionDict
        assert frozenset({'17', '16', '15'}) in assertionDict
        assert frozenset({'17', '15', '16'}) in assertionDict
        assert frozenset({'16', '17', '15'}) in assertionDict
        assert frozenset({'15', '17', '16'}) in assertionDict
        assert frozenset({'16', '15', '17'}) in assertionDict
        assert frozenset({'15', '16', '17'}) in assertionDict

        assert assertionDict[frozenset({'16', '15'})] == [NEN('15', '16', ['17'], self.cands)]
        assert assertionDict[frozenset({'17', '15'})] == [NEN('15', '17', ['16'], self.cands)]
        assert assertionDict[frozenset({'16', '17', '15'})] == [NEN('15', '17', [], self.cands)]

        assert len(assertionDict.keys()) == 3

    # This says that 17 has to be eliminated first, and then 15 wins when 17 is eliminated.
    ExpectedNENList2 = [NEN('15', '16', ['17'], cands), NEN('16', '17', [], cands), NEN('15', '17', [], cands)]

    # Tests the appending to lists when multiple NEN assertions have the same still-standing set.
    def test2_storeNENAssertionsInDict(self):
        assertionDict = storeNENAssertionsInDict(self.ExpectedNENList2)

        assert frozenset({'15', '16'}) in assertionDict
        assert frozenset({'16', '15'}) in assertionDict
        assert frozenset({'17', '16', '15'}) in assertionDict
        assert frozenset({'17', '15', '16'}) in assertionDict
        assert frozenset({'16', '17', '15'}) in assertionDict
        assert frozenset({'15', '17', '16'}) in assertionDict
        assert frozenset({'16', '15', '17'}) in assertionDict
        assert frozenset({'15', '16', '17'}) in assertionDict

        assert assertionDict[frozenset({'16', '15'})] == [NEN('15', '16', ['17'], self.cands)]

        # The order really isn't necessary, but they're not sortable.
        assert assertionDict[frozenset({'16', '17', '15'})] == [NEN('16', '17', [], self.cands), NEN('15', '17', [], self.cands)]

        assert len(assertionDict.keys()) == 2

    simpleNEBTestAudit = {
        'contest': '33',
        'winner': '9',
        'eliminated': ['3', '5'],
        'Expected Polls (#)': '71',
        'Expected Polls (%)': '1',
        'assertions': [{
                        "winner": "9",
                        "loser": "5",
                        "already_eliminated": "",
                        "assertion_type": "WINNER_ONLY",
                        "explanation": "Rules out case where 9 is eliminated before 5"
                },
                {
                        "winner": "9",
                        "loser": "3",
                        "already_eliminated": "",
                        "assertion_type": "WINNER_ONLY",
                        "explanation": "Rules out case where 9 is eliminated before 3"
                }
        ]}

    NEBTestCands = frozenset(simpleNEBTestAudit["eliminated"] + [simpleNEBTestAudit["winner"]])
    ExpectedNEBList = [NEB('9', '5'), NEB('9', '3')]

    def test_parseNEBAssertionsIntoAssertionList(self):
        audit = self.simpleNEBTestAudit
        (NENList, NEBList) = parseAssertionsIntoAssertionList(audit, False, self.NEBTestCands)

        assert NEBList == self.ExpectedNEBList
        assert NENList == []

    def test_storeNEBAssertionsInArray(self):
        NEBArray = storeNEBAssertionsInArray(self.ExpectedNEBList, self.NEBTestCands)
        assert NEBArray == [[False, False, False], [False, False, False], [True, True, False]]

##########################################################################################
if __name__ == "__main__":
    sys.exit(pytest.main(["-qq"], plugins=None))
