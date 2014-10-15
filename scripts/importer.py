#!/usr/bin/env python3

# Copyright 2014 Claude (longneck) <longneck@scratchbook.ch>

# This file is part of qutebrowser.
#
# qutebrowser is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# qutebrowser is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with qutebrowser.  If not, see <http://www.gnu.org/licenses/>.


"""Tool to import data from other browsers.

Currently only importing bookmarks from Chromium is supported.
"""


import argparse


def main():
    """Main entry point."""
    args = get_args()
    if args.browser == 'chromium':
        import_chromium(args.bookmarks)


def get_args():
    """Get the argparse parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument('browser', help="Which browser?", choices=['chromium'],
                        metavar='browser')
    parser.add_argument('bookmarks', help="Bookmarks file")
    args = parser.parse_args()
    return args


def import_chromium(bookmarks_file):
    """Import bookmarks from a HTML file generated by Chromium."""
    import bs4

    soup = bs4.BeautifulSoup(open(bookmarks_file, encoding='utf-8'))

    html_tags = soup.findAll('a')

    bookmarks = []
    for tag in html_tags:
        if tag['href'] not in bookmarks:
            bookmarks.append('{tag.string} {tag[href]}'.format(tag=tag))

    for bookmark in bookmarks:
        print(bookmark)


if __name__ == '__main__':
    main()
