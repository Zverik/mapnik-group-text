#!/usr/bin/env python
import sys
import argparse
from lxml import etree


def parse_tree(tree, options):
    def sign(x):
        return -1 if x < 0 else 1

    if 'dmax' not in options:
        options['dmax'] = 20
    if 'verbose' not in options:
        options['verbose'] = False
    if 'single' not in options:
        options['single'] = False
    if 'group' not in options:
        options['group'] = True

    nsm = {'svg': 'http://www.w3.org/2000/svg', 'xlink': 'http://www.w3.org/1999/xlink'}
    xlhref = '{%s}href' % nsm['xlink']

    # Build list of spaces
    spaces = []
    for sympath in tree.findall('svg:defs/svg:g/svg:symbol/svg:path', nsm):
        if sympath.attrib['d'] == '':
            spaces.append('#'+sympath.iterancestors().next().attrib['id'])
    spaces = set(spaces)

    # Find the first letter
    search = 'svg:g/svg:g/svg:use[@x]' if options['group'] else 'svg:g/svg:use[@x]'
    glyph = tree.find(search, nsm)
    while glyph is not None:
        # Find word starting with letter glyph
        curg = glyph.iterancestors().next()
        word = [curg]
        lcnt = 0 if glyph.attrib[xlhref] in spaces else 1
        p = (float(glyph.attrib['x']), float(glyph.attrib['y']))
        linep = p
        for nxt in curg.itersiblings():
            nxtuse = nxt.find('svg:use[@x]', nsm)
            if (nxtuse is None or xlhref not in nxtuse.attrib
                    or not nxtuse.attrib[xlhref].startswith('#glyph')):
                break
            pp = (float(nxtuse.attrib['x']), float(nxtuse.attrib['y']))
            if abs(p[0]-pp[0]) + abs(p[1]-pp[1]) > options['dmax']:
                # Maybe it's the next line
                if options['single'] or abs(linep[0]-pp[0]) + abs(linep[1]-pp[1]) > options['dmax']:
                    break
                linep = pp
            p = pp
            word.append(nxt)
            if nxtuse.attrib[xlhref] not in spaces:
                lcnt += 1

        # We have our word, now check for casing
        casing = []
        lcasing = 0
        for path in curg.itersiblings(preceding=True):
            if (path.tag != '{%s}path' % nsm['svg'] or 'style' not in path.attrib
                    or 'stroke-linecap:butt;stroke-linejoin:round;' not in path.attrib['style']):
                break
            casing.insert(0, path)
            if path.attrib['d'] != '':
                lcasing += 1
            if lcasing == lcnt:
                break
        if lcasing < lcnt:
            casing = []

        if options['verbose']:
            print glyph.attrib[xlhref], len(word), lcnt, len(casing)

        # Enclose casing and word in a group
        group = etree.Element('{%s}g' % nsm['svg'])
        word[-1].addnext(group)
        for c in casing:
            group.append(c)
        for w in word:
            group.append(w)

        # Find the first unenveloped letter (that is, the next one)
        glyph = tree.find(search, nsm)


def process_stream(inp, out, options):
    tree = etree.parse(inp)
    inp.close()
    parse_tree(tree, options)
    tree.write(sys.stdout if out == '-' else out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Group letters in mapnik-generated SVG')
    parser.add_argument('inp', type=argparse.FileType('r'), metavar='input',
                        help='input svg file ("-" for stdin)')
    parser.add_argument('output', nargs='?', default='-',
                        help='output svg file (can be the same as input, default is stdout)')
    parser.add_argument('-d', dest='dmax', type=int, default='20',
                        help='maximum distance between glyph start points in a word (default=20)')
    parser.add_argument('-s', dest='single', action='store_true',
                        help='do not attempt detecting multi-line labels')
    parser.add_argument('-g', dest='group', action='store_false',
                        help='vector data is not grouped', default=True)
    parser.add_argument('-v', dest='verbose', action='store_true',
                        help='display debug information')
    options = parser.parse_args()
    process_stream(options.inp, options.output, vars(options))
