#!/usr/bin/python2.5
#

"""This module represents what people have voted for."""

import unittest
import logging
import operator


class Question(object):
  """Base class for all questions."""

  def Calculate(self, votes):
    """Calculate the winners for the questions.

    Args:
      votes: A complete list of people's votes.

    Returns:
      A list of the winners in the order that they won.
    """
    raise NotImplemented()


class ListQuestion(object):
  """Base class for all questions which have a list of options."""

  def __init__(self, question, options, winners=1):
    """
    Args:
      question: The question to ask.
      options: The options which people should pick from.
      winners: The number of winners.
    """
    self.question = question
    self.options = options
    self.winners = winners

  def Count(self, votes, toignore=[]):
    """Counts the number of votes for each choice.

    Args:
      toignore: Choices which will be removed from a vote before the values are
                summed.

    Returns a dictionary of
      {'choice': [number of first choice,
                  number of second,
                  ....]}
    """
    sum = {}
    for vote in votes:
      # Remove people we are ignoring
      for i in toignore:
        if i in vote:
          vote.remove(i)

      # Work out the votes
      for i, choice in enumerate(vote):
        if choice not in sum:
          sum[choice] = [0]*len(self.options)

        sum[choice][i] += 1

    return sum


class Plurality(ListQuestion):
  """Question is decided by a simple highest number of votes wins.

  Voters select a single candidate from a list.

  This system is also often called "first past the post" or "furthest past the
  post".
  """

  def Calculate(self, votes):
    choices = self.Count(votes).items()
    choices.sort(key=operator.itemgetter(1))
    return [choices[0]]


class InstantRunOff(ListQuestion):
  """Question is decided by a run-off system, "most supported" option wins.

  Voters rank the list of candidates from most preferred to least preferred.

  If no candidate is the first preference of a majority of voters, the candidate
  with the fewest number of first preference rankings is eliminated and that
  candidate's ballots are redistributed at full value to the remaining
  candidates according to the next ranking on each ballot. This process is
  repeated until one candidate obtains a majority of votes among candidates not
  eliminated.

  This system is also often called "preferential voting" or "alternative
  voting".
  """

  def Calculate(self, votes):
    """
    """

    # This contains a list of people who are no longer able to win
    alreadylost = []

    while True:
      sum = self.Count(votes, toignore=alreadylost)

      winners = sum.items()
      winners.sort(key=operator.itemgetter(1))

      logging.info("Rankings %s", winners)

      if len(winners) <= self.winners:
        return zip(*winners)[0][::-1]

      # The person who has the least votes becomes an invalid choice
      alreadylost.append(winners.pop(0)[0])
      logging.info("%s just got knocked out", alreadylost[-1])


class InstantRunOffTest(unittest.TestCase):

  def testCalculate(self):
    t = "Tom"
    d = "Dick"
    h = "Harry"

    question = InstantRunOff("Who do you like more?", [t, d, h])

    # Single vote, Tom wins
    self.assert_((t,), question.Calculate([
        [t, d, h]
      ]))

    # Tom has the most first preferences
    self.assert_((t,), question.Calculate([
        [t, d, h],
        [t, d, h],
        [d, t, h],
      ]))

    # No clear winner in the first round
    #   Harry has the least number of votes so is eliminated.
    # Tom wins the second round
    self.assert_((t,), question.Calculate([
        [t, h, d],
        [t, h, d],
        [d, t, h],
        [d, t, h],
        [h, t, d],
      ]))

    # No clear winner in the first round.
    #   Harry is eliminated as he has the the least weighted votes.
    # Tom wins the second round.
    self.assert_((t,), question.Calculate([
        [t, d, h],
        [d, t, h],
        [h, t, d],
      ]))

    self.assert_((d,), question.Calculate([
        [t, d, h],
        [t, h, d],
        [d, h, t],
        [d, h, t],
        [h, d, t],
      ]))

  def _testCalculateDraw(self):
    # Draws...
    self.assert_((t,), question.Calculate([
        [t, h, d],
        [t, h, d],
        [h, t, d],
      ]))

    self.assert_((d,), question.Calculate([
        [t, d, h],
        [t, d, h],
        [h, d, t],
        [h, d, t],
      ]))


class Positional(Question):
  """Question is decided by a weighted sum of preferences.

  Voters rank the list of candidates from most preferred to least preferred.

  Candidates get points for the different positions. The candidate with the most
  points wins.
  """
  pass


if __name__ == '__main__':
    unittest.main()
