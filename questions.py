#!/usr/bin/python2.5
#

"""This module represents what people have voted for."""

import copy
import unittest
import logging
import operator

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

def Votes(v):
  return list(enumerate(v))


def VotesTest(v, dieon):

  class DieList(list):
    def __getslice__(self, i, j):
      return DieList(list.__getslice__(self, i, j))

    def __iter__(self):
      for i, j in enumerate(list.__iter__(self)):
        if i == self.dieon:
          DieList.dieon = -1
          raise SystemError("Die!")
        yield j

    def __init__(self, l):
      list.__init__(self, l)

  DieList.dieon = dieon

  return DieList(enumerate(v))


class Question(object):
  """Base class for all questions."""

  class CalculateState(object):
    """Class which stores part of a Calculate method."""
    pass

  def Calculate(self, votes):
    """Calculate the winners for the questions.

    If an exception is raised the current state of the calculation should be
    saved in the self.state instance.

    Args:
      votes: A complete list of people's votes.

    Returns:
      A list of the winners in the order that they won.
    """
    raise NotImplemented()

  def Render(self, vote=None):
    """
    Render the question to HTML, if given a vote render that as selected.
    """
    raise NotImplemented()


class ListQuestion(Question):
  """Base class for all questions which have a list of options."""

  class State(object):
    __slots__ = ["voteid", "sum", "toignore"]

  def __init__(self, question, options, winners=1):
    """
    Args:
      question: The question to ask.
      options: The options which people should pick from.
      winners: The number of winners.
    """
    Question.__init__(self, question)

    self.options = options
    self.winners = winners

    self.state = self.State()


  def Count(self, votes, toignore=[]):
    self.CountSetup(votes, toignore)
    return self.CountContinue(votes)

  def CountSetup(self, votes, toignore=[]):
    """Counts the number of votes for each choice.

    Args:
      toignore: Choices which will be removed from a vote before the values are
                summed.

    Returns a dictionary of
      {'choice': [number of first choice,
                  number of second,
                  ....]}
    """
    self.state.voteid = -1
    self.state.sum = {}
    self.state.toignore = toignore

  def CountContinue(self, votes):
    """Method which continues to count from the previous given state."""
    sum = copy.copy(self.state.sum)
    offset = self.state.voteid

    for voteid, vote in votes[offset+1:]:
      # Remove people we are ignoring
      for i in self.state.toignore:
        if i in vote:
          vote.remove(i)

      # Work out the votes
      for i, choice in enumerate(vote):
        if choice not in sum:
          sum[choice] = [0]*len(self.options)

        sum[choice][i] += 1

      self.state.voteid = voteid
      self.state.sum = copy.copy(sum)

    return sum



class ListQuestionTest(unittest.TestCase):
  def testCount(self):
    t = "Tom"
    d = "Dick"
    h = "Harry"
    actual_votes = [(t,d,h), (t,d,h), (t,d,h), (t,d,h), (t,d,h)]

    # Test normal vote counting
    question = ListQuestion("testquestion", [t, d, h])
    results = question.Count(Votes(actual_votes))
    self.assertEqual({t: [5, 0, 0], d: [0, 5, 0], h: [0,0, 5]}, results)

    # Test incremental vote counting
    votes = VotesTest(actual_votes, 2)
    question.CountSetup(votes)
    try:
      question.CountContinue(votes)
      self.assert_(False)
    except SystemError, e:
      pass

    results = question.CountContinue(votes)
    self.assertEqual({t: [5, 0, 0], d: [0, 5, 0], h: [0,0, 5]}, results)



class Plurality(ListQuestion):
  """Question is decided by a simple highest number of votes wins.

  Voters select a single candidate from a list.

  This system is also often called "first past the post" or "furthest past the
  post".
  """

  def Calculate(self, votes):
    self.CountSetup(votes)
    self.CalculateContinue(votes)

  def CalculateContinue(self, votes):
    choices = self.CountContinue(votes).items()
    choices.sort(key=operator.itemgetter(1))
    return [choices[0]]

  def Render(self, vote):
    # Randomise the order of the choices
    return """
<p class="instructions">
 Select the candidate you wish to vote for.
</p>
<ul>
{% for choice in self.choice_set.all %}
  <li>
    <input type="radio" name="{{  }}" value="{{ choice }}"
      {% if vote == choice %}checked="checked"{% endif %} />
    {{ choice }}
  </li>
{% endfor %}
</ul>
"""


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

  class State(ListQuestion.State):
    __slots__ = ["voteid", "sum", "toignore", "alreadylost"]


  def Calculate(self, votes):
    self.CalculateSetup(votes)
    return self.CalculateContinue(votes)

  def CalculateSetup(self, votes):
    self.state.alreadylost = []
    self.CountSetup(votes)

  def CalculateContinue(self, votes):
    while True:
      sum = self.CountContinue(votes)

      winners = sum.items()
      winners.sort(key=operator.itemgetter(1))

      logging.info("Rankings %s", winners)

      if len(winners) <= self.winners:
        return zip(*winners)[0][::-1]

      # The person who has the least votes becomes an invalid choice
      self.state.alreadylost.append(winners.pop(0)[0])
      logging.info("%s just got knocked out", self.state.alreadylost[-1])

      self.CountSetup(votes, toignore=self.state.alreadylost)

  def Render(self, vote):
    # See http://jqueryui.com/demos/sortable/#empty-lists
    return """
<h2>{{ self.title }}</h2>
<p class="description">
 {{ self.description }}
</p>

<p class="instructions">
 Drag candidates from the list on the right to the list on the left in the order
 of preference.
</p>

<!-- Hidden fields which actually stores the results -->
<div id="{{ self.id }}">
{% for choice in vote %}
  <input type="text"
    name="{{ self.id }}[forloop.counter]"
    value="{{ choice }}" />
{% endfor %}
</div>

<!-- The candidates which have been ranked -->
<div>
<h3>Ranked Candidates</h3>
<ul id="{{ self.id }}-ranked">
{% for choice in vote %}
  <li>{{ choice }}</li>
{% endfor %}
</ul>
</div>

<!-- The possible candidates yet to be ranked -->
<div>
<h3><b>Un</b>ranked Candidates</h3>
<ul id="{{ self.id }}-unranked">
{% for choice in self.choices %}
  {% if choice in vote %}
    <li>{{ choice }}</li>
  {% endif %}
{% endfor %}
</ul>
</div>
"""

class InstantRunOffTest(unittest.TestCase):

  def testCalculateIncremental(self):
    t = "Tom"
    d = "Dick"
    h = "Harry"
    actual_votes = [[t,d,h], [t,d,h], [t,d,h], [t,d,h], [t,d,h]]

    question = InstantRunOff("testquestion", [t, d, h])

    # Test incremental vote counting
    votes = VotesTest(actual_votes, 2)
    question.CalculateSetup(votes)
    try:
      question.CalculateContinue(votes)
      self.assert_(False)
    except SystemError, e:
      logging.info("Exception: %s", e)

    votes = VotesTest(actual_votes, 3)
    try:
      question.CalculateContinue(votes)
      self.assert_(False)
    except SystemError, e:
      logging.info("Exception: %s", e)

    results = question.CalculateContinue(votes)
    self.assertEqual((t,), results)

  def testCalculateIncremental2(self):

    t = "Tom"
    d = "Dick"
    h = "Harry"
    actual_votes = [[t,d,h], [t,d,h], [d,t,h], [d,t,h], [h,t,d]]

    question = InstantRunOff("testquestion", [t, d, h])

    # Test incremental vote counting
    votes = VotesTest(actual_votes, 2)
    question.CalculateSetup(votes)
    try:
      question.CalculateContinue(votes)
      self.assert_(False)
    except SystemError, e:
      logging.info("Exception: %s", e)

    results = question.CalculateContinue(votes)
    self.assertEqual((t,), results)


  def _testCalculate(self):
    t = "Tom"
    d = "Dick"
    h = "Harry"

    question = InstantRunOff("Who do you like more?", [t, d, h])

    # Single vote, Tom wins
    self.assert_((t,), question.Calculate(Votes([
        [t, d, h]
      ])))

    # Tom has the most first preferences
    self.assert_((t,), question.Calculate(Votes([
        [t, d, h],
        [t, d, h],
        [d, t, h],
      ])))

    # No clear winner in the first round
    #   Harry has the least number of votes so is eliminated.
    # Tom wins the second round
    self.assert_((t,), question.Calculate(Votes([
        [t, h, d],
        [t, h, d],
        [d, t, h],
        [d, t, h],
        [h, t, d],
      ])))

    # No clear winner in the first round.
    #   Harry is eliminated as he has the the least weighted votes.
    # Tom wins the second round.
    self.assert_((t,), question.Calculate(Votes([
        [t, d, h],
        [d, t, h],
        [h, t, d],
      ])))

    self.assert_((d,), question.Calculate(Votes([
        [t, d, h],
        [t, h, d],
        [d, h, t],
        [d, h, t],
        [h, d, t],
      ])))

  def _testCalculateDraw(self):
    # Draws...
    self.assert_((t,), question.Calculate(Votes([
        [t, h, d],
        [t, h, d],
        [h, t, d],
      ])))

    self.assert_((d,), question.Calculate(Votes([
        [t, d, h],
        [t, d, h],
        [h, d, t],
        [h, d, t],
      ])))


class Positional(Question):
  """Question is decided by a weighted sum of preferences.

  Voters rank the list of candidates from most preferred to least preferred.

  Candidates get points for the different positions. The candidate with the most
  points wins.
  """
  pass


if __name__ == '__main__':
    unittest.main()
