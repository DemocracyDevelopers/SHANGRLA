import colorama
from colorama import Fore, Style
import functools
import warnings
from warnings import warn
from collections import namedtuple


# A not-eliminated-before assertion, also sometimes called winner-only.
# Asserts that winner's first preferences are greater than any mentions of loser not preceded by winner.
NEB = namedtuple('NEB', 'winner, loser')

# A Not-eliminated-next assertion, also sometimes called an IRV assertion.
# asserts that winner > loser when elim is the eliminated set, out of a whole candidate list cands.
# also stores the still-standing set, which is simply cands - elim.
class NEN:
    def __new__(self, winner, loser, elim, cands):
        self.winner = winner
        self.loser = loser
        self.elim = elim
        self.standing = cands.difference(elim)

        return self

# Organise the assertions into a data structure which makes it easy to figure out whether a proposed elimination
# step is excluded.
# Assumes json assertions
# The dictionary is indexed by winner w (which will be the candidate we're thinking of eliminating)
# each value has two sets:
# - the NEB assertions with w as the winner
# - the NEN assertions with w as the winner
# we will need to look through these whenever we are considering pruning an edge.
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

# Decide whether a proposed elimination of candidate elim_candidate given a still standing candidate set is excluded by
# assertion
def can_exclude(elim_candidate, assertion, standing_set):

    match assertion:
        case NEB(w,l):
            # If l is still standing, NEB(w,l) says w can never be eliminated
            assert isinstance(l, object)
            return w == elim_candidate and l in standing_set
        case NEN:
            # An NEN assertion applies only if the still-standing set exactly matches
            return NEN.winner == elim_candidate and NEN.standing == standing_set