import string

import colorama
import numpy
from colorama import Fore, Style
import functools
import warnings
from warnings import warn
from collections import namedtuple, Counter
from dataclasses import dataclass

from shangrla.IRVVisualisationUtils import printTuple, findCandidateName, findListCandidateNames

# A not-eliminated-before assertion, also sometimes called winner-only.
# Asserts that winner's first preferences are greater than any mentions of loser not preceded by winner.
class NEB:
    def __init__(self, winner, loser):
        # The winner of the assertion
        self.winner = winner
        # The loser of the assertion
        self.loser = loser
        # Whether proved (by RLA) or not. T/F
        self.proved = False
        # Human-readable description of the assertion. Used as an index into the assertions dict in Audit.py
        self.handle = "" + winner + ' v ' + loser + ' '

    def __eq__(self,other):
        return self.winner == other.winner and self.loser == other.loser

# A Not-eliminated-next assertion, also sometimes called an IRV assertion.
# asserts that winner > loser when elim is the eliminated set, out of a whole candidate list cands.
# also stores the still-continuing set, which is simply cands - elim.
class NEN:
    def __init__(self, winner, loser, elim, cands):
        # The winner of the assertion
        self.winner = winner
        # The loser of the assertion
        self.loser = loser
        # Whether proved (by RLA) or not. T/F
        self.proved = False
        # Human-readable description of the assertion. Used as an index into the assertions dict in Audit.py
        self.handle = "" + winner + ' v ' + loser + ' ' + ('elim ' + ' '.join(elim))
        # set of already-eliminated candidates
        self.elim = elim
        # set of continuing candidates
        self.continuing = frozenset(cands.difference(elim))


    def __eq__(self,other):
        return self.winner == other.winner \
            and self.loser == other.loser \
            and Counter(self.elim) == Counter(other.elim) \
            and self.continuing == other.continuing

def validate_and_visualise_assertions(auditfile, candidatefile):
    (auditsArray, IsRLALogFile) = parseAuditFileIntoAuditsArray(auditfile)
    for audit in auditsArray:
        (apparentWinnerID, apparentWinner, apparentNonWinnersIDs, apparentNonWinners, candidates) \
            = parseApparentWinnersAndLosers(audit, candidatefile, IsRLALogFile)
        printApparentWinnersAndLosers(apparentWinner, apparentNonWinners)

        (NENList, NEBList) = parseAssertionsIntoAssertionList(audit, IsRLALogFile, candidates)
        NEBArray = storeNEBAssertionsInArray(NEBList, candidates)
        NENDict = storeNENAssertionsInDict(NENList)
        valid = validate_assertion_set(NEBArray, NENDict, apparentNonWinners, apparentWinner)
        print('That set of assertions does ')
        if not valid:
            print('not ')
        s = 'imply that ' + apparentWinner + ' won.'
        print(s)


# check whether a set of assertions implies that apparent_winner won.
# Returns the lexicographically-first counterexample if counterexamples exist.
# Otherwise the assertions are valid - returns an empty sequence.
def validate_assertion_set(NEBArray, NENDict, apparentNonWinners, apparentWinner):
    return False



# Decide whether a proposed elimination of candidate elim_candidate given a still continuing candidate set is
# pruned by assertion
def can_prune(elim_candidate, assertion, continuing_set):

    match assertion:
        case NEB(w,l):
            # If l is still continuing, NEB(w,l) says w can never be eliminated
            assert isinstance(l, object)
            return w == elim_candidate and l in continuing_set
        case NEN:
            # An NEN assertion applies only if the still-continuing set exactly matches
            return NEN.winner == elim_candidate and NEN.continuing == continuing_set


# Parses a json file containing assertions.
# A copy of parseAssertions from IRVVisualisationUtils.
# Complicated by the fact that we have two slightly different
# formats, one produced by RAIRE and the other as a log file
# of the audit process.  Some of the field names are slightly
# different.

def parseAuditFileIntoAuditsArray(auditfile):
    IsRLALogfile = False
    auditsArray = []


    if 'seed' in auditfile:
        # Assume this is formatted like a log file from assertion-RLA.
        IsRLALogfile = True
        for contestNum in auditfile["contests"]:
            contest = auditfile["contests"][contestNum]

            if contest["choice_function"] == "IRV":
                auditsArray.append(contest)
            else:
                warn("IRV Visualisations: visualising a non-IRV assertion set.")

            if len(contest["reported_winners"]) != 1:
                warn("IRV contest with either zero or >1 winner")

    else:
        # Assume this is formatted like the assertions output from RAIRE
        auditsArray = auditfile["audits"]

    return (auditsArray,IsRLALogfile)


## FIXME. Looks like the RLA  log file has only names, not candidate numbers??
## So is 'apparentWinner' a number if it's RAIRE and a name if it's an RLA log file??
## Should we just use strings/names from now on??
def parseApparentWinnersAndLosers(audit,candidatefile,IsRLALogFile):

    if(IsRLALogFile):
        apparentWinner = audit["reported_winners"][0]
        print("apparentWinner = " + apparentWinner)

        # SHANGRLA log files list all candidates including the winner
        candidateList = audit["candidates"]
        print("candidates = " + candidateList)

        #FIXME apparentWInnerIDs aren't defined...
        apparentNonWinners = candidateList.copy()
        apparentNonWinners.remove(apparentWinner)
        # apparentNonWinners = audit["candidates"].remove(apparentWinner)
        print("apparent Non Winners: " + str(apparentNonWinners))
        # assertions = audit["assertion_json"]

    else:
        # Assume this is formatted like the assertions output from RAIRE
        apparentWinnerID = audit["winner"]
        apparentNonWinnersIDs = audit["eliminated"]
        candidateList = apparentNonWinnersIDs + apparentWinnerID

        apparentWinner = findCandidateName(apparentWinnerID, candidatefile)

        apparentNonWinners = findListCandidateNames(apparentNonWinnersIDs, candidatefile)

    # FIXME It would be nice if the candidate list could be immutable (and ordered).
    # immutableCandidateIDs = numpy.empty(range(candidateList), string)
    # for i in range(candidateList):
    #    immutableCandidateIDs[i] = candidateList[i]
    # immutableCandidateIDs.flags.writeable = False

    return(apparentWinnerID, apparentWinner, apparentNonWinnersIDs, apparentNonWinners, candidateList)

def printApparentWinnersAndLosers(apparentWinner, apparentNonWinners):
    print("apparent Winner: " + apparentWinner)
    print("apparent Non Winners: " + str(apparentNonWinners))

# Parses an audit record, which is either RAIRE assertions or a SHANGRLA audit log,
# and returns a pair of lists: one with the NEB/WO assertions,
# the other with the NEN/IRV assertions.
def parseAssertionsIntoAssertionList(audit,IsRLALogfile, cands):
    NEBAssertionList = []
    NENAssertionList = []

    if IsRLALogfile:
        # SHANGRLA log file format
        assertions = audit["assertion_json"]
    else:
        # RAIRE Assertion format
        assertions = audit["assertions"]

    for a in assertions:
        if a["assertion_type"] == "IRV_ELIMINATION":
            elim = [e for e in a['already_eliminated']]
            new_assertion = NEN(a['winner'],a['loser'], elim, cands)
            NENAssertionList.append(new_assertion)
        else:
            new_assertion = NEB(a['winner'],a['loser'])
            NEBAssertionList.append(new_assertion)

        if IsRLALogfile:
        # We need to recreate the tags used by the assertion-RLA notebook to identify IRV
        # assertions.  Note that a WO assertion is tagged 'winner v loser '
        # but an IRVElim assertion with an empty already-eliminated set is tagged
        # 'winner v loser elim '
        #    handle = a["winner"] + ' v ' + a["loser"] + ' '

        #    if a["assertion_type"] == "IRV_ELIMINATION":
        #        elim = [e for e in a['already_eliminated']]
        #        handle += ('elim ' + ' '.join(elim))

            if ("proved" in audit):
                new_assertion.proved = audit["proved"][new_assertion.handle]
            else:
                warn("No proved information in log file - assuming all unconfirmed.")
                # Constructor makes all false by default.
                # proved = False

        else:
        # RAIRE Assertion format.
            if ("proved" in a) and (a["proved"] == "True"):
                new_assertion.proved = True
            else:
                new_assertion.proved = False

    return (NENAssertionList, NEBAssertionList)

# Stores assertions in two ways that should make lookup easy later:
# 1. NEN/IRV assertions are stored in a hashtable, with the 'still standing' set as the key.
# 2. NEB/WO assertions are stored in an n*n array for instant lookup:
# NEBArray(w,l) = True if we have the assertion NEB(w,l). Otherwise false.
def storeNENAssertionsInDict(NENAssertionList):

    assertionDict = {}

    for a in NENAssertionList:

        if a.continuing in assertionDict:
            # We already have this continuing-set - add to the set of two-candidate comparisons we know
            assertionDict[a.continuing].append(a)
        else:
            # Add a new value for this winner in the dictionary, with singleton set for this assertion
            assertionDict[a.continuing] = [a]

    return assertionDict

def storeNEBAssertionsInArray(NEBAssertionList, candidates):

    n = len(candidates)

    # NEBArray[w][l] is true if we have an assertion NEB(w,l)
    NEBArray = [[False] * n] * n

    for a in NEBAssertionList:
        wIndex = candidates.index(a.winner)
        lIndex = candidates.index(a.loser)
        NEBArray[wIndex][lIndex] = True

    return NEBArray





# Organise the assertions into a data structure which makes it easy to figure out whether a proposed elimination
# step is excluded.
# Assumes json assertions
# The dictionary is indexed by winner w (which will be the candidate we're thinking of eliminating)
# each value has two sets:
# - the NEB assertions with w as the winner
# - the NEN assertions with w as the winner
# we will need to look through these whenever we are considering pruning an edge.
# FIXME Pay attention to whether they're proved or not - this should be part of the data structure. Also add handles
# as above.
def parse_assertions(assertions):
    assertionDict = {}

    for a in assertions:
        if a.winner in assertionDict:
            # We already have this winner - add to the set of situations where they win
            assertionDict[a.winner].add(a)
        else:
            # Add a new value for this winner in the dictionary, with singleton set for this assertion
            assertionDict[a.winner] = {a}

    return assertionDict
