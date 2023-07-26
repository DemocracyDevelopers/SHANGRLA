import colorama
from colorama import Fore, Style
import functools
import warnings
from warnings import warn
from collections import namedtuple

from shangrla.IRVVisualisationUtils import printTuple, findCandidateName, findListCandidateNames

# A not-eliminated-before assertion, also sometimes called winner-only.
# Asserts that winner's first preferences are greater than any mentions of loser not preceded by winner.
class NEB:
    def __new__(self, winner, loser):
        # The winner of the assertion
        self.winner = winner
        # The loser of the assertion
        self.loser = loser
        # Whether proved (by RLA) or not. T/F
        self.proved = False
        # Human-readable description of the assertion. Used as an index into the assertions dict in Audit.py
        self.handle = "" + winner + ' v ' + loser + ' '

        return self

# A Not-eliminated-next assertion, also sometimes called an IRV assertion.
# asserts that winner > loser when elim is the eliminated set, out of a whole candidate list cands.
# also stores the still-continuing set, which is simply cands - elim.
class NEN:
    def __new__(self, winner, loser, elim, cands):
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
        self.continuing = cands.difference(elim)

        return self

def validate_and_visualise_assertions(auditfile, candidatefile):
    (auditsArray, IsRLALogFile) = parseAuditFileIntoAuditsArray(auditfile, candidatefile)
    for audit in auditsArray:
        printApparentWinnersAndLosers(audit, candidatefile, IsRLALogFile)
        validate_assertion_set(audit)


# check whether a set of assertions implies that apparent_winner won.
# Returns the lexicographically-first counterexample if counterexamples exist.
# Otherwise the assertions are valid - returns an empty sequence.
def validate_assertion_set(audit):
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

def parseAuditFileIntoAuditsArray(auditfile, candidatefile):
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
def parseAssertionsAndApparentWinnersAndLosers(audit,candidatefile,IsRLALogFile):

    if(IsRLALogFile):
        apparentWinner = audit["reported_winners"][0]
        print("apparentWinner = " + apparentWinner)
        print("candidates = " + str(audit["candidates"]))
        apparentNonWinners = audit["candidates"].copy()
        apparentNonWinners.remove(apparentWinner)
        # apparentNonWinners = audit["candidates"].remove(apparentWinner)
        print("apparent Non Winners: " + str(apparentNonWinners))
        assertions = audit["assertion_json"]

    else:
        # Assume this is formatted like the assertions output from RAIRE
        apparentWinnerNumber = audit["winner"]
        apparentNonWinnersIDs = audit["eliminated"]
        assertions = audit["assertions"]

        apparentWinner = findCandidateName(apparentWinnerNumber, candidatefile)
        # print("Apparent winner: " + "\n" + printTuple((apparentWinner, apparentWinnerName)))

        apparentNonWinners = findListCandidateNames(apparentNonWinnersIDs, candidatefile)
        #apparentNonWinnersWithNames = findListCandidateNames(apparentNonWinners, candidatefile)
        #print("Apparently eliminated:")
        #print(",\n".join(list(map(printTuple, apparentNonWinnersWithNames))))
        #print("\n")

    return(assertions,apparentWinner,apparentNonWinners)

def printApparentWinnersAndLosers(apparentWinner, apparentNonWinners):
    print("apparentWinner = " + apparentWinner)
    print("apparent Non Winners: " + str(apparentNonWinners))

def parseAssertionsIntoDict(audit,IsRLALogfile):
    assertionDict = {}

    if IsRLALogfile:
        assertions = audit["assertion_json"]
    else:
        # RAIRE Assertion format
        assertions = audit["assertions"]

    for a in assertions:
        if a["assertion_type"] == "IRV_ELIMINATION":
            elim = [e for e in a['already_eliminated']]
            cands = {c for c in audit['eliminated']}
            new_assertion = NEN(a['winner'],a['loser'], elim, cands)
        else:
            new_assertion = NEB(a['winner'],a['loser'])

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

        if new_assertion.winner in assertionDict:
        # We already have this winner - add to the set of situations where they win
            assertionDict[new_assertion.winner].append(new_assertion)
        else:
        # Add a new value for this winner in the dictionary, with singleton set for this assertion
            singletonAssertionSet = [a]
            assertionDict[new_assertion.winner] = singletonAssertionSet
        # assertionDict = parse_assertions(assertions)

    return assertionDict

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
