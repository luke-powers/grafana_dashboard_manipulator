'''
Shunting algorithm for reverse polish notation
http://rosettacode.org/wiki/Parsing/Shunting-yard_algorithm#Python

and

rpn parser
http://danishmujeeb.com/blog/2014/12/parsing-reverse-polish-notation-in-python
'''
from collections import namedtuple
from copy import deepcopy
import simplejson as json
import re

GRAFANA_OPERATIONS = ['absolute',
                      'alias',
                      'aliasByMetric',
                      'aliasByNode',
                      'aliasSub',
                      'asPercent',
                      'averageAbove',
                      'averageBelow',
                      'averageSeries',
                      'averageSeriesWithWildcards',
                      'cactiStyle',
                      'changed',
                      'consolidateBy',
                      'constantLine',
                      'countSeries',
                      'cumulative',
                      'currentAbove',
                      'currentBelow',
                      'derivative',
                      'diffSeries',
                      'divideSeries',
                      'exclude',
                      'grep',
                      'group',
                      'groupByNode',
                      'highestAverage',
                      'highestCurrent',
                      'highestMax',
                      'hitcount',
                      'holtWintersAberration',
                      'holtWintersConfidenceBands',
                      'holtWintersForecast',
                      'integral',
                      'isNonNull',
                      'keepLastValue',
                      'limit',
                      'log',
                      'lowestAverage',
                      'lowestCurrent',
                      'mapSeries',
                      'maxSeries',
                      'maximumAbove',
                      'maximumBelow',
                      'minSeries',
                      'minimumAbove',
                      'minimumBelow',
                      'mostDeviant',
                      'movingAverage',
                      'movingMedian',
                      'multiplySeries',
                      'nPercentile',
                      'nonNegativeDerivative',
                      'offset',
                      'offsetToZero',
                      'perSecond',
                      'percentileOfSeries',
                      'randomWalk',
                      'rangeOfSeries',
                      'reduceSeries',
                      'removeAbovePercentile',
                      'removeAboveValue',
                      'removeBelowPercentile',
                      'removeBelowValue',
                      'removeEmptySeries',
                      'scale',
                      'scaleToSeconds',
                      'smartSummarize',
                      'sortByMaxima',
                      'sortByMinima',
                      'sortByName',
                      'sortByTotal',
                      'stacked',
                      'stdev',
                      'substr',
                      'sumSeries',
                      'sumSeriesWithWildcards',
                      'summarize',
                      'timeShift',
                      'timeStack',
                      'transformNull',
                      'useSeriesAbove',
                      'weightedAverage']


OP_INFO = namedtuple('OP_INFO', 'prec assoc')
LEFT, RIGHT = 'Left Right'.split()

OPS = {
 '^': OP_INFO(prec=4, assoc=RIGHT),
 '*': OP_INFO(prec=3, assoc=LEFT),
 '/': OP_INFO(prec=3, assoc=LEFT),
 '+': OP_INFO(prec=2, assoc=LEFT),
 '-': OP_INFO(prec=2, assoc=LEFT),
 '(': OP_INFO(prec=9, assoc=LEFT),
 ')': OP_INFO(prec=0, assoc=LEFT),
 }

NUM, LPAREN, RPAREN = 'NUMBER ( )'.split()


def get_input(inp = None):
    '''Inputs an expression and returns list of (TOKENTYPE, tokenvalue).

    '''

    if inp is None:
        inp = input('expression: ')
    tokens = inp.strip().split()
    tokenvals = []
    for token in tokens:
        if token in OPS:
            tokenvals.append((token, OPS[token]))
        else:
            tokenvals.append((NUM, token))
    return tokenvals


def shunting(tokenvals):
    outq, stack = [], []
    table = ['TOKEN,ACTION,RPN OUTPUT,OP STACK,NOTES'.split(',')]
    for token, val in tokenvals:
        note = action = ''
        if token is NUM:
            action = 'Add token to output'
            outq.append(val)
            table.append((val, action, ' '.join(outq), ' '.join(s[0] for s in stack), note))
        elif token in OPS:
            t1, (p1, a1) = token, val
            v = t1
            note = 'Pop OPS from stack to output'
            while stack:
                t2, (p2, a2) = stack[-1]
                if (a1 == LEFT and p1 <= p2) or (a1 == RIGHT and p1 < p2):
                    if t1 != RPAREN:
                        if t2 != LPAREN:
                            stack.pop()
                            action = '(Pop op)'
                            outq.append(t2)
                        else:
                            break
                    else:
                        if t2 != LPAREN:
                            stack.pop()
                            action = '(Pop op)'
                            outq.append(t2)
                        else:
                            stack.pop()
                            action = '(Pop & discard "(")'
                            table.append((v, action, ' '.join(outq),
                                          ' '.join(s[0] for s in stack), note))
                            break
                    table.append((v, action, ' '.join(outq), ' '.join(s[0] for s in stack), note))
                    v = note = ''
                else:
                    note = ''
                    break
                note = ''
            note = ''
            if t1 != RPAREN:
                stack.append((token, val))
                action = 'Push op token to stack'
            else:
                action = 'Discard ")"'
            table.append((v, action, ' '.join(outq), ' '.join(s[0] for s in stack), note))
    note = 'Drain stack to output'
    while stack:
        v = ''
        t2, (p2, a2) = stack[-1]
        action = '(Pop op)'
        stack.pop()
        outq.append(t2)
        table.append((v, action, ' '.join(outq), ' '.join(s[0] for s in stack), note))
        v = note = ''
    return table


def parse_rpn_to_grafana_functions(expression):
    '''Evaluate a reverse polish notation.

    Modified from:
    http://danishmujeeb.com/blog/2014/12/parsing-reverse-polish-notation-in-python
    '''

    stack = []

    for val in expression.split(' '):
        if val in ['-', '+', '*', '/']:
            op1 = stack.pop()
            op2 = stack.pop()
            value, scaler = (op1, op2) if is_number(op2) else (op2, op1)
            if val == '-':
                if is_number(op1) or is_number(op2):
                    result = 'offset(%s, %s)' % (value, '-'+scaler)
                else:
                    result = 'diffSeries(%s, %s)' % (op2, op1)
            if val == '+':
                if is_number(op1) or is_number(op2):
                    result = 'offset(%s, %s)' % (value, scaler)
                else:
                    result = 'sumSeries(%s, %s)' % (op2, op1)
            if val == '*':
                if is_number(op1) or is_number(op2):
                    result = 'scale(%s, %s)' % (value, scaler)
                else:
                    result = 'multiplySeries(%s, %s)' % (op2, op1)
            if val == '/':
                if is_number(op1) or is_number(op2):
                    result = 'scale(%s, %s)' % (value, float(1/float(scaler)))
                else:
                    result = 'divideSeries(%s, %s)' % (op2, op1)
            stack.append(result)
        else:
            stack.append(val)

    return stack.pop()


def convert_infix_to_grafana(infix_string):
    '''Convert the given infix_string to a string using grafana's
    functions.

    http://danishmujeeb.com/blog/2014/12/parsing-reverse-polish-notation-in-python
    '''
    # If grafana operators are already in the string, just return it.
    for op in GRAFANA_OPERATIONS:
        if op in infix_string:
            return infix_string
    rp = shunting(get_input(' '.join(re.split(r'([+\-/*()])', infix_string))))
    return parse_rpn_to_grafana_functions(rp[-1][2])


def is_number(st):
    '''Check if a number is either an integer or a float.

    '''
    if st.isdigit():
        return True
    else:
        try:
            float(st)
            return True
        except ValueError:
            return False


def json_obj_to_grafana_target(json_object):
    '''Given a json object with a valid grafana json object, return a
    grafana path string.

    '''
    return json.dumps(json_object).replace('": [{"',
                                           '(').replace(']}',
                                                        ')').replace('": ["',
                                                                     '(').replace('"',
                                                                                  '').strip('{')


def grafana_target_to_json_obj(grafana_string):
    '''Given a grafana path, return a jsonable python object.

    '''
    functions = []
    name, _, working = grafana_string.partition('(')
    stack = []
    splitters = [')', '(']
    splitter = splitters.pop()
    while working:
        if name in GRAFANA_OPERATIONS:
            functions.append(name)
        else:
            stack.append(name)
        name, _, working = working.partition(splitter)
        if not working and splitters:
            splitter = splitters.pop()
            working = name
            name, _, working = working.partition(splitter)
        if not working and not splitters:
            stack.append(name)
    prev = None
    for f in functions[::-1]:
        struct = {}
        struct[f] = []
        if prev:
            struct[f].append(deepcopy(prev))
        struct[f] += [x for x in stack.pop(0).split(', ') if x]
        prev = deepcopy(struct)
    return struct


def test_convert_infix_to_grafana():
    tests = (
        {'args': "testA + 100",
         'expected': "offset(testA, 100)"},
        {'args': "testA + testB",
         'expected': "sumSeries(testA, testB)"},
        {'args': "testA - 100",
         'expected': "offset(testA, -100)"},
        {'args': "testA - testB",
         'expected': "diffSeries(testA, testB)"},
        {'args': "testA - testB - test1",
         'expected': "diffSeries(diffSeries(testA, testB), test1)"},
        {'args': "testA + testB + test1",
         'expected': "sumSeries(sumSeries(testA, testB), test1)"},
        {'args': "testA * testB * test1",
         'expected': "multiplySeries(multiplySeries(testA, testB), test1)"},
        {'args': "testA - testB * test1",
         'expected': "diffSeries(testA, multiplySeries(testB, test1))"},
        {'args': "testA + testB * test1",
         'expected': "sumSeries(testA, multiplySeries(testB, test1))"},
        {'args': "testA * testB",
         'expected': "multiplySeries(testA, testB)"},
        {'args': "testA * 100",
         'expected': "scale(testA, 100)"},
        {'args': "testA / testB",
         'expected': "divideSeries(testA, testB)"},
        {'args': "testA / testB / testC",
         'expected': "divideSeries(divideSeries(testA, testB), testC)"},
        {'args': "testA / 100",
         'expected': "scale(testA, 0.01)"},
        {'args': "(testA / testB) / 1000",
         'expected': "scale(divideSeries(testA, testB), 0.001)"},
        {'args': "((testA * test1) / testB) / 1000",
         'expected': "scale(divideSeries(multiplySeries(testA, test1), testB), 0.001)"},
        {'args': "((testA * test1 * test2) / testB / test3) / 1000",
         'expected': "scale(divideSeries(divideSeries(multiplySeries(multiplySeries(testA, test1), test2), testB), test3), 0.001)"},
        {'args': "((testA * test1 + test2 * test3) / testB / test4) / 1000",
         'expected': "scale(divideSeries(divideSeries(sumSeries(multiplySeries(testA, test1), multiplySeries(test2, test3)), testB), test4), 0.001)"},
    )

    for test in tests:
        res = convert_infix_to_grafana(test['args'])
        if res != test['expected']:
            raise Exception('test failed "%s" === "%s"' % (res, test['expected']))
        else:
            print 'passed %s === %s' % (res, test['expected'])


if __name__ == '__main__':
    test_convert_infix_to_grafana()
    print '''
Only the test cases are run from cli, import the module and use
there, namely convert_infix_to_grafana()'''
